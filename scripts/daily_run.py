# 每日运行
import schedule
import os

schedule.every().day.at("09:35").do(lambda: os.system("python scripts/run_trade.py"))

while True:
    schedule.run_pending()
    time.sleep(1)
