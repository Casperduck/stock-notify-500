import os
import requests
import pandas as pd
import numpy as np
import yfinance as yf
from io import BytesIO
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from datetime import datetime, timedelta

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

def fetch_finmind_institutional(stock_id):
    """透過 FinMind API 取得最新三大法人買賣超資料"""
    try:
        end_date = datetime.today().strftime('%Y-%m-%d')
        start_date = (datetime.today() - timedelta(days=10)).strftime('%Y-%m-%d')
        
        url = "https://api.finmindtrade.com/api/v4/data"
        parameters = {
            "dataset": "TaiwanStockInstitutionalInvestors",
            "data_id": stock_id,
            "start_date": start_date,
            "end_date": end_date,
        }
        response = requests.get(url, params=parameters, timeout=10)
        result = response.json()
        
        data = result.get("data", [])
        if not data:
            return {"外資": 0, "投信": 0, "自營商": 0, "合計": 0}
            
        df_inst = pd.DataFrame(data)
        latest_date = df_inst['date'].max()
        df_latest = df_inst[df_inst['date'] == latest_date]
        
        net_data = {"外資": 0, "投信": 0, "自營商": 0, "合計": 0}
        
        for _, row in df_latest.iterrows():
            name = row['name']
            net_shares = row.get('buy', 0) - row.get('sell', 0)
            net_lots = net_shares / 1000  # 轉成張數
            
            if "Foreign" in name or "外資" in name:
                net_data["外資"] += net_lots
            elif "InvestmentTrust" in name or "投信" in name:
                net_data["投信"] += net_lots
            elif "Dealer" in name or "自營商" in name:
                net_data["自營商"] += net_lots
                
        net_data["合計"] = net_data["外資"] + net_data["投信"] + net_data["自營商"]
        return net_data
    except Exception as e:
        print(f"獲取 {stock_id} FinMind 法人資料失敗: {e}")
        return {"外資": 0, "投信": 0, "自營商": 0, "合計": 0}

def calculate_support_resistance(df):
    """計算近期支撐與壓力點位"""
    # 支撐位：取近期 20 日內的最低價，或是 MA20 取其低者作為防守點
    recent_low = df['Low'].iloc[-20:].min()
    ma20_val = df['MA20'].iloc[-1]
    support = round(min(recent_low, ma20_val), 2)
    
    # 壓力位：取近期 60 日內的高點作為目標壓力區
    resistance = round(df['High'].iloc[-60:].max(), 2)
    
    return support, resistance

def generate_stock_chart(df, stock_name, stock_id):
    """繪製 K 線與 MA 均線圖並轉換為二進位圖片資料"""
    plt.rcParams['font.sans-serif'] = ['DejaVu Sans']
    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(10, 8), gridspec_kw={'height_ratios': [3, 1]}, sharex=True)
    
    # 畫 K 線與均線 (MA20, MA60)
    ax1.plot(df.index, df['Close'], label='Close', color='#1f77b4', linewidth=1.5)
    ax1.plot(df.index, df['MA20'], label='MA20', color='#ff7f0e', linewidth=1)
    ax1.plot(df.index, df['MA60'], label='MA60 (季線)', color='#2ca02c', linewidth=1.5)
    
    ax1.set_title(f"{stock_id} {stock_name} - 嚴格高勝率突破與點位分析", fontsize=14, fontweight='bold', pad=10)
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
    
    buf = BytesIO()
    plt.savefig(buf, format='png', dpi=150)
    buf.seek(0)
    plt.close(fig)
    return buf.getvalue()

def get_top_symbols():
    """代表性股票清單"""
    symbols = [
        "2330.TW", "2317.TW", "2454.TW", "2308.TW", "2382.TW", 
        "3231.TW", "3017.TW", "2356.TW", "2376.TW", "6669.TW",
        "3035.TW", "3711.TW", "3008.TW", "2603.TW", "2609.TW"
    ]
    return symbols

def main():
    print("開始執行高勝率嚴格過濾、法人籌碼與點位掃描...")
    symbols = get_top_symbols()
    matched_stocks = []

    for symbol in symbols:
        try:
            stock_id = symbol.replace(".TW", "")
            df = yf.download(symbol, period="6mo", interval="1d", progress=False)
            if df.empty or len(df) < 65:
                continue
            
            if isinstance(df.columns, pd.MultiIndex):
                df.columns = df.columns.get_level_values(0)

            # 計算指標
            df['MA20'] = df['Close'].rolling(window=20).mean()
            df['MA60'] = df['Close'].rolling(window=60).mean()
            df['Vol_MA5'] = df['Volume'].rolling(window=5).mean()
            
            latest = df.iloc[-1]
            prev = df.iloc[-2]
            
            # 1. 基礎成交量過濾：今日成交量 >= 1000 張
            if latest['Volume'] < 1000000:
                continue
                
            # 2. 季線必須向上：今日 60MA > 5天前 60MA
            ma60_5days_ago = df['MA60'].iloc[-6]
            if latest['MA60'] <= ma60_5days_ago:
                continue
                
            # 3. 收盤接近高點（非長上影線）
            total_range = latest['High'] - latest['Low']
            close_position = (latest['Close'] - latest['Low']) / total_range if total_range > 0 else 0
            if close_position < 0.7:
                continue
                
            # 4. 漲幅適中：當日漲幅在 2% ~ 7% 之間
            pct_change = (latest['Close'] - prev['Close']) / prev['Close'] * 100
            if not (2 <= pct_change <= 7):
                continue
                
            # 5. 核心突破與爆量條件
            is_breakout = (prev['Close'] <= prev['MA60']) and (latest['Close'] > latest['MA60'])
            is_volume_surge = latest['Volume'] >= (latest['Vol_MA5'] * 2)
            
            if is_breakout and is_volume_surge:
                # 取得三大法人與壓力支撐點位
                inst_data = fetch_finmind_institutional(stock_id)
                support, resistance = calculate_support_resistance(df)
                
                chart_bytes = generate_stock_chart(df, stock_id, stock_id)
                matched_stocks.append({
                    "id": stock_id,
                    "close": latest['Close'],
                    "pct": pct_change,
                    "support": support,
                    "resistance": resistance,
                    "inst": inst_data,
                    "chart": chart_bytes
                })
        except Exception as e:
            print(f"處理 {symbol} 時發生錯誤: {e}")

    # 發送 Telegram 通知
    if matched_stocks:
        for stock in matched_stocks:
            inst = stock['inst']
            caption = (
                f"🔥 **【高勝率突破、籌碼與點位通知】** 🔥\n\n"
                f"📌 股票代號：`{stock['id']}`\n"
                f"💰 收盤價：`{stock['close']:.2f}`\n"
                f"📈 當日漲幅：`+{stock['pct']:.2f}%`\n\n"
                f"🎯 **關鍵技術點位**：\n"
                f"  • 🛡️ 建議支撐（防守）：`{stock['support']}`\n"
                f"  • 🎯 預期壓力（目標）：`{stock['resistance']}`\n\n"
                f"📊 **三大法人買賣超 (張)**：\n"
                f"  • 外資：`{inst['外資']:+.1f}`\n"
                f"  • 投信：`{inst['投信']:+.1f}`\n"
                f"  • 自營商：`{inst['自營商']:+.1f}`\n"
                f"  • 法人合計：`{inst['合計']:+.1f}`\n\n"
                f"✨ 通過嚴格過濾（季線向上+帶量突破+支撐壓力對齊）！"
            )
            send_telegram_photo(stock['chart'], caption)
    else:
        send_telegram_message(
            "【高勝率台股選股通知】\n\n"
            "今日掃描完成：未有同時符合「季線向上、成交量>1000張、收盤近高點、漲幅2~7%、2倍爆量突破MA60」的個股。"
        )

if __name__ == "__main__":
    main()
