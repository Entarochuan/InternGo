import subprocess
import json
import os
from pathlib import Path
from enum import Enum


class GoSign(Enum):
    """围棋棋子类型"""

    BLACK = 1  # 黑子
    WHITE = -1  # 白子
    EMPTY = 0  # 空位

class GoGamePythonInterface:
    def __init__(self, js_module_path="./go-game-module.js"):
        """
        初始化围棋游戏Python接口

        Args:
            js_module_path: JavaScript模块的路径
        """
        self.js_module_path = js_module_path
        self.node_project_dir = os.path.dirname(os.path.abspath(js_module_path))

        # 围棋棋盘标识
        self.row_line = [
            "A",
            "B",
            "C",
            "D",
            "E",
            "F",
            "G",
            "H",
            "J",
            "K",
            "L",
            "M",
            "N",
            "O",
            "P",
            "Q",
            "R",
            "S",
            "T",
        ]
        self.current_board = None  # 缓存当前棋盘状态

        # 检查必要文件是否存在
        self._check_requirements()

    def _check_requirements(self):
        """检查Node.js项目和依赖是否正确配置"""
        # 检查JavaScript模块文件
        if not os.path.exists(self.js_module_path):
            raise FileNotFoundError(f"JavaScript模块文件不存在: {self.js_module_path}")

        # 检查package.json
        package_json_path = os.path.join(self.node_project_dir, "package.json")
        if not os.path.exists(package_json_path):
            raise FileNotFoundError(f"package.json文件不存在: {package_json_path}")

        # 检查node_modules
        node_modules_path = os.path.join(self.node_project_dir, "node_modules")
        if not os.path.exists(node_modules_path):
            raise FileNotFoundError(
                f"node_modules目录不存在: {node_modules_path}，请运行 'npm install'"
            )

        # 检查@sabaki/go-board包
        sabaki_path = os.path.join(node_modules_path, "@sabaki", "go-board")
        if not os.path.exists(sabaki_path):
            raise FileNotFoundError(
                "@sabaki/go-board包未安装，请运行 'npm install @sabaki/go-board'"
            )

    def _run_js_function(self, function_name, *args):
        """
        运行JavaScript函数

        Args:
            function_name: 要调用的函数名
            *args: 函数参数

        Returns:
            函数执行结果
        """
        # 构建JavaScript代码
        js_code = f"""
        const {{ {function_name} }} = require('{self.js_module_path}');
        try {{
            const args = {json.dumps(args)};
            const result = {function_name}(...args);
            console.log(JSON.stringify({{ success: true, data: result }}));
        }} catch (error) {{
            console.log(JSON.stringify({{ success: false, error: error.message }}));
        }}
        """

        # 执行Node.js代码
        try:
            result = subprocess.run(
                ["node", "-e", js_code],
                capture_output=True,
                text=True,
                cwd=self.node_project_dir,  # 在正确的目录下执行
                timeout=30,  # 设置超时
            )

            if result.returncode != 0:
                raise RuntimeError(f"Node.js执行错误: {result.stderr}")

            # 解析结果
            response = json.loads(result.stdout.strip())

            if not response["success"]:
                raise RuntimeError(f"JavaScript函数执行错误: {response['error']}")

            return response["data"]

        except subprocess.TimeoutExpired:
            raise RuntimeError("Node.js执行超时")
        except json.JSONDecodeError as e:
            raise RuntimeError(f"JSON解析错误: {e}, 输出: {result.stdout}")

    def quick_batch_move(self, moves):
        """
        快速批量落子

        Args:
            moves: 落子序列，格式: [{"sign": 1, "vertex": [row, col]}, ...]

        Returns:
            包含棋盘状态的结果
        """
        result = self._run_js_function("quickBatchMove", moves)
        # 缓存棋盘状态
        if result and "board" in result:
            self.current_board = result["board"]
        return result

    def get_board(self):
        """
        获取当前棋盘状态

        Returns:
            棋盘状态二维数组，如果没有则返回None
        """
        return self.current_board

    def print_board(self):
        """打印当前棋盘状态"""
        board = self.get_board()
        if not board:
            print("棋盘状态为空，请先进行落子操作")
            return

        print("\n当前棋盘状态:")
        print("   ", end="")
        for i in range(19):
            print(f"{self.row_line[i]:2}", end=" ")
        print()

        for i, row in enumerate(board):
            print(f"{(19-i):2} ", end="")
            for cell in row:
                if cell == GoSign.BLACK.value:
                    print(" ●", end=" ")
                elif cell == GoSign.WHITE.value:
                    print(" ○", end=" ")
                else:
                    print(" ·", end=" ")
            print()
        print()  # 额外空行

    def print_board_with_moves(self, moves):
        """
        显示落子过程，逐步打印棋盘

        Args:
            moves: 落子序列
        """
        print("=== 围棋落子过程演示 ===")

        # 先打印空棋盘
        print("\n初始空棋盘:")
        self.current_board = [[0 for _ in range(19)] for _ in range(19)]
        self.print_board()

        # 逐步落子并显示
        for i, move in enumerate(moves, 1):
            single_move = [move]
            result = self.quick_batch_move(single_move)

            if result and result["success"]:
                color_name = "黑子" if move["sign"] == GoSign.BLACK.value else "白子"
                pos = self.convert_vertex_to_pos(move["vertex"])
                print(f"第{i}步: {color_name}落在 {pos} ({move['vertex']})")
                self.print_board()
            else:
                print(f"第{i}步落子失败: {result.get('message', '未知错误')}")
                break

    def convert_vertex_to_pos(self, vertex):
        """
        将坐标转换为围棋位置表示法

        Args:
            vertex: [row, col] 坐标

        Returns:
            位置字符串，如 "D4"
        """
        if not vertex or len(vertex) != 2:
            return ""

        row, col = vertex
        if 0 <= row < 19 and 0 <= col < 19:
            # 注意：这里需要根据实际的坐标系进行调整
            row_char = self.row_line[row]
            col_num = 19 - col  # 根据实际情况可能需要调整
            return f"{row_char}{col_num}"
        return ""

    def quick_batch_check(self, moves):
        """
        快速检查一系列落子是否合法

        Args:
            moves: 落子序列

        Returns:
            检查结果列表
        """
        return self._run_js_function("quickBatchCheck", moves)

    def create_game_from_moves(self, moves):
        """
        从落子历史创建游戏

        Args:
            moves: 落子历史

        Returns:
            游戏状态信息
        """
        return self._run_js_function("createGameFromMoves", moves)


# 使用示例
def main():
    try:
        # 创建接口实例
        go_interface = GoGamePythonInterface("./go-game-module.js")

        # 定义落子序列
        moves = [
            {"sign": GoSign.BLACK.value, "vertex": [3, 3]},  # 黑子下在 D4
            {"sign": GoSign.WHITE.value, "vertex": [15, 15]},  # 白子下在 P4
            {"sign": GoSign.BLACK.value, "vertex": [3, 15]},  # 黑子下在 D16
            {"sign": GoSign.WHITE.value, "vertex": [9, 9]},  # 白子下在中心
            {"sign": GoSign.BLACK.value, "vertex": [6, 6]},  # 黑子
        ]

        print("=== 围棋游戏Python接口测试 ===")

        # 方式1: 批量落子后显示最终结果
        print("\n【方式1】批量落子测试:")
        result = go_interface.quick_batch_move(moves)
        print(f"result: {result}")
        if result["success"]:
            print("✅ 批量落子成功！")
            print(f"总步数: {len(result['steps'])}")
            board = result['board']
            print("current board:")
            print(board)
            # 打印最终棋盘状态
            # go_interface.print_board()

            # 显示每步落子结果
            print("落子详情:")
            for step in result["steps"]:
                status = "✅成功" if step["success"] else "❌失败"
                color = "黑" if step["sign"] == GoSign.BLACK.value else "白"
                pos = go_interface.convert_vertex_to_pos(step["vertex"])
                print(
                    f"  第{step['step']}步: {color}子 {step['vertex']} ({pos}) - {status}"
                )
        else:
            print(f"❌ 落子失败: {result['message']}")

        print("\n" + "=" * 60)

        # 方式2: 逐步落子演示（重新开始）
        # print("\n【方式2】逐步落子演示:")
        # go_interface_demo = GoGamePythonInterface("./go-game-module.js")
        # go_interface_demo.print_board_with_moves(moves[:3])  # 只演示前3步

        # print("\n" + "=" * 60)

        # # 方式3: 检查落子合法性
        # print("\n【方式3】落子合法性检查:")
        # check_result = go_interface.quick_batch_check(moves)

        # print("合法性检查结果:")
        # for check in check_result:
        #     status_icon = "✅" if check["isValid"] else "❌"
        #     color = "黑" if check["sign"] == GoSign.BLACK.value else "白"
        #     pos = go_interface.convert_vertex_to_pos(check["vertex"])
        #     reason = f"({check['reason']})" if not check["isValid"] else ""
        #     print(
        #         f"  {status_icon} 第{check['step']}步: {color}子 {check['vertex']} ({pos}) {reason}"
        #     )

        # # 方式4: 测试非法落子
        # print("\n【方式4】非法落子测试:")
        # illegal_moves = [
        #     {"sign": GoSign.BLACK.value, "vertex": [3, 3]},  # 重复位置
        #     {"sign": GoSign.WHITE.value, "vertex": [3, 3]},  # 再次重复
        # ]

        # illegal_result = go_interface.quick_batch_move(illegal_moves)
        # if not illegal_result["success"]:
        #     print(f"✅ 正确检测到非法落子: {illegal_result['message']}")
        # else:
        #     print("❌ 未能检测到非法落子")

    except Exception as e:
        print(f"❌ 程序执行错误: {e}")
        print("\n🔧 请确保:")
        print("1. ✅ 已安装Node.js")
        print("2. ✅ 在项目目录下运行了 'npm install @sabaki/go-board'")
        print("3. ✅ go-game-module.js文件存在且路径正确")
        print("4. ✅ 当前目录结构正确")


def demo_board_display():
    """演示棋盘显示功能"""
    try:
        go_interface = GoGamePythonInterface("./go-game-module.js")

        # 创建一个经典开局的演示
        opening_moves = [
            {"sign": GoSign.BLACK.value, "vertex": [3, 3]},  # 右上星位
            {"sign": GoSign.WHITE.value, "vertex": [15, 15]},  # 左下星位
            {"sign": GoSign.BLACK.value, "vertex": [3, 15]},  # 左上星位
            {"sign": GoSign.WHITE.value, "vertex": [15, 3]},  # 右下星位
            {"sign": GoSign.BLACK.value, "vertex": [9, 9]},  # 天元
        ]

        print("=== 围棋经典开局演示 ===")
        result = go_interface.quick_batch_move(opening_moves)
        print(f"result: {result}")

    except Exception as e:
        print(f"演示失败: {e}")


if __name__ == "__main__":
    # 运行主要测试
    main()

    print("\n" + "=" * 80)

    # 运行开局演示
    demo_board_display()
