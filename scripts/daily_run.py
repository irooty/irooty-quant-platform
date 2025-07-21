# 每日运行
# scripts/daily_run.py
# 自动定时任务脚本：每天定时运行自动交易入口（可用于定时调度）
import schedule
import os
import time

def run_trade():
    # 可根据实际路径调整（支持日志重定向等）
    os.system("python scripts/run_trade.py")

# 设置每天早上16:12自动执行 run_trade
schedule.every().day.at("16:12").do(run_trade)

print("定时任务已启动，将在每天16:12自动运行交易脚本。")

while True:
    schedule.run_pending()
    time.sleep(1)
