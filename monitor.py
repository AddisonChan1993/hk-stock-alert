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
    '0293.HK': '國泰航空',
    '0883.HK': '中國海油',
    '3690.HK': '美團-W',
    '9988.HK': '阿里巴巴-W'
}

def ai_prediction_logic(df):
    try:
        close = df['Close'].squeeze()
        volume = df['Volume'].squeeze()
        price = float(close.iloc[-1])
        
        # --- 1. 原有指標 (RSI, 均線, 成交量) ---
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
        
        # --- 2. 新增：MACD (判斷動能轉勢) ---
        exp1 = close.ewm(span=12, adjust=False).mean()
        exp2 = close.ewm(span=26, adjust=False).mean()
        macd = exp1 - exp2
        signal = macd.ewm(span=9, adjust=False).mean()
        
        macd_today = macd.iloc[-1]
        signal_today = signal.iloc[-1]
        macd_ytd = macd.iloc[-2]
        signal_ytd = signal.iloc[-2]
        
        macd_cross = ""
        # 尋找黃金交叉 / 死亡交叉
        if macd_today > signal_today and macd_ytd <= signal_ytd:
            macd_cross = "金叉"
        elif macd_today < signal_today and macd_ytd >= signal_ytd:
            macd_cross = "死叉"
            
        # --- 3. 新增：布林帶 Bollinger Bands (判斷頂底) ---
        std20 = close.rolling(window=20).std().iloc[-1]
        upper_band = ma20 + (std20 * 2)
        lower_band = ma20 - (std20 * 2)
        
        bb_status = ""
        if price >= upper_band: bb_status = "頂"
        elif price <= lower_band: bb_status = "底"
            
        # --- 👑 終極高精度綜合評分系統 ---
        score = 0
        tags = [] # 用來收集特別訊號，顯示喺 Telegram
        
        # 基本趨勢分
        if price > ma5 and ma5 > ma20: score += 20
        if price < ma5 and ma5 < ma20: score -= 20
        
        # RSI 狀態
        if 40 < rsi < 65: score += 10
        if rsi >= 75: 
            score -= 20
            tags.append("超買")
        elif rsi <= 30:
            score += 20
            tags.append("超賣")
            
        # 成交量狀態
        if vol_ratio > 1.5 and price > ma5: 
            score += 20
            tags.append("放量")
            
        # MACD 加成
        if macd_cross == "金叉":
            score += 30
            tags.append("🌟MACD金叉")
        elif macd_cross == "死叉":
            score -= 30
            tags.append("💀MACD死叉")
        elif macd_today > signal_today:
            score += 10 # 處於多頭區間
            
        # 布林帶極端訊號加成
        if bb_status == "頂":
            if rsi > 70:
                score -= 30 
                tags.append("⚠️觸頂回落風險")
            elif vol_ratio > 1.5:
                score += 20
                tags.append("🔥強勢破上軌")
        elif bb_status == "底":
            if rsi < 30:
                score += 30
                tags.append("🎯觸底反彈區")
        
        # 決定最終評級
        if score >= 50: res = "🚀 強力買入"
        elif score >= 20: res = "⬆️ 趨勢向好"
        elif score <= -30: res = "🚨 強烈警告/轉勢"
        elif score <= -10: res = "⬇️ 走勢偏弱"
        else: res = "⚖️ 區間盤整"
        
        # 將 Tags 組合顯示
        if tags:
            res += f" [{', '.join(tags)}]"
            
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
