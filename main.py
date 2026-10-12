import os
import requests
import yfinance as yf
import pandas as pd
from datetime import datetime

# 設定 Telegram 金鑰與 Google Sheets 網址
TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")
CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID")
SHEETS_URL = os.environ.get("GOOGLE_SHEETS_WEB_APP_URL")

def send_telegram_message(text):
    """發送 Telegram 選股結果通知"""
    if not TOKEN or not CHAT_ID:
        print("未設定 Telegram 金鑰，略過發送。")
        return
    url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
    payload = {
        "chat_id": CHAT_ID,
        "text": text,
        "parse_mode": "Markdown"
    }
    try:
        response = requests.post(url, json=payload, timeout=10)
        response.raise_for_status()
    except Exception as e:
        print(f"發送 Telegram 失敗: {e}")

def log_to_google_sheets(stock_text, close_price, change_pct, support, resistance, sentiment):
    """將選股與戰情數據同步寫入 Google 試算表"""
    if not SHEETS_URL:
        print("未設定 GOOGLE_SHEETS_WEB_APP_URL，略過雲端存檔。")
        return
    
    payload = {
        "date": datetime.now().strftime("%Y-%m-%d"),
        "stocks": stock_text,
        "close_price": str(close_price),
        "change_pct": str(change_pct),
        "support": str(support),
        "resistance": str(resistance),
        "institutional": "主力籌碼共振確認",
        "sentiment": sentiment
    }
    
    try:
        res = requests.post(SHEETS_URL, json=payload, timeout=10)
        if res.status_code == 200:
            print("成功同步數據至 Google 試算表！")
        else:
            print(f"寫入 Google 試算表失敗，狀態碼：{res.status_code}")
    except Exception as e:
        print(f"寫入 Google 試算表發生例外錯誤：{e}")

def check_institutional_and_volume_resonance(code):
    """
    【主力籌碼與量價共振過濾機制】
    檢查條件：
    1. 近期成交量放大（突破近期平均量 1.2 倍以上），代表主力資金點火。
    2. 價格站穩 5MA 且呈現多頭排列。
    """
    try:
        ticker = yf.Ticker(code)
        df = ticker.history(period="20d")
        
        if len(df) >= 10:
            df['MA5'] = df['Close'].rolling(window=5).mean()
            df['MA20'] = df['Close'].rolling(window=20).mean()
            
            current_price = df['Close'].iloc[-1]
            ma5 = df['MA5'].iloc[-1]
            ma20 = df['MA20'].iloc[-1]
            
            recent_volume = df['Volume'].iloc[-1]
            avg_volume_5d = df['Volume'].iloc[-6:-1].mean()
            
            # 判斷共振條件：現價高於 5MA 與 20MA，且當日成交量大於 5 日均量 1.2 倍
            is_volume_breakout = recent_volume >= (avg_volume_5d * 1.2)
            is_trend_up = current_price > ma5 and ma5 > ma20
            
            if is_volume_breakout and is_trend_up:
                support_price = round(ma5, 2)
                resistance_price = round(current_price * 1.05, 2)  # 預期壓力約上方 5%
                change_p = ((current_price - df['Close'].iloc[-2]) / df['Close'].iloc[-2]) * 100
                
                return True, round(current_price, 2), round(change_p, 2), support_price, resistance_price
                
    except Exception as e:
        print(f"分析 {code} 籌碼與量價失敗: {e}")
        
    return False, 0, 0, 0, 0

def main():
    print("開始執行模組一與二：高勝率技術選股與主力籌碼共振掃描...")
    
    # 你關注的自選潛力池或全市場掃描清單
    watch_pool = [
        {"code": "3455.TW", "name": "由田"},
        {"code": "5475.TW", "name": "德宏"},
        {"code": "6239.TW", "name": "力成"},
        {"code": "6708.TW", "name": "力智"},
        {"code": "8039.TW", "name": "台虹"},
        {"code": "2330.TW", "name": "台積電"},
        {"code": "2382.TW", "name": "廣達"}
    ]
    
    triggered_stocks = []
    
    for stock in watch_pool:
        code = stock["code"]
        name = stock["name"]
        
        # 進行主力籌碼與量價共振過濾
        passed, price, change, support, resistance = check_institutional_and_volume_resonance(code)
        
        if passed:
            triggered_stocks.append({
                "name": name,
                "code": code,
                "price": price,
                "change": change,
                "support": support,
                "resistance": resistance
            })
            
    # 組合推播訊息與試算表記錄
    if triggered_stocks:
        stock_lines = []
        for s in triggered_stocks:
            stock_lines.append(f"• `{s['name']} ({s['code']})`: 現價 `{s['price']}` (`{s['change']:+.2f}%`) | 建議支撐: `{s['support']}` | 預期壓力: `{s['resistance']}`")
        
        # 修正後的正確字串格式
        stock_text = "\n".join([f"{s['name']} ({s['code']})" for s in triggered_stocks])
        primary_stock = triggered_stocks[0]
        
        report = (
            f"🚀 **【高勝率爆量突破與主力籌碼共振日報】**\n"
            f"📅 掃描日期：`{datetime.today().strftime('%Y-%m-%d')}`\n\n"
            f"🎯 **符合共振條件標的**：\n" + "\n".join(stock_lines) + "\n\n"
            f"💡 **系統評語**：「成交量放大伴隨多頭排列，主力資金積極介入，短線動能強勁。」"
        )
        
        send_telegram_message(report)
        log_to_google_sheets(
            stock_text=stock_text,
            close_price=primary_stock['price'],
            change_pct=primary_stock['change'],
            support=primary_stock['support'],
            resistance=primary_stock['resistance'],
            sentiment="主力籌碼共振偏多"
        )
    else:
        no_match_text = "今日無標的符合主力籌碼與量價共振條件（盤勢震盪整理中）"
        print(no_match_text)
        send_telegram_message(f"📊 **【選股掃描日報】**\n📅 日期：`{datetime.today().strftime('%Y-%m-%d')}`\n\n{no_match_text}")
        log_to_google_sheets(
            stock_text="今日未觸發",
            close_price="-",
            change_pct="-",
            support="-",
            resistance="-",
            sentiment="盤勢觀望"
        )

if __name__ == "__main__":
    main()
