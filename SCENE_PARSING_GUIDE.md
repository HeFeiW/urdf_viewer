# 场景生成和解析使用指南

## 功能概述

本模块提供两个核心工具：
1. **generate_random_scene.py** - 随机生成场景配置
2. **parse_scene.py** - 解析场景并采样点云用于运动规划

## 安装依赖

```bash
pip install -r requirements_scene.txt
```

核心依赖：
- numpy - 数值计算
- trimesh - Mesh处理和点云采样
- scipy - 科学计算

可选依赖：
- open3d - 3D可视化

---

## 1. 场景生成 (generate_random_scene.py)

### 基础用法

生成默认场景（3-10个随机物体）：
```bash
python3 generate_random_scene.py
```

### 常用参数

```bash
# 生成指定数量物体的场景
python3 generate_random_scene.py -n 15

# 控制物体尺寸范围
python3 generate_random_scene.py --min-size 0.02 --max-size 0.08

# 使用固定随机种子（可复现）
python3 generate_random_scene.py --seed 42

# 指定输出文件
python3 generate_random_scene.py -o my_scene.json

# 允许物体重叠（默认检测碰撞）
python3 generate_random_scene.py --allow-overlap
```

### 加载自定义OBJ形状

将OBJ文件放在一个目录中，然后：
```bash
python3 generate_random_scene.py --obj-dir ./obj_models
```

生成器会：
1. 自动加载目录中所有.obj文件
2. 计算每个mesh的边界框尺寸
3. 将OBJ形状加入物体类型池
4. 生成场景时可能使用这些自定义形状

生成的JSON会包含 `mesh_file` 字段指向OBJ文件路径。

### 场景配置格式

生成的JSON格式：
```json
{
  "description": "Random scene with 8 objects",
  "frame_id": "world",
  "objects": [
    {
      "name": "table",
      "type": "box",
      "position": [0.6, 0.0, 0.0],
      "orientation": [0, 0, 0],
      "scale": [1.0, 1.2, 0.05],
      "color": [0.6, 0.4, 0.2, 1.0]
    },
    {
      "name": "sphere_0",
      "type": "sphere",
      "position": [0.5, -0.3, 0.1],
      "scale": [0.08, 0.08, 0.08]
    },
    {
      "name": "custom_obj_1",
      "type": "mesh",
      "mesh_file": "/path/to/object.obj",
      "position": [0.7, 0.2, 0.15],
      "scale": [0.1, 0.1, 0.12]
    }
  ]
}
```

---

## 2. 场景解析 (parse_scene.py)

### Python API 使用

#### 基础使用

```python
from parse_scene import SceneParser

# 创建解析器并加载场景
parser = SceneParser('scene_config.json')

# 获取所有物体
objects = parser.get_all_objects()

# 获取指定物体
obj = parser.get_object('red_sphere')
print(obj['position'])  # [0.5, -0.3, 0.1]
print(obj['type'])      # 'sphere'
```

#### 点云采样

```python
# 在物体表面采样点
points = parser.sample_object_in_world('red_sphere', num_points=1000)
# 返回: numpy数组 (1000, 3)
```

#### Target和Obstacles采样

```python
# 指定一个物体为target，其他为obstacles
target_points, obstacle_points = parser.sample_scene(
    target_name='red_sphere',
    num_target_points=2000,
    num_obstacle_points=5000,
    exclude_objects=['table']  # 排除桌面
)

# target_points: (2000, 3)
# obstacle_points: (N, 3) 所有其他物体的点云合并
```

#### 坐标变换

```python
# 局部坐标系的点
local_points = np.array([[0.1, 0, 0], [0, 0.1, 0]])

# 变换到世界坐标系
position = np.array([1.0, 2.0, 0.5])
orientation = np.array([0, 0, np.pi/4])  # RPY
world_points = parser.transform_points(local_points, position, orientation)
```

#### Mesh操作

```python
# 获取物体的mesh
obj_info = parser.get_object('green_box')
mesh = parser.get_or_create_mesh(obj_info)

# Mesh属性
print(mesh.vertices)  # 顶点
print(mesh.faces)     # 面
print(mesh.volume)    # 体积
print(mesh.area)      # 表面积
```

#### 物体边界框

```python
# 获取物体在世界坐标系的边界框
min_bound, max_bound = parser.get_object_bounds('red_sphere')
size = max_bound - min_bound
```

#### 可视化（需要open3d）

```python
# 可视化整个场景
parser.visualize_scene(
    target_name='red_sphere',  # target显示为红色
    num_points_per_object=500
)
```

### 命令行使用

```bash
# 查看场景信息
python3 parse_scene.py scene_config.json

# 采样并导出点云
python3 parse_scene.py scene_config.json \
    --target red_sphere \
    --num-points 2000 \
    --export sampled.npz

# 可视化场景
python3 parse_scene.py scene_config.json \
    --target red_sphere \
    --visualize
```

---

## 3. 完整工作流程示例

### 步骤1: 生成随机场景

```bash
# 生成场景
python3 generate_random_scene.py -n 10 --seed 42 -o my_scene.json
```

### 步骤2: 解析和采样

```python
from parse_scene import SceneParser
import numpy as np

# 加载场景
parser = SceneParser('my_scene.json')

# 选择一个物体作为抓取目标
objects = parser.get_all_objects()
target_name = 'sphere_0'  # 或任何非桌面物体

# 采样点云
target_points, obstacle_points = parser.sample_scene(
    target_name=target_name,
    num_target_points=2000,
    num_obstacle_points=8000,
    exclude_objects=['table']
)

# 保存点云用于运动规划
np.savez('planning_data.npz',
         target=target_points,
         obstacles=obstacle_points,
         target_name=target_name)

print(f"目标点云: {target_points.shape}")
print(f"障碍物点云: {obstacle_points.shape}")
```

### 步骤3: 用于运动规划

```python
# 加载采样的点云
data = np.load('planning_data.npz')
target = data['target']
obstacles = data['obstacles']

# 传入你的运动规划算法
# plan = motion_planner.plan(
#     target_points=target,
#     obstacle_points=obstacles,
#     ...
# )
```

---

## 4. 高级用法

### 自定义OBJ物体

1. 准备OBJ文件（例如：cup.obj, bottle.obj）
2. 放入目录（例如：./custom_objects/）
3. 生成场景时指定目录：

```bash
python3 generate_random_scene.py --obj-dir ./custom_objects -n 15
```

场景JSON会包含：
```json
{
  "name": "cup_2",
  "type": "mesh",
  "mesh_file": "./custom_objects/cup.obj",
  "position": [0.5, 0.2, 0.1],
  "scale": [0.08, 0.08, 0.12]
}
```

解析时会自动加载OBJ文件。

### 批量生成场景

```bash
# 批量生成100个不同的场景
for i in {1..100}; do
    python3 generate_random_scene.py \
        --seed $i \
        -n $(( RANDOM % 8 + 3 )) \
        -o "scenes/scene_$i.json"
done
```

### 点云下采样

```python
# 如果点云太密集，可以下采样
def downsample_points(points, target_num):
    if len(points) <= target_num:
        return points
    indices = np.random.choice(len(points), target_num, replace=False)
    return points[indices]

target_points = downsample_points(target_points, 1000)
```

---

## 5. API参考

### SceneParser 主要方法

| 方法 | 说明 |
|------|------|
| `load_scene_from_json(path)` | 从JSON加载场景 |
| `get_object(name)` | 获取指定物体 |
| `get_all_objects()` | 获取所有物体字典 |
| `sample_object_in_world(name, num_points)` | 在世界坐标系采样物体 |
| `sample_scene(target_name, ...)` | 采样target和obstacles |
| `transform_points(points, pos, ori)` | 坐标变换 |
| `get_or_create_mesh(obj_info)` | 获取/创建mesh |
| `visualize_scene(target_name)` | 可视化场景 |

### 物体信息字典格式

```python
{
    'name': str,
    'type': str,  # 'box', 'sphere', 'cylinder', 'mesh'
    'position': np.ndarray,  # [x, y, z]
    'orientation': np.ndarray,  # [roll, pitch, yaw]
    'scale': np.ndarray,  # [sx, sy, sz]
    'color': list,  # [r, g, b, a]
    'mesh_file': str,  # 可选，OBJ文件路径
}
```

---

## 6. 故障排除

### 问题：trimesh导入失败
```bash
pip install trimesh
```

### 问题：可视化不工作
```bash
pip install open3d
```

### 问题：OBJ文件加载失败
- 确保OBJ文件格式正确
- 检查文件路径是否存在
- trimesh支持多种mesh格式（.obj, .stl, .ply等）

### 问题：点云采样太慢
- 减少采样点数
- 使用更简单的mesh（减少subdivisions）

---

## 7. 示例代码

运行完整示例：
```bash
python3 example_parse_scene.py
```

这会演示所有主要功能。

---

## 与ROS集成

场景解析模块可与show_urdf包配合使用：

```bash
# 1. 生成场景
python3 generate_random_scene.py -o scene_config.json

# 2. 在RViz中可视化
ros2 launch show_urdf trajectory_launch.py scene_config:=scene_config.json

# 3. 同时解析场景进行运动规划
python3 your_planning_script.py --scene scene_config.json
```

---

## 总结

- **generate_random_scene.py** - 快速生成测试场景
- **parse_scene.py** - 解析场景，采样点云
- 支持标准几何体（box/sphere/cylinder）和OBJ文件
- 提供完整的坐标变换和mesh操作
- 可选的3D可视化

更多示例请参考 `example_parse_scene.py`。
