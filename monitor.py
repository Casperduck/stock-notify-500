import os
import requests
import yfinance as yf
import pandas as pd
from datetime import datetime

# 設定 Telegram 金鑰
TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")
CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID")

# 你的 5 檔核心持股、自訂防守價
WATCHLIST = [
    {"code": "3455.TW", "name": "由田", "support": 280.0},
    {"code": "5475.TW", "name": "德宏", "support": 195.0},
    {"code": "6239.TW", "name": "力成", "support": 290.0},
    {"code": "6708.TW", "name": "力智", "support": 180.0},
    {"code": "8039.TW", "name": "台虹", "support": 290.0}
]

def send_telegram_alert(text):
    """發送 Telegram 風險警報"""
    if not TOKEN or not CHAT_ID:
        return
    url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
    payload = {"chat_id": CHAT_ID, "text": text, "parse_mode": "Markdown"}
    try:
        requests.post(url, json=payload, timeout=10)
    except Exception as e:
        print(f"發送警報失敗: {e}")

def monitor_watchlist():
    print("開始執行持股防守點位與 5MA 動態監控...")
    alert_messages = []
    
    for stock in WATCHLIST:
        code = stock["code"]
        name = stock["name"]
        fixed_support = stock["support"]
        
        try:
            ticker = yf.Ticker(code)
            df = ticker.history(period="15d")
            
            if len(df) >= 5:
                # 計算 5 日均線 (5MA)
                df['MA5'] = df['Close'].rolling(window=5).mean()
                
                current_price = df['Close'].iloc[-1]
                ma5_price = df['MA5'].iloc[-1]
                prev_close = df['Close'].iloc[-2] if len(df) > 1 else current_price
                
                print(f"[{name} ({code})] 現價: {current_price:.2f} | 5MA: {ma5_price:.2f} | 自訂支撐: {fixed_support}")
                
                # 檢查條件一：跌破自訂防守價
                if current_price < fixed_support:
                    alert_messages.append(
                        f"⚠️ **【自訂支撐破線】**：`{name} ({code})` 收盤價 `{current_price:.2f}` 已跌破防守價 `{fixed_support}`！"
                    )
                
                # 檢查條件二：跌破 5 日均線 (5MA)
                if current_price < ma5_price:
                    alert_messages.append(
                        f"📉 **【跌破 5MA 警報】**：`{name} ({code})` 收盤價 `{current_price:.2f}` 已跌破 5 日均線 (`{ma5_price:.2f}`)！"
                    )
                    
        except Exception as e:
            print(f"獲取 {name} 股價與計算 5MA 失敗: {e}")
            
    # 如果有觸發任何警報，發送 Telegram 通知
    if alert_messages:
        alert_text = "🚨 **持股風險動態雷達（雙重防守監控）**\n\n" + "\n".join(alert_messages)
        send_telegram_alert(alert_text)
        print("已發送持股防守與 5MA 警報至 Telegram。")
    else:
        print("今日持股皆安穩站上 5MA 與防守支撐之上。")

if __name__ == "__main__":
    monitor_watchlist()
