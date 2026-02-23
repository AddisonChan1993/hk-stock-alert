import yfinance as yf
import pandas as pd
import requests
import os

# 💡 從環境變數讀取安全資訊
TOKEN = os.getenv('TELEGRAM_TOKEN')
CHAT_ID = os.getenv('TELEGRAM_CHAT_ID')

# 你持有的 7 隻股票
STOCKS = ['1810.HK', '3750.HK', '9611.HK', '2561.HK', '2050.HK', '0005.HK', '1299.HK']

def send_tg(msg):
    url = f"https://api.telegram.org/bot{TOKEN}/sendMessage?chat_id={CHAT_ID}&text={msg}&parse_mode=Markdown"
    requests.get(url)

def ai_prediction_logic(df):
    """呢度係你最初代碼嘅 AI 預測邏輯簡化版"""
    # 計算 RSI
    delta = df['Close'].diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
    rs = gain / loss
    rsi = 100 - (100 / (1 + rs))
    
    # 計算 MACD
    exp1 = df['Close'].ewm(span=12, adjust=False).mean()
    exp2 = df['Close'].ewm(span=26, adjust=False).mean()
    macd = exp1 - exp2
    
    last_rsi = float(rsi.iloc[-1])
    last_macd = float(macd.iloc[-1])
    
    # 最初 AI 代碼嘅評分系統
    score = 0
    if last_rsi < 35: score += 35      # 底部反彈訊號
    if last_macd > 0: score += 25      # 趨勢向上
    if last_rsi > 68: score -= 30      # 超買風險
    
    if score > 20: return "🚀 大升機率高", last_rsi
    elif score < -10: return "📉 走勢轉弱", last_rsi
    else: return "⚖️ 區間盤整", last_rsi

def monitor():
    report = "📊 *最初 AI 邏輯 - 雲端掃描報告*\n"
    for symbol in STOCKS:
        try:
            df = yf.download(symbol, period='2mo', interval='1d', progress=False)
            if df.empty: continue
            
            price = float(df['Close'].iloc[-1])
            prediction, rsi = ai_prediction_logic(df)
            
            # 針對 1810 嘅獲利保護邏輯
            if symbol == '1810.HK' and rsi > 70:
                prediction = "⚠️ 獲利回吐風險 (RSI超買)"
            
            report += f"\n*{symbol}*\n現價: `${price:.2f}`\nAI 預測: {prediction}\nRSI: {rsi:.1f}\n"
        except Exception as e:
            print(f"Error analyzing {symbol}: {e}")
            
    send_tg(report)

if __name__ == "__main__":
    monitor()
