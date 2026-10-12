import os
import requests
import yfinance as yf
import pandas as pd
from datetime import datetime

TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")
CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID")

# 你的 5 檔核心持股（加入追蹤波段高點與移動停利回檔幅度設定，例如回檔 7% 啟動警報）
WATCHLIST = [
    {"code": "3455.TW", "name": "由田", "support": 280.0, "max_drawdown_pct": 7.0},
    {"code": "5475.TW", "name": "德宏", "support": 195.0, "max_drawdown_pct": 7.0},
    {"code": "6239.TW", "name": "力成", "support": 290.0, "max_drawdown_pct": 7.0},
    {"code": "6708.TW", "name": "力智", "support": 180.0, "max_drawdown_pct": 7.0},
    {"code": "8039.TW", "name": "台虹", "support": 290.0, "max_drawdown_pct": 7.0}
]

def send_telegram_alert(text):
    if not TOKEN or not CHAT_ID:
        return
    url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
    payload = {"chat_id": CHAT_ID, "text": text, "parse_mode": "Markdown"}
    try:
        requests.post(url, json=payload, timeout=10)
    except Exception as e:
        print(f"發送警報失敗: {e}")

def monitor_watchlist():
    print("開始執行持股動態移動停利與 5MA 雙重防守監控...")
    alert_messages = []
    
    for stock in WATCHLIST:
        code = stock["code"]
        name = stock["name"]
        fixed_support = stock["support"]
        allowed_drawdown = stock["max_drawdown_pct"]
        
        try:
            ticker = yf.Ticker(code)
            # 抓取較長天數（例如近 30 天）來計算波段最高點，實現移動停利
            df = ticker.history(period="30d")
            
            if len(df) >= 5:
                df['MA5'] = df['Close'].rolling(window=5).mean()
                
                current_price = df['Close'].iloc[-1]
                ma5_price = df['MA5'].iloc[-1]
                
                # 計算近 30 天內的波段最高收盤價（移動停利基準）
                recent_highest = df['Close'].max()
                drawdown_from_high = ((recent_highest - current_price) / recent_highest) * 100
                
                print(f"[{name} ({code})] 現價: {current_price:.2f} | 5MA: {ma5_price:.2f} | 近期高點: {recent_highest:.2f} (回檔 {drawdown_from_high:.1f}%)")
                
                # 條件一：跌破固定防守支撐價
                if current_price < fixed_support:
                    alert_messages.append(
                        f"⚠️ **【自訂支撐破線】**：`{name} ({code})` 收盤價 `{current_price:.2f}` 已跌破防守價 `{fixed_support}`！"
                    )
                
                # 條件二：跌破 5 日均線 (5MA)
                if current_price < ma5_price:
                    alert_messages.append(
                        f"📉 **【跌破 5MA 警報】**：`{name} ({code})` 收盤價 `{current_price:.2f}` 已跌破 5 日均線 (`{ma5_price:.2f}`)！"
                    )
                
                # 條件三：移動停利觸發（從波段最高點回檔超過設定幅度）
                if drawdown_from_high >= allowed_drawdown:
                    alert_messages.append(
                        f"💰 **【移動停利觸發】**：`{name} ({code})` 自波段高點 `{recent_highest:.2f}` 回檔達 `{drawdown_from_high:.1f}%`（現價 `{current_price:.2f}`），請注意獲利入袋！"
                    )
                    
        except Exception as e:
            print(f"獲取 {name} 股價與計算移動停利失敗: {e}")
            
    if alert_messages:
        alert_text = "🚨 **持股智慧風控雷達（移動停利與雙重防守）**\n\n" + "\n".join(alert_messages)
        send_telegram_alert(alert_text)
        print("已發送智慧風控警報至 Telegram。")
    else:
        print("今日持股皆在安全防守與移動停利區間內。")

if __name__ == "__main__":
    monitor_watchlist()
