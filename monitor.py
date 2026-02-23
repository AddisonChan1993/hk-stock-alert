import yfinance as yf
import pandas as pd
import requests
import os

# 從環境變數讀取安全資訊
TOKEN = os.getenv('TELEGRAM_TOKEN')
CHAT_ID = os.getenv('TELEGRAM_CHAT_ID')

# 你持有的 7 隻股票
STOCKS = ['1810.HK', '3750.HK', '9611.HK', '2561.HK', '2050.HK', '0005.HK', '1299.HK']

def send_tg(msg):
    url = f"https://api.telegram.org/bot{TOKEN}/sendMessage?chat_id={CHAT_ID}&text={msg}&parse_mode=Markdown"
    requests.get(url)

def analyze_stock(symbol):
    try:
        # 抓取 2 個月數據以確保指標準確
        df = yf.download(symbol, period='2mo', interval='1d', progress=False)
        if df.empty or len(df) < 20: return None
        
        # --- 手動計指標 (避開版本衝突) ---
        # 1. RSI (14)
        delta = df['Close'].diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
        rs = gain / loss
        df['RSI'] = 100 - (100 / (1 + rs))
        
        # 2. MACD (12, 26, 9)
        exp1 = df['Close'].ewm(span=12, adjust=False).mean()
        exp2 = df['Close'].ewm(span=26, adjust=False).mean()
        df['MACD'] = exp1 - exp2
        
        last_row = df.iloc[-1]
        price = float(last_row['Close'])
        rsi = float(last_row['RSI'])
        macd = float(last_row['MACD'])
        
        # --- 最初代碼嘅 AI 評分邏輯 ---
        score = 0
        if rsi < 35: score += 35      # 底部反彈訊號
        if macd > 0: score += 25      # 趨勢向上
        if rsi > 68: score -= 30      # 超買風險
        
        # 針對 1810 小米嘅特別加權
        if symbol == '1810.HK' and rsi > 70:
            status = "⚠️ 獲利回吐風險極高"
        elif score > 20:
            status = "🚀 大升機率高 (動能強)"
        elif score < -10:
            status = "📉 走勢轉弱 (建議避險)"
        else:
            status = "⚖️ 區間盤整"
            
        return f"*{symbol}*\n現價: `${price:.2f}`\n訊號: {status}\nRSI: {rsi:.1f} | MACD:
