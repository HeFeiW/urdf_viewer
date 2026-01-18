#!/usr/bin/env python3
"""
场景配置文件生成工具

这个脚本展示如何以编程方式生成场景JSON配置文件。
"""

import json
import math
from typing import List, Dict, Any

def generate_assembly_scene() -> Dict[str, Any]:
    """生成装配任务场景"""
    objects = [
        {
            "name": "assembly_table",
            "type": "box",
            "position": [0.8, 0.0, -0.4],
            "orientation": [0, 0, 0],
            "scale": [0.8, 0.6, 0.02],
            "color": [0.4, 0.25, 0.1, 1.0],
            "description": "装配工作台"
        },
        {
            "name": "base_component",
            "type": "box",
            "position": [0.6, -0.15, 0.1],
            "orientation": [0, 0, 0],
            "scale": [0.15, 0.1, 0.05],
            "color": [0.8, 0.8, 0.8, 1.0],
            "description": "基座组件"
        },
        {
            "name": "top_component",
            "type": "box",
            "position": [0.8, -0.15, 0.1],
            "orientation": [0, 0, 0],
            "scale": [0.1, 0.1, 0.08],
            "color": [0.2, 0.2, 0.2, 1.0],
            "description": "顶部组件"
        },
        {
            "name": "screw_pile",
            "type": "cylinder",
            "position": [1.0, -0.15, 0.1],
            "orientation": [0, 1.57, 0],
            "scale": [0.01, 0.01, 0.1],
            "color": [0.9, 0.9, 0.1, 1.0],
            "description": "螺钉堆"
        }
    ]
    
    return {
        "description": "机器人装配任务场景",
        "objects": objects
    }

def generate_cluttered_scene() -> Dict[str, Any]:
    """生成物体堆放场景"""
    objects = []
    
    # 添加工作台
    objects.append({
        "name": "workspace_table",
        "type": "box",
        "position": [0.8, 0.0, -0.3],
        "orientation": [0, 0, 0],
        "scale": [1.0, 0.8, 0.02],
        "color": [0.6, 0.4, 0.2, 1.0],
        "description": "工作区"
    })
    
    # 添加多个物体（模拟堆放）
    colors = [
        [1.0, 0.0, 0.0, 1.0],  # 红
        [0.0, 0.0, 1.0, 1.0],  # 蓝
        [0.0, 1.0, 0.0, 1.0],  # 绿
        [1.0, 1.0, 0.0, 1.0],  # 黄
        [1.0, 0.0, 1.0, 1.0],  # 洋红
    ]
    
    # 第一排物体
    for i in range(3):
        objects.append({
            "name": f"sphere_{i}",
            "type": "sphere",
            "position": [0.5 + i*0.15, -0.3, 0.1],
            "orientation": [0, 0, 0],
            "scale": [0.08, 0.08, 0.08],
            "color": colors[i % len(colors)],
            "description": f"球体 {i+1}"
        })
    
    # 第二排物体
    for i in range(3):
        objects.append({
            "name": f"box_{i}",
            "type": "box",
            "position": [0.5 + i*0.15, 0.0, 0.1],
            "orientation": [0.1*i, 0, 0],
            "scale": [0.12, 0.08, 0.08],
            "color": colors[(i+2) % len(colors)],
            "description": f"方块 {i+1}"
        })
    
    # 第三排物体
    for i in range(2):
        objects.append({
            "name": f"cylinder_{i}",
            "type": "cylinder",
            "position": [0.55 + i*0.2, 0.3, 0.1],
            "orientation": [1.57, 0, 0],
            "scale": [0.06, 0.06, 0.12],
            "color": colors[(i+4) % len(colors)],
            "description": f"圆柱 {i+1}"
        })
    
    return {
        "description": "物体堆放场景（拣选和放置任务）",
        "objects": objects
    }

def generate_structured_scene() -> Dict[str, Any]:
    """生成有规律的场景（网格布局）"""
    objects = []
    
    # 工作台
    objects.append({
        "name": "main_table",
        "type": "box",
        "position": [0.5, 0.0, -0.35],
        "orientation": [0, 0, 0],
        "scale": [1.2, 0.6, 0.02],
        "color": [0.5, 0.35, 0.15, 1.0],
        "description": "主工作台"
    })
    
    # 物体网格排列 (3x3)
    positions = []
    for i in range(3):
        for j in range(3):
            x = 0.3 + i * 0.2
            y = -0.2 + j * 0.2
            positions.append((x, y, 0.15))
    
    obj_types = ["sphere", "box", "cylinder"]
    
    for idx, (x, y, z) in enumerate(positions):
        obj_type = obj_types[idx % 3]
        color_idx = (idx // 3) % 5
        colors = [
            [1.0, 0.3, 0.3, 1.0],
            [0.3, 0.8, 1.0, 1.0],
            [0.2, 0.9, 0.3, 1.0],
            [1.0, 0.9, 0.2, 1.0],
            [0.8, 0.3, 0.8, 1.0]
        ]
        
        scale = [0.06, 0.06, 0.06]
        if obj_type == "cylinder":
            scale = [0.05, 0.05, 0.12]
        
        objects.append({
            "name": f"{obj_type}_{idx}",
            "type": obj_type,
            "position": [x, y, z],
            "orientation": [0, 0, 0],
            "scale": scale,
            "color": colors[color_idx],
            "description": f"{obj_type} {idx+1}"
        })
    
    return {
        "description": "规律网格场景（适合测试精确放置）",
        "objects": objects
    }

def generate_warehouse_scene() -> Dict[str, Any]:
    """生成仓库/货架场景"""
    objects = []
    
    # 地面
    objects.append({
        "name": "ground",
        "type": "box",
        "position": [0.0, 0.0, -0.5],
        "orientation": [0, 0, 0],
        "scale": [3.0, 2.0, 0.02],
        "color": [0.3, 0.3, 0.3, 0.5],
        "description": "地面"
    })
    
    # 左侧货架
    objects.append({
        "name": "shelf_left",
        "type": "box",
        "position": [-0.3, 0.0, 0.0],
        "orientation": [0, 0, 0],
        "scale": [0.05, 0.5, 0.5],
        "color": [0.4, 0.2, 0.0, 1.0],
        "description": "左侧货架"
    })
    
    # 右侧货架
    objects.append({
        "name": "shelf_right",
        "type": "box",
        "position": [0.3, 0.0, 0.0],
        "orientation": [0, 0, 0],
        "scale": [0.05, 0.5, 0.5],
        "color": [0.4, 0.2, 0.0, 1.0],
        "description": "右侧货架"
    })
    
    # 货架上的物品
    for shelf_x in [-0.3, 0.3]:
        for level in range(3):
            z = -0.15 + level * 0.25
            for item in range(2):
                y = -0.1 + item * 0.2
                objects.append({
                    "name": f"item_shelf_{int(shelf_x*10)}_{level}_{item}",
                    "type": "box",
                    "position": [shelf_x, y, z],
                    "orientation": [0, 0, 0],
                    "scale": [0.08, 0.08, 0.08],
                    "color": [1.0, 0.8, 0.0, 1.0],
                    "description": f"货架物品 {level+1}-{item+1}"
                })
    
    # 工作台
    objects.append({
        "name": "workbench",
        "type": "box",
        "position": [0.0, -0.5, -0.25],
        "orientation": [0, 0, 0],
        "scale": [0.6, 0.3, 0.02],
        "color": [0.6, 0.4, 0.2, 1.0],
        "description": "工作台"
    })
    
    return {
        "description": "仓库/货架场景",
        "objects": objects
    }

def save_scene(scene_dict: Dict[str, Any], filename: str):
    """保存场景配置到JSON文件"""
    with open(filename, 'w') as f:
        json.dump(scene_dict, f, indent=2)
    print(f"✓ 场景已保存到: {filename} ({len(scene_dict['objects'])} 个物体)")

if __name__ == '__main__':
    print("生成场景配置文件...\n")
    
    # 1. 装配任务场景
    print("1. 生成装配任务场景...")
    assembly = generate_assembly_scene()
    save_scene(assembly, 'scene_assembly.json')
    
    # 2. 物体堆放场景
    print("2. 生成物体堆放场景...")
    cluttered = generate_cluttered_scene()
    save_scene(cluttered, 'scene_cluttered.json')
    
    # 3. 有规律的网格场景
    print("3. 生成规律网格场景...")
    structured = generate_structured_scene()
    save_scene(structured, 'scene_structured.json')
    
    # 4. 仓库场景
    print("4. 生成仓库货架场景...")
    warehouse = generate_warehouse_scene()
    save_scene(warehouse, 'scene_warehouse.json')
    
    print("\n所有场景文件已生成！")
    print("\n使用方法:")
    print("ros2 launch show_urdf trajectory_launch.py scene_config:=scene_assembly.json")
    print("ros2 launch show_urdf trajectory_launch.py scene_config:=scene_cluttered.json")
    print("ros2 launch show_urdf trajectory_launch.py scene_config:=scene_structured.json")
    print("ros2 launch show_urdf trajectory_launch.py scene_config:=scene_warehouse.json")
