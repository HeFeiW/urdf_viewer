import rclpy
from rclpy.node import Node
from std_msgs.msg import Float32MultiArray

class RotBroadcaster(Node):
    def __init__(self):
        super().__init__('rot_broadcaster')
        self.joint_pub = self.create_publisher(Float32MultiArray, 'joint_rot_matrices', 10)
        self.link_pub = self.create_publisher(Float32MultiArray, 'link_rot_matrices', 10)
        self.timer = self.create_timer(0.1, self.timer_callback)

    def timer_callback(self):
        # 假设你有两个列表，每个元素是一个3x3旋转矩阵
        joint_rot_matrices = self.get_joint_rot_matrices()
        link_rot_matrices = self.get_link_rot_matrices()

        joint_msg = Float32MultiArray()
        joint_msg.data = [item for mat in joint_rot_matrices for item in mat.flatten()]
        self.joint_pub.publish(joint_msg)

        link_msg = Float32MultiArray()
        link_msg.data = [item for mat in link_rot_matrices for item in mat.flatten()]
        self.link_pub.publish(link_msg)

    def get_joint_rot_matrices(self):
        # TODO: 用你的运动学代码获取所有关节相对于 panda_link0 的旋转矩阵
        # 返回 [np.array(3x3), ...]
        return []

    def get_link_rot_matrices(self):
        # TODO: 用你的运动学代码获取所有 link 相对于 panda_link0 的旋转矩阵
        # 返回 [np.array(3x3), ...]
        return []

def main(args=None):
    rclpy.init(args=args)
    node = RotBroadcaster()
    rclpy.spin(node)
    node.destroy_node()
    rclpy.shutdown()

if __name__ == '__main__':
    main()