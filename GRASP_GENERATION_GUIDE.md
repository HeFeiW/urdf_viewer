# 抓取生成与可视化使用指南

## 功能概述

该工具集成了 lightning-grasp 和 show_urdf，实现以下功能：
1. 从场景中选择目标物体
2. 使用 lightning-grasp 生成抓取姿态
3. 将抓取从 canonical 空间转换到场景空间
4. 进行碰撞检查（与桌面）
5. 在 RViz 中可视化选中的抓取

## 依赖安装

```bash
# 安装 lightning-grasp 依赖
cd /home/hefei/lightning-grasp
pip install -e .

# 确保已安装 ROS2 和 show_urdf
cd /home/hefei/RDF_ori/show_urdf_ws
colcon build --packages-select show_urdf
source install/setup.bash
```

## 使用流程

### 1. 生成随机场景（可选）

如果还没有场景配置：

```bash
cd /home/hefei/RDF_ori/show_urdf_ws

# 生成包含YCB物体的场景
python3 generate_random_scene.py \
    --obj-dir /home/hefei/lightning-grasp/assets/object/ycb \
    -n 5 \
    -o scene_config.json
```

### 2. 生成抓取

从场景中选择物体并生成抓取：

```bash
# 随机选择一个物体
python3 grasp_generation.py \
    --scene scene_config.json \
    --robot leap \
    --batch-outer 32 \
    --batch-inner 32 \
    --output selected_grasp.json

# 或指定目标物体
python3 grasp_generation.py \
    --scene scene_config.json \
    --robot leap \
    --target "013_apple_0" \
    --output selected_grasp.json
```

参数说明：
- `--scene`: 场景配置文件路径
- `--robot`: 机器人类型 (leap/leap/shadow/dclaw)
- `--target`: 目标物体名称（可选，不指定则随机选择）
- `--batch-outer`: 外层batch大小（物体位姿采样数量）
- `--batch-inner`: 内层batch大小（接触域变体数量）
- `--output`: 输出文件路径
- `--seed`: 随机种子（可选，用于复现）

输出示例：
```
加载场景...
选中目标物体: 013_apple_0 (type: mesh)
加载物体mesh...
物体mesh顶点数: 2048, 面片数: 4096
物体在场景中的位置: [0.6, 0.3, 0.07]
物体在场景中的姿态: [0, 0.0, -0.036]
初始化 lightning-grasp...
开始生成抓取...
生成了 156 个有效抓取
检查碰撞...
碰撞检查: 128/156 个抓取有效
选择抓取 #0
手基座在场景中的位置: [0.65, 0.32, 0.15]
抓取数据已保存到: selected_grasp.json

完成! 使用以下命令可视化:
  python3 visualize_grasp_rviz.py --grasp selected_grasp.json --scene scene_config.json
```

### 3. 在 RViz 中可视化

#### 方法 1：使用 launch 文件（推荐）

```bash
# 启动场景可视化
ros2 launch show_urdf trajectory_launch.py \
    scene_config:=scene_config.json \
    with_scene:=True \
    with_rviz:=True

# 在另一个终端启动抓取可视化
python3 visualize_grasp_rviz.py \
    --grasp selected_grasp.json \
    --scene scene_config.json
```

#### 方法 2：独立启动各组件

```bash
# 终端1：启动 RViz
ros2 run rviz2 rviz2

# 终端2：发布场景
ros2 run show_urdf scene_publisher --ros-args \
    -p scene_config:=scene_config.json

# 终端3：发布抓取
python3 visualize_grasp_rviz.py \
    --grasp selected_grasp.json \
    --scene scene_config.json
```

在 RViz 中添加以下显示：
- **RobotModel**: 显示手的模型
  - Topic: `/robot_description`
  - TF Prefix: `hand_`
- **MarkerArray**: 显示场景物体
  - Topic: `/visualization_marker_array`
- **TF**: 显示坐标系
- **Grid**: 参考网格（Fixed Frame: `world`）

## 输出文件格式

### 抓取数据 (selected_grasp.json)

```json
{
  "robot_name": "leap",
  "joint_angles": [0.1, 0.2, ...],
  "hand_base_position": [0.65, 0.32, 0.15],
  "hand_base_orientation": [0.0, 0.1, 0.5],
  "hand_base_transform": [[...], [...], [...], [...]]
}
```

字段说明：
- `robot_name`: 机器人类型
- `joint_angles`: 关节角度列表（弧度）
- `hand_base_position`: 手基座在世界坐标系中的位置 [x, y, z]
- `hand_base_orientation`: 手基座姿态 [roll, pitch, yaw]（弧度）
- `hand_base_transform`: 4x4 变换矩阵

## 高级用法

### 批量生成多个抓取

```python
import json

# 生成多个抓取并保存
for i in range(5):
    os.system(f"""
        python3 grasp_generation.py \
            --scene scene_config.json \
            --robot leap \
            --seed {i} \
            --output grasp_{i}.json
    """)
```

### 自定义碰撞检查

修改 `grasp_generation.py` 中的 `filter_grasps_by_collision()` 函数：

```python
def filter_grasps_by_collision(result, robot, tree, scene, scene_object_transform):
    # 添加自定义碰撞检查逻辑
    # 例如：检查与其他物体的碰撞
    
    for obj in scene['objects']:
        if obj['name'] == 'table':
            # 检查与桌面的碰撞
            if check_collision_with_table(hand_mesh, obj):
                continue
        
        elif obj['type'] == 'mesh':
            # 检查与其他物体的碰撞
            if check_collision_with_mesh(hand_mesh, obj):
                continue
    
    return valid_indices
```

### 调整抓取生成参数

在 `generate_grasps_lightning()` 函数中调整参数：

```python
# 增加采样点数以提高精度
n_sample_point = 4096  # 默认 2048

# 增加IK迭代次数
ik_finetune_iter = 10  # 默认 5

# 调整接触点数量
n_contact = 4  # 默认 3
```

## 故障排除

### 问题1：CUDA out of memory

解决方案：减少 batch 大小

```bash
python3 grasp_generation.py \
    --batch-outer 16 \
    --batch-inner 16
```

### 问题2：没有生成有效抓取

原因：
- 物体太小或形状不适合抓取
- batch 大小太小

解决方案：
```bash
# 增加 batch 大小
python3 grasp_generation.py \
    --batch-outer 128 \
    --batch-inner 128
```

### 问题3：所有抓取都碰撞

原因：
- 物体离桌面太近
- 桌面配置不正确

解决方案：
```bash
# 重新生成场景，增加物体尺寸约束
python3 generate_random_scene.py \
    --min-size 0.05 \
    --max-size 0.20
```

### 问题4：RViz 中看不到手模型

检查项：
1. 确认 `robot_description` topic 有数据
2. 确认 TF tree 正确
3. 检查 `hand_base` frame 是否发布

```bash
# 检查 topics
ros2 topic list | grep robot_description

# 检查 TF
ros2 run tf2_tools view_frames
```

## 示例工作流程

完整的端到端示例：

```bash
# 1. 生成场景
python3 generate_random_scene.py \
    --obj-dir /home/hefei/lightning-grasp/assets/object/ycb \
    -n 6 \
    --seed 42 \
    -o my_scene.json

# 2. 生成抓取
python3 grasp_generation.py \
    --scene my_scene.json \
    --robot leap \
    --batch-outer 64 \
    --batch-inner 64 \
    --seed 42 \
    --output my_grasp.json

# 3. 可视化场景
ros2 launch show_urdf trajectory_launch.py \
    scene_config:=my_scene.json \
    with_scene:=True &

# 4. 可视化抓取（在另一个终端）
python3 visualize_grasp_rviz.py \
    --grasp my_grasp.json \
    --scene my_scene.json
```

## 性能建议

- 对于快速测试：`--batch-outer 32 --batch-inner 32`
- 对于高质量抓取：`--batch-outer 128 --batch-inner 128`
- GPU 内存有限：减少 batch 大小或 `n_sample_point`

## 下一步开发

计划中的功能：
- [ ] 与其他物体的碰撞检查
- [ ] 多个抓取的可视化对比
- [ ] 抓取质量评分
- [ ] 轨迹规划集成
- [ ] 实时抓取更新

---

更多信息请参考：
- Lightning-Grasp: https://github.com/lightning-grasp
- Show-URDF: `/home/hefei/RDF_ori/show_urdf_ws/USAGE.md`
