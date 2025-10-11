const Board = require('@sabaki/go-board');

/**
 * 围棋游戏核心类
 */
class GoGame {
    constructor() {
        this.board = Board.fromDimensions(19);
        this.ROW_LIST = ['A', 'B', 'C', 'D', 'E', 'F', 'G', 'H', 'J', 'K', 'L', 'M', 'N', 'O', 'P', 'Q', 'R', 'S', 'T'];
        this.COL_LIST = ['1', '2', '3', '4', '5', '6', '7', '8', '9', '10', '11', '12', '13', '14', '15', '16', '17', '18', '19'].reverse();
    }

    /**
     * 单步落子
     * @param {number} sign - 棋子颜色 (1为黑子，-1为白子)
     * @param {Array} vertex - 坐标 [row, col]
     * @returns {Object} 结果对象
     */
    move(sign, vertex) {
        try {
            this.board = this.board.makeMove(
                sign,
                vertex,
                {
                    preventOverwrite: true,
                    preventSuicide: true,
                    preventKo: true
                }
            );
            return { success: true, message: '落子成功' };
        } catch (error) {
            return { success: false, message: error.message };
        }
    }

    /**
     * 批量落子
     * @param {Array} moves - 落子序列 [{sign: 1, vertex: [row, col]}, ...]
     * @returns {Object} 结果对象，包含棋盘状态
     */
    batchMove(moves) {
        const results = [];
        let success = true;
        let errorMessage = '';

        for (let i = 0; i < moves.length; i++) {
            const { sign, vertex } = moves[i];
            const result = this.move(sign, vertex);
            results.push({
                step: i + 1,
                sign,
                vertex,
                success: result.success,
                message: result.message
            });

            if (!result.success) {
                success = false;
                errorMessage = `第${i + 1}步落子失败: ${result.message}`;
                break;
            }
        }

        return {
            success,
            message: success ? '批量落子完成' : errorMessage,
            steps: results,
            board: this.getMap()
        };
    }

    /**
     * 检查落子是否合法
     * @param {number} sign - 棋子颜色
     * @param {Array} vertex - 坐标
     * @returns {boolean} 是否合法
     */
    check(sign, vertex) {
        try {
            const result = this.board.analyzeMove(Number(sign), vertex);
            const isCapturing = result.capturing;
            const isSuicide = result.suicide;
            const isKo = result.ko;
            const isOverwrite = result.overwrite;
            const isPass = result.pass;

            return !isSuicide && !isKo && !isOverwrite && !isPass;
        } catch (error) {
            return false;
        }
    }

    /**
     * 批量检查落子合法性
     * @param {Array} moves - 落子序列
     * @returns {Array} 每步的合法性检查结果
     */
    batchCheck(moves) {
        // 创建临时棋盘用于检查
        let tempBoard = this.board;
        const results = [];

        for (let i = 0; i < moves.length; i++) {
            const { sign, vertex } = moves[i];
            try {
                const result = tempBoard.analyzeMove(Number(sign), vertex);
                const isValid = !result.suicide && !result.ko && !result.overwrite && !result.pass;
                
                results.push({
                    step: i + 1,
                    sign,
                    vertex,
                    isValid,
                    reason: isValid ? '合法' : this.getInvalidReason(result)
                });

                // 如果合法，更新临时棋盘
                if (isValid) {
                    tempBoard = tempBoard.makeMove(sign, vertex, {
                        preventOverwrite: true,
                        preventSuicide: true,
                        preventKo: true
                    });
                } else {
                    break; // 遇到非法步骤就停止检查
                }
            } catch (error) {
                results.push({
                    step: i + 1,
                    sign,
                    vertex,
                    isValid: false,
                    reason: error.message
                });
                break;
            }
        }

        return results;
    }

    /**
     * 获取非法原因
     * @param {Object} result - 分析结果
     * @returns {string} 非法原因
     */
    getInvalidReason(result) {
        if (result.suicide) return '自杀手';
        if (result.ko) return '劫争';
        if (result.overwrite) return '已有棋子';
        if (result.pass) return '传递';
        return '未知原因';
    }

    /**
     * 获取棋盘状态
     * @returns {Array} 棋盘状态二维数组
     */
    getMap() {
        return this.board.signMap;
    }

    /**
     * 获取棋盘状态（扁平化）
     * @returns {Array} 一维数组表示的棋盘状态
     */
    getFlatMap() {
        return this.board.signMap.flat();
    }

    /**
     * 顶点坐标转换为位置字符串
     * @param {Array} vertex - 顶点坐标 [row, col]
     * @returns {string} 位置字符串 (如 "A1")
     */
    convertVertexToPos(vertex) {
        if (!vertex || vertex.length !== 2) {
            return '';
        }
        const [row, col] = vertex;
        if (row < 0 || row >= this.ROW_LIST.length || col < 0 || col >= this.COL_LIST.length) {
            return '';
        }
        return `${this.ROW_LIST[row]}${this.COL_LIST[col]}`;
    }

    /**
     * 位置字符串转换为顶点坐标
     * @param {string} pos - 位置字符串 (如 "A1")
     * @returns {Array} 顶点坐标 [row, col]
     */
    convertPosToVertex(pos) {
        if (!pos) {
            return [];
        }
        const row = this.ROW_LIST.indexOf(pos.slice(0, 1));
        const col = this.COL_LIST.indexOf(pos.slice(1));
        return [row, col];
    }

    /**
     * 重启游戏
     * @returns {Object} 结果对象
     */
    restart() {
        this.board = Board.fromDimensions(19);
        return { success: true, message: '游戏重启成功' };
    }

    /**
     * 获取游戏统计信息
     * @returns {Object} 统计信息
     */
    getGameStats() {
        const signMap = this.board.signMap;
        let blackCount = 0;
        let whiteCount = 0;
        let emptyCount = 0;

        for (let row = 0; row < 19; row++) {
            for (let col = 0; col < 19; col++) {
                const sign = signMap[row][col];
                if (sign === 1) blackCount++;
                else if (sign === -1) whiteCount++;
                else emptyCount++;
            }
        }

        return {
            blackStones: blackCount,
            whiteStones: whiteCount,
            emptyPoints: emptyCount,
            totalMoves: blackCount + whiteCount
        };
    }

    /**
     * 克隆当前游戏状态
     * @returns {GoGame} 新的游戏实例
     */
    clone() {
        const newGame = new GoGame();
        newGame.board = this.board;
        return newGame;
    }
}

// 便捷函数

/**
 * 创建新的围棋游戏
 * @returns {GoGame} 游戏实例
 */
function createGame() {
    return new GoGame();
}

/**
 * 快速批量落子并获取棋盘状态
 * @param {Array} moves - 落子序列
 * @returns {Object} 包含棋盘状态的结果
 */
function quickBatchMove(moves) {
    const game = new GoGame();
    return game.batchMove(moves);
}

/**
 * 快速检查一系列落子是否合法
 * @param {Array} moves - 落子序列
 * @returns {Array} 检查结果
 */
function quickBatchCheck(moves) {
    const game = new GoGame();
    return game.batchCheck(moves);
}

/**
 * 从棋盘状态创建游戏（用于恢复游戏状态）
 * @param {Array} moves - 落子历史
 * @returns {GoGame} 游戏实例
 */
function createGameFromMoves(moves) {
    const game = new GoGame();
    const result = game.batchMove(moves);
    if (result.success) {
        return game;
    } else {
        throw new Error(`无法从落子历史恢复游戏状态: ${result.message}`);
    }
}

// 导出
module.exports = {
    GoGame,
    createGame,
    quickBatchMove,
    quickBatchCheck,
    createGameFromMoves
};