import yfinance as yf
import pandas as pd
import requests
import os
import pandas_ta as ta

# 填入你提供的資訊
TOKEN = "8713539312:AAGTPQ-MhzvRRfL-XpaZPxs8Hyo9MlWfWcw"
CHAT_ID = "6248100698"

# 你持有的 7 隻股票
STOCKS = ['1810.HK', '3750.HK', '9611.HK', '2561.HK', '2050.HK', '0005.HK', '1299.HK']

def send_tg(msg):
    url = f"https://api.telegram.org/bot{TOKEN}/sendMessage?chat_id={CHAT_ID}&text={msg}&parse_mode=Markdown"
    requests.get(url)

def analyze_stock(symbol):
    df = yf.download(symbol, period='1mo', interval='1d')
    if df.empty: return
    
    # 計算技術指標
    df.ta.rsi(length=14, append=True)
    df.ta.macd(append=True)
    
    last_row = df.iloc[-1]
    rsi = last_row['RSI_14']
    macd = last_row['MACD_12_26_9']
    price = last_row['Close']
    
    # 簡易 AI 邏輯評分 (模擬 XGBoost 決策)
    score = 0
    if rsi < 30: score += 30  # 超賣反彈機率高
    if macd > 0: score += 20  # 趨勢向上
    if rsi > 70: score -= 20  # 超買風險
    
    # 判斷訊號
    signal = "⚖️ 盤整"
    if score > 20: signal = "🚀 大升機率高"
    elif score < -10: signal = "⚠️ 大跌風險"
    
    return f"*{symbol}* 現價: ${price:.2f}\n訊號: {signal}\nRSI: {rsi:.1f}"

# 執行監控
report = "📊 *AI 每日持倉掃描報告*\n\n"
for s in STOCKS:
    res = analyze_stock(s)
    if res: report += res + "\n\n"

send_tg(report)
