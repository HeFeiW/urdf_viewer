#!/usr/bin/env python3
"""
从场景中选择物体，使用 lightning-grasp 生成抓取，并在 RViz 中可视化
"""

import sys
import json
import argparse
import random
from pathlib import Path
import numpy as np
import torch
import trimesh
import open3d as o3d

# Lightning-grasp imports
sys.path.append('/home/hefei/lightning-grasp')
from lygra.robot import build_robot
from lygra.contact_set import get_dependency_matrix, get_link_dependency_matrix
from lygra.kinematics import build_kinematics_tree
from lygra.mesh import get_urdf_mesh, get_urdf_mesh_decomposed, get_urdf_mesh_for_projection, trimesh_to_open3d
from lygra.mesh_analyzer import get_support_point_mask
from lygra.utils.geom_utils import MeshObject
from lygra.memory import IKGPUBufferPool
from lygra.utils.robot_visualizer import RobotVisualizer

from lygra.pipeline.module.object_placement import sample_object_pose, get_object_pose_sampling_args
from lygra.pipeline.module.contact_query import batch_object_all_contact_fields_interaction
from lygra.pipeline.module.contact_collection import sample_pose_and_contact_from_interaction
from lygra.pipeline.module.contact_optimization import search_contact_point
from lygra.pipeline.module.kinematics import batch_ik, batch_contact_adjustment
from lygra.pipeline.module.collision import batch_filter_collision
from lygra.pipeline.module.postprocess import batch_assign_free_finger_and_filter


def load_scene(scene_config_path):
    """加载场景配置"""
    with open(scene_config_path, 'r') as f:
        scene = json.load(f)
    return scene


def select_target_object(scene, target_name=None):
    """
    从场景中选择目标物体
    
    Args:
        scene: 场景配置字典
        target_name: 指定的物体名称，None则随机选择
        
    Returns:
        target_obj: 目标物体配置
    """
    # 过滤掉桌子
    objects = [obj for obj in scene['objects'] if obj['name'] != 'table']
    
    if not objects:
        raise ValueError("场景中没有可抓取的物体")
    
    if target_name:
        target_obj = next((obj for obj in objects if obj['name'] == target_name), None)
        if not target_obj:
            raise ValueError(f"未找到物体: {target_name}")
    else:
        target_obj = random.choice(objects)
    
    print(f"选中目标物体: {target_obj['name']} (type: {target_obj['type']})")
    return target_obj


def load_object_mesh(obj_config, obj_dir='/home/hefei/lightning-grasp/assets/object/ycb'):
    """
    加载物体mesh，考虑scale
    
    Args:
        obj_config: 物体配置字典
        obj_dir: YCB物体目录
        
    Returns:
        mesh: trimesh对象
        scale: 缩放因子
    """
    obj_type = obj_config['type']
    scale = obj_config['scale']
    
    if obj_type == 'mesh':
        # 加载OBJ文件
        mesh_file = obj_config['mesh_file']
        if not Path(mesh_file).exists():
            # 尝试相对于obj_dir
            mesh_file = Path(obj_dir) / Path(mesh_file).name
        
        if not Path(mesh_file).exists():
            raise FileNotFoundError(f"未找到mesh文件: {mesh_file}")
        
        mesh = trimesh.load(str(mesh_file))
        
    elif obj_type == 'box':
        # 创建方块mesh
        mesh = trimesh.creation.box(extents=[1.0, 1.0, 1.0])
        
    elif obj_type == 'sphere':
        # 创建球体mesh
        radius = 0.5  # 单位球
        mesh = trimesh.creation.icosphere(subdivisions=3, radius=radius)
        
    elif obj_type == 'cylinder':
        # 创建圆柱mesh
        radius = 0.5
        height = 1.0
        mesh = trimesh.creation.cylinder(radius=radius, height=height)
        
    else:
        raise ValueError(f"不支持的物体类型: {obj_type}")
    
    # 应用缩放
    scale_matrix = np.diag(list(scale) + [1.0])
    mesh.apply_transform(scale_matrix)
    
    return mesh, scale


def rpy_to_rotation_matrix(roll, pitch, yaw):
    """RPY角度转旋转矩阵"""
    # Roll (X轴)
    Rx = np.array([
        [1, 0, 0],
        [0, np.cos(roll), -np.sin(roll)],
        [0, np.sin(roll), np.cos(roll)]
    ])
    
    # Pitch (Y轴)
    Ry = np.array([
        [np.cos(pitch), 0, np.sin(pitch)],
        [0, 1, 0],
        [-np.sin(pitch), 0, np.cos(pitch)]
    ])
    
    # Yaw (Z轴)
    Rz = np.array([
        [np.cos(yaw), -np.sin(yaw), 0],
        [np.sin(yaw), np.cos(yaw), 0],
        [0, 0, 1]
    ])
    
    return Rz @ Ry @ Rx


def get_object_transform_in_scene(obj_config):
    """
    获取物体在场景中的变换矩阵
    
    Args:
        obj_config: 物体配置
        
    Returns:
        transform: 4x4变换矩阵
    """
    position = obj_config['position']
    orientation = obj_config['orientation']  # [roll, pitch, yaw]
    
    transform = np.eye(4)
    transform[:3, :3] = rpy_to_rotation_matrix(*orientation)
    transform[:3, 3] = position
    
    return transform


def generate_grasps_lightning(mesh, robot_name='allegro', batch_size_outer=128, batch_size_inner=128):
    """
    使用 lightning-grasp 生成抓取
    
    Args:
        mesh: trimesh对象
        robot_name: 机器人名称
        batch_size_outer: 外层batch大小
        batch_size_inner: 内层batch大小
        
    Returns:
        result: 包含 q (关节角) 和 object_pose (物体位姿) 的字典
    """
    print("初始化 lightning-grasp...")
    
    # 参数设置
    n_contact = 3
    n_sample_point = 2048
    ik_finetune_iter = 5
    cf_accel = 'lbvhs2'
    object_pose_sampling_strategy = 'canonical'
    
    # 构建机器人
    robot = build_robot(robot_name)
    
    # 机器人结构
    tree = build_kinematics_tree(
        urdf_path=robot.urdf_path,
        active_joint_names=robot.get_active_joints()
    )
    
    # 机器人mesh数据
    mesh_data = get_urdf_mesh(
        urdf_path=robot.urdf_path,
        tree=tree,
        mesh_scale=robot.get_mesh_scale()
    )
    
    mesh_data_for_ik = get_urdf_mesh_for_projection(
        urdf_path=robot.urdf_path,
        tree=tree,
        config=robot.get_contact_field_config(),
        mesh_scale=robot.get_mesh_scale()
    )
    
    decomposed_static_mesh_data = get_urdf_mesh_decomposed(
        urdf_path=robot.urdf_path,
        tree=tree,
        override_link_names=robot.get_static_links(),
        mesh_scale=robot.get_mesh_scale()
    )
    
    decomposed_mesh_data = get_urdf_mesh_decomposed(
        urdf_path=robot.urdf_path,
        tree=tree,
        mesh_scale=robot.get_mesh_scale()
    )
    
    # 碰撞检测配置
    self_collision_link_pairs = tree.get_self_collision_check_link_pairs(
        link_body_id=decomposed_mesh_data['link_body_id'],
        whitelist_link=[]
    )
    self_collision_link_pairs = torch.from_numpy(self_collision_link_pairs).cuda().int()
    
    contact_field = robot.get_contact_field()
    dependency_sets = tree.get_dependency_sets([robot.get_base_link()])
    
    contact_parent_links = contact_field.get_all_parent_link_names()
    contact_parent_ids = [tree.get_link_id(link) for link in contact_parent_links]
    contact_parent_ids = torch.tensor(contact_parent_ids).cuda()
    
    dependency_matrix = get_link_dependency_matrix(contact_field, dependency_sets)
    dependency_matrix = dependency_matrix.cuda()
    
    # Contact Field加速结构
    accel_structure = contact_field.generate_acceleration_structure(method=cf_accel)
    
    # 物体数据
    object_wrapper = MeshObject.__new__(MeshObject)
    object_wrapper.mesh = mesh
    
    object_area = object_wrapper.get_area()
    zo_lr = ((object_area / n_sample_point) ** 0.5) * 5.0
    
    points, normals = object_wrapper.sample_point_and_normal(count=n_sample_point)
    points_all = torch.from_numpy(points).cuda().float()
    normals_all = torch.from_numpy(normals).cuda().float()
    
    # 过滤支撑点
    support_point_mask = get_support_point_mask(points_all, normals_all, [0.01])[0]
    points = points_all[torch.where(support_point_mask)]
    normals = normals_all[torch.where(support_point_mask)]
    
    # IK GPU缓冲池
    gpu_memory_pool = IKGPUBufferPool(
        n_dof=tree.n_dof(), 
        n_link=tree.n_link(), 
        max_batch=min([batch_size_outer * batch_size_inner, 65536]), 
        retry=10
    )
    
    print("开始生成抓取...")
    with torch.no_grad():
        # 物体位姿采样
        object_poses, condition = sample_object_pose(
            n=batch_size_outer, 
            points=points, 
            normals=normals, 
            contact_field=contact_field, 
            tree=tree, 
            mesh_data=decomposed_static_mesh_data,
            sampling_args=get_object_pose_sampling_args(object_pose_sampling_strategy, robot)
        )
        
        # Contact Field BVH遍历
        interaction_matrix_hand_point_idx = batch_object_all_contact_fields_interaction(
            object_pos=points, 
            object_normal=normals, 
            object_pose=object_poses, 
            accel_structure=accel_structure
        )
        
        interaction_matrix = (interaction_matrix_hand_point_idx >= 0).int()
        link_interaction_matrix = contact_field.reduce_link_interaction(interaction_matrix)
        
        # 获取接触域
        contact_domain_pos, contact_domain_normal, contact_domain_point_idx, \
        object_poses, contact_link_ids, condition, valid_outer_idx = \
        sample_pose_and_contact_from_interaction(
            n_contact=n_contact,
            interaction_matrix=link_interaction_matrix, 
            dependency_matrix=dependency_matrix, 
            object_points=points, 
            object_normals=normals, 
            object_poses=object_poses,
            condition=condition
        )
        
        # 搜索接触点
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
        
        contact_ids, local_contact_ids = contact_field.sample_contact_ids(
            interaction_matrix=interaction_matrix[valid_outer_idx], 
            interaction_matrix_hand_point_idx=interaction_matrix_hand_point_idx[valid_outer_idx],
            target_batch_outer_ids=target_batch_outer_ids, 
            target_contact_link_ids=target_contact_link_ids, 
            target_contact_point_idx=target_contact_point_idx
        )
        
        contact_pos_in_linkf, contact_normal_in_linkf = contact_field.sample_contact_geometry(
            contact_ids, local_contact_ids
        )
        
        # IK求解
        result = batch_ik(
            tree=tree,
            contact_ids=contact_ids,
            contact_parent_ids=contact_parent_ids,
            contact_pos_in_linkf=contact_pos_in_linkf.float(),
            contact_normal_in_linkf=contact_normal_in_linkf.float(),
            target_contact_pos=target_contact_pos.float(),
            target_contact_normal=target_contact_normal.float(),
            object_pose=object_poses.float(),
            gpu_memory_pool=gpu_memory_pool
        )
        
        # 接触调整
        result = batch_contact_adjustment(
            tree=tree,
            mesh=mesh_data_for_ik,
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
        
        # 后处理：分配自由手指并过滤
        result = batch_assign_free_finger_and_filter(
            tree=tree,
            result=result,
            object_point=points_all,
            self_collision_link_pairs=self_collision_link_pairs,
            decomposed_mesh_data=decomposed_mesh_data
        )
    
    n_result = len(result['q'])
    print(f"生成了 {n_result} 个有效抓取")
    
    return result, robot, tree


def transform_grasp_to_scene(grasp_q, grasp_object_pose, scene_object_transform):
    """
    将抓取从canonical空间转换到场景空间
    
    Args:
        grasp_q: 关节角 [n]
        grasp_object_pose: 物体位姿 [4, 4]
        scene_object_transform: 物体在场景中的变换 [4, 4]
        
    Returns:
        hand_base_transform: 手的基座在场景中的变换 [4, 4]
    """
    # grasp_object_pose 是手坐标系下的物体位姿
    # 我们需要计算手在场景中的位姿
    
    # T_scene_object = scene_object_transform
    # T_hand_object = grasp_object_pose
    # T_scene_hand = T_scene_object @ inv(T_hand_object)
    
    grasp_object_pose_np = grasp_object_pose.cpu().numpy()
    
    T_scene_object = scene_object_transform
    T_hand_object = grasp_object_pose_np
    T_object_hand = np.linalg.inv(T_hand_object)
    T_scene_hand = T_scene_object @ T_object_hand
    
    return T_scene_hand


def check_collision_with_table(hand_mesh, table_config):
    """
    检查手与桌面的碰撞
    
    Args:
        hand_mesh: 手的mesh (trimesh)
        table_config: 桌面配置
        
    Returns:
        is_collision: 是否碰撞
    """
    # 桌面参数
    table_pos = table_config['position']
    table_scale = table_config['scale']
    
    # 桌面顶部z坐标
    table_top_z = table_pos[2] + table_scale[2] / 2
    
    # 桌面范围
    table_x_min = table_pos[0] - table_scale[0] / 2
    table_x_max = table_pos[0] + table_scale[0] / 2
    table_y_min = table_pos[1] - table_scale[1] / 2
    table_y_max = table_pos[1] + table_scale[1] / 2
    
    # 获取手的所有顶点
    hand_vertices = hand_mesh.vertices
    
    # 检查是否有顶点穿透桌面
    for vertex in hand_vertices:
        x, y, z = vertex
        
        # 检查顶点是否在桌面范围内
        if table_x_min <= x <= table_x_max and table_y_min <= y <= table_y_max:
            # 检查是否低于桌面顶部
            if z < table_top_z + 0.005:  # 5mm容差
                return True
    
    return False


def filter_grasps_by_collision(result, robot, tree, scene, scene_object_transform):
    """
    根据碰撞过滤抓取
    
    Args:
        result: lightning-grasp结果
        robot: 机器人对象
        tree: 运动学树
        scene: 场景配置
        scene_object_transform: 目标物体在场景中的变换
        
    Returns:
        valid_indices: 有效抓取的索引列表
    """
    print("检查碰撞...")
    
    # 获取桌面配置
    table_obj = next(obj for obj in scene['objects'] if obj['name'] == 'table')
    
    # 获取机器人mesh数据
    mesh_data = get_urdf_mesh(
        urdf_path=robot.urdf_path,
        tree=tree,
        mesh_scale=robot.get_mesh_scale()
    )
    
    valid_indices = []
    n_grasps = len(result['q'])
    
    for i in range(n_grasps):
        q = result['q'][i:i+1].cpu().numpy()
        grasp_object_pose = result['object_pose'][i]
        
        # 转换到场景空间
        hand_base_transform = transform_grasp_to_scene(
            result['q'][i],
            grasp_object_pose,
            scene_object_transform
        )
        
        # 正向运动学获取手的mesh
        link_poses = tree.forward_kinematics(torch.from_numpy(q).cuda())
        
        # 创建完整的手mesh
        hand_meshes = []
        for link_id in range(tree.n_link()):
            if link_id >= len(mesh_data['vertices']) or len(mesh_data['vertices'][link_id]) == 0:
                continue
            
            link_pose = link_poses[0, link_id].cpu().numpy()
            vertices = mesh_data['vertices'][link_id]
            faces = mesh_data['faces'][link_id]
            
            # 创建link mesh
            link_mesh = trimesh.Trimesh(vertices=vertices, faces=faces)
            
            # 应用link变换（在手坐标系中）
            link_mesh.apply_transform(link_pose)
            
            hand_meshes.append(link_mesh)
        
        # 合并所有link mesh
        if hand_meshes:
            combined_hand_mesh = trimesh.util.concatenate(hand_meshes)
            
            # 应用手基座变换到场景空间
            combined_hand_mesh.apply_transform(hand_base_transform)
            
            # 检查与桌面的碰撞
            if not check_collision_with_table(combined_hand_mesh, table_obj):
                valid_indices.append(i)
    
    print(f"碰撞检查: {len(valid_indices)}/{n_grasps} 个抓取有效")
    
    return valid_indices


def save_grasp_for_rviz(grasp_q, hand_base_transform, robot_name, output_file):
    """
    保存抓取数据用于RViz可视化
    
    Args:
        grasp_q: 关节角
        hand_base_transform: 手基座变换矩阵
        robot_name: 机器人名称
        output_file: 输出文件路径
    """
    # 提取位置和姿态
    position = hand_base_transform[:3, 3].tolist()
    rotation_matrix = hand_base_transform[:3, :3]
    
    # 转换旋转矩阵为RPY
    # 这是一个简化的转换，实际应该使用scipy或其他库
    import math
    sy = math.sqrt(rotation_matrix[0, 0]**2 + rotation_matrix[1, 0]**2)
    
    if sy > 1e-6:
        roll = math.atan2(rotation_matrix[2, 1], rotation_matrix[2, 2])
        pitch = math.atan2(-rotation_matrix[2, 0], sy)
        yaw = math.atan2(rotation_matrix[1, 0], rotation_matrix[0, 0])
    else:
        roll = math.atan2(-rotation_matrix[1, 2], rotation_matrix[1, 1])
        pitch = math.atan2(-rotation_matrix[2, 0], sy)
        yaw = 0
    
    orientation = [roll, pitch, yaw]
    
    # 构建数据结构
    grasp_data = {
        'robot_name': robot_name,
        'joint_angles': grasp_q.tolist() if isinstance(grasp_q, np.ndarray) else grasp_q.cpu().numpy().tolist(),
        'hand_base_position': position,
        'hand_base_orientation': orientation,  # [roll, pitch, yaw]
        'hand_base_transform': hand_base_transform.tolist()
    }
    
    # 保存为JSON
    with open(output_file, 'w') as f:
        json.dump(grasp_data, f, indent=2)
    
    print(f"抓取数据已保存到: {output_file}")


def main():
    parser = argparse.ArgumentParser(description='从场景生成抓取')
    parser.add_argument('--scene', type=str, default='scene_config.json',
                       help='场景配置文件路径')
    parser.add_argument('--robot', type=str, default='allegro',
                       help='机器人类型 (allegro/leap/shadow/dclaw)')
    parser.add_argument('--target', type=str, default=None,
                       help='目标物体名称（不指定则随机选择）')
    parser.add_argument('--batch-outer', type=int, default=32,
                       help='外层batch大小')
    parser.add_argument('--batch-inner', type=int, default=32,
                       help='内层batch大小')
    parser.add_argument('--output', type=str, default='selected_grasp.json',
                       help='输出文件路径')
    parser.add_argument('--seed', type=int, default=None,
                       help='随机种子')
    
    args = parser.parse_args()
    
    if args.seed is not None:
        random.seed(args.seed)
        np.random.seed(args.seed)
        torch.manual_seed(args.seed)
    
    # 1. 加载场景
    print("加载场景...")
    scene = load_scene(args.scene)
    
    # 2. 选择目标物体
    target_obj = select_target_object(scene, args.target)
    
    # 3. 加载物体mesh
    print("加载物体mesh...")
    mesh, scale = load_object_mesh(target_obj)
    print(f"物体mesh顶点数: {len(mesh.vertices)}, 面片数: {len(mesh.faces)}")
    
    # 4. 获取物体在场景中的变换
    scene_object_transform = get_object_transform_in_scene(target_obj)
    print(f"物体在场景中的位置: {target_obj['position']}")
    print(f"物体在场景中的姿态: {target_obj['orientation']}")
    
    # 5. 生成抓取
    result, robot, tree = generate_grasps_lightning(
        mesh,
        robot_name=args.robot,
        batch_size_outer=args.batch_outer,
        batch_size_inner=args.batch_inner
    )
    
    if len(result['q']) == 0:
        print("错误: 没有生成有效的抓取")
        return
    
    # 6. 碰撞检查
    valid_indices = filter_grasps_by_collision(
        result,
        robot,
        tree,
        scene,
        scene_object_transform
    )
    
    if not valid_indices:
        print("错误: 所有抓取都与桌面碰撞")
        return
    
    # 7. 选择一个有效抓取
    selected_idx = valid_indices[0]
    print(f"选择抓取 #{selected_idx}")
    
    grasp_q = result['q'][selected_idx]
    grasp_object_pose = result['object_pose'][selected_idx]
    
    # 8. 转换到场景空间
    hand_base_transform = transform_grasp_to_scene(
        grasp_q,
        grasp_object_pose,
        scene_object_transform
    )
    
    print(f"手基座在场景中的位置: {hand_base_transform[:3, 3]}")
    
    # 9. 保存用于可视化
    save_grasp_for_rviz(
        grasp_q,
        hand_base_transform,
        args.robot,
        args.output
    )
    
    print("\n完成! 使用以下命令可视化:")
    print(f"  python3 visualize_grasp_rviz.py --grasp {args.output} --scene {args.scene}")


if __name__ == '__main__':
    main()
