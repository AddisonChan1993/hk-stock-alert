import yfinance as yf
import pandas as pd
import requests
import os

# 💡 必須改為咁樣，唔好直接寫粒 Token 入去
TOKEN = os.getenv('TELEGRAM_TOKEN')
CHAT_ID = os.getenv('TELEGRAM_CHAT_ID')

# 設定持股對照表：代碼與中文名稱
STOCK_MAP = {
    '1810.HK': '小米集團',
    '0005.HK': '匯豐控股',
    '1299.HK': '友邦保險',
    '3750.HK': '寧德時代',
    '9611.HK': '龍旗科技',
    '2561.HK': '維昇藥業',
    '2050.HK': '三花智控',
    '1088.HK': '中國神華',
    '0823.HK': '領展房產',
    '0293.HK': '國泰航空',
    '0883.HK': '中國海油',
    '3690.HK': '美團-W',
    '9988.HK': '阿里巴巴',
    '0700.HK': '騰訊控股'
}

def send_tg(msg):
    url = f"https://api.telegram.org/bot{TOKEN}/sendMessage?chat_id={CHAT_ID}&text={msg}&parse_mode=Markdown"
    requests.get(url)

def ai_prediction_logic(df):
    """最初 AI 邏輯的技術指標權重評分系統"""
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
    
    # AI 評分系統邏輯
    score = 0
    if last_rsi < 35: score += 35      # 底部超賣
    if last_macd > 0: score += 25      # 趨勢向上
    if last_rsi > 68: score -= 30      # 超買風險
    
    if score > 20: return "🚀 大升機率高", last_rsi
    elif score < -10: return "📉 走勢轉弱", last_rsi
    else: return "⚖️ 區間盤整", last_rsi

def monitor():
    report = "📊 *最初 AI 邏輯 - 雲端持倉報告*\n"
    for symbol, name in STOCK_MAP.items():
        try:
            # 抓取數據
            df = yf.download(symbol, period='2mo', interval='1d', progress=False)
            if df.empty: continue
            
            price = float(df['Close'].iloc[-1])
            prediction, rsi = ai_prediction_logic(df)
            
            # 針對 1810 小米獲利保護邏輯
            if symbol == '1810.HK' and rsi > 70:
                prediction = "⚠️ 獲利回吐風險 (RSI超買)"
            
            # 組合報告內容
            report += f"\n*{name} ({symbol})*\n現價: `${price:.2f}`\nAI 預測: {prediction}\nRSI: {rsi:.1f}\n"
        except Exception as e:
            print(f"Error analyzing {symbol}: {e}")
            
    send_tg(report)

if __name__ == "__main__":
    monitor()
