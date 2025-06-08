import sys, os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
# 导入 Qlib 策略、回测、评估等相关模块
from qlib.contrib.strategy import TopkDropoutStrategy
from qlib.contrib.evaluate import risk_analysis
from qlib.backtest import backtest, executor
from qlib.contrib.data.handler import Alpha158
from datasets.init_qlib import init_qlib

def main():
    """
    初始化 Qlib 环境，执行简单的 TopKDropout 策略回测，并输出绩效指标
    """
    # 1. 初始化 Qlib 数据（本地模式）
    init_qlib()

    # 2.使用 Alpha158 数据处理器，用 handler 生成 signal DataFrame
    handler = Alpha158()
    # 默认用因子 "RESI5" 作为信号分数，你也可以选其它因子
    df_feature = handler.fetch(col_set="feature")  # 取全部因子
    print("可用因子:", df_feature.columns.tolist())

    # 3.自动挑一个“非空且非全0/NaN”的因子作为score，优先RESI5、否则用第一个有效因子
    # df_score = df_feature[["RESI5"]].rename(columns={"RESI5": "score"})
    candidate_cols = ["RESI5"] + df_feature.columns.tolist()
    for col in candidate_cols:
        if col in df_feature.columns and df_feature[col].notnull().any() and (df_feature[col] != 0).any():
            print(f"用 {col} 作为 score")
            df_score = df_feature[[col]].rename(columns={col: "score"})
            break
    else:
        raise ValueError("找不到任何可用的信号列，回测无法执行！")

    # 4. 检查信号数据分布
    print("score列分布：")
    print(df_score["score"].describe())
    print("信号最大日期：", df_score.index.get_level_values(0).max())
    print("信号最小日期：", df_score.index.get_level_values(0).min())

    # 5. 取信号日期作为回测区间边界，end_time用倒数第二天（保证Qlib不越界）
    all_dates = sorted(set(df_score.index.get_level_values(0)))
    if len(all_dates) > 1:
        safe_end_date = all_dates[-2]
    else:
        raise ValueError("信号数据天数太少，无法回测！")
    start_time = str(all_dates[0])
    print(f"实际回测区间：{start_time} - {safe_end_date}")

    # 6. 用 TopkDropoutStrategy 构造策略（传入 signal），策略（取前50只，丢弃5只）
    strategy = TopkDropoutStrategy(signal=df_score, topk=50, n_drop=5)

    # 7. 构造执行器，常用选项有 "day"（按日回测）、"week"、"month"。
    trade_executor = executor.SimulatorExecutor(time_per_step="day")

    # 8. 正式回测
    report, positions = backtest(
        start_time=start_time,
        end_time=str(safe_end_date),
        strategy=strategy,
        executor=trade_executor,
        account=100000000,
        benchmark="SH000300"
    )
    print("回测结果类型：", type(report), type(positions))
    print("report内容：", report)

    # 9. 输出绩效分析（如年化收益率、夏普比率等）
    # 如果要分析每日资金曲线用 "account_value"，要分析持仓结构用 positions。
    if isinstance(report, dict) and "account_value" in report and hasattr(report["account_value"], "mean"):
        analysis = risk_analysis(report["account_value"], "report")
        print("绩效分析：")
        print(analysis)
    else:
        print("[警告] 回测未生成有效资金曲线，检查信号/数据/区间！")
        print("report内容：", report)

    # 6. 可选：输出资金曲线或保存结果
    # report.to_csv("backtest_report.csv")
    # positions.to_csv("positions.csv")

if __name__ == "__main__":
    main()
