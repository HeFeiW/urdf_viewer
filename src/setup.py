from setuptools import setup
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
    ]
    for directory in directories_to_install:
        data_files += collect_data_files(package_name, directory)
    return data_files
    
setup(
    name=package_name,
    version='0.0.0',
    packages=[package_name],
    data_files=get_data_files(),
    install_requires=['setuptools'],
    zip_safe=True,
    maintainer='your_name',
    maintainer_email='your_email@example.com',
    description='TODO: Package description',
    license='TODO: License declaration',
    tests_require=['pytest'],
    entry_points={
        'console_scripts': [
            'broadcast_rot = show_urdf.broadcast_rot:main',
        ],
    },
)