import json
from openai import OpenAI
from typing import List, Dict
import re
import argparse
import time
from tqdm import tqdm
import os
from concurrent.futures import ThreadPoolExecutor
import math
from datetime import datetime
from python_caller import GoGamePythonInterface

def extract_moves(content):
    """从对局记录中提取移动列表"""
    moves = []
    pattern = r'\d+\.(X|O)-([A-T]\d+)'
    matches = re.findall(pattern, content)
    return matches

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

class GoAPIEvaluator:
    def __init__(self, api_base: str, model_name: str, system_prompt: str = None, prompt_template: str = None, task_type: str = None):
        """初始化GO API评估器
        
        Args:
            api_base: API基础URL
            model_name: 模型名称
            system_prompt: 自定义system prompt，如果为None则使用默认值
        """
        
        self.client = OpenAI(base_url=api_base, api_key="None")
        self.model_name = model_name
        self.system_prompt = system_prompt or None
        self.prompt_template = prompt_template
        self.task_type = task_type
        # 评估统计
        self.total_moves = 0
        self.matched_moves = 0
        self.total_win_rate_gap = 0.0

    def get_move(self, board_moves: List[str], mode: str = "numbered", retry: int = 3) -> tuple[str, str]:
        """获取模型预测的下一步走法
        
        Args:
            board_moves: 之前的所有移动列表，格式如 ["Q16", "D4", ...]
            mode: 输入格式模式，可选 "basic" 或 "numbered"
            
        Returns:
            (predicted_move, raw_response): 预测的移动和原始响应
        """
        
        # 1. render the board + moves
        board_prepare_moves = [{"sign": 1 if i % 2 == 0 else -1, "vertex": convert_move_to_vertex(move)} for i,move in enumerate(board_moves)]
        client = GoGamePythonInterface()
        moves_str = "\n".join([f"{i+1}.{'X' if i % 2 == 0 else 'O'}-{move}" for i, move in enumerate(board_moves)])
        result = client.quick_batch_move(board_prepare_moves)
        board = result['board']
        moves_str += f"\n\n\n当前盘面情况为:{board}\n其中1表示黑棋，-1表示白棋，0表示空位。"    
                
        if self.system_prompt is not None:
            messages = [
                {"role": "system", "content": self.system_prompt},
                {"role": "user", "content": self.prompt_template.replace("{moves_str}", moves_str)},
                # {"role": "assistant", "content": ""}
            ]
        else:
            messages = [
                {"role": "user", "content": self.prompt_template.replace("{moves_str}", moves_str)},
            ]
        
        prompt = messages

        try:
            for _ in range(retry):
                if _ > 0:
                    print(f"尝试第{_ + 1}次API调用")
                response = self.client.chat.completions.create(
                    model=self.model_name,
                    messages=messages,
                    temperature=0,
                    max_tokens=4096
                )
                raw_response = response.choices[0].message.content
                break
        except Exception as e:
            print(f"API调用出错: {e}")
            return "", ""

        predicted_move = self._extract_move(raw_response)
        return predicted_move, raw_response, prompt

    def _extract_move(self, response: str) -> str:
        """从响应中提取有效的下一步落子位置(如"D6")
        
        Args:
            response: API返回的原始响应文本

        Returns:
            str: 提取出的移动位置（如 "D6"），如果没有找到有效移动则返回空字符串
        """
        
        position_match = re.search(r'\\boxed{下一步位置\s*:\s*([A-HJ-T]\d{1,2})\s*}', response)
        if position_match:
            return position_match.group(1)
        else :
            position_match = re.search(r'\\boxed{下一步\s*:\s*([A-HJ-T]\d{1,2})\s*}', response)
            if position_match:
                return position_match.group(1)

        return ""

    def _extract_win_rate(self, response: str) -> float:
        """从模型回复中提取胜率值
        
        Args:
            response: API返回的原始响应文本
            
        Returns:
            float: 提取出的胜率值，如果没有找到有效胜率则返回None
        """
        # 尝试匹配 \boxed{下一步胜率:XX%} 或 \boxed{下一步胜率:0.XX} 格式
        win_rate_match = re.search(r'\\boxed{下一步胜率\s*:\s*([0-9.]+%?)\s*}', response)
        if win_rate_match:
            win_rate_str = win_rate_match.group(1)
            # 处理百分比格式
            if '%' in win_rate_str:
                try:
                    return float(win_rate_str.replace('%', '')) / 100
                except ValueError:
                    return None
            # 处理小数格式
            else:
                try:
                    return float(win_rate_str)
                except ValueError:
                    return None
        return None

    def _is_valid_move(self, move: str) -> bool:
        """验证预测的move是否有效(A-T, 1-19)"""
        if not move or len(move) < 2:
            return False
        
        valid_letters = set("ABCDEFGHJKLMNOPQRST")
        if move[0] not in valid_letters:
            return False
            
        try:
            num = int(move[1:])
            return 1 <= num <= 19
        except ValueError:
            return False

    def evaluate_position(self, board_moves: List[str], candidates: List[Dict], input_mode: str = "basic") -> Dict:
        """评估单个局面的模型表现"""
        predicted_move, raw_response, prompt = self.get_move(board_moves, input_mode)
        predicted_win_rate = self._extract_win_rate(raw_response)
        if predicted_win_rate is None:
            pass
            # print(f"无预测胜率。")
        
        best_candidate = max(candidates, key=lambda x: x['win_rate'])
        matched_candidate = None
        rank = None
        
        for i, candidate in enumerate(candidates):
            if candidate['move'] == predicted_move:
                matched_candidate = candidate
                rank = i + 1
                break
        
        if matched_candidate:
            if predicted_win_rate is None:
                win_rate_gap = None
                pass
            else:
                win_rate_gap = abs(predicted_win_rate - matched_candidate['win_rate'])
            score_lead_gap = abs(best_candidate['score_lead'] - matched_candidate['score_lead'])
        else:
            win_rate_gap = None
            score_lead_gap = None

        # 更新统计
        self.total_moves += 1
        if matched_candidate:
            self.matched_moves += 1
            
        if win_rate_gap is not None:
            self.total_win_rate_gap += win_rate_gap

        if matched_candidate:
            matched_win_rate = matched_candidate['win_rate']
        else:
            matched_win_rate = None
            
        return {
            'predicted_move': predicted_move,
            'predicted_win_rate_info': dict(predicted_win_rate=predicted_win_rate,
                                            curr_move_win_rate=matched_win_rate,
                                            best_move_win_rate=best_candidate['win_rate']),
            'matched': matched_candidate is not None,
            'rank': rank,
            'win_rate_gap': win_rate_gap,
            'score_lead_gap': score_lead_gap,
            'raw_prompt': prompt,
            'raw_response': raw_response,
            'best_move': best_candidate['move'],
            'best_win_rate': best_candidate['win_rate']
        }

    def evaluate_file(self, input_file: str, output_file: str, input_mode: str = "basic", num_threads: int = 4) -> Dict:
        """评估整个测试文件"""
        # 读取所有数据
        with open(input_file, 'r') as f:
            all_data = [json.loads(line) for line in f]
        
        total_lines = len(all_data)
        
        # TQDM进度条和输出文件
        pbar = tqdm(total=total_lines, desc="评估进度")
        out_f = open(output_file, 'w')
        
        def process_and_write(data):
            result = self.evaluate_position(
                data['board_moves'],
                data['candidates'],
                input_mode
            )
            result['board_moves'] = data['board_moves']
            out_f.write(json.dumps(result, ensure_ascii=False) + '\n')
            out_f.flush()  # 实时写入
            pbar.update(1)
            return result
        
        # 使用线程池并行处理
        with ThreadPoolExecutor(max_workers=num_threads) as executor:
            results = list(executor.map(process_and_write, all_data))
        
        pbar.close()
        out_f.close()
        
        # 计算统计信息
        stats = {
            'total_moves': self.total_moves,
            'matched_moves': self.matched_moves,
            'match_rate': self.matched_moves / self.total_moves if self.total_moves > 0 else 0,
            'average_win_rate_gap': self.total_win_rate_gap / self.total_moves if self.total_moves > 0 else 1.0
        }
        
        return stats

# 10.130.129.235
# Qwen_30B_A3_instruct_data_verify_20250713f

def main():
    parser = argparse.ArgumentParser(description='KataGo Bench 1K Eval')
    parser.add_argument('--api_base', type=str, default="Your API base URL",
                      help='API基础URL')
    parser.add_argument('--model_name', type=str, default="Your Model Name",
                      help='模型名称')
    parser.add_argument('--api_key', type=str, default="Empty",
                      help='API密钥')
    parser.add_argument('--input_file', type=str, default="KataGO-1k-eval/eval-files/KataGO-Bench-1k-eval.jsonl",
                      help='输入文件路径')
    parser.add_argument('--output_dir', type=str, default="KataGO-1k-eval/eval-results",
                      help='输出文件路径')
    parser.add_argument('--input_mode', type=str, choices=['basic', 'numbered'],
                      default='numbered', 
                      help='输入格式模式：basic(空格分隔) 或 numbered(带序号)')
    parser.add_argument('--num_threads', type=int, default=64,
                      help='并行线程数')
    parser.add_argument('--task_type', type=str, choices=['Reasoning_LM', 'Addboard-KataGo-Eval'],
                      default='Addboard-KataGo-Eval',
                      help='任务类型')

    args = parser.parse_args()
    TYPE = args.task_type     
    
    if TYPE == "Reasoning_LM": # for general LLMs
        system_prompt = None
        prompt_template = """你是一位专业的围棋棋手。你的任务是根据给定的棋局记录，分析局面信息，挑选若干可能的下一步并进行分析，推演对应的后续变化，进行合理的分析与思考，最后总结并挑选出最好的下一步位置。在给出的棋局中，\"X\"表示黑棋，\"O\"表示白棋。棋盘的大小为19x19，每个落子的坐标是一个字母加上一个数字的形式。字母为A-T(跳过I)，对应于棋盘上从左到右。数字为1-19，对应于棋盘上从下到上。\n你需要首先对当前局面进行合理的分析和思考，对后续的步骤进行合理的预测、推演和分析，并最后总结你的思考结果，选择出最合适的下一步。请进行严谨和详细的推理分析，并及时进行总结。你的总结格式为:\n<answer>\n\\boxed{下一步颜色:黑/白}\n\\boxed{下一步位置:落子位置}\n\n</answer>\n以下是当前的对局记录：\n\n{moves_str}\n\n请遵循给出的格式，预测并分析下一步的落子位置。"""
    elif TYPE == "Addboard-KataGo-Eval":
        system_prompt = """你是一个精通各种围棋策略、理念和围棋下法的围棋职业棋手。你现在在进行一盘棋局的对弈，你需要根据棋盘信息对接下来的下法进行合理的预测。你的回复语言风格严谨认真而不失趣味，同时你乐于和对手进行友好的互动。你的任务是根据给定的棋局记录，分析局面信息，挑选若干可能的下一步并进行分析，推演对应的后续变化，进行合理的分析与思考，总结并挑选出最好的下一步位置，并最终形成一个有趣生动和富含思考的回复。在给出的棋局中，\"X\"表示黑棋，\"O\"表示白棋。棋盘的大小为19x19，每个落子的坐标是一个字母加上一个数字的形式。字母为A-T(跳过I)，对应于棋盘上从左到右。数字为1-19，对应于棋盘上从下到上。\n你需要首先对当前局面进行合理的分析和思考，对后续的步骤进行合理的预测、推演和分析，并最后总结你的思考结果，选择出最合适的下一步。请进行严谨详细、生动自然的推理和分析，及时进行总结，并最终输出符合格式要求的结果。你的输出格式为:\n\n<reasoning>\n你的思考过程。\n</reasoning>\n\n<answer>\n\\boxed{下一步颜色:黑/白}\n\\boxed{下一步位置:落子位置}\n\\boxed{下一步胜率:胜率}\n\n</answer>\n"""
        prompt_template = """以下是当前的对局记录：\n\n{moves_str}\n\n请遵循给出的格式，预测并分析下一步的落子位置。"""

    # 创建评估器
    evaluator = GoAPIEvaluator(
        api_base=args.api_base,
        model_name=args.model_name,
        system_prompt=system_prompt,
        prompt_template=prompt_template,
        task_type=TYPE
    )
    
    # 创建文件夹
    timestamp = str(datetime.now().strftime("%Y%m%d_%H%M%S"))
    # 如果是一个路径形式的model_name, 拆分最后一个/后面的名字
    model_name_short = args.model_name.split('/')[-1] if '/' in args.model_name else args.model_name
    
    os.makedirs(os.path.join(args.output_dir, model_name_short), exist_ok=True)
    os.makedirs(os.path.join(args.output_dir, model_name_short, timestamp), exist_ok=True)
    
    output_file = os.path.join(args.output_dir, model_name_short, timestamp, "eval_results.jsonl")
    summary_file = os.path.join(args.output_dir, model_name_short, timestamp, "summary.txt")
    
    # 开始评估
    print(f"Start Evaluating...")
    print(f"Model Name: {args.model_name}")
    print(f"Input Mode: {args.input_mode}")
    
    start_time = time.time()
    stats = evaluator.evaluate_file(
        args.input_file, 
        output_file, 
        args.input_mode,
        args.num_threads
    )
    end_time = time.time()
    
    # 打印结果
    print("\n评估结果:")
    print(f"总移动数: {stats['total_moves']}")
    print(f"匹配移动数: {stats['matched_moves']}")
    print(f"匹配率: {stats['match_rate']:.2%}")
    print(f"平均胜率差距: {stats['average_win_rate_gap']:.4f}")
    print(f"评估耗时: {end_time - start_time:.2f}秒")
    
    print(f"\n详细结果已保存至: {output_file}")
    
    # 将评估结果写入summary.txt文件
    with open(summary_file, 'w', encoding='utf-8') as f:
        f.write("围棋评估结果摘要\n")
        f.write("=" * 50 + "\n\n")
        f.write(f"模型名称: {args.model_name}\n")
        f.write(f"API基础URL: {args.api_base}\n")
        f.write(f"任务类型: {TYPE}\n")
        f.write(f"输入模式: {args.input_mode}\n")
        f.write(f"评估时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
        f.write("评估结果:\n")
        f.write(f"总移动数: {stats['total_moves']}\n")
        f.write(f"匹配移动数: {stats['matched_moves']}\n")
        f.write(f"匹配率: {stats['match_rate']:.2%}\n")
        f.write(f"平均胜率差距: {stats['average_win_rate_gap']:.4f}\n")
        f.write(f"评估耗时: {end_time - start_time:.2f}秒\n\n")
        f.write(f"详细结果文件: {output_file}\n")
    
    print(f"评估摘要已保存至: {summary_file}")

if __name__ == "__main__":
    main()