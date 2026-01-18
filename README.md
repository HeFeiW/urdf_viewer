# show_urdf：URDF可视化与轨迹回放
[GitHub链接](https://github.com/HeFeiW/urdf_viewer.git)

## 主要改动
1. 支持机器人 Base 6 自由度可视化（world 固定，base 可移动和旋转）。
2. 轨迹回放节点：从 JSON 加载轨迹并发布到 /joint_states（支持数组或关节名映射）。
3. 场景可视化：通过场景配置文件在 RViz 中显示静态物体。
4. 增加默认 RViz 配置文件。

## 目录结构（关键部分）
```
|-- workspace/
        |-- src/
                |-- show_urdf/
                |   |-- launch/
                |   |   |-- display_launch.py
                |   |   |-- trajectory_launch.py
        |   |   |-- trajectory_json_launch.py
        |   |-- rviz/
        |   |   |-- show_urdf.rviz
                |   |-- panda.urdf
                |   |-- panda_with_base.urdf
                |   |-- trajectory_publisher.py
                |   |-- scene_publisher.py
                |   |-- trajectory.json
                |   |-- scene_config.json
                |-- package.xml
                |-- setup.py
```

## 使用方法

### 1) 编译
```bash
cd /home/hefei/RDF_ori/show_urdf_ws
colcon build --packages-select show_urdf
source install/setup.bash
```

### 2) 基础可视化（GUI调关节）
```bash
ros2 launch show_urdf display_launch.py
```
说明：默认使用panda_with_base.urdf，可在GUI里控制14个DOF（6个base + 7个关节 + 1个夹爪）。

可选参数：
```bash
ros2 launch show_urdf display_launch.py urdf:=panda.urdf gui:=True
ros2 launch show_urdf display_launch.py with_scene:=True scene_config:=scene_config.json
```

### 3) 轨迹回放 + 场景
```bash
ros2 launch show_urdf trajectory_launch.py
```
常用参数示例：
```bash
ros2 launch show_urdf trajectory_launch.py trajectory_file:=trajectory.json
ros2 launch show_urdf trajectory_launch.py with_scene:=False
ros2 launch show_urdf trajectory_launch.py with_rviz:=False
ros2 launch show_urdf trajectory_launch.py \
    robot_model:=panda_with_base \
    trajectory_file:=/path/to/trajectory.json \
    scene_config:=/path/to/scene_config.json
ros2 launch show_urdf trajectory_launch.py rviz_config:=/path/to/custom.rviz
```

### 4) JSON 轨迹启动文件（新）
```bash
ros2 launch show_urdf trajectory_json_launch.py
```

该 launch 与 trajectory_launch.py 行为一致，保留在此用于区分用途。

## 轨迹 JSON 格式
支持两种写法：

### 1) 数组格式
```json
{
    "description": "轨迹描述",
    "robot_model": "panda_with_base",
    "trajectory": [
        {"time_interval": 0.01, "joints": [0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0]}
    ]
}
```
关节顺序（panda_with_base）：
1. panda_base_x, panda_base_y, panda_base_z
2. panda_base_roll, panda_base_pitch, panda_base_yaw
3. panda_joint1 - panda_joint7
4. panda_finger_joint1（panda_finger_joint2为mimic）

### 2) 映射格式（推荐）
```json
{
    "trajectory": [
        {
            "time_interval": 0.02,
            "joints": {
                "panda_base_x": 0.1,
                "panda_base_y": 0.0,
                "panda_base_z": 0.0,
                "panda_base_roll": 0.0,
                "panda_base_pitch": 0.2,
                "panda_base_yaw": 0.0,
                "panda_joint1": 0.1,
                "panda_joint2": -0.2,
                "panda_joint3": 0.3,
                "panda_joint4": 0.0,
                "panda_joint5": 0.2,
                "panda_joint6": 0.0,
                "panda_joint7": 0.1,
                "panda_finger_joint1": 0.02
            }
        }
    ]
}
```

## 场景配置 JSON 格式
```json
{
    "description": "场景描述",
    "frame_id": "world",
    "objects": [
        {
            "name": "box_1",
            "type": "box",
            "frame_id": "world",
            "position": [0.5, 0.0, 0.1],
            "orientation": [0, 0, 0],
            "scale": [0.2, 0.2, 0.2],
            "color": [1.0, 0.0, 0.0, 1.0]
        }
    ]
}
```

## 注意事项
- URDF与mesh路径需保持一致，例如：
```xml
<mesh filename="package://show_urdf/meshes/panda_link1.stl"/>
```
- 若自定义JSON文件，请使用绝对路径或放在包的share目录。
- 默认 RViz 配置文件位于 [src/show_urdf/show_urdf/rviz/show_urdf.rviz](src/show_urdf/show_urdf/rviz/show_urdf.rviz)，launch 默认加载该配置。
