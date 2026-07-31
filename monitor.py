import yfinance as yf
import pandas as pd
import requests
import os

TOKEN = os.getenv('TELEGRAM_TOKEN')
CHAT_ID = os.getenv('TELEGRAM_CHAT_ID')

# ==========================================
# 1. 持倉股票設定 (修復漏寫逗號問題)
# ==========================================
STOCK_MAP = {
    '1810.HK': '小米集團-W',
    '0005.HK': '匯豐控股',
    '3750.HK': '寧德時代', 
    '2561.HK': '維昇藥業',
    '2050.HK': '三花智控',
    '0823.HK': '領展房產基金',
    '0883.HK': '中國海油',
    '3690.HK': '美團-W',
    '9988.HK': '阿里巴巴-W',  # 👈 已補上逗號
    '6823.HK': '香港電訊',    # 👈 已補上逗號
    '0939.HK': '建設銀行'
}

def ai_prediction_logic(df):
    try:
        # 確保提取出來的是純粹的 Series
        close = df['Close'].astype(float)
        high = df['High'].astype(float)
        low = df['Low'].astype(float)
        volume = df['Volume'].astype(float)
        
        price = float(close.iloc[-1])
        
        # --- 1. 原有基礎指標 (RSI, 均線, 成交量) ---
        delta = close.diff()
        gain = delta.clip(lower=0).rolling(window=14).mean()
        loss = -delta.clip(upper=0).rolling(window=14).mean()
        loss = loss.replace(0, 0.0001)
        rsi = float(100 - (100 / (1 + (gain / loss))).iloc[-1])
        
        ma5 = float(close.rolling(window=5).mean().iloc[-1])
        ma20 = float(close.rolling(window=20).mean().iloc[-1])
        
        vol_ma5 = float(volume.rolling(window=5).mean().iloc[-1])
        last_vol = float(volume.iloc[-1])
        vol_ratio = float(last_vol / vol_ma5) if vol_ma5 > 0 else 1.0
        
        # --- 2. MACD ---
        exp1 = close.ewm(span=12, adjust=False).mean()
        exp2 = close.ewm(span=26, adjust=False).mean()
        macd = exp1 - exp2
        signal = macd.ewm(span=9, adjust=False).mean()
        
        macd_today, signal_today = float(macd.iloc[-1]), float(signal.iloc[-1])
        macd_ytd, signal_ytd = float(macd.iloc[-2]), float(signal.iloc[-2])
        
        macd_cross = "金叉" if macd_today > signal_today and macd_ytd <= signal_ytd else ("死叉" if macd_today < signal_today and macd_ytd >= signal_ytd else "")

        # --- 3. 布林帶 Bollinger Bands ---
        std20 = float(close.rolling(window=20).std().iloc[-1])
        upper_band = ma20 + (std20 * 2)
        lower_band = ma20 - (std20 * 2)
        bb_status = "頂" if price >= upper_band else ("底" if price <= lower_band else "")

        # --- 4. KDJ ---
        low_9 = low.rolling(window=9, min_periods=1).min()
        high_9 = high.rolling(window=9, min_periods=1).max()
        rsv = (close - low_9) / (high_9 - low_9 + 0.0001) * 100
        
        K = rsv.ewm(com=2, adjust=False).mean()
        D = K.ewm(com=2, adjust=False).mean()
        J = 3 * K - 2 * D
        
        j_today, k_today = float(J.iloc[-1]), float(K.iloc[-1])
        j_ytd, k_ytd = float(J.iloc[-2]), float(K.iloc[-2])
        
        kdj_cross = ""
        if j_today > k_today and j_ytd <= k_ytd:
            kdj_cross = "金叉"
        elif j_today < k_today and j_ytd >= k_ytd:
            kdj_cross = "死叉"

        # --- 5. OBV 能量潮 ---
        direction = delta.apply(lambda x: 1 if x > 0 else (-1 if x < 0 else 0))
        obv = (direction * volume).fillna(0).cumsum()
        
        obv_ma20 = float(obv.rolling(window=20).mean().iloc[-1])
        obv_current = float(obv.iloc[-1])
        obv_ytd = float(obv.iloc[-2])
        
        obv_status = "吸籌" if obv_current > obv_ma20 and obv_current > obv_ytd else ""
        obv_divergence = "頂背馳" if price > ma5 and obv_current < obv_ytd else ""

        # --- 綜合評分系統 ---
        score = 0
        tags = []
        
        if price > ma5 and ma5 > ma20: score += 15
        if price < ma5 and ma5 < ma20: score -= 15
        
        if 40 < rsi < 65: score += 10
        if rsi >= 75: 
            score -= 15; tags.append("超買")
        elif rsi <= 30:
            score += 15; tags.append("超賣")
            
        if vol_ratio > 1.5 and price > ma5: score += 10; tags.append("放量")
            
        if macd_cross == "金叉": score += 20; tags.append("🌟MACD金叉")
        elif macd_cross == "死叉": score -= 20; tags.append("💀MACD死叉")
            
        if bb_status == "頂":
            if rsi > 70: score -= 20; tags.append("⚠️觸頂")
        elif bb_status == "底":
            if rsi < 30: score += 20; tags.append("🎯觸底")

        if kdj_cross == "金叉" and j_today < 50:
            score += 15; tags.append("⚡短線啟動(KDJ)")
        elif kdj_cross == "死叉" and j_today > 80:
            score -= 15; tags.append("✂️短線見頂(KDJ)")
            
        if obv_status == "吸籌":
            score += 15; tags.append("🕵️‍♂️大戶吸籌")
        elif obv_divergence == "頂背馳":
            score -= 15; tags.append("🏃‍♂️量價背馳(大戶散水)")
        
        if score >= 50: res = "🚀 強力買入"
        elif score >= 20: res = "⬆️ 趨勢向好"
        elif score <= -30: res = "🚨 強烈警告/轉勢"
        elif score <= -10: res = "⬇️ 走勢偏弱"
        else: res = "⚖️ 區間盤整"
        
        if tags:
            res += f"\n    👉 [{', '.join(tags)}]"
            
        return res, rsi, vol_ratio
        
    except Exception as e:
        return f"⚠️ 運算錯誤 ({str(e)[:15]})", 50.0, 1.0

# 改用 HTML parse mode 防範 Telegram 特殊字元碰撞
def send_tg(msg):
    if not msg or not msg.strip(): return
    if not TOKEN or not CHAT_ID:
        print("❌ 未設定 TOKEN 或 CHAT_ID")
        return
    url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
    payload = {'chat_id': CHAT_ID, 'text': msg, 'parse_mode': 'HTML'}
    requests.post(url, data=payload)

def monitor():
    send_tg("🎯 <b>AI 高精度實戰診斷啟動</b>")
    report = ""
    count = 0
    
    for symbol, name in STOCK_MAP.items():
        try:
            # yfinance 下載數據 (強制關閉 multi_level_index 以兼容新版 yfinance)
            df = yf.download(symbol, period='3mo', interval='1d', progress=False, multi_level_index=False)
            if df.empty or len(df) < 20: 
                continue
            
            price = float(df['Close'].iloc[-1])
            prediction, rsi, v_ratio = ai_prediction_logic(df)
            
            # HTML 排版格式
            report += f"\n<b>{name} ({symbol})</b>\n價: <code>${price:.2f}</code> | RSI: {rsi:.1f} | 量: {v_ratio:.1f}x\n訊號: {prediction}\n"
            count += 1
            
            if count % 5 == 0:
                send_tg(report)
                report = ""
        except Exception as e:
            print(f"處理 {symbol} 時出錯: {e}")
            continue
            
    if report:
        send_tg(report)

if __name__ == "__main__":
    monitor()
