import os
import time
import requests
import yfinance as yf

# ==========================================
# 1. 用戶持倉設定 (已根據圖片最新數據更新)
# ==========================================
PORTFOLIO = {
    '3070.HK': {'name': '平安香港高息', 'shares': 2300, 'avg_price': 41.494},
    '3466.HK': {'name': '恒生高息股',   'shares': 4400, 'avg_price': 20.775},
    '0005.HK': {'name': '滙豐控股',     'shares': 400,  'avg_price': 124.300},
    '3750.HK': {'name': '寧德時代',     'shares': 100,  'avg_price': 705.000},
    '0939.HK': {'name': '建設銀行',     'shares': 5000, 'avg_price': 8.920},
    '6823.HK': {'name': '香港電訊',     'shares': 3000, 'avg_price': 12.630},
    '1810.HK': {'name': '小米集團-W',   'shares': 800,  'avg_price': 22.100},
}

# ==========================================
# 2. 獲取數據函數
# ==========================================
def get_stock_data(symbol):
    """
    獲取股票 [現價, 上日收市價]，失敗時返回 None, None
    """
    try:
        print(f"🔍 正在查詢: {symbol} ...")
        ticker = yf.Ticker(symbol)
        
        # 獲取過去 5 日數據
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
            return None, None
            
    except Exception as e:
        print(f"⚠️ {symbol} 讀取錯誤: {e}")
        return None, None

# ==========================================
# 3. 發送 Telegram 訊息函數 (使用 HTML 格式)
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
        
        time.sleep(1) # 防封鎖延遲
        
        price, prev_close = get_stock_data(symbol)
        
        if price is not None:
            # 1. 計算今日盈虧
            daily_change = price - prev_close
            daily_pnl = daily_change * shares
            daily_pct = (daily_change / prev_close) * 100 if prev_close else 0
            
            # 2. 計算總持倉盈虧
            total_pnl = (price - avg_price) * shares
            total_pct = ((price - avg_price) / avg_price) * 100 if avg_price else 0
            
            # 3. 累積總額
            total_daily_pnl += daily_pnl
            total_hold_pnl += total_pnl
            total_cost += (avg_price * shares)
            
            # 4. 圖標
            d_icon = "🔺" if daily_pnl >= 0 else "🔻"
            t_icon = "🟢" if total_pnl >= 0 else "🔴"
            
            # 5. 組裝內文 (HTML 格式)
            report_lines.append(f"<b>{name}</b> ({symbol})")
            report_lines.append(f"   現價: ${price:.3f}")
            report_lines.append(f"   📅 今日: {d_icon} <b>${daily_pnl:+.1f}</b> ({daily_pct:+.2f}%)")
            report_lines.append(f"   💰 總計: {t_icon} <b>${total_pnl:+.1f}</b> ({total_pct:+.1f}%)")
            report_lines.append("")
        else:
            report_lines.append(f"<b>{name}</b> ({symbol}) ⚠️ 數據讀取失敗\n")

    # 總結計算
    total_daily_icon = "🟢" if total_daily_pnl >= 0 else "🔴"
    total_hold_icon = "🟢" if total_hold_pnl >= 0 else "🔴"
    
    hold_pct = (total_hold_pnl / total_cost) * 100 if total_cost > 0 else 0

    report_lines.append("========================")
    report_lines.append(f"📅 <b>今日總盈虧</b>: {total_daily_icon} <b>${total_daily_pnl:+.1f}</b>")
    report_lines.append(f"💰 <b>總持倉盈虧</b>: {total_hold_icon} <b>${total_hold_pnl:+.1f}</b> ({hold_pct:+.2f}%)")
    
    final_message = "\n".join(report_lines)
    send_telegram_message(final_message)
    print("🎉 結算完成！")

if __name__ == "__main__":
    main()
