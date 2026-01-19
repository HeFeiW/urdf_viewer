#!/usr/bin/env python3
"""
测试 scene_publisher 对 mesh 物体的支持
"""

import os
import sys

# 添加路径
sys.path.append('/home/hefei/RDF_ori/show_urdf_ws')

def test_mesh_scene_generation():
    """测试生成包含 mesh 的场景"""
    from generate_random_scene import RandomSceneGenerator
    
    # 指定 OBJ 文件目录
    obj_dir = "/home/hefei/RDF_ori/show_urdf_ws/obj_dir"
    
    # 创建生成器
    generator = RandomSceneGenerator(seed=42, obj_dir=obj_dir)
    
    # 生成场景（包含3-5个物体）
    scene = generator.generate_scene(
        min_objects=3,
        max_objects=5,
        min_size=0.05,
        max_size=0.15,
        allow_overlap=False
    )
    
    # 保存到文件
    output_file = "/home/hefei/RDF_ori/show_urdf_ws/src/show_urdf/show_urdf/scene_with_mesh.json"
    generator.save_scene(scene, output_file)
    
    print(f"✓ 生成场景已保存到: {output_file}")
    print(f"  - 物体数量: {len(scene['objects']) - 1} (不含桌子)")
    
    # 统计物体类型
    obj_types = {}
    for obj in scene['objects']:
        if obj['name'] != 'table':
            obj_type = obj['type']
            obj_types[obj_type] = obj_types.get(obj_type, 0) + 1
    
    print(f"  - 物体类型分布:")
    for obj_type, count in obj_types.items():
        print(f"    * {obj_type}: {count}")

def test_scene_publisher_launch():
    """打印启动命令"""
    print("\n" + "="*60)
    print("启动 RViz 可视化场景（包含 mesh 物体）:")
    print("="*60)
    print("""
# 方式1: 使用生成的场景文件
cd /home/hefei/RDF_ori/show_urdf_ws
source install/setup.bash
ros2 launch show_urdf trajectory_launch.py \\
    scene_config:=scene_with_mesh.json \\
    with_scene:=True

# 方式2: 使用示例 mesh 场景
ros2 launch show_urdf trajectory_launch.py \\
    scene_config:=scene_config_with_mesh.json \\
    with_scene:=True

# 方式3: 仅发布场景（不启动轨迹和 RViz）
ros2 run show_urdf scene_publisher \\
    --ros-args \\
    -p scene_config:=scene_with_mesh.json
""")

def print_mesh_config_format():
    """打印 mesh 配置格式说明"""
    print("\n" + "="*60)
    print("Mesh 物体配置格式:")
    print("="*60)
    print("""
{
  "name": "mesh_object_name",
  "type": "mesh",
  "frame_id": "world",
  "position": [x, y, z],           // 世界坐标系位置 (米)
  "orientation": [roll, pitch, yaw], // 姿态角 (弧度)
  "scale": [sx, sy, sz],           // 缩放比例
  "color": [r, g, b, a],           // 颜色 (0-1)
  "mesh_file": "path/to/mesh.obj", // OBJ 文件路径
  "use_embedded_materials": false, // 是否使用嵌入的材质
  "description": "描述信息"
}

支持的 mesh_file 路径格式:
1. 绝对路径: /home/user/meshes/object.obj
2. 相对路径: obj_dir/object.obj (相对于包目录)
3. ROS 包路径: package://show_urdf/meshes/object.obj
4. file:// URI: file:///home/user/meshes/object.obj

注意事项:
- mesh_file 是必需字段（仅对 type="mesh"）
- scale 会应用到 mesh 上（默认 [1.0, 1.0, 1.0]）
- 如果 use_embedded_materials=true，会使用 OBJ 的材质（忽略 color）
- position 的 Z 坐标应该考虑桌面高度
""")

def print_supported_formats():
    """打印支持的物体类型"""
    print("\n" + "="*60)
    print("Scene Publisher 支持的物体类型:")
    print("="*60)
    print("""
1. box/cube (方块)
   - scale: [长度, 宽度, 高度]
   
2. sphere (球体)
   - scale: [直径, 直径, 直径] (三个值应该相同)
   
3. cylinder (圆柱体)
   - scale: [直径, 直径, 高度]
   
4. mesh (OBJ 网格模型) ✨ 新增
   - scale: [X缩放, Y缩放, Z缩放]
   - 需要额外的 mesh_file 字段
   - 支持 .obj 格式（其他格式可能也支持，如 .stl, .dae）

所有类型都支持:
- position: [x, y, z] 世界坐标
- orientation: [roll, pitch, yaw] 欧拉角（弧度）
- color: [r, g, b, a] RGBA 颜色（0.0-1.0）
- frame_id: 参考坐标系（默认 "world"）
""")

if __name__ == '__main__':
    print("="*60)
    print("Scene Publisher Mesh 支持测试")
    print("="*60)
    
    # 测试场景生成
    if os.path.exists("/home/hefei/RDF_ori/show_urdf_ws/obj_dir"):
        try:
            test_mesh_scene_generation()
        except Exception as e:
            print(f"⚠ 场景生成失败: {e}")
            print("  请确保已安装 trimesh: pip install trimesh")
    else:
        print("⚠ OBJ 目录不存在: /home/hefei/RDF_ori/show_urdf_ws/obj_dir")
        print("  跳过场景生成测试")
    
    # 打印使用说明
    test_scene_publisher_launch()
    print_mesh_config_format()
    print_supported_formats()
    
    print("\n" + "="*60)
    print("✓ 测试完成")
    print("="*60)
