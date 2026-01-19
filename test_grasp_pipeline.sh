#!/bin/bash
# 测试抓取生成和可视化流程

set -e

echo "======================================"
echo "抓取生成与可视化测试"
echo "======================================"
echo ""

# 配置路径
SCRIPT_DIR="/workspace/RDF_ori/show_urdf_ws"
SCENE_CONFIG="$SCRIPT_DIR/src/show_urdf/show_urdf/scene_config.json"
OUTPUT_GRASP="$SCRIPT_DIR/test_grasp_result.json"

cd $SCRIPT_DIR

echo "1. 生成随机场景（可选）"
echo "-------------------------------------"
# python3 generate_random_scene.py --output random_scene.json --num_objects 5
echo "跳过（使用现有场景配置）"
echo ""

echo "2. 生成抓取"
echo "-------------------------------------"

python3 grasp_scene_integration.py \
    --scene "/workspace/RDF_ori/show_urdf_ws/src/show_urdf/show_urdf/scene_config.json" \
    --robot leap \
    --output "/workspace/RDF_ori/show_urdf_ws/test_grasp_result.json" \
    --batch_outer 64 \
    --batch_inner 64

if [ ! -f $OUTPUT_GRASP ]; then
    echo "错误: 抓取生成失败"
    # exit 1
fi

echo ""
echo "3. 启动 RViz 可视化"
echo "-------------------------------------"
echo "请在另一个终端运行以下命令："
echo ""
echo "  source install/setup.bash"
echo "  ros2 launch show_urdf trajectory_launch.py scene_config:=$SCENE_CONFIG"
echo ""
echo "然后运行："
echo "  python3 visualize_grasp_rviz.py --grasp $OUTPUT_GRASP --scene $SCENE_CONFIG --robot allegro"
echo ""
echo "======================================"
echo "测试完成！"
echo "======================================"
