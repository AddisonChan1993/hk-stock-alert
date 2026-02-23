import yfinance as yf
import requests
import os

# 💡 從 GitHub Secrets 讀取
TOKEN = os.getenv('TELEGRAM_TOKEN')
CHAT_ID = os.getenv('TELEGRAM_CHAT_ID')

# 你持有的 7 隻股票
STOCKS = ['1810.HK', '3750.HK', '9611.HK', '2561.HK', '2050.HK', '0005.HK', '1299.HK']

def send_tg(msg):
    if not TOKEN or not CHAT_ID:
        print("Error: TOKEN or CHAT_ID is missing!")
        return
    url = f"https://api.telegram.org/bot{TOKEN}/sendMessage?chat_id={CHAT_ID}&text={msg}&parse_mode=Markdown"
    requests.get(url)

def analyze(symbol):
    try:
        df = yf.download(symbol, period='1mo', interval='1d', progress=False)
        if df.empty: return None
        
        price = float(df['Close'].iloc[-1])
        # 簡單動能分析 (5日升跌)
        change_5d = ((price - float(df['Close'].iloc[-5])) / float(df['Close'].iloc[-5])) * 100
        
        signal = "⚖️ 盤整"
        if change_5d > 2: signal = "🚀 強勢上漲"
        elif change_5d < -2: signal = "⚠️ 走勢轉弱"
        
        return f"*{symbol}*\n現價: `${price:.2f}`\n5日變動: {change_5d:.1f}%\n預測: {signal}"
    except:
        return None

report = "📊 *AI 持倉監控報告*\n"
for s in STOCKS:
    res = analyze(s)
    if res: report += "\n" + res + "\n"

send_tg(report)
