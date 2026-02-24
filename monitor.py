import yfinance as yf
import pandas as pd
import requests
import os

# 從 Secrets 讀取
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
    # 1. RSI 計算
    delta = df['Close'].diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
    rsi = 100 - (100 / (1 + (gain / loss))).iloc[-1]
    
    # 2. 均線過濾 (5日 vs 20日)
    ma5 = df['Close'].rolling(window=5).mean().iloc[-1]
    ma20 = df['Close'].rolling(window=20).mean().iloc[-1]
    
    # 3. 成交量分析 (判斷是否帶量)
    vol_ma5 = df['Volume'].rolling(window=5).mean().iloc[-1]
    last_vol = df['Volume'].iloc[-1]
    vol_ratio = float(last_vol / vol_ma5)
    
    price = float(df['Close'].iloc[-1])
    
    # --- 高精度評分邏輯 ---
    score = 0
    if price > ma5 > ma20: score += 40  # 趨勢向上
    if price < ma5 < ma20: score -= 40  # 趨勢向下
    
    if 40 < rsi < 65: score += 20       # 動能健康
    if rsi > 75: score -= 30            # 嚴重超買警告
    
    if vol_ratio > 1.4 and price > ma5: score += 20 # 帶量突破
    
    # 根據分數給出結論
    if score >= 50: 
        return f"🚀 強力買入 (帶量突破)", rsi, vol_ratio
    elif score >= 15: 
        return f"⬆️ 趨勢向好", rsi, vol_ratio
    elif score <= -30: 
        return f"🚨 轉向跌勢", rsi, vol_ratio
    else: 
        return f"⚖️ 區間盤整", rsi, vol_ratio

def monitor():
    report = "🎯 *AI 高精度實戰診斷*\n"
    for symbol, name in STOCK_MAP.items():
        try:
            df = yf.download(symbol, period='3mo', interval='1d', progress=False)
            if df.empty: continue
            
            price = float(df['Close'].iloc[-1])
            prediction, rsi, v_ratio = ai_prediction_logic(df)
            
            # 格式化輸出
            report += f"\n*{name} ({symbol})*\n現價: `${price:.2f}` | RSI: {rsi:.1f}\n成交量: {v_ratio:.1f}x\n訊號: {prediction}\n"
        except:
            continue
            
    url = f"https://api.telegram.org/bot{TOKEN}/sendMessage?chat_id={CHAT_ID}&text={report}&parse_mode=Markdown"
    requests.get(url)

if __name__ == "__main__":
    monitor()
