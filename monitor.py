import yfinance as yf
import requests
import os

# 從 GitHub Secrets 攞 Token
TOKEN = os.getenv('TELEGRAM_TOKEN')
CHAT_ID = os.getenv('TELEGRAM_CHAT_ID')
STOCKS = ['1810.HK', '3750.HK', '9611.HK', '2561.HK', '2050.HK', '0005.HK', '1299.HK']

def send_tg(msg):
    url = f"https://api.telegram.org/bot{TOKEN}/sendMessage?chat_id={CHAT_ID}&text={msg}"
    requests.get(url)

for symbol in STOCKS:
    stock = yf.Ticker(symbol)
    hist = stock.history(period="2d")
    if len(hist) < 2: continue
    
    last_price = hist['Close'].iloc[-1]
    prev_price = hist['Close'].iloc[-2]
    change = (last_price - prev_price) / prev_price * 100
    
    # 設置免費版觸發條件：例如升跌超過 3% 就報警
    if abs(change) >= 3.0:
        emoji = "🚀" if change > 0 else "📉"
        send_tg(f"{emoji} {symbol} 異動！\n現價: ${last_price:.2f}\n幅度: {change:.2f}%")
