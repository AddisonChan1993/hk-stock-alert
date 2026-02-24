import yfinance as yf
import pandas as pd
import requests
import os

TOKEN = os.getenv('TELEGRAM_TOKEN')
CHAT_ID = os.getenv('TELEGRAM_CHAT_ID')

STOCK_MAP = {
    '1810.HK': '小米集團-W',
    '0005.HK': '匯豐控股',
    '1299.HK': '友邦保險',
    '3750.HK': '寧德時代', 
    '9611.HK': '龍旗科技',
    '2561.HK': '維昇藥業',
    '2050.HK': '三花智控',
    '1088.HK': '中國神華',
    '0823.HK': '領展房產基金',
    '0293.HK': '國泰航空',
    '0883.HK': '中國海油',
    '3690.HK': '美團-W',
    '9988.HK': '阿里巴巴-W'
}

def ai_prediction_logic(df):
    try:
        delta = df['Close'].diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
        rs = gain / loss
        rsi = 100 - (100 / (1 + rs)).iloc[-1]
        
        ma5 = df['Close'].rolling(window=5).mean().iloc[-1]
        ma20 = df['Close'].rolling(window=20).mean().iloc[-1]
        vol_ma5 = df['Volume'].rolling(window=5).mean().iloc[-1]
        last_vol = df['Volume'].iloc[-1]
        vol_ratio = float(last_vol / vol_ma5)
        price = float(df['Close'].iloc[-1])
        
        score = 0
        if price > ma5 > ma20: score += 40
        if price < ma5 < ma20: score -= 40
        if 40 < rsi < 65: score += 20
        if rsi > 75: score -= 30
        if vol_ratio > 1.4 and price > ma5: score += 20
        
        if score >= 50: res = "🚀 強力買入"
        elif score >= 15: res = "⬆️ 趨勢向好"
        elif score <= -30: res = "🚨 轉向跌勢"
        else: res = "⚖️ 區間盤整"
        return res, float(rsi), vol_ratio
    except:
        return "⚠️ 數據不足", 50.0, 1.0

def send_tg(msg):
    if not msg.strip(): return
    url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
    payload = {'chat_id': CHAT_ID, 'text': msg, 'parse_mode': 'Markdown'}
    requests.post(url, data=payload)

def monitor():
    send_tg("🎯 *AI 高精度實戰診斷啟動*")
    report = ""
    count = 0
    
    for symbol, name in STOCK_MAP.items():
        try:
            df = yf.download(symbol, period='3mo', interval='1d', progress=False)
            if df.empty: continue
            
            price = float(df['Close'].iloc[-1])
            prediction, rsi, v_ratio = ai_prediction_logic(df)
            
            report += f"\n*{name} ({symbol})*\n價: `${price:.2f}` | RSI: {rsi:.1f} | 量: {v_ratio:.1f}x\n訊號: {prediction}\n"
            count += 1
            
            # 每 5 隻股票發送一次，避免訊息太長
            if count % 5 == 0:
                send_tg(report)
                report = ""
        except Exception as e:
            continue
    
    # 發送餘下的股票
    if report:
        send_tg(report)

if __name__ == "__main__":
    monitor()
