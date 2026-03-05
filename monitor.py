import yfinance as yf
import pandas as pd
import requests
import os

TOKEN = os.getenv('TELEGRAM_TOKEN')
CHAT_ID = os.getenv('TELEGRAM_CHAT_ID')

STOCK_MAP = {
    '1810.HK': '小米集團-W',
    '0005.HK': '匯豐控股',
    '1299.HK': '友邦保險',
    '3750.HK': '寧德時代', 
    '9611.HK': '龍旗科技',
    '2561.HK': '維昇藥業',
    '2050.HK': '三花智控',
    '1088.HK': '中國神華',
    '0823.HK': '領展房產基金',
    '6809.HK': '瀾起科技',
    '0883.HK': '中國海油',
    '3690.HK': '美團-W',
    '9988.HK': '阿里巴巴-W'
}

def ai_prediction_logic(df):
    try:
        close = df['Close'].squeeze()
        high = df['High'].squeeze()
        low = df['Low'].squeeze()
        volume = df['Volume'].squeeze()
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
        
        # --- 2. MACD (動能轉勢) ---
        exp1 = close.ewm(span=12, adjust=False).mean()
        exp2 = close.ewm(span=26, adjust=False).mean()
        macd = exp1 - exp2
        signal = macd.ewm(span=9, adjust=False).mean()
        
        macd_today, signal_today = macd.iloc[-1], signal.iloc[-1]
        macd_ytd, signal_ytd = macd.iloc[-2], signal.iloc[-2]
        
        macd_cross = "金叉" if macd_today > signal_today and macd_ytd <= signal_ytd else ("死叉" if macd_today < signal_today and macd_ytd >= signal_ytd else "")

        # --- 3. 布林帶 Bollinger Bands (頂底) ---
        std20 = close.rolling(window=20).std().iloc[-1]
        upper_band = ma20 + (std20 * 2)
        lower_band = ma20 - (std20 * 2)
        bb_status = "頂" if price >= upper_band else ("底" if price <= lower_band else "")

        # --- 4. 🔥新增：KDJ (極速短線雷達) ---
        # 計算 9日 RSV
        low_9 = low.rolling(window=9, min_periods=1).min()
        high_9 = high.rolling(window=9, min_periods=1).max()
        rsv = (close - low_9) / (high_9 - low_9 + 0.0001) * 100
        
        # 計算 K, D, J (使用 EWM 模擬平滑)
        K = rsv.ewm(com=2, adjust=False).mean()
        D = K.ewm(com=2, adjust=False).mean()
        J = 3 * K - 2 * D
        
        j_today, k_today, d_today = J.iloc[-1], K.iloc[-1], D.iloc[-1]
        j_ytd, k_ytd, d_ytd = J.iloc[-2], K.iloc[-2], D.iloc[-2]
        
        kdj_cross = ""
        # 尋找低位金叉 (J向上穿過K/D) 或 高位死叉
        if j_today > k_today and j_ytd <= k_ytd:
            kdj_cross = "金叉"
        elif j_today < k_today and j_ytd >= k_ytd:
            kdj_cross = "死叉"

        # --- 5. 🔥新增：OBV 能量潮 (大戶資金流向) ---
        # 計算每日資金流入流出方向
        direction = delta.apply(lambda x: 1 if x > 0 else (-1 if x < 0 else 0))
        obv = (direction * volume).fillna(0).cumsum()
        
        obv_ma20 = float(obv.rolling(window=20).mean().iloc[-1])
        obv_current = float(obv.iloc[-1])
        obv_ytd = float(obv.iloc[-2])
        
        # 判斷大戶係咪儲緊貨 (OBV 向上突破平均線且持續上升)
        obv_status = "吸籌" if obv_current > obv_ma20 and obv_current > obv_ytd else ""
        obv_divergence = "頂背馳" if price > ma5 and obv_current < obv_ytd else ""

        # --- 👑 滿配版綜合評分系統 ---
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

        # KDJ 短線加成
        if kdj_cross == "金叉" and j_today < 50:
            score += 15; tags.append("⚡短線啟動(KDJ)")
        elif kdj_cross == "死叉" and j_today > 80:
            score -= 15; tags.append("✂️短線見頂(KDJ)")
            
        # OBV 資金流加成
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
            res += f" \n   👉 [{', '.join(tags)}]"
            
        return res, rsi, vol_ratio
        
    except Exception as e:
        return f"⚠️ 運算錯誤 ({str(e)[:10]})", 50.0, 1.0

def send_tg(msg):
    if not msg.strip(): return
    url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
    payload = {'chat_id': CHAT_ID, 'text': msg, 'parse_mode': 'Markdown'}
    requests.post(url, data=payload)

def monitor():
    send_tg("🎯 *AI 高精度實戰診斷啟動*")
    report = ""
    count = 0
    
    for symbol, name in STOCK_MAP.items():
        try:
            df = yf.download(symbol, period='3mo', interval='1d', progress=False)
            if df.empty: continue
            
            price = float(df['Close'].squeeze().iloc[-1])
            prediction, rsi, v_ratio = ai_prediction_logic(df)
            
            report += f"\n*{name} ({symbol})*\n價: `${price:.2f}` | RSI: {rsi:.1f} | 量: {v_ratio:.1f}x\n訊號: {prediction}\n"
            count += 1
            
            # 每 5 隻發送一次
            if count % 5 == 0:
                send_tg(report)
                report = ""
        except Exception as e:
            continue
            
    if report:
        send_tg(report)

if __name__ == "__main__":
    monitor()
