#!/usr/bin/env python3
"""
场景解析和点云采样示例
展示如何使用parse_scene模块进行运动规划准备
"""

import numpy as np
from parse_scene import SceneParser


def example_basic_usage():
    """基础用法：加载场景并查看信息"""
    print("=" * 60)
    print("示例1: 基础用法 - 加载场景")
    print("=" * 60)
    
    # 创建解析器并加载场景
    parser = SceneParser('scene_config.json')
    
    # 获取所有物体
    objects = parser.get_all_objects()
    print(f"\n场景包含 {len(objects)} 个物体:")
    for name, obj in objects.items():
        print(f"  - {name}: {obj['type']}, "
              f"位置={obj['position']}, "
              f"尺寸={obj['scale']}")


def example_point_cloud_sampling():
    """示例2: 点云采样"""
    print("\n" + "=" * 60)
    print("示例2: 点云采样")
    print("=" * 60)
    
    parser = SceneParser('scene_config.json')
    
    # 对单个物体采样
    obj_name = 'red_sphere'
    if obj_name in parser.objects:
        points = parser.sample_object_in_world(obj_name, num_points=1000)
        print(f"\n对 {obj_name} 采样了 {len(points)} 个点")
        print(f"点云范围: min={np.min(points, axis=0)}, max={np.max(points, axis=0)}")
    else:
        print(f"\n物体 {obj_name} 不存在")


def example_target_obstacles():
    """示例3: 采样target和obstacles"""
    print("\n" + "=" * 60)
    print("示例3: Target和Obstacles采样")
    print("=" * 60)
    
    parser = SceneParser('scene_config.json')
    
    # 找一个非桌面的物体作为target
    non_table_objects = [name for name in parser.objects.keys() 
                        if name != 'table']
    
    if non_table_objects:
        target_name = non_table_objects[0]
        print(f"\n目标物体: {target_name}")
        
        # 采样target和obstacles
        target_points, obstacle_points = parser.sample_scene(
            target_name=target_name,
            num_target_points=2000,
            num_obstacle_points=5000,
            exclude_objects=['table']
        )
        
        print(f"目标点云形状: {target_points.shape}")
        print(f"障碍物点云形状: {obstacle_points.shape}")
        
        # 保存点云
        output_file = 'sampled_scene.npz'
        np.savez(output_file,
                target=target_points,
                obstacles=obstacle_points,
                target_name=target_name)
        print(f"\n点云已保存到: {output_file}")
        
        return target_points, obstacle_points
    else:
        print("\n场景中没有可用的物体")
        return None, None


def example_coordinate_transform():
    """示例4: 坐标变换"""
    print("\n" + "=" * 60)
    print("示例4: 坐标变换")
    print("=" * 60)
    
    parser = SceneParser('scene_config.json')
    
    # 在局部坐标系生成一些点
    local_points = np.array([
        [0.1, 0, 0],
        [0, 0.1, 0],
        [0, 0, 0.1]
    ])
    print("\n局部坐标系点:")
    print(local_points)
    
    # 定义变换
    position = np.array([1.0, 2.0, 0.5])
    orientation = np.array([0, 0, np.pi/4])  # 绕Z轴旋转45度
    
    # 应用变换
    world_points = parser.transform_points(local_points, position, orientation)
    print("\n世界坐标系点:")
    print(world_points)


def example_object_bounds():
    """示例5: 获取物体边界框"""
    print("\n" + "=" * 60)
    print("示例5: 物体边界框")
    print("=" * 60)
    
    parser = SceneParser('scene_config.json')
    
    print("\n所有物体的边界框:")
    for name in parser.objects.keys():
        try:
            min_bound, max_bound = parser.get_object_bounds(name)
            print(f"  {name}:")
            print(f"    最小: {min_bound}")
            print(f"    最大: {max_bound}")
            print(f"    尺寸: {max_bound - min_bound}")
        except Exception as e:
            print(f"  {name}: 错误 - {e}")


def example_visualization():
    """示例6: 可视化场景（需要open3d）"""
    print("\n" + "=" * 60)
    print("示例6: 可视化场景")
    print("=" * 60)
    
    try:
        import open3d as o3d
        
        parser = SceneParser('scene_config.json')
        
        # 找一个物体作为target
        non_table_objects = [name for name in parser.objects.keys() 
                            if name != 'table']
        
        if non_table_objects:
            target_name = non_table_objects[0]
            print(f"\n启动可视化，目标物体: {target_name} (显示为红色)")
            print("关闭窗口以继续...")
            
            parser.visualize_scene(target_name=target_name, 
                                 num_points_per_object=500)
        else:
            print("\n场景中没有可用的物体进行可视化")
            
    except ImportError:
        print("\n未安装open3d，跳过可视化")
        print("安装方法: pip install open3d")


def example_mesh_operations():
    """示例7: Mesh操作"""
    print("\n" + "=" * 60)
    print("示例7: Mesh操作")
    print("=" * 60)
    
    parser = SceneParser('scene_config.json')
    
    # 获取物体信息
    obj_name = 'green_box'
    if obj_name in parser.objects:
        obj_info = parser.get_object(obj_name)
        
        # 创建mesh
        mesh = parser.get_or_create_mesh(obj_info)
        
        print(f"\n{obj_name} 的mesh信息:")
        print(f"  顶点数: {len(mesh.vertices)}")
        print(f"  面数: {len(mesh.faces)}")
        print(f"  体积: {mesh.volume:.6f}")
        print(f"  表面积: {mesh.area:.6f}")
        print(f"  边界框: {mesh.bounds}")


def example_export_for_planning():
    """示例8: 导出用于运动规划的数据"""
    print("\n" + "=" * 60)
    print("示例8: 导出运动规划数据")
    print("=" * 60)
    
    parser = SceneParser('scene_config.json')
    
    # 导出所有物体信息
    export_data = parser.export_to_dict()
    
    print(f"\n导出的场景数据包含 {len(export_data['objects'])} 个物体")
    
    # 保存为JSON
    import json
    output_file = 'scene_for_planning.json'
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(export_data, f, indent=2)
    print(f"已保存到: {output_file}")


def main():
    """运行所有示例"""
    print("\n" + "=" * 60)
    print("场景解析模块使用示例")
    print("=" * 60)
    
    try:
        # 基础示例
        example_basic_usage()
        example_point_cloud_sampling()
        example_target_obstacles()
        example_coordinate_transform()
        example_object_bounds()
        example_mesh_operations()
        example_export_for_planning()
        
        # 可视化（可选）
        example_visualization()
        
        print("\n" + "=" * 60)
        print("所有示例完成！")
        print("=" * 60)
        
    except Exception as e:
        print(f"\n错误: {e}")
        import traceback
        traceback.print_exc()


if __name__ == '__main__':
    main()
