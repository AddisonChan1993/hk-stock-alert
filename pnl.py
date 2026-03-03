import os
import time
import requests
import yfinance as yf

# ==========================================
# 1. 用戶持倉設定 (已更新最新數據)
# ==========================================
PORTFOLIO = {
    '0005.HK': {'name': '匯豐控股', 'shares': 400, 'avg_price': 124.300},
    '1088.HK': {'name': '中國神華', 'shares': 500, 'avg_price': 43.900},
    '1299.HK': {'name': '友邦保險', 'shares': 200, 'avg_price': 85.450},
    '3070.HK': {'name': '平安香港高息', 'shares': 1100, 'avg_price': 40.078},
    '3081.HK': {'name': '價值黃金ETF', 'shares': 1100, 'avg_price': 23.625},
    '3466.HK': {'name': '恒生高息股', 'shares': 2800, 'avg_price': 20.163}
}

# ==========================================
# 2. 獲取股價函數 (加入防封鎖邏輯)
# ==========================================
def get_current_price(symbol):
    """
    獲取股票現價，失敗時返回 None
    """
    try:
        print(f"🔍 正在查詢: {symbol} ...")
        ticker = yf.Ticker(symbol)
        
        # 嘗試獲取當日數據
        # history(period="1d") 比 .info 更穩定且不易被封鎖
        data = ticker.history(period="1d")
        
        if not data.empty:
            price = data['Close'].iloc[-1]
            return float(price)
        else:
            print(f"❌ {symbol} 數據為空")
            return None
            
    except Exception as e:
        print(f"⚠️ {symbol} 讀取錯誤: {e}")
        return None

# ==========================================
# 3. 發送 Telegram 訊息函數
# ==========================================
def send_telegram_message(message):
    token = os.environ.get("TELEGRAM_TOKEN")
    chat_id = os.environ.get("TELEGRAM_CHAT_ID")

    if not token or not chat_id:
        print("❌ 錯誤: 找不到 TELEGRAM_TOKEN 或 TELEGRAM_CHAT_ID 環境變數")
        return

    url = f"https://api.telegram.org/bot{token}/sendMessage"
    payload = {
        "chat_id": chat_id,
        "text": message,
        "parse_mode": "Markdown"
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
    print("🚀 開始執行盈虧結算...")
    
    report_lines = []
    report_lines.append("📊 *每日收市盈虧結算 (16:20)*")
    report_lines.append("------------------------")

    total_market_value = 0
    total_cost_value = 0
    
    # 遍歷持倉
    for symbol, data in PORTFOLIO.items():
        name = data['name']
        shares = data['shares']
        avg_price = data['avg_price']
        
        # 🔥 關鍵：每查一隻股票，暫停 2 秒，防止被 Yahoo 封鎖
        time.sleep(2)
        
        current_price = get_current_price(symbol)
        
        if current_price is not None:
            # 計算數值
            market_val = current_price * shares
            cost_val = avg_price * shares
            pnl = market_val - cost_val
            pnl_percent = ((current_price - avg_price) / avg_price) * 100
            
            # 累積總數
            total_market_value += market_val
            total_cost_value += cost_val
            
            # 判斷 Emoji
            icon = "🟢" if pnl >= 0 else "🔴"
            
            # 加入報告行
            report_lines.append(f"*{name}* ({symbol})")
            report_lines.append(f"   現價: ${current_price:.2f} | 成本: ${avg_price:.2f}")
            report_lines.append(f"   盈虧: {icon} *${pnl:+.1f}* ({pnl_percent:+.1f}%)")
            report_lines.append("") # 空行分隔
        else:
            report_lines.append(f"*{name}* ({symbol}) ⚠️ 數據讀取失敗")
            report_lines.append("")

    # 計算總結
    total_pnl = total_market_value - total_cost_value
    total_pnl_percent = 0
    if total_cost_value > 0:
        total_pnl_percent = (total_pnl / total_cost_value) * 100
        
    total_icon = "🟢" if total_pnl >= 0 else "🔴"

    report_lines.append("========================")
    report_lines.append(f"💰 *大市總結算*")
    report_lines.append(f"總盈虧: {total_icon} *${total_pnl:+.1f}* ({total_pnl_percent:+.2f}%)")
    
    # 組合訊息並發送
    final_message = "\n".join(report_lines)
    send_telegram_message(final_message)
    print("🎉 結算完成！")

if __name__ == "__main__":
    main()
