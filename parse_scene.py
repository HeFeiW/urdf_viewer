#!/usr/bin/env python3
"""
场景解析模块 - 用于运动规划
从JSON场景配置文件中加载物体信息，进行点云采样和坐标变换
"""

import json
import numpy as np
from typing import Dict, List, Tuple, Optional
from pathlib import Path
import trimesh


class SceneParser:
    """场景解析器，支持从JSON加载场景并进行点云采样"""
    
    def __init__(self, scene_file: str = None):
        """
        初始化场景解析器
        
        Args:
            scene_file: 场景配置JSON文件路径
        """
        self.scene_data = None
        self.objects = {}
        self.meshes = {}
        
        if scene_file:
            self.load_scene_from_json(scene_file)
    
    def load_scene_from_json(self, json_path: str) -> Dict:
        """
        从JSON文件加载场景配置
        
        Args:
            json_path: JSON文件路径
            
        Returns:
            场景配置字典
        """
        json_path = Path(json_path)
        if not json_path.exists():
            raise FileNotFoundError(f"Scene file not found: {json_path}")
        
        with open(json_path, 'r', encoding='utf-8') as f:
            self.scene_data = json.load(f)
        
        # 解析所有物体
        self.objects = {}
        for obj in self.scene_data.get('objects', []):
            name = obj.get('name', 'unnamed')
            self.objects[name] = self._parse_object(obj)
        
        print(f"Loaded scene with {len(self.objects)} objects")
        return self.scene_data
    
    def _parse_object(self, obj_config: Dict) -> Dict:
        """
        解析单个物体配置
        
        Args:
            obj_config: 物体配置字典
            
        Returns:
            标准化的物体信息字典
        """
        obj_info = {
            'name': obj_config.get('name', 'unnamed'),
            'type': obj_config.get('type', 'box'),
            'position': np.array(obj_config.get('position', [0, 0, 0])),
            'orientation': np.array(obj_config.get('orientation', [0, 0, 0])),  # RPY
            'scale': np.array(obj_config.get('scale', [0.1, 0.1, 0.1])),
            'color': obj_config.get('color', [0.5, 0.5, 0.5, 1.0]),
            'frame_id': obj_config.get('frame_id', 'world'),
        }
        
        # 如果是从obj文件加载
        if 'mesh_file' in obj_config:
            obj_info['mesh_file'] = obj_config['mesh_file']
        
        return obj_info
    
    def get_object(self, name: str) -> Optional[Dict]:
        """获取指定名称的物体"""
        return self.objects.get(name)
    
    def get_all_objects(self) -> Dict[str, Dict]:
        """获取所有物体"""
        return self.objects
    
    def get_objects_by_type(self, obj_type: str) -> Dict[str, Dict]:
        """获取指定类型的所有物体"""
        return {name: obj for name, obj in self.objects.items() 
                if obj['type'] == obj_type}
    
    def create_primitive_mesh(self, obj_info: Dict) -> trimesh.Trimesh:
        """
        为标准几何体创建mesh
        
        Args:
            obj_info: 物体信息字典
            
        Returns:
            trimesh.Trimesh对象
        """
        obj_type = obj_info['type']
        scale = obj_info['scale']
        
        if obj_type == 'box' or obj_type == 'cube':
            # 创建立方体
            mesh = trimesh.creation.box(extents=scale)
            
        elif obj_type == 'sphere':
            # 创建球体，scale[0]作为半径
            radius = scale[0] / 2
            mesh = trimesh.creation.icosphere(subdivisions=3, radius=radius)
            
        elif obj_type == 'cylinder':
            # 创建圆柱体，scale[0]/2为半径，scale[2]为高度
            radius = scale[0] / 2
            height = scale[2]
            mesh = trimesh.creation.cylinder(radius=radius, height=height)
            
        else:
            raise ValueError(f"Unsupported primitive type: {obj_type}")
        
        return mesh
    
    def load_mesh_from_obj(self, obj_path: str, scale: np.ndarray = None) -> trimesh.Trimesh:
        """
        从OBJ文件加载mesh
        
        Args:
            obj_path: OBJ文件路径
            scale: 缩放比例 [sx, sy, sz]
            
        Returns:
            trimesh.Trimesh对象
        """
        obj_path = Path(obj_path)
        if not obj_path.exists():
            raise FileNotFoundError(f"OBJ file not found: {obj_path}")
        
        mesh = trimesh.load(str(obj_path))
        
        # 应用缩放
        if scale is not None:
            scale_matrix = np.diag(list(scale) + [1])
            mesh.apply_transform(scale_matrix)
        
        return mesh
    
    def get_or_create_mesh(self, obj_info: Dict) -> trimesh.Trimesh:
        """
        获取或创建物体的mesh
        
        Args:
            obj_info: 物体信息字典
            
        Returns:
            trimesh.Trimesh对象
        """
        name = obj_info['name']
        
        # 检查缓存
        if name in self.meshes:
            return self.meshes[name]
        
        # 创建或加载mesh
        if 'mesh_file' in obj_info:
            # 从OBJ文件加载
            mesh = self.load_mesh_from_obj(
                obj_info['mesh_file'], 
                scale=obj_info['scale']
            )
        else:
            # 创建标准几何体
            mesh = self.create_primitive_mesh(obj_info)
        
        # 缓存
        self.meshes[name] = mesh
        return mesh
    
    def sample_points_on_object(self, obj_info: Dict, num_points: int = 1000) -> np.ndarray:
        """
        在物体表面均匀采样点
        
        Args:
            obj_info: 物体信息字典
            num_points: 采样点数量
            
        Returns:
            点云数组 (N, 3)
        """
        # 获取mesh
        mesh = self.get_or_create_mesh(obj_info)
        
        # 在mesh表面采样
        points, _ = trimesh.sample.sample_surface(mesh, num_points)
        
        return points
    
    def rpy_to_rotation_matrix(self, rpy: np.ndarray) -> np.ndarray:
        """
        将RPY角度转换为旋转矩阵
        
        Args:
            rpy: Roll-Pitch-Yaw角度数组 [roll, pitch, yaw]
            
        Returns:
            3x3旋转矩阵
        """
        roll, pitch, yaw = rpy
        
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
        
        # 组合旋转: R = Rz * Ry * Rx
        R = Rz @ Ry @ Rx
        return R
    
    def transform_points(self, points: np.ndarray, 
                        position: np.ndarray, 
                        orientation: np.ndarray) -> np.ndarray:
        """
        对点云进行坐标变换
        
        Args:
            points: 点云数组 (N, 3)
            position: 位置平移 [x, y, z]
            orientation: 姿态RPY [roll, pitch, yaw]
            
        Returns:
            变换后的点云 (N, 3)
        """
        # 获取旋转矩阵
        R = self.rpy_to_rotation_matrix(orientation)
        
        # 应用旋转和平移
        transformed_points = (R @ points.T).T + position
        
        return transformed_points
    
    def sample_object_in_world(self, obj_name: str, num_points: int = 1000) -> np.ndarray:
        """
        在世界坐标系下采样物体点云
        
        Args:
            obj_name: 物体名称
            num_points: 采样点数量
            
        Returns:
            世界坐标系下的点云 (N, 3)
        """
        obj_info = self.get_object(obj_name)
        if obj_info is None:
            raise ValueError(f"Object not found: {obj_name}")
        
        # 在局部坐标系采样
        local_points = self.sample_points_on_object(obj_info, num_points)
        
        # 变换到世界坐标系
        world_points = self.transform_points(
            local_points,
            obj_info['position'],
            obj_info['orientation']
        )
        
        return world_points
    
    def sample_scene(self, target_name: str, 
                    num_target_points: int = 2000,
                    num_obstacle_points: int = 5000,
                    exclude_objects: List[str] = None) -> Tuple[np.ndarray, np.ndarray]:
        """
        采样场景：分别采样target和obstacles
        
        Args:
            target_name: 目标物体名称
            num_target_points: 目标物体采样点数
            num_obstacle_points: 障碍物总采样点数
            exclude_objects: 排除的物体名称列表（如桌面）
            
        Returns:
            (target_points, obstacle_points) - 两个点云数组
        """
        if exclude_objects is None:
            exclude_objects = ['table']  # 默认排除桌面
        
        # 采样target
        target_points = self.sample_object_in_world(target_name, num_target_points)
        
        # 收集所有obstacle
        obstacle_objects = []
        for name, obj_info in self.objects.items():
            if name != target_name and name not in exclude_objects:
                obstacle_objects.append(name)
        
        if not obstacle_objects:
            # 没有障碍物，返回空数组
            return target_points, np.empty((0, 3))
        
        # 为每个obstacle分配采样点数
        points_per_object = num_obstacle_points // len(obstacle_objects)
        
        obstacle_points_list = []
        for obj_name in obstacle_objects:
            points = self.sample_object_in_world(obj_name, points_per_object)
            obstacle_points_list.append(points)
        
        # 合并所有obstacle点云
        obstacle_points = np.vstack(obstacle_points_list)
        
        return target_points, obstacle_points
    
    def get_object_bounds(self, obj_name: str) -> Tuple[np.ndarray, np.ndarray]:
        """
        获取物体在世界坐标系下的边界框
        
        Args:
            obj_name: 物体名称
            
        Returns:
            (min_bound, max_bound) - 最小和最大边界点
        """
        points = self.sample_object_in_world(obj_name, num_points=100)
        min_bound = np.min(points, axis=0)
        max_bound = np.max(points, axis=0)
        return min_bound, max_bound
    
    def visualize_scene(self, target_name: str = None, 
                       num_points_per_object: int = 500):
        """
        可视化场景（需要open3d）
        
        Args:
            target_name: 目标物体名称（会用不同颜色显示）
            num_points_per_object: 每个物体的采样点数
        """
        try:
            import open3d as o3d
        except ImportError:
            print("Error: open3d not installed. Run: pip install open3d")
            return
        
        point_clouds = []
        
        for name, obj_info in self.objects.items():
            # 采样点云
            points = self.sample_object_in_world(name, num_points_per_object)
            
            # 创建点云对象
            pcd = o3d.geometry.PointCloud()
            pcd.points = o3d.utility.Vector3dVector(points)
            
            # 设置颜色
            if name == target_name:
                color = [1.0, 0.0, 0.0]  # 目标物体：红色
            elif name == 'table':
                color = [0.6, 0.4, 0.2]  # 桌面：棕色
            else:
                color = obj_info['color'][:3]  # 使用配置的颜色
            
            pcd.paint_uniform_color(color)
            point_clouds.append(pcd)
        
        # 创建坐标系
        coord_frame = o3d.geometry.TriangleMesh.create_coordinate_frame(
            size=0.3, origin=[0, 0, 0]
        )
        
        # 可视化
        o3d.visualization.draw_geometries(point_clouds + [coord_frame])
    
    def export_to_dict(self) -> Dict:
        """
        导出场景为字典格式（用于其他模块）
        
        Returns:
            包含所有物体信息的字典
        """
        export_data = {
            'objects': [],
            'target': None,
            'obstacles': []
        }
        
        for name, obj_info in self.objects.items():
            export_data['objects'].append({
                'name': name,
                'type': obj_info['type'],
                'position': obj_info['position'].tolist(),
                'orientation': obj_info['orientation'].tolist(),
                'scale': obj_info['scale'].tolist(),
                'color': obj_info['color']
            })
        
        return export_data


def main():
    """示例用法"""
    import argparse
    
    parser = argparse.ArgumentParser(description='解析场景配置文件')
    parser.add_argument('scene_file', type=str, help='场景JSON文件路径')
    parser.add_argument('--target', type=str, default=None, help='目标物体名称')
    parser.add_argument('--num-points', type=int, default=1000, help='每个物体采样点数')
    parser.add_argument('--visualize', action='store_true', help='可视化场景')
    parser.add_argument('--export', type=str, default=None, help='导出点云到文件')
    
    args = parser.parse_args()
    
    # 创建解析器
    parser = SceneParser(args.scene_file)
    
    # 打印场景信息
    print("\n场景物体列表:")
    for name, obj in parser.get_all_objects().items():
        print(f"  {name}: {obj['type']}, pos={obj['position']}, scale={obj['scale']}")
    
    # 如果指定target，进行采样
    if args.target:
        print(f"\n采样目标物体: {args.target}")
        target_points, obstacle_points = parser.sample_scene(
            args.target,
            num_target_points=args.num_points,
            num_obstacle_points=args.num_points * 3
        )
        print(f"  目标点云: {target_points.shape}")
        print(f"  障碍物点云: {obstacle_points.shape}")
        
        # 导出点云
        if args.export:
            np.savez(args.export,
                    target=target_points,
                    obstacles=obstacle_points)
            print(f"  已导出到: {args.export}")
    
    # 可视化
    if args.visualize:
        print("\n启动可视化...")
        parser.visualize_scene(target_name=args.target, 
                              num_points_per_object=args.num_points)


if __name__ == '__main__':
    main()
