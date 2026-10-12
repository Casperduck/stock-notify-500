import os
import requests
import yfinance as yf
import pandas as pd
from datetime import datetime

TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")
CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID")

def send_telegram_alert(text):
    """發送策略勝率與績效報告至 Telegram"""
    if not TOKEN or not CHAT_ID:
        print("未設定 Telegram 金鑰，略過發送。")
        return
    url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
    payload = {"chat_id": CHAT_ID, "text": text, "parse_mode": "Markdown"}
    try:
        response = requests.post(url, json=payload, timeout=10)
        response.raise_for_status()
    except Exception as e:
        print(f"發送歷史勝率追蹤通知失敗: {e}")

def track_strategy_performance():
    print("開始執行『系統策略推薦標的』歷史勝率與績效追蹤...")
    
    # 【嚴格規範】這裡僅記錄「系統條件篩選出的推薦標的」，絕不包含個人持股庫存
    # 隨著每日自動化掃頻執行，系統會將選出的標的累積於此（或透過 Google 試算表同步回測）
    # 目前為空清單或模擬歷史推薦池，等待系統累積真實數據
    strategy_recommended_picks = [
        # 範例格式：{"code": "2330.TW", "name": "台積電", "pick_date": "2026-10-01", "pick_price": 1000.0}
    ]
    
    if not strategy_recommended_picks:
        print("目前尚無累積的策略推薦歷史標的，等待每日選股累積中...")
        # 也可以選擇不發送訊息，或發送提示
        return

    win_count = 0
    total_count = len(strategy_recommended_picks)
    return_sum = 0.0
    report_lines = []
    
    for pick in strategy_recommended_picks:
        try:
            ticker = yf.Ticker(pick["code"])
            df = ticker.history(period="5d")
            if not df.empty:
                current_price = df['Close'].iloc[-1]
                ret = ((current_price - pick["pick_price"]) / pick["pick_price"]) * 100
                return_sum += ret
                if ret > 0:
                    win_count += 1
                report_lines.append(f"• `{pick['name']}` ({pick['pick_date']}策略推薦): 現價 `{current_price:.2f}` | 累積報酬: `{ret:+.2f}%`")
        except Exception as e:
            print(f"計算 {pick['name']} 績效失敗: {e}")
            
    if total_count > 0:
        avg_return = return_sum / total_count
        win_rate = (win_count / total_count) * 100
        
        summary_text = (
            f"📊 **【系統策略選股歷史勝率與績效】**\n"
            f"📈 推薦樣本數：`{total_count} 檔`\n"
            f"🎯 策略累積勝率：`{win_rate:.1f}%`\n"
            f"💰 平均報酬率：`{avg_return:+.2f}%`\n\n"
            f"🔍 **策略推薦標的追蹤明細**：\n" + "\n".join(report_lines)
        )
        
        send_telegram_alert(summary_text)
        print("已發送策略歷史勝率追蹤報告至 Telegram。")

if __name__ == "__main__":
    track_strategy_performance()
