#!/usr/bin/env python3
"""
随机生成场景配置文件
生成包含固定桌面和随机物体的场景
"""

import json
import random
import argparse
from pathlib import Path
from typing import Dict, List


class RandomSceneGenerator:
    def __init__(self, seed=None):
        """
        初始化场景生成器
        
        Args:
            seed: 随机种子，None则使用系统时间
        """
        if seed is not None:
            random.seed(seed)
        
        # 桌面参数（固定）
        self.table_config = {
            "position": [0.6, 0.0, 0.0],  # 桌面中心位置
            "size": [1.0, 1.2, 0.05],     # 桌面尺寸 (长x宽x高)
            "color": [0.6, 0.4, 0.2, 1.0]
        }
        
        # 物体类型配置
        self.object_types = ['box', 'sphere', 'cylinder']
        
        # 颜色池
        self.colors = [
            [1.0, 0.0, 0.0, 1.0],  # 红
            [0.0, 1.0, 0.0, 1.0],  # 绿
            [0.0, 0.0, 1.0, 1.0],  # 蓝
            [1.0, 1.0, 0.0, 1.0],  # 黄
            [1.0, 0.0, 1.0, 1.0],  # 洋红
            [0.0, 1.0, 1.0, 1.0],  # 青
            [1.0, 0.5, 0.0, 1.0],  # 橙
            [0.5, 0.0, 1.0, 1.0],  # 紫
            [1.0, 0.75, 0.8, 1.0], # 粉
            [0.5, 0.5, 0.5, 1.0],  # 灰
        ]
    
    def generate_scene(self, num_objects: int = None, 
                      min_objects: int = 3, 
                      max_objects: int = 10,
                      min_size: float = 0.03,
                      max_size: float = 0.15,
                      allow_overlap: bool = False) -> Dict:
        """
        生成随机场景
        
        Args:
            num_objects: 物体数量，None则随机
            min_objects: 最小物体数量
            max_objects: 最大物体数量
            min_size: 最小物体尺寸
            max_size: 最大物体尺寸
            allow_overlap: 是否允许物体重叠
            
        Returns:
            场景配置字典
        """
        if num_objects is None:
            num_objects = random.randint(min_objects, max_objects)
        
        scene = {
            "description": f"Random scene with {num_objects} objects",
            "frame_id": "world",
            "objects": []
        }
        
        # 添加固定桌面
        table = self._create_table()
        scene["objects"].append(table)
        
        # 生成随机物体
        placed_objects = []
        attempts = 0
        max_attempts = num_objects * 50  # 防止无限循环
        
        while len(placed_objects) < num_objects and attempts < max_attempts:
            attempts += 1
            obj = self._create_random_object(
                len(placed_objects), 
                min_size, 
                max_size
            )
            
            # 检查碰撞
            if allow_overlap or not self._check_collision(obj, placed_objects):
                placed_objects.append(obj)
                scene["objects"].append(obj)
        
        if len(placed_objects) < num_objects:
            print(f"警告: 只成功放置了 {len(placed_objects)}/{num_objects} 个物体")
        
        return scene
    
    def _create_table(self) -> Dict:
        """创建固定桌面"""
        pos = self.table_config["position"]
        size = self.table_config["size"]
        
        return {
            "name": "table",
            "type": "box",
            "frame_id": "world",
            "position": pos,
            "orientation": [0, 0, 0],
            "scale": size,
            "color": self.table_config["color"],
            "description": "Fixed table surface"
        }
    
    def _create_random_object(self, index: int, 
                            min_size: float, 
                            max_size: float) -> Dict:
        """创建随机物体"""
        obj_type = random.choice(self.object_types)
        color = random.choice(self.colors)
        
        # 随机尺寸
        if obj_type == 'sphere':
            # 球体使用单一尺寸
            size = random.uniform(min_size, max_size)
            scale = [size, size, size]
        elif obj_type == 'cylinder':
            # 圆柱体：直径和高度
            diameter = random.uniform(min_size, max_size)
            height = random.uniform(min_size * 1.5, max_size * 2)
            scale = [diameter, diameter, height]
        else:  # box
            # 方块：三个维度独立
            scale = [
                random.uniform(min_size, max_size),
                random.uniform(min_size, max_size),
                random.uniform(min_size, max_size * 1.5)
            ]
        
        # 计算桌面边界
        table_pos = self.table_config["position"]
        table_size = self.table_config["size"]
        table_half_x = table_size[0] / 2
        table_half_y = table_size[1] / 2
        table_top_z = table_pos[2] + table_size[2] / 2
        
        # 在桌面范围内随机位置，留出边距
        margin = 0.05
        x = table_pos[0] + random.uniform(-table_half_x + margin, table_half_x - margin)
        y = table_pos[1] + random.uniform(-table_half_y + margin, table_half_y - margin)
        
        # Z 位置：桌面顶部 + 物体高度的一半
        z = table_top_z + scale[2] / 2
        
        # 随机朝向（仅绕 Z 轴旋转）
        yaw = random.uniform(-3.14159, 3.14159)
        
        return {
            "name": f"{obj_type}_{index}",
            "type": obj_type,
            "frame_id": "world",
            "position": [round(x, 4), round(y, 4), round(z, 4)],
            "orientation": [0, 0, round(yaw, 4)],
            "scale": [round(s, 4) for s in scale],
            "color": color,
            "description": f"Random {obj_type}"
        }
    
    def _check_collision(self, new_obj: Dict, existing_objects: List[Dict]) -> bool:
        """
        简单的2D碰撞检测（俯视图，忽略高度）
        
        Args:
            new_obj: 新物体
            existing_objects: 已放置物体列表
            
        Returns:
            True 如果碰撞，False 如果不碰撞
        """
        new_pos = new_obj["position"]
        new_scale = new_obj["scale"]
        
        # 获取新物体的边界半径（2D）
        new_radius = max(new_scale[0], new_scale[1]) / 2
        
        for obj in existing_objects:
            obj_pos = obj["position"]
            obj_scale = obj["scale"]
            obj_radius = max(obj_scale[0], obj_scale[1]) / 2
            
            # 计算2D距离
            dx = new_pos[0] - obj_pos[0]
            dy = new_pos[1] - obj_pos[1]
            distance = (dx**2 + dy**2)**0.5
            
            # 添加安全边距
            min_distance = new_radius + obj_radius + 0.01
            
            if distance < min_distance:
                return True
        
        return False
    
    def save_to_file(self, scene: Dict, output_path: str):
        """保存场景到文件"""
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(scene, f, indent=2, ensure_ascii=False)
        print(f"场景已保存到: {output_path}")
        print(f"包含 {len(scene['objects'])} 个物体 (1个桌面 + {len(scene['objects'])-1}个随机物体)")


def main():
    parser = argparse.ArgumentParser(
        description='生成随机场景配置文件',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  # 生成默认场景（3-10个物体）
  python3 generate_random_scene.py
  
  # 生成包含15个物体的场景
  python3 generate_random_scene.py -n 15
  
  # 生成小物体场景
  python3 generate_random_scene.py --min-size 0.02 --max-size 0.08
  
  # 使用固定随机种子（可复现）
  python3 generate_random_scene.py --seed 42
  
  # 指定输出文件
  python3 generate_random_scene.py -o my_scene.json
        """
    )
    
    parser.add_argument(
        '-n', '--num-objects',
        type=int,
        default=None,
        help='物体数量（不含桌面），不指定则随机3-10个'
    )
    parser.add_argument(
        '--min-objects',
        type=int,
        default=3,
        help='最小物体数量（当-n未指定时）'
    )
    parser.add_argument(
        '--max-objects',
        type=int,
        default=10,
        help='最大物体数量（当-n未指定时）'
    )
    parser.add_argument(
        '--min-size',
        type=float,
        default=0.03,
        help='物体最小尺寸（米）'
    )
    parser.add_argument(
        '--max-size',
        type=float,
        default=0.15,
        help='物体最大尺寸（米）'
    )
    parser.add_argument(
        '--seed',
        type=int,
        default=None,
        help='随机种子（用于复现）'
    )
    parser.add_argument(
        '--allow-overlap',
        action='store_true',
        help='允许物体重叠'
    )
    parser.add_argument(
        '-o', '--output',
        type=str,
        default='scene_config.json',
        help='输出文件路径'
    )
    
    args = parser.parse_args()
    
    # 创建生成器
    generator = RandomSceneGenerator(seed=args.seed)
    
    # 生成场景
    print(f"正在生成随机场景...")
    if args.seed is not None:
        print(f"使用随机种子: {args.seed}")
    
    scene = generator.generate_scene(
        num_objects=args.num_objects,
        min_objects=args.min_objects,
        max_objects=args.max_objects,
        min_size=args.min_size,
        max_size=args.max_size,
        allow_overlap=args.allow_overlap
    )
    
    # 保存
    generator.save_to_file(scene, args.output)
    
    # 打印物体类型统计
    type_counts = {}
    for obj in scene["objects"]:
        if obj["name"] != "table":
            obj_type = obj["type"]
            type_counts[obj_type] = type_counts.get(obj_type, 0) + 1
    
    print("\n物体类型统计:")
    for obj_type, count in sorted(type_counts.items()):
        print(f"  {obj_type}: {count}")


if __name__ == '__main__':
    main()
