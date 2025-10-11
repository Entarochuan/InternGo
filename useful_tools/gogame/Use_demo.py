from python_caller import GoGamePythonInterface

def convert_move_to_vertex(move):
    """将棋盘坐标(如'A1', 'T19')转换为数组索引[x,y]
    
    Args:
        move (str): 棋盘坐标，例如'A1', 'T19'
        
    Returns:
        list: 返回[x,y]格式的数组索引，y坐标从下到上对应18到0
    """
    # 提取字母和数字部分
    letter = move[0]
    number = int(move[1:])
    
    # 字母转换为x坐标(从左到右 A->0, B->1, ..., T->18)
    letters = 'ABCDEFGHJKLMNOPQRST'  # 跳过I
    x = letters.index(letter)
    
    # 数字转换为y坐标(从下到上 1->18, 2->17, ..., 19->0)
    y = 19 - number
    
    return [x, y]

if __name__ == "__main__":
    
    board_moves = ["Q16", "D16", "Q4", "D4", "C3", "C4", "D3", "E3", "E2", "F3", "F2", "G3", "B4"]

    # Prepare moves for API call
    board_prepare_moves = [{"sign": 1 if i % 2 == 0 else -1, "vertex": convert_move_to_vertex(move)} for i,move in enumerate(board_moves)]
    client = GoGamePythonInterface()
    result = client.quick_batch_move(board_prepare_moves)
    board = result['board']

    print(board)
    
    # 1 stands for black, -1 stands for white, 0 stands for empty.

