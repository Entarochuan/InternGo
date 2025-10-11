# Copyright 2024 Bytedance Ltd. and/or its affiliates
# Copyright 2022 EleutherAI and the HuggingFace Inc. team. All rights reserved.
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
# Adapted from https://github.com/EleutherAI/lm-evaluation-harness/blob/main/lm_eval/tasks/hendrycks_math/utils.py

import re
import ast
import json
import traceback
import requests
import random

ASSISTANT_PATTERN = re.compile(r'<\|im_start\|>assistant\n(.*)', re.DOTALL)
REASONING_PATTERN = re.compile(r'<reasoning>(.*?)</reasoning>', re.DOTALL)

def extract_coordinate(solution_str):
    """
    从模型输出中提取坐标和颜色
    处理步骤：
    1. 提取assistant回复部分
    2. 检查是否存在<think>标签
    3. 从<answer>标签或原始格式中提取坐标和颜色
    """
    try:
        # 提取assistant回复部分
        assistant_match = ASSISTANT_PATTERN.search(solution_str)
        if not assistant_match:
            content = solution_str
        else :
            content = assistant_match.group(1)

        # 检查是否存在<reasoning>标签
        has_think = bool(REASONING_PATTERN.search(content))
        
        # 提取<reasoning>中包含的内容
        reasoning_match = REASONING_PATTERN.search(content)
        if reasoning_match:
            reasoning_content = reasoning_match.group(1)
        else :
            reasoning_content = ""
        
        # 尝试从<answer>标签中提取
        answer_match = re.search(r'<answer>(.*?)</answer>', content, re.DOTALL)
        if answer_match:
            content = answer_match.group(1)
        else :
            return None
        
        # 提取颜色,坐标和胜率
        color_match = re.search(r'\\boxed\{下一步颜色:(黑|白)\}', content)
        if not color_match:
            return None
        color = color_match.group(1)
        
        coord_match = re.search(r'\\boxed\{下一步位置:([A-HJ-T]\d+)\}', content)
        if not coord_match:
            # 尝试旧格式匹配
            coord_match = re.search(r'\\boxed\{([A-HJ-T]\d+)\}', content)
            if not coord_match:
                return None
        
        win_rate_match = re.search(r'\\boxed\{下一步胜率:(\d+\.\d+)\%\}', content)
        if not win_rate_match:
            return None
        win_rate = float(win_rate_match.group(1))
        
        coordinate = coord_match.group(1)
        # 验证数字部分是否在1-19范围内
        letter, number = coordinate[0], int(coordinate[1:])
        if 1 <= number <= 19:
            # 返回坐标、颜色和是否包含think标签
            return coordinate, color, win_rate, has_think, reasoning_content
        return None
        
    except Exception as e:
        print(f"Error extracting coordinate and color: {str(e)}")
        return None

def compute_score(solution_str, ground_truth) -> float:
    
    if random.random() < 0.001:
        # 限制输出长度
        print(f"solution_str:\n {solution_str}...")
        
    score = 0.0
    try:
        # 提取坐标
        result = extract_coordinate(solution_str)
        if not result:
            print("提取信息失败")
            return score
        
        move, color, pred_win_rate, has_think, think_content = result
        
        # print(f"move: {move}, color: {color}, has_think: {has_think}, think_content: {think_content}")
        if not has_think or think_content == "":
            return score
                
        score += 0.1
        
        # 判断黑白是否正确
        original_move_number = len(ground_truth['former_moves']) + 1
        if original_move_number % 2 == 1:
            gt_color = '黑' # 最后一步是白棋，因此当前是黑棋
        else:
            gt_color = '白'
        
        if gt_color != color:
            print(f"黑白颜色错误: {gt_color} != {color}")
            score -= 0.1
            return score
        
        # 获取当前这一步的最优落子
        candidates = {str(move_info['move']): move_info for move_info in ground_truth['candidates']}
        gt_best_move, gt_best_win_rate = None, 0
        for move_info in ground_truth['candidates']:
            win_rate_value = float(move_info['win_rate'])  # 确保转换为Python float
            if gt_best_win_rate < win_rate_value:
                gt_best_move = str(move_info['move'])
                gt_best_win_rate = win_rate_value
        
        if str(move) in candidates: # Our main Reward Function
            in_state = 0
            if str(move) == gt_best_move: 
                in_state = 0
                score += 0.6
                
            # 奖励和top 1差距在0.9以内
            elif float(candidates[str(move)]['win_rate']) > gt_best_win_rate*0.9 :
                in_state = 1
                score += 0.4 
            else:
                in_state = 2
                score += 0.2
            win_rate = candidates[str(move)]['win_rate']
            
            diff = win_rate - gt_best_win_rate
            score += 0.1 * (1 / (1 + 10 * abs(diff))) # 奖励实际winrate接近最优winrate的落子
            if in_state == 0:
                move_str = f"当前落子是top 1落子"
            elif in_state == 1:
                move_str = f"当前胜率在top 1落子的0.9以内"
            elif in_state == 2:
                move_str = f"当前胜率在top 1落子的0.9以外"
                
            # winrate和这一步的实际胜率越接近，得分越高
            diff = abs(win_rate - pred_win_rate*0.01)
            score += 0.2 * (1 / (1 + 10 * abs(diff)))
            
            print(f"{move_str},胜率:{win_rate:.2f},最优胜率:{gt_best_win_rate:.2f},预测胜率:{pred_win_rate*0.01:.2f},得分:{score:.2f}")
        else : 
            print(f"当前落子不在top 10落子中!")
            score -= 0.1 
            
        return score
        
    except Exception as e:
        print(f"Error in compute_score: {type(e).__name__}: {str(e)}")
        return 0.0
