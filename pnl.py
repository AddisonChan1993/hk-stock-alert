import os
import time
import requests
import yfinance as yf

# ==========================================
# 1. 用戶持倉設定 (你的最新持倉)
# ==========================================
PORTFOLIO = {
    '0005.HK': {'name': '匯豐控股', 'shares': 400, 'avg_price': 124.300},
    '1088.HK': {'name': '中國神華', 'shares': 500, 'avg_price': 43.900},
    '3070.HK': {'name': '平安香港高息', 'shares': 1100, 'avg_price': 40.078},
    '3081.HK': {'name': '價值黃金ETF', 'shares': 1100, 'avg_price': 23.625},
    '3466.HK': {'name': '恒生高息股', 'shares': 3200, 'avg_price': 20.428}
}

# ==========================================
# 2. 獲取數據函數 (包含現價 & 上日收市價)
# ==========================================
def get_stock_data(symbol):
    """
    獲取股票 [現價, 上日收市價]，失敗時返回 None, None
    """
    try:
        print(f"🔍 正在查詢: {symbol} ...")
        ticker = yf.Ticker(symbol)
        
        # 獲取過去 5 日數據，確保有足夠數據找到「上日收市」
        hist = ticker.history(period="5d")
        
        if len(hist) >= 2:
            current_price = float(hist['Close'].iloc[-1]) # 最新收市價
            prev_close = float(hist['Close'].iloc[-2])    # 上日收市價
            return current_price, prev_close
        elif len(hist) == 1:
            # 如果剛好得一日數據 (例如新上市或極少交易)，就當作無變動
            current_price = float(hist['Close'].iloc[-1])
            return current_price, current_price
        else:
            print(f"❌ {symbol} 數據不足")
            return None, None
            
    except Exception as e:
        print(f"⚠️ {symbol} 讀取錯誤: {e}")
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
    report_lines.append("📊 *每日收市詳細結算 (16:20)*")
    report_lines.append("------------------------")

    # 累積變數
    total_daily_pnl = 0   # 今日總盈虧
    total_hold_pnl = 0    # 持倉總盈虧
    total_cost = 0        # 總成本
    
    # 遍歷持倉
    for symbol, data in PORTFOLIO.items():
        name = data['name']
        shares = data['shares']
        avg_price = data['avg_price']
        
        # 🔥 防封鎖延遲
        time.sleep(2)
        
        price, prev_close = get_stock_data(symbol)
        
        if price is not None:
            # 1. 計算今日盈虧 (Daily PnL)
            daily_change = price - prev_close
            daily_pnl = daily_change * shares
            daily_pct = (daily_change / prev_close) * 100
            
            # 2. 計算總持倉盈虧 (Total PnL)
            total_pnl = (price - avg_price) * shares
            total_pct = ((price - avg_price) / avg_price) * 100
            
            # 3. 累積大數
            total_daily_pnl += daily_pnl
            total_hold_pnl += total_pnl
            total_cost += (avg_price * shares)
            
            # 4. 判斷 Emoji
            d_icon = "🔺" if daily_pnl >= 0 else "🔻"
            t_icon = "🟢" if total_pnl >= 0 else "🔴"
            
            # 5. 排版輸出
            report_lines.append(f"*{name}* ({symbol})")
            report_lines.append(f"   現價: ${price:.2f}")
            report_lines.append(f"   📅 今日: {d_icon} *${daily_pnl:+.1f}* ({daily_pct:+.2f}%)")
            report_lines.append(f"   💰 總計: {t_icon} *${total_pnl:+.1f}* ({total_pct:+.1f}%)")
            report_lines.append("") # 空行
        else:
            report_lines.append(f"*{name}* ({symbol}) ⚠️ 數據讀取失敗")
            report_lines.append("")

    # 計算大市總結
    total_daily_icon = "🟢" if total_daily_pnl >= 0 else "🔴"
    total_hold_icon = "🟢" if total_hold_pnl >= 0 else "🔴"
    
    hold_pct = 0
    if total_cost > 0:
        hold_pct = (total_hold_pnl / total_cost) * 100

    report_lines.append("========================")
    report_lines.append(f"📅 *今日總盈虧*: {total_daily_icon} *${total_daily_pnl:+.1f}*")
    report_lines.append(f"💰 *總持倉盈虧*: {total_hold_icon} *${total_hold_pnl:+.1f}* ({hold_pct:+.2f}%)")
    
    # 發送
    final_message = "\n".join(report_lines)
    send_telegram_message(final_message)
    print("🎉 結算完成！")

if __name__ == "__main__":
    main()
