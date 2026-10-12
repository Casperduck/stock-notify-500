import os
import requests
import yfinance as yf
import pandas as pd
from datetime import datetime

# 設定 Telegram 金鑰
TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")
CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID")

def send_telegram_alert(text):
    """發送勝率追蹤與績效報告至 Telegram"""
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

def track_historical_performance():
    print("開始執行歷史策略勝率與績效追蹤...")
    
    # 這裡可以隨著日後 Google Sheets 累積的歷史選股資料進行擴充
    # 目前為示範結構：追蹤過去所挑選標的的表現
    sample_historical_picks = [
        {"code": "3455.TW", "name": "由田", "pick_date": "2026-10-01", "pick_price": 280.0},
        {"code": "6239.TW", "name": "力成", "pick_date": "2026-10-01", "pick_price": 295.0}
    ]
    
    win_count = 0
    total_count = len(sample_historical_picks)
    return_sum = 0.0
    report_lines = []
    
    for pick in sample_historical_picks:
        try:
            ticker = yf.Ticker(pick["code"])
            df = ticker.history(period="5d")
            if not df.empty:
                current_price = df['Close'].iloc[-1]
                ret = ((current_price - pick["pick_price"]) / pick["pick_price"]) * 100
                return_sum += ret
                if ret > 0:
                    win_count += 1
                report_lines.append(f"• `{pick['name']}` ({pick['pick_date']}推薦): 現價 `{current_price:.2f}` | 累積報酬: `{ret:+.2f}%`")
        except Exception as e:
            print(f"計算 {pick['name']} 績效失敗: {e}")
            
    if total_count > 0:
        avg_return = return_sum / total_count
        win_rate = (win_count / total_count) * 100
        
        summary_text = (
            f"📊 **【策略歷史勝率與績效追蹤】**\n"
            f"📈 樣本數：`{total_count} 檔`\n"
            f"🎯 累積勝率：`{win_rate:.1f}%`\n"
            f"💰 平均報酬率：`{avg_return:+.2f}%`\n\n"
            f"🔍 **近期標的追蹤明細**：\n" + "\n".join(report_lines)
        )
        
        send_telegram_alert(summary_text)
        print("已發送歷史勝率追蹤報告至 Telegram。")
    else:
        print("目前尚無歷史追蹤樣本。")

if __name__ == "__main__":
    track_historical_performance()
