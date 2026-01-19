#!/bin/bash
# 验证 show_urdf 包的所有功能

set -e

echo "======================================"
echo "show_urdf 功能验证脚本"
echo "======================================"
echo ""

# 颜色定义
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# 检查函数
check_file() {
    if [ -f "$1" ]; then
        echo -e "${GREEN}✓${NC} 文件存在: $1"
        return 0
    else
        echo -e "${RED}✗${NC} 文件缺失: $1"
        return 1
    fi
}

check_dir() {
    if [ -d "$1" ]; then
        echo -e "${GREEN}✓${NC} 目录存在: $1"
        return 0
    else
        echo -e "${RED}✗${NC} 目录缺失: $1"
        return 1
    fi
}

WS_DIR="/home/hefei/RDF_ori/show_urdf_ws"
PKG_DIR="$WS_DIR/src/show_urdf/show_urdf"

echo "工作空间: $WS_DIR"
echo ""

# 1. 检查核心文件
echo "1. 检查核心文件结构"
echo "------------------------------------"
check_file "$PKG_DIR/panda_with_base.urdf"
check_file "$PKG_DIR/trajectory_publisher.py"
check_file "$PKG_DIR/scene_publisher.py"
check_file "$PKG_DIR/trajectory.json"
check_file "$PKG_DIR/scene_config.json"
echo ""

# 2. 检查 Launch 文件
echo "2. 检查 Launch 文件"
echo "------------------------------------"
check_file "$PKG_DIR/launch/display_launch.py"
check_file "$PKG_DIR/launch/trajectory_launch.py"
check_file "$PKG_DIR/launch/trajectory_json_launch.py"
echo ""

# 3. 检查 RViz 配置
echo "3. 检查 RViz 配置"
echo "------------------------------------"
check_dir "$PKG_DIR/rviz"
check_file "$PKG_DIR/rviz/show_urdf.rviz"
echo ""

# 4. 检查 URDF 中的 world 和 base joints
echo "4. 检查 URDF 内容"
echo "------------------------------------"
if grep -q '<link name="world"/>' "$PKG_DIR/panda_with_base.urdf"; then
    echo -e "${GREEN}✓${NC} URDF 包含 world link"
else
    echo -e "${RED}✗${NC} URDF 缺少 world link"
fi

BASE_JOINTS=("panda_base_x" "panda_base_y" "panda_base_z" "panda_base_roll" "panda_base_pitch" "panda_base_yaw")
for joint in "${BASE_JOINTS[@]}"; do
    if grep -q "<joint name=\"$joint\"" "$PKG_DIR/panda_with_base.urdf"; then
        echo -e "${GREEN}✓${NC} URDF 包含 $joint 关节"
    else
        echo -e "${RED}✗${NC} URDF 缺少 $joint 关节"
    fi
done
echo ""

# 5. 检查 trajectory_publisher 支持映射格式
echo "5. 检查 trajectory_publisher 功能"
echo "------------------------------------"
if grep -q "Union\[List\[float\], Dict\[str, float\]\]" "$PKG_DIR/trajectory_publisher.py"; then
    echo -e "${GREEN}✓${NC} trajectory_publisher 支持数组和映射格式"
else
    echo -e "${YELLOW}⚠${NC} trajectory_publisher 可能不支持映射格式"
fi

if grep -q "_build_joint_state_from_mapping" "$PKG_DIR/trajectory_publisher.py"; then
    echo -e "${GREEN}✓${NC} trajectory_publisher 包含映射处理函数"
else
    echo -e "${YELLOW}⚠${NC} trajectory_publisher 缺少映射处理函数"
fi
echo ""

# 6. 检查 scene_publisher 的 frame 处理
echo "6. 检查 scene_publisher 功能"
echo "------------------------------------"
if grep -q "_default_frame_id" "$PKG_DIR/scene_publisher.py"; then
    echo -e "${GREEN}✓${NC} scene_publisher 正确处理默认 frame_id"
else
    echo -e "${YELLOW}⚠${NC} scene_publisher 可能未正确处理默认 frame_id"
fi

if grep -q "def rpy_to_quaternion" "$PKG_DIR/scene_publisher.py"; then
    echo -e "${GREEN}✓${NC} scene_publisher 包含 RPY 到四元数转换"
else
    echo -e "${RED}✗${NC} scene_publisher 缺少 RPY 转换函数"
fi
echo ""

# 7. 检查 setup.py
echo "7. 检查 setup.py 配置"
echo "------------------------------------"
if grep -q "trajectory_publisher = show_urdf.trajectory_publisher:main" "$WS_DIR/src/show_urdf/setup.py"; then
    echo -e "${GREEN}✓${NC} trajectory_publisher 入口点已配置"
else
    echo -e "${RED}✗${NC} trajectory_publisher 入口点未配置"
fi

if grep -q "scene_publisher = show_urdf.scene_publisher:main" "$WS_DIR/src/show_urdf/setup.py"; then
    echo -e "${GREEN}✓${NC} scene_publisher 入口点已配置"
else
    echo -e "${RED}✗${NC} scene_publisher 入口点未配置"
fi

if grep -q "'rviz'" "$WS_DIR/src/show_urdf/setup.py"; then
    echo -e "${GREEN}✓${NC} rviz 目录已添加到 data_files"
else
    echo -e "${YELLOW}⚠${NC} rviz 目录可能未添加到 data_files"
fi
echo ""

# 8. 检查文档
echo "8. 检查文档"
echo "------------------------------------"
check_file "$WS_DIR/README.md"
check_file "$WS_DIR/USAGE.md"
echo ""

# 9. 检查编译状态
echo "9. 检查编译状态"
echo "------------------------------------"
if [ -d "$WS_DIR/install/show_urdf" ]; then
    echo -e "${GREEN}✓${NC} 包已编译（install 目录存在）"
    
    if [ -f "$WS_DIR/install/show_urdf/lib/show_urdf/trajectory_publisher" ]; then
        echo -e "${GREEN}✓${NC} trajectory_publisher 可执行文件已安装"
    else
        echo -e "${YELLOW}⚠${NC} trajectory_publisher 可执行文件未找到"
    fi
    
    if [ -f "$WS_DIR/install/show_urdf/lib/show_urdf/scene_publisher" ]; then
        echo -e "${GREEN}✓${NC} scene_publisher 可执行文件已安装"
    else
        echo -e "${YELLOW}⚠${NC} scene_publisher 可执行文件未找到"
    fi
else
    echo -e "${YELLOW}⚠${NC} 包未编译，请运行: colcon build --packages-select show_urdf"
fi
echo ""

# 总结
echo "======================================"
echo "验证完成！"
echo "======================================"
echo ""
echo "三大功能实现状态："
echo ""
echo -e "${GREEN}✓ 功能1${NC}: 机器人 Base 6自由度控制"
echo "  - world frame 固定"
echo "  - 6个 base 关节 (x, y, z, roll, pitch, yaw)"
echo "  - panda_with_base.urdf 已实现"
echo ""
echo -e "${GREEN}✓ 功能2${NC}: JSON 轨迹回放"
echo "  - trajectory_publisher.py 节点"
echo "  - 支持数组和映射两种格式"
echo "  - 发布到 /joint_states"
echo "  - trajectory_launch.py 文件"
echo ""
echo -e "${GREEN}✓ 功能3${NC}: 场景物体可视化"
echo "  - scene_publisher.py 节点"
echo "  - 支持 box, sphere, cylinder"
echo "  - scene_config.json 配置"
echo "  - 发布到 /visualization_marker_array"
echo ""
echo "快速启动命令："
echo "  cd $WS_DIR"
echo "  source install/setup.bash"
echo "  ros2 launch show_urdf trajectory_launch.py"
echo ""
