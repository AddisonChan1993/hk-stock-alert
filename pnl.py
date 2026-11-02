import os
import time
import requests
from datetime import datetime
import yfinance as yf

# ==========================================
# 1. 用戶持倉設定
# ==========================================
PORTFOLIO = {
    '3070.HK': {'name': '平安香港高息', 'shares': 2300, 'avg_price': 41.494},
    '3466.HK': {'name': '恒生高息股',   'shares': 5200, 'avg_price': 20.689},
    '0005.HK': {'name': '滙豐控股',     'shares': 400,  'avg_price': 124.300},
    '3750.HK': {'name': '寧德時代',     'shares': 200,  'avg_price': 593.500},
    '0939.HK': {'name': '建設銀行',     'shares': 5000, 'avg_price': 8.920},
    '6823.HK': {'name': '香港電訊',     'shares': 3000, 'avg_price': 12.630},
    '1810.HK': {'name': '小米集團-W',   'shares': 3600, 'avg_price': 25.180},
}

# 設定 Session 偽裝瀏覽器，降低被 Yahoo Finance 封鎖的機率 (GitHub Actions 常見問題)
session = requests.Session()
session.headers.update({
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
})

# ==========================================
# 2. 獲取數據函數 (加入重試機制)
# ==========================================
def get_stock_data(symbol, retries=3):
    for attempt in range(retries):
        try:
            print(f"🔍 正在查詢: {symbol} (嘗試 {attempt + 1}/{retries})...")
            ticker = yf.Ticker(symbol, session=session)
            hist = ticker.history(period="5d")
            
            if len(hist) >= 2:
                current_price = float(hist['Close'].iloc[-1])
                prev_close = float(hist['Close'].iloc[-2])
                return current_price, prev_close
            elif len(hist) == 1:
                current_price = float(hist['Close'].iloc[-1])
                return current_price, current_price
            else:
                print(f"❌ {symbol} 數據不足")
                
        except Exception as e:
            print(f"⚠️ {symbol} 讀取錯誤: {e}")
            
        time.sleep(2)  # 失敗後等待 2 秒再試
        
    return None, None

# ==========================================
# 3. 發送 Telegram 訊息函數
# ==========================================
def send_telegram_message(message):
    token = os.environ.get("TELEGRAM_TOKEN")
    chat_id = os.environ.get("TELEGRAM_CHAT_ID")

    if not token or not chat_id:
        print("❌ 錯誤: 找不到 TELEGRAM_TOKEN 或 TELEGRAM_CHAT_ID")
        return

    url = f"https://api.telegram.org/bot{token}/sendMessage"
    payload = {
        "chat_id": chat_id,
        "text": message,
        "parse_mode": "HTML"
    }
    
    try:
        response = requests.post(url, json=payload)
        if response.status_code == 200:
            print("✅ Telegram 訊息發送成功")
        else:
            print(f"❌ 發送失敗: {response.text}")
    except Exception as e:
        print(f"❌ 連線錯誤: {e}")

# ==========================================
# 4. 主程式邏輯
# ==========================================
def main():
    # 週末防呆：如果是星期六 (5) 或星期日 (6)，直接停止執行
    if datetime.today().weekday() >= 5:
        print("⏸️ 今日是週末，股市休市，停止結算。")
        return

    print("🚀 開始執行盈虧結算...")
    
    report_lines = []
    report_lines.append("📊 <b>每日收市詳細結算 (16:20)</b>")
    report_lines.append("------------------------")

    total_daily_pnl = 0
    total_hold_pnl = 0
    total_cost = 0
    
    for symbol, data in PORTFOLIO.items():
        name = data['name']
        shares = data['shares']
        avg_price = data['avg_price']
        
        price, prev_close = get_stock_data(symbol)
        
        if price is not None:
            # 1. 計算今日盈虧 (加入防禦除以零)
            daily_change = price - prev_close
            daily_pnl = daily_change * shares
            daily_pct = (daily_change / prev_close) * 100 if prev_close > 0 else 0
            
            # 2. 計算總持倉盈虧
            total_pnl = (price - avg_price) * shares
            total_pct = ((price - avg_price) / avg_price) * 100 if avg_price > 0 else 0
            
            # 3. 累積總額
            total_daily_pnl += daily_pnl
            total_hold_pnl += total_pnl
            total_cost += (avg_price * shares)
            
            # 4. 圖標
            d_icon = "🔺" if daily_pnl >= 0 else "🔻"
            t_icon = "🟢" if total_pnl >= 0 else "🔴"
            
            # 5.
