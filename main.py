import os
import requests
import pandas as pd
import numpy as np
import yfinance as yf
from io import BytesIO
import matplotlib.pyplot as plt
import matplotlib.dates as mdates

# 設定 Telegram 金鑰
TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")
CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID")

def send_telegram_message(text):
    """發送純文字 Telegram 通知"""
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
        print(f"發送 Telegram 文字訊息失敗: {e}")

def send_telegram_photo(photo_bytes, caption):
    """發送帶有圖說的圖片到 Telegram"""
    url = f"https://api.telegram.org/bot{TOKEN}/sendPhoto"
    files = {
        "photo": ("chart.png", photo_bytes, "image/png")
    }
    data = {
        "chat_id": CHAT_ID,
        "caption": caption,
        "parse_mode": "Markdown"
    }
    try:
        response = requests.post(url, data=data, files=files, timeout=15)
        response.raise_for_status()
    except Exception as e:
        print(f"發送 Telegram 圖片失敗: {e}")

def generate_stock_chart(df, stock_name, stock_id):
    """繪製 K 線與 MA 均線圖並轉換為二進位圖片資料"""
    plt.rcParams['font.sans-serif'] = ['DejaVu Sans'] # 確保圖表字型相容
    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(10, 8), gridspec_kw={'height_ratios': [3, 1]}, sharex=True)
    
    # 畫 K 線與均線 (MA20, MA60)
    ax1.plot(df.index, df['Close'], label='Close', color='#1f77b4', linewidth=1.5)
    ax1.plot(df.index, df['MA20'], label='MA20', color='#ff7f0e', linewidth=1)
    ax1.plot(df.index, df['MA60'], label='MA60 (季線)', color='#2ca02c', linewidth=1.5)
    
    ax1.set_title(f"{stock_id} {stock_name} - 技術線圖突破", fontsize=14, fontweight='bold', pad=10)
    ax1.set_ylabel("Price (TWD)", fontsize=11)
    ax1.legend(loc='upper left', fontsize=10)
    ax1.grid(True, linestyle='--', alpha=0.5)
    
    # 畫成交量 Volume
    colors = ['#d62728' if close >= open_ else '#2ca02c' for close, open_ in zip(df['Close'], df['Open'])]
    ax2.bar(df.index, df['Volume'] / 1000, color=colors, alpha=0.8, width=0.8)
    ax2.set_ylabel("Volume (千股)", fontsize=11)
    ax2.grid(True, linestyle='--', alpha=0.5)
    
    # 日期格式化
    ax2.xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m-%d'))
    fig.autofmt_xdate()
    
    plt.tight_layout()
    
    # 將圖片存入記憶體緩衝區
    buf = BytesIO()
    plt.savefig(buf, format='png', dpi=150)
    buf.seek(0)
    plt.close(fig)
    return buf.getvalue()

def get_top500_symbols():
    """從 Yahoo Finance 抓取代表性股票清單"""
    symbols = [
        "2330.TW", "2317.TW", "2454.TW", "2308.TW", "2382.TW", 
        "3231.TW", "3017.TW", "2356.TW", "2376.TW", "6669.TW",
        "3035.TW", "3711.TW", "3008.TW", "2603.TW", "2609.TW"
    ]
    return symbols

def main():
    print("開始執行高勝率台股圖表化選股掃描...")
    symbols = get_top500_symbols()
    matched_stocks = []

    for symbol in symbols:
        try:
            df = yf.download(symbol, period="6mo", interval="1d", progress=False)
            if df.empty or len(df) < 60:
                continue
            
            # 確保欄位扁平化
            if isinstance(df.columns, pd.MultiIndex):
                df.columns = df.columns.get_level_values(0)

            # 計算技術指標
            df['MA20'] = df['Close'].rolling(window=20).mean()
            df['MA60'] = df['Close'].rolling(window=60).mean()
            df['Vol_MA5'] = df['Volume'].rolling(window=5).mean()
            
            latest = df.iloc[-1]
            prev = df.iloc[-2]
            
            body = abs(latest['Close'] - latest['Open'])
            total_range = latest['High'] - latest['Low']
            body_ratio = body / total_range if total_range > 0 else 0
            pct_change = (latest['Close'] - prev['Close']) / prev['Close'] * 100
            
            is_breakout = (prev['Close'] <= prev['MA60']) and (latest['Close'] > latest['MA60'])
            is_volume_surge = latest['Volume'] >= (latest['Vol_MA5'] * 2)
            is_strong_k = (2 <= pct_change <= 7) and (body_ratio >= 0.7)
            
            if is_breakout and is_volume_surge and is_strong_k:
                stock_id = symbol.replace(".TW", "")
                chart_bytes = generate_stock_chart(df, stock_id, stock_id)
                matched_stocks.append({
                    "id": stock_id,
                    "close": latest['Close'],
                    "pct": pct_change,
                    "chart": chart_bytes
                })
        except Exception as e:
            print(f"處理 {symbol} 時發生錯誤: {e}")

    # 發送 Telegram 通知
    if matched_stocks:
        for stock in matched_stocks:
            caption = (
                f"🔥 **【高勝率突破選股通知】** 🔥\n\n"
                f"📌 股票代號：`{stock['id']}`\n"
                f"💰 收盤價：`{stock['close']:.2f}`\n"
                f"📈 當日漲幅：`+{stock['pct']:.2f}%`\n"
                f"✨ 達成條件：突破 MA60 季線 + 爆量 2 倍 + 強勢長紅 K！"
            )
            send_telegram_photo(stock['chart'], caption)
    else:
        send_telegram_message(
            "【高勝率台股選股通知】\n\n"
            "今日掃描完成：未有同時符合嚴格多頭突破條件的個股。"
        )

if __name__ == "__main__":
    main()
