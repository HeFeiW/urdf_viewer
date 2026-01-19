from setuptools import setup, find_packages
import os
from glob import glob

package_name = 'show_urdf'

# 递归获取所有文件
def collect_data_files(base_dir, rel_dir):
    abs_dir = os.path.join(base_dir, rel_dir)
    collected = []
    if not os.path.exists(abs_dir):
        return collected
    for entry in os.listdir(abs_dir):
        entry_path = os.path.join(abs_dir, entry)
        entry_rel = os.path.join(rel_dir, entry)
        if os.path.isfile(entry_path):
            collected.append((os.path.join('share', package_name, rel_dir), [entry_path]))
        elif os.path.isdir(entry_path):
            collected += collect_data_files(base_dir, entry_rel)
    return collected

def get_data_files():
    data_files = [('share/' + package_name, ['package.xml'])]
    directories_to_install = [
        'launch',
        'meshes',
        'leaphand-meshes',
        'dexhand-meshes',
        'rviz',
        'config',
        'obj_dir',
    ]
    for directory in directories_to_install:
        data_files += collect_data_files(package_name, directory)
    data_files += [
        (
            os.path.join('share', package_name),
            [
                os.path.join(package_name, 'panda.urdf'),
                os.path.join(package_name, 'panda_with_base.urdf'),
                os.path.join(package_name, 'dexhand.urdf'),
                os.path.join(package_name, 'leaphand.urdf'),
                os.path.join(package_name, 'leaphand_with_base.urdf'),
            ]
        )
    ]
    return data_files
    
setup(
    name=package_name,
    version='0.0.0',
    packages=find_packages(),
    data_files=get_data_files(),
    install_requires=['setuptools'],
    zip_safe=True,
    maintainer='HeFeiW',
    maintainer_email='hefei1504@163.com',
    description='TODO: Package description',
    license='TODO: License declaration',
    entry_points={
        'console_scripts': [
            'broadcast_rot = show_urdf.broadcast_rot:main',
            'trajectory_publisher = show_urdf.trajectory_publisher:main',
            'scene_publisher = show_urdf.scene_publisher:main',
            'grasp_visualizer = show_urdf.grasp_visualizer:main',
            'traj_visualizer = show_urdf.traj_visualizer:main',
        ],
    },
)