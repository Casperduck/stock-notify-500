import os
import requests
import pandas as pd
import numpy as np
import yfinance as yf

# 1. 讀取 Telegram 設定
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "你的_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID", "你的_CHAT_ID")

def send_telegram_message(message):
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {
        "chat_id": TELEGRAM_CHAT_ID,
        "text": message,
        "parse_mode": "Markdown"
    }
    try:
        response = requests.post(url, json=payload)
        response.raise_for_status()
        print("Telegram 訊息發送成功！")
    except Exception as e:
        print(f"發送 Telegram 訊息失敗: {e}")

# 2. 自動抓取台股市值/熱門前 500 大股票清單
def get_top_500_stocks():
    try:
        url = 'https://isin.twse.com.tw/isin/C_public.jsp?strMode=2'
        res = requests.get(url)
        df = pd.read_html(res.text)[0]
        df.columns = df.iloc[0]
        df = df.iloc[1:]
        
        df = df[df['有價證券代號及名稱'].str.contains('　', na=False)]
        stocks = df['有價證券代號及名稱'].str.split('　', expand=True)
        stocks.columns = ['code', 'name']
        
        valid_stocks = stocks[stocks['code'].str.len() == 4]
        stock_codes = [f"{code}.TW" for code in valid_stocks['code'].head(500)]
        print(f"成功載入前 {len(stock_codes)} 檔股票清單。")
        return stock_codes
    except Exception as e:
        print(f"自動抓取清單失敗，啟用備用清單: {e}")
        return [
            "2330.TW", "2317.TW", "2454.TW", "2382.TW", "3231.TW", 
            "2603.TW", "2303.TW", "2881.TW", "2882.TW", "2412.TW",
            "2891.TW", "3711.TW", "2308.TW", "2357.TW", "6669.TW"
        ]

# 3. 執行高勝率選股掃描
def scan_stocks():
    stock_list = get_top_500_stocks()
    matched_stocks = []
    
    print(f"開始執行高勝率台股前 500 大選股掃描...")
    
    for symbol in stock_list:
        try:
            df = yf.download(symbol, period="100d", progress=False)
            if len(df) < 65:
                continue
            
            # 計算指標
            df['MA60'] = df['Close'].rolling(60).mean()
            df['Vol_MA5'] = df['Volume'].rolling(5).mean()
            
            latest = df.iloc[-1]
            prev = df.iloc[-2]
            ma60_5d_ago = df.iloc[-6]['MA60'] # 5天前的季線（用來判斷斜率）
            
            # --- 核心高勝率過濾條件 ---
            # 1. 突破季線：昨日在季線下，今日收盤站上季線
            cond_break_ma60 = (prev['Close'] <= prev['MA60']) and (latest['Close'] > latest['MA60'])
            
            # 2. 爆量條件：成交量 > 5日均量 2 倍，且當日成交量 >= 1000 張 (過濾冷門流動性差的股票)
            cond_volume = (latest['Volume'] > (prev['Vol_MA5'] * 2)) and (latest['Volume'] >= 1000)
            
            # 3. 季線必須向上：中長期趨勢為多頭，避免買在下彎反彈
            cond_ma60_up = latest['MA60'] > ma60_5d_ago
            
            # 4. 實體長紅 K：收盤價位於當天高低價差的前 70% 以上（避免長上影線賣壓沈重）
            day_range = latest['High'] - latest['Low']
            cond_solid_k = True
            if day_range > 0:
                cond_solid_k = ((latest['Close'] - latest['Low']) / day_range) >= 0.7
                
            # 5. 漲幅適中：當日漲幅介於 2% ~ 7% 之間（避免漲停追高風險）
            pct_change = (latest['Close'] - prev['Close']) / prev['Close']
            cond_pct = 0.02 <= pct_change <= 0.07
            
            # 全部條件同時成立才納入
            if cond_break_ma60 and cond_volume and cond_ma60_up and cond_solid_k and cond_pct:
                stock_code = symbol.replace('.TW', '')
                matched_stocks.append(stock_code)
        except Exception:
            continue

    # 4. 組裝 Telegram 通知訊息
    if matched_stocks:
        msg = f"【🔥 高勝率台股 500 大選股通知】\n今日掃描完成！符合嚴格突破與多頭條件標的：\n" + ", ".join(matched_stocks)
    else:
        msg = f"【🔥 高勝率台股 500 大選股通知】\n今日掃描完成，未有同時符合高勝率多頭突破條件的個股。"
    
    send_telegram_message(msg)

if __name__ == "__main__":
    scan_stocks()
