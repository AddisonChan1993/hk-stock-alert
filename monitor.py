import yfinance as yf
import pandas as pd
import requests
import os

# 💡 改為從環境變數讀取，對應返 Secrets
TOKEN = os.getenv('TELEGRAM_TOKEN')
CHAT_ID = os.getenv('TELEGRAM_CHAT_ID')

STOCKS = ['1810.HK', '3750.HK', '9611.HK', '2561.HK', '2050.HK', '0005.HK', '1299.HK']

def send_tg(msg):
    url = f"https://api.telegram.org/bot{TOKEN}/sendMessage?chat_id={CHAT_ID}&text={msg}&parse_mode=Markdown"
    requests.get(url)

def analyze_stock(symbol):
    df = yf.download(symbol, period='2mo', interval='1d')
    if df.empty or len(df) < 20: return
    
    # 手動計算 RSI (14)
    delta = df['Close'].diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
    rs = gain / loss
    df['RSI'] = 100 - (100 / (1 + rs))
    
    # 手動計算 MACD
    exp1 = df['Close'].ewm(span=12, adjust=False).mean()
    exp2 = df['Close'].ewm(span=26, adjust=False).mean()
    df['MACD'] = exp1 - exp2
    
    last_row = df.iloc[-1]
    rsi = float(last_row['RSI'])
    macd = float(last_row['MACD'])
    price = float(last_row['Close'])
    
    # 針對你持倉的 AI 診斷邏輯
    score = 0
    if rsi < 35: score += 30  # 超賣反彈
    if macd > 0: score += 20  # 趨勢轉強
    if rsi > 65: score -= 25  # 小心超買回調
    
    signal = "⚖️ 盤整中"
    if score > 20: signal = "🚀 大升機率高"
    elif score < -10: signal = "⚠️ 注意大跌風險"
    
    return f"*{symbol}*\n現價: `${price:.2f}`\n訊號: {signal}\nRSI: {rsi:.1f}"

# 執行並發送報告
report = "📊 *AI 每日持倉掃描報告*\n"
for s in STOCKS:
    res = analyze_stock(s)
    if res: report += "\n" + res + "\n"

send_tg(report)
