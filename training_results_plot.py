import matplotlib.pyplot as plt
import numpy as np

# 设置中文字体
plt.rcParams['font.sans-serif'] = ['SimHei', 'DejaVu Sans']
plt.rcParams['axes.unicode_minus'] = False

# 数据
epochs = [0, 20, 60, 100, 200, 300, 400, 500, 600, 700, 800, 900, 1000, 1100, 1200, 1300, 1400]
go_1_epoch = [63.46, 65.32, 71.49, 74.79, 80.68, 81.40, 83.16, 82.95, 83.06, 84.19, 85.16, 85.99, 85.13, 86.61, 86.19, 86.92, 87.54]
go_2_epoch = [68.04, 67.90, 71.83, 75.45, 79.86, 80.06, 82.54, 81.30, 83.16, 83.44, 85.26, 85.68, 85.50, 86.50, 86.30, 86.26, 86.71]

# 创建图表
plt.figure(figsize=(12, 8))

# 绘制两条线
plt.plot(epochs, go_1_epoch, 'o-', linewidth=2.5, markersize=6, label='Go 1 Epoch', color='#2E86AB', markerfacecolor='#2E86AB', markeredgecolor='white', markeredgewidth=1)
plt.plot(epochs, go_2_epoch, 's-', linewidth=2.5, markersize=6, label='Go 2 Epoch', color='#A23B72', markerfacecolor='#A23B72', markeredgecolor='white', markeredgewidth=1)

# 设置图表样式
plt.xlabel('Training Epochs', fontsize=14, fontweight='bold')
plt.ylabel('Performance (%)', fontsize=14, fontweight='bold')
plt.title('LoGos Training Performance: Go 1 Epoch vs Go 2 Epoch', fontsize=16, fontweight='bold', pad=20)

# 设置网格
plt.grid(True, alpha=0.3, linestyle='--')
plt.legend(fontsize=12, loc='lower right')

# 设置坐标轴范围
plt.xlim(-50, 1450)
plt.ylim(60, 90)

# 添加关键点标注
plt.annotate('Initial Point', xy=(0, 63.46), xytext=(100, 65), 
             arrowprops=dict(arrowstyle='->', color='gray', alpha=0.7),
             fontsize=10, ha='center')

plt.annotate('Best Performance\n(Go 1 Epoch)', xy=(1400, 87.54), xytext=(1200, 88.5), 
             arrowprops=dict(arrowstyle='->', color='#2E86AB', alpha=0.8),
             fontsize=10, ha='center', color='#2E86AB')

# 设置刻度
plt.xticks(np.arange(0, 1500, 200), fontsize=11)
plt.yticks(np.arange(60, 91, 5), fontsize=11)

# 调整布局
plt.tight_layout()

# 保存图片
plt.savefig('/mnt/shared-storage-user/llmbr-share/mayichuan/Open-Source/LoGos/images/training_results.png', 
            dpi=300, bbox_inches='tight', facecolor='white')

# 显示图片
plt.show()

print("图表已保存为: images/training_results.png")

