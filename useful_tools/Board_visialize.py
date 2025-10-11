import matplotlib.pyplot as plt
import numpy as np

def coord_to_number(coord):
    """将字母数字坐标转换为数字坐标"""
    letter = coord[0].upper()
    number = int(coord[1:])
    # 字母转数字（A=1, B=2, ..., T=19），跳过I
    col = ord(letter) - ord('A')
    if letter > 'I':
        col -= 1
    # 围棋坐标是从下到上计数的，所以需要翻转
    row = 19 - number
    return row, col

def plot_goban(moves, save_path='goban.png'):
    # 创建图形
    plt.figure(figsize=(10, 10))
    
    # 绘制19x19的网格
    for i in range(19):
        plt.plot([0, 18], [i, i], 'k', linewidth=0.5)
        plt.plot([i, i], [0, 18], 'k', linewidth=0.5)
    
    # 绘制星位
    star_points = [(3, 3), (3, 9), (3, 15),
                   (9, 3), (9, 9), (9, 15),
                   (15, 3), (15, 9), (15, 15)]
    for point in star_points:
        plt.plot(point[0], point[1], 'k.', markersize=10)
    
    # 绘制棋子
    moves = moves.split(',')
    for i, move in enumerate(moves):
        row, col = coord_to_number(move)
        color = 'k' if i % 2 == 0 else 'w'
        circle = plt.Circle((col, row), 0.45, color=color)
        if color == 'w':
            circle.set_edgecolor('black')
        plt.gca().add_artist(circle)
        # 添加手数标记
        plt.text(col, row, str(i+1), ha='center', va='center',
                color='w' if color == 'k' else 'k')
    
    # 设置坐标轴
    plt.grid(False)
    plt.xticks(range(19), [chr(x + ord('A')) if x < 8 else chr(x + ord('A') + 1) for x in range(19)])
    plt.yticks(range(19), range(19, 0, -1))
    
    # 设置视图范围
    plt.xlim(-1, 19)
    plt.ylim(-1, 19)
    
    # 保持坐标轴比例相等
    plt.axis('equal')
    
    # Save
    plt.savefig(save_path, dpi=300, bbox_inches='tight')
    plt.close()  # Close fig

# 测试
moves =  ["Q16", 
    "D4", 
    "C16", 
    "R4",
    "P4", 
    "P3", 
    "O3", 
    "Q3", 
    "C6", 
    "F3", 
    "N4", 
    "Q5", 
    "J3", 
    "E17", 
    "H16", 
    "C13", 
    "E16", 
    "C10", 
    "D17", 
    "B4", 
    "O17", 
    "R11", 
    "E4", 
    "E5", 
    "D9", 
    "F4", 
    "C9", 
    "D10", 
    "E10", 
    "E11", 
    "F11", 
    "E12", 
    "F12", 
    "B10", 
    "F9", 
    "F13", 
    "G13",
    "F14", 
    "G14", 
    "N17", 
    "N16", 
    "M17", 
    "O18", 
    "J16", 
    "H17",
    "K13", 
    "Q10", 
    "Q11", 
    "P10", 
    "P11", 
    "O11", 
    "O12", 
    "N12", 
    "O13", 
    "N13", 
    "N11", 
    "O10", 
    "N14", 
    "M11", 
    "O15", 
    "O16", 
    "N10", 
    "M14", 
    "N9",
    "N15", 
    "O14", 
    "M12", 
    "R10", 
    "L9", 
    "J9", 
    "K11", 
    "G12", 
    "H10", 
    "G15", 
    "H15", 
    "F16", 
    "F17", 
    "L11"
]

# moves = "Q16,D16,Q4,D4,C3,C4,D3,E3,E2,F3,F2,G3,B4"

PIC_save_path = 'YOUR_SAVE_PATH'
moves = ",".join(moves)
plot_goban(moves, PIC_save_path)
