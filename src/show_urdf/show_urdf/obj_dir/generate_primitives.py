# 为box, sphere, cylinder等基本形状生成obj文件
import trimesh
from trimesh.remesh import subdivide_loop
from pathlib import Path
import numpy as np
def generate_box(size, file_path):
    # 生成dense的box网格(trimesh默认生成的box网格比较稀疏)
    box = trimesh.creation.box(extents=size)
    # box = subdivide_loop(box.vertices, box.faces, iterations=2)
    # # 把dense_mesh重新构造成trimesh对象
    # box = trimesh.Trimesh(vertices=box[0], faces=box[1])
    box.export(file_path)
def generate_sphere(radius, file_path):
    sphere = trimesh.creation.icosphere(radius=radius)
    sphere.export(file_path)
def generate_cylinder(radius, height, file_path):
    cylinder = trimesh.creation.cylinder(radius=radius, height=height)
    cylinder.export(file_path)
if __name__ == "__main__":
    output_dir = Path(__file__).parent / "primitives"
    output_dir.mkdir(exist_ok=True)
    
    generate_box(size=[1.0, 1.0, 1.0], file_path=output_dir / "box.obj")
    generate_sphere(radius=0.5, file_path=output_dir / "sphere.obj")
    generate_cylinder(radius=0.5, height=1.0, file_path=output_dir / "cylinder.obj")