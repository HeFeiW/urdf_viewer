# `show_urdf`：用于可视化URDF文件的工具。
[GitHub链接](https://github.com/HeFeiW/urdf_viewer.git)  
## 目录结构
```
|-- workspace/
    |-- src/
        |-- show_urdf/
        |   |-- __init__.py
        |   |-- meshes/
        |   |-- dexhand-meshes/
        |   |-- leaphand-meshes/
        |   |-- launch/
        |   |   |-- display_launch.py
        |   |-- broadcast_rot.py
        |   |-- panda.urdf
        |   |-- dexhand.urdf
        |   |-- leaphand.urdf
        |
        |-- package.xml
        |-- setup.py
```
## 使用：  
环境配置见`Dockerfile`，也可以手动安装所需ROS2包(`robot_state_publisher_gui`)。
```
ros
```
```bash
cd workspace
colcon build
source install/setup.bash
ros2 launch show_urdf display_launch.py robot:=panda.urdf # choices: panda.urdf, dexhand.urdf, leaphand.urdf，指定使用的urdf文件相对于包目录的路径。
```
加载不同的URDF文件和对应的meshes以可视化对应机器人。提供GUI界面以交互式调整机器人关节角度。
使用时要在setup.py中指定正确的URDF文件路径，meshes路径等，才能在build后正确加载资源。例如：
```python
# setup.py
# ...
def get_data_files():
    data_files = [('share/' + package_name, ['package.xml'])]
    directories_to_install = [# 在此处添加需要安装的目录（在package中即src/show_urdf/的路径）
        'launch',
        'meshes',
        'leaphand-meshes',
        'dexhand-meshes',
    ]
# ...
```
另外，需要检查urdf文件中mesh路径是否正确。例如：
```xml
<mesh filename="package://show_urdf/meshes/panda_link1.stl"/>
```
