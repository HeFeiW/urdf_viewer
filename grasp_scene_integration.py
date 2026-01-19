#!/usr/bin/env python3
"""
集成 lightning-grasp 和 show_urdf 的抓取生成和可视化脚本
使用 demo.py 中的标准调用方式
"""

import sys
import os
import json
import random
import argparse
import numpy as np
import torch
import trimesh

# Lightning-grasp imports (following demo.py style)
sys.path.append('/app/lightning-grasp')
from lygra.robot import build_robot
from lygra.contact_set import get_link_dependency_matrix
from lygra.kinematics import build_kinematics_tree
from lygra.mesh import get_urdf_mesh, get_urdf_mesh_decomposed, get_urdf_mesh_for_projection
from lygra.mesh_analyzer import get_support_point_mask
from lygra.utils.geom_utils import MeshObject
from lygra.memory import IKGPUBufferPool

# Pipeline modules
from lygra.pipeline.module.object_placement import sample_object_pose, get_object_pose_sampling_args
from lygra.pipeline.module.contact_query import batch_object_all_contact_fields_interaction
from lygra.pipeline.module.contact_collection import sample_pose_and_contact_from_interaction
from lygra.pipeline.module.contact_optimization import search_contact_point
from lygra.pipeline.module.kinematics import batch_ik, batch_contact_adjustment
from lygra.pipeline.module.collision import batch_filter_collision
from lygra.pipeline.module.postprocess import batch_assign_free_finger_and_filter

# Local imports
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from parse_scene import SceneParser


class GraspSceneIntegration:
    """集成场景解析和抓取生成"""
    
    def __init__(self, scene_config_path, robot_name='leap'):
        self.scene_config_path = scene_config_path
        self.robot_name = robot_name
        
        # 加载场景
        self.scene_parser = SceneParser(scene_config_path)
        self.scene_data = self.scene_parser.scene_data
        
        # 初始化机器人（使用 demo.py 的方式）
        self.robot = build_robot(robot_name)
        self._setup_robot()
        
        print(f"✓ 场景加载完成，包含 {len(self.scene_data['objects'])} 个物体")
        print(f"✓ 机器人: {robot_name}")
    
    def _setup_robot(self):
        """设置机器人结构（参考 demo.py）"""
        # 构建运动学树
        self.tree = build_kinematics_tree(
            urdf_path=self.robot.urdf_path,
            active_joint_names=self.robot.get_active_joints()
        )
        
        # 获取 mesh 数据
        self.mesh_data = get_urdf_mesh(
            urdf_path=self.robot.urdf_path,
            tree=self.tree,
            mesh_scale=self.robot.get_mesh_scale()
        )
        
        self.mesh_data_for_ik = get_urdf_mesh_for_projection(
            urdf_path=self.robot.urdf_path,
            tree=self.tree,
            config=self.robot.get_contact_field_config(),
            mesh_scale=self.robot.get_mesh_scale()
        )
        
        self.decomposed_static_mesh_data = get_urdf_mesh_decomposed(
            urdf_path=self.robot.urdf_path,
            tree=self.tree,
            override_link_names=self.robot.get_static_links(),
            mesh_scale=self.robot.get_mesh_scale()
        )
        
        self.decomposed_mesh_data = get_urdf_mesh_decomposed(
            urdf_path=self.robot.urdf_path,
            tree=self.tree,
            mesh_scale=self.robot.get_mesh_scale()
        )
        
        # 碰撞检测配置
        self.self_collision_link_pairs = self.tree.get_self_collision_check_link_pairs(
            link_body_id=self.decomposed_mesh_data['link_body_id'],
            whitelist_link=[]
        )
        self.self_collision_link_pairs = torch.from_numpy(self.self_collision_link_pairs).cuda().int()
        
        # Contact field
        self.contact_field = self.robot.get_contact_field()
        dependency_sets = self.tree.get_dependency_sets([self.robot.get_base_link()])
        
        contact_parent_links = self.contact_field.get_all_parent_link_names()
        self.contact_parent_ids = [self.tree.get_link_id(link) for link in contact_parent_links]
        self.contact_parent_ids = torch.tensor(self.contact_parent_ids).cuda()
        
        self.dependency_matrix = get_link_dependency_matrix(self.contact_field, dependency_sets)
        self.dependency_matrix = self.dependency_matrix.cuda()
        
        # 加速结构
        self.accel_structure = self.contact_field.generate_acceleration_structure(method='lbvhs2')
        
        print("✓ 机器人设置完成")
    
    def select_target_object(self, target_name=None):
        """
        选择目标物体
        如果 target_name 为 None，则随机选择一个非桌面物体
        """
        objects = self.scene_data['objects']
        
        # 过滤掉桌面
        non_table_objects = [obj for obj in objects if obj['name'] != 'table']
        
        if not non_table_objects:
            raise ValueError("场景中没有可抓取的物体（除了桌面）")
        
        if target_name:
            target = next((obj for obj in non_table_objects if obj['name'] == target_name), None)
            if not target:
                raise ValueError(f"未找到名为 {target_name} 的物体")
        else:
            target = random.choice(non_table_objects)
        
        print(f"\n✓ 选择目标物体: {target['name']}")
        print(f"  类型: {target['type']}")
        print(f"  位置: {target['position']}")
        print(f"  姿态: {target.get('orientation', [0, 0, 0])}")
        
        return target
    
    def load_object_mesh(self, target_obj):
        """
        加载物体 mesh（使用 demo.py 的方式）
        支持从 obj 文件加载或从基本形状生成
        """
        if target_obj['type'] == 'mesh':
            # 从 obj 文件加载
            mesh_path = target_obj['mesh_path']
            if not os.path.isabs(mesh_path):
                # 尝试相对于场景配置文件的路径
                config_dir = os.path.dirname(self.scene_config_path)
                mesh_path = os.path.join(config_dir, mesh_path)
            
            print(f"  加载 mesh: {mesh_path}")
            # 使用 MeshObject（与 demo.py 一致）
            object_mesh = MeshObject(mesh_path)
            
            # 应用 scale
            if 'mesh_scale' in target_obj:
                scale = target_obj['mesh_scale']
                if isinstance(scale, (int, float)):
                    scale = [scale, scale, scale]
                scale_matrix = np.eye(4)
                scale_matrix[0, 0] = scale[0]
                scale_matrix[1, 1] = scale[1]
                scale_matrix[2, 2] = scale[2]
                object_mesh.mesh.apply_transform(scale_matrix)
        else:
            # 从基本形状生成 mesh
            object_mesh = self._create_primitive_mesh(target_obj)
        
        return object_mesh
    
    def _create_primitive_mesh(self, obj):
        """创建基本形状的 mesh"""
        scale = obj.get('scale', [0.1, 0.1, 0.1])
        
        if obj['type'] in ['box', 'cube']:
            mesh = trimesh.creation.box(extents=scale)
        elif obj['type'] == 'sphere':
            radius = scale[0] / 2
            mesh = trimesh.creation.icosphere(subdivisions=3, radius=radius)
        elif obj['type'] == 'cylinder':
            radius = scale[0] / 2
            height = scale[2]
            mesh = trimesh.creation.cylinder(radius=radius, height=height)
        else:
            raise ValueError(f"不支持的物体类型: {obj['type']}")
        
        # 包装为 MeshObject
        class SimpleMeshObject:
            def __init__(self, mesh):
                self.mesh = mesh
            
            def get_area(self):
                return self.mesh.area
            
            def sample_point_and_normal(self, count):
                points, face_indices = trimesh.sample.sample_surface(self.mesh, count)
                normals = self.mesh.face_normals[face_indices]
                return points, normals
        
        return SimpleMeshObject(mesh)
    
    def generate_grasps(self, object_mesh, 
                       batch_size_outer=128,
                       batch_size_inner=128,
                       n_contact=3,
                       n_sample_point=2048,
                       ik_finetune_iter=5,
                       zo_lr_sigma=5,
                       object_pose_sampling_strategy='canonical'):
        """
        生成抓取（使用 demo.py 的流程）
        
        注意：这里生成的是在物体局部坐标系下的抓取
        """
        print("\n开始生成抓取...")
        
        # 采样物体点云
        object_area = object_mesh.get_area()
        zo_lr = ((object_area / n_sample_point) ** 0.5) * zo_lr_sigma
        points, normals = object_mesh.sample_point_and_normal(count=n_sample_point)
        points_all = torch.from_numpy(points).cuda().float()
        normals_all = torch.from_numpy(normals).cuda().float()
        
        # 过滤支撑点
        support_point_mask = get_support_point_mask(points_all, normals_all, [0.01])[0]
        points = points_all[torch.where(support_point_mask)]
        normals = normals_all[torch.where(support_point_mask)]
        
        print(f"  采样点数: {len(points_all)}, 支撑点数: {len(points)}")
        
        # IK GPU buffer
        gpu_memory_pool = IKGPUBufferPool(
            n_dof=self.tree.n_dof(),
            n_link=self.tree.n_link(),
            max_batch=min([batch_size_outer * batch_size_inner, 65536]),
            retry=10
        )
        
        with torch.no_grad():
            # 1. Object Placement
            print("  [1/8] Object placement...")
            object_poses, condition = sample_object_pose(
                n=batch_size_outer,
                points=points,
                normals=normals,
                contact_field=self.contact_field,
                tree=self.tree,
                mesh_data=self.decomposed_static_mesh_data,
                sampling_args=get_object_pose_sampling_args(object_pose_sampling_strategy, self.robot)
            )
            
            # 2. Contact Field BVH Traversal
            print("  [2/8] BVH traversal...")
            interaction_matrix_hand_point_idx = batch_object_all_contact_fields_interaction(
                object_pos=points,
                object_normal=normals,
                object_pose=object_poses,
                accel_structure=self.accel_structure
            )
            
            interaction_matrix = (interaction_matrix_hand_point_idx >= 0).int()
            link_interaction_matrix = self.contact_field.reduce_link_interaction(interaction_matrix)
            
            # 3. Get Contact Domain
            print("  [3/8] Contact domain...")
            contact_domain_pos, contact_domain_normal, contact_domain_point_idx, \
            object_poses, contact_link_ids, condition, valid_outer_idx = \
            sample_pose_and_contact_from_interaction(
                n_contact=n_contact,
                interaction_matrix=link_interaction_matrix,
                dependency_matrix=self.dependency_matrix,
                object_points=points,
                object_normals=normals,
                object_poses=object_poses,
                condition=condition
            )
            
            # 4. Search Contact Points
            print("  [4/8] Search contact points...")
            target_contact_pos, target_contact_normal, target_contact_point_idx, \
            object_poses, target_contact_link_ids, target_batch_outer_ids = \
            search_contact_point(
                contact_domain_pos=contact_domain_pos,
                contact_domain_normal=contact_domain_normal,
                contact_domain_point_idx=contact_domain_point_idx,
                object_poses=object_poses,
                contact_ids=contact_link_ids,
                batch_size=batch_size_inner,
                return_hand_frame=True,
                condition=condition,
                zo_lr=zo_lr
            )
            
            # 5. Sample Contact IDs
            print("  [5/8] Sample contact IDs...")
            contact_ids, local_contact_ids = self.contact_field.sample_contact_ids(
                interaction_matrix=interaction_matrix[valid_outer_idx],
                interaction_matrix_hand_point_idx=interaction_matrix_hand_point_idx[valid_outer_idx],
                target_batch_outer_ids=target_batch_outer_ids,
                target_contact_link_ids=target_contact_link_ids,
                target_contact_point_idx=target_contact_point_idx
            )
            
            contact_pos_in_linkf, contact_normal_in_linkf = self.contact_field.sample_contact_geometry(
                contact_ids, local_contact_ids
            )
            
            # 6. Coarse IK
            print("  [6/8] Batch IK...")
            result = batch_ik(
                tree=self.tree,
                contact_ids=contact_ids,
                contact_parent_ids=self.contact_parent_ids,
                contact_pos_in_linkf=contact_pos_in_linkf.float(),
                contact_normal_in_linkf=contact_normal_in_linkf.float(),
                target_contact_pos=target_contact_pos.float(),
                target_contact_normal=target_contact_normal.float(),
                object_pose=object_poses.float(),
                gpu_memory_pool=gpu_memory_pool
            )
            
            # 7. Contact Adjustment
            print("  [7/8] Contact adjustment...")
            result = batch_contact_adjustment(
                tree=self.tree,
                mesh=self.mesh_data_for_ik,
                q_init=result["q"],
                q_mask=result["q_mask"],
                contact_ids=contact_ids,
                contact_link_ids=result["contact_link_id"],
                contact_pos_in_linkf=result["contact_pos"],
                contact_normal_in_linkf=result["contact_normal"],
                target_contact_pos=result["target_pos"],
                target_contact_normal=result["target_normal"],
                object_pose=result["object_pose"],
                n_iter=ik_finetune_iter,
                gpu_memory_pool=gpu_memory_pool,
                ret_mesh_buffer=True
            )
            
            # 8. Postprocessing
            print("  [8/8] Postprocessing...")
            result = batch_assign_free_finger_and_filter(
                tree=self.tree,
                result=result,
                object_point=points_all,
                self_collision_link_pairs=self.self_collision_link_pairs,
                decomposed_mesh_data=self.decomposed_mesh_data
            )
        
        n_result = len(result['q'])
        print(f"\n✓ 生成 {n_result} 个有效抓取")
        
        return result, points_all
    
    def transform_grasps_to_world(self, result, target_obj):
        """
        将抓取从物体局部坐标系转换到世界坐标系
        
        Lightning-grasp 生成的 result['object_pose'] 是物体在标准姿态下相对于手的变换
        我们需要将其转换到场景中物体的实际位置
        """
        # 获取物体在场景中的位置和姿态
        position = np.array(target_obj['position'])
        orientation = np.array(target_obj.get('orientation', [0, 0, 0]))
        
        # 构建物体在世界坐标系中的变换矩阵
        from scipy.spatial.transform import Rotation
        R_world = Rotation.from_euler('xyz', orientation).as_matrix()
        T_world = np.eye(4)
        T_world[:3, :3] = R_world
        T_world[:3, 3] = position
        
        # 转换每个抓取
        n_grasps = len(result['q'])
        hand_poses_world = []
        
        for i in range(n_grasps):
            # result['object_pose'][i] 是 4x4 变换矩阵
            # 表示物体相对于手的变换 (T_hand_to_obj)
            T_hand_to_obj = result['object_pose'][i].cpu().numpy()
            
            # 计算手在世界坐标系中的位置
            # T_world_to_hand = T_world_to_obj * T_obj_to_hand
            T_obj_to_hand = np.linalg.inv(T_hand_to_obj)
            T_world_to_hand = T_world @ T_obj_to_hand
            
            hand_poses_world.append(T_world_to_hand)
        
        result['hand_poses_world'] = hand_poses_world
        result['object_world_pose'] = T_world
        
        return result
    
    def filter_table_collisions(self, result, target_obj):
        """
        过滤与桌面碰撞的抓取
        """
        # 获取桌面信息
        table = next((obj for obj in self.scene_data['objects'] if obj['name'] == 'table'), None)
        if not table:
            print("  警告: 未找到桌面，跳过桌面碰撞检测")
            return result
        
        table_pos = np.array(table['position'])
        table_scale = np.array(table['scale'])
        table_top_z = table_pos[2] + table_scale[2] / 2
        
        # 获取手的最低点
        # 简化版本：检查手的 base 位置是否低于桌面
        valid_indices = []
        
        for i, hand_pose in enumerate(result['hand_poses_world']):
            hand_z = hand_pose[2, 3]
            
            # 添加安全余量
            safety_margin = 0.02
            if hand_z > table_top_z + safety_margin:
                valid_indices.append(i)
        
        print(f"  桌面碰撞检测: {len(valid_indices)}/{len(result['q'])} 个抓取有效")
        
        # 过滤结果
        if valid_indices:
            result['q'] = result['q'][valid_indices]
            result['object_pose'] = result['object_pose'][valid_indices]
            result['hand_poses_world'] = [result['hand_poses_world'][i] for i in valid_indices]
        
        return result
    
    def save_grasp_visualization_data(self, result, target_obj, output_path):
        """
        保存抓取可视化数据（用于 RViz）
        """
        # 选择一个抓取
        if len(result['q']) == 0:
            print("警告: 没有有效抓取可保存")
            return None
        
        # 随机选择或选择第一个
        idx = 0 if len(result['q']) == 1 else random.randint(0, len(result['q']) - 1)
        
        grasp_data = {
            'robot_name': self.robot_name,
            'joint_positions': result['q'][idx].cpu().numpy().tolist(),
            'hand_pose': result['hand_poses_world'][idx].tolist(),
            'object_name': target_obj['name'],
            'object_world_pose': result['object_world_pose'].tolist()
        }
        
        with open(output_path, 'w') as f:
            json.dump(grasp_data, f, indent=2)
        
        print(f"\n✓ 抓取数据已保存到: {output_path}")
        return grasp_data


def main():
    parser = argparse.ArgumentParser(description="场景抓取生成")
    parser.add_argument('--scene', type=str, 
                       default='/workspace/RDF_ori/show_urdf_ws/src/show_urdf/show_urdf/scene_config.json',
                       help='场景配置文件路径')
    parser.add_argument('--robot', type=str, default='allegro', help='机器人类型')
    parser.add_argument('--target', type=str, default=None, help='目标物体名称（留空则随机选择）')
    parser.add_argument('--output', type=str, default='grasp_result.json', help='输出文件路径')
    parser.add_argument('--batch_outer', type=int, default=128, help='外层批次大小')
    parser.add_argument('--batch_inner', type=int, default=128, help='内层批次大小')
    
    args = parser.parse_args()
    
    # 初始化
    integrator = GraspSceneIntegration(args.scene, args.robot)
    
    # 选择目标物体
    target_obj = integrator.select_target_object(args.target)
    
    # 加载物体 mesh
    object_mesh = integrator.load_object_mesh(target_obj)
    
    # 生成抓取
    result, object_points = integrator.generate_grasps(
        object_mesh,
        batch_size_outer=args.batch_outer,
        batch_size_inner=args.batch_inner
    )
    
    if len(result['q']) == 0:
        print("\n错误: 未生成任何有效抓取")
        return
    
    # 转换到世界坐标系
    result = integrator.transform_grasps_to_world(result, target_obj)
    
    # 桌面碰撞检测
    result = integrator.filter_table_collisions(result, target_obj)
    
    if len(result['q']) == 0:
        print("\n错误: 所有抓取都与桌面碰撞")
        return
    
    # 保存结果
    integrator.save_grasp_visualization_data(result, target_obj, args.output)
    
    print(f"\n{'='*50}")
    print("抓取生成完成！")
    print(f"最终有效抓取数: {len(result['q'])}")
    print(f"{'='*50}\n")


if __name__ == '__main__':
    main()
