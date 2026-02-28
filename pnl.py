import yfinance as yf
import pandas as pd
import requests
import os

TOKEN = os.getenv('TELEGRAM_TOKEN')
CHAT_ID = os.getenv('TELEGRAM_CHAT_ID')

# 📊 你的專屬持倉名單 (記得改 shares 股數！)
PORTFOLIO = {
    '0005.HK': {'shares': 400, 'avg_price': 124.300},  # 匯豐控股
    '1088.HK': {'shares': 500, 'avg_price': 43.900},   # 中國神華
    '1299.HK': {'shares': 200, 'avg_price': 85.450},   # 友邦保險
    '3070.HK': {'shares': 1100, 'avg_price': 40.078},  # 平安香港高息
    '3081.HK': {'shares': 1100, 'avg_price': 23.625},  # 價值黃金ETF
    '3466.HK': {'shares': 2800, 'avg_price': 20.163}   # 恒生高息股
}

def send_tg(msg):
    if not msg.strip(): return
    url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
    payload = {'chat_id': CHAT_ID, 'text': msg, 'parse_mode': 'Markdown'}
    requests.post(url, data=payload)

def calculate_pnl():
    report = "📊 *每日收市盈虧結算 (16:20)*\n"
    report += "------------------------\n"
    
    total_daily_pnl = 0
    total_overall_pnl = 0
    
    for symbol, data in PORTFOLIO.items():
        try:
            hist = yf.Ticker(symbol).history(period="5d")
            if len(hist) < 2: continue
            
            today_close = float(hist['Close'].iloc[-1])
            ytd_close = float(hist['Close'].iloc[-2])
            
            name = data['name']
            buy_price = data['buy_price']
            shares = data['shares']
            
            # 計算
            daily_pnl = (today_close - ytd_close) * shares
            overall_pnl = (today_close - buy_price) * shares
            
            total_daily_pnl += daily_pnl
            total_overall_pnl += overall_pnl
            
            d_icon = "🟢" if daily_pnl >= 0 else "🔴"
            o_icon = "🟢" if overall_pnl >= 0 else "🔴"
            
            report += f"*{name} ({symbol})*\n"
            report += f"現價: `${today_close:.3f}` (成本: `${buy_price:.3f}`)\n"
            report += f"今日: {d_icon} `${daily_pnl:,.1f}`\n"
            report += f"累積: {o_icon} `${overall_pnl:,.1f}`\n\n"
            
        except Exception as e:
            report += f"*{data['name']} ({symbol})* ⚠️ 數據讀取失敗\n\n"

    report += "========================\n"
    report += "💰 *大市總結算*\n"
    td_icon = "🟢 賺" if total_daily_pnl >= 0 else "🔴 蝕"
    to_icon = "🟢 賺" if total_overall_pnl >= 0 else "🔴 蝕"
    report += f"今日總盈虧: {td_icon} `${total_daily_pnl:,.1f}`\n"
    report += f"累積總盈虧: {to_icon} `${total_overall_pnl:,.1f}`\n"
    
    send_tg(report)

if __name__ == "__main__":
    calculate_pnl()
