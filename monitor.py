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
        # 【核心修復】強制將數據轉為 1D 陣列，解決格式兼容問題
        close = df['Close'].squeeze()
        volume = df['Volume'].squeeze()
        
        # 1. RSI 計算 (加入除以零保護)
        delta = close.diff()
        gain = delta.clip(lower=0).rolling(window=14).mean()
        loss = -delta.clip(upper=0).rolling(window=14).mean()
        
        # 防止 loss 為 0 導致無限大錯誤
        loss = loss.replace(0, 0.0001)
        rs = gain / loss
        rsi = float(100 - (100 / (1 + rs)).iloc[-1])
        
        # 2. 均線計算
        ma5 = float(close.rolling(window=5).mean().iloc[-1])
        ma20 = float(close.rolling(window=20).mean().iloc[-1])
        
        # 3. 成交量計算 (加入除以零保護)
        vol_ma5 = float(volume.rolling(window=5).mean().iloc[-1])
        last_vol = float(volume.iloc[-1])
        
        if vol_ma5 <= 0:
            vol_ratio = 1.0
        else:
            vol_ratio = float(last_vol / vol_ma5)
            
        price = float(close.iloc[-1])
        
        # --- 高精度評分邏輯 ---
        score = 0
        if price > ma5 and ma5 > ma20: score += 40
        if price < ma5 and ma5 < ma20: score -= 40
        if 40 < rsi < 65: score += 20
        if rsi > 75: score -= 30
        if vol_ratio > 1.4 and price > ma5: score += 20
        
        if score >= 50: res = "🚀 強力買入"
        elif score >= 15: res = "⬆️ 趨勢向好"
        elif score <= -30: res = "🚨 轉向跌勢"
        else: res = "⚖️ 區間盤整"
        
        return res, rsi, vol_ratio
        
    except Exception as e:
        # 💡 如果再錯，會直接顯示錯誤原因，唔會再收收埋埋
        return f"⚠️ 運算錯誤 ({str(e)[:10]})", 50.0, 1.0

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
            
            price = float(df['Close'].squeeze().iloc[-1])
            prediction, rsi, v_ratio = ai_prediction_logic(df)
            
            report += f"\n*{name} ({symbol})*\n價: `${price:.2f}` | RSI: {rsi:.1f} | 量: {v_ratio:.1f}x\n訊號: {prediction}\n"
            count += 1
            
            # 每 5 隻發送一次
            if count % 5 == 0:
                send_tg(report)
                report = ""
        except Exception as e:
            continue
            
    if report:
        send_tg(report)

if __name__ == "__main__":
    monitor()
