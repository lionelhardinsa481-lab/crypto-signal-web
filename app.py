import streamlit as st
import ccxt
import pandas as pd
import requests
import time

# ================= 配置区 =================
SYMBOLS = [
    "BTC/USDT", "ETH/USDT", "BNB/USDT", "SOL/USDT", "XRP/USDT",
    "DOGE/USDT", "ADA/USDT", "TRX/USDT", "AVAX/USDT", "LINK/USDT",
    "TON/USDT", "DOT/USDT", "MATIC/USDT", "SHIB/USDT", "LTC/USDT",
    "UNI/USDT", "ATOM/USDT", "ETC/USDT", "FIL/USDT", "AAVE/USDT"
]

DINGTALK_WEBHOOK = "https://oapi.dingtalk.com/robot/send?access_token=c5d26cf25df7d56b5e9bf1b08bbf888ee9b18ed2f9e89ef9cdd2548b3ffeede3"
WECOM_WEBHOOK = "在此粘贴你的企微 Webhook"
# ==========================================

st.set_page_config(page_title="Crypto 信号监控", layout="wide", page_icon="📈")
st.title("📊 主流虚拟货币多周期信号监控")
st.caption("支持 5m/15m/1h/4h 周期 | 趋势+动量+成交量过滤 | 防重复推送")

# --- 1. 界面配置 ---
col1, col2 = st.columns([1, 3])
with col1:
    timeframe = st.selectbox("选择K线周期", ["5m", "15m", "1h", "4h"], index=1)
with col2:
    st.info("💡 短周期信号更多，建议配合严格止损。已推送信号在同一根K线内不会重复发送。")

# --- 2. 缓存与状态管理 ---
@st.cache_data(ttl=20)
def get_ohlcv(symbol, tf, limit=250):
    try:
        exchange = ccxt.binance({"enableRateLimit": True, "timeout": 10000})
        ohlcv = exchange.fetch_ohlcv(symbol, timeframe=tf, limit=limit)
        return pd.DataFrame(ohlcv, columns=["ts", "o", "h", "l", "c", "v"])
    except Exception as e:
        return pd.DataFrame()

def send_push(text):
    webhooks = [w for w in [DINGTALK_WEBHOOK, WECOM_WEBHOOK] if w]
    if not webhooks: return
    content = f"【Crypto信号-{timeframe}】\n{text}"
    for wh in webhooks:
        try: requests.post(wh, json={"msgtype": "text", "text": {"content": content}}, timeout=5)
        except: pass

# 初始化 session_state 记录已发送信号 (防重复轰炸)
if "signaled_keys" not in st.session_state:
    st.session_state.signaled_keys = set()

# --- 3. 核心策略 (高胜率优化版) ---
def scan_signals(tf):
    results = []
    
    for sym in SYMBOLS:
        df = get_ohlcv(sym, tf, 250)
        if df.empty or len(df) < 60: continue

        df["dt"] = pd.to_datetime(df["ts"], unit="ms")
        df["EMA50"] = df["c"].ewm(span=50, adjust=False).mean()
        df["EMA200"] = df["c"].ewm(span=200, adjust=False).mean()
        
        # MACD
        ema12 = df["c"].ewm(span=12, adjust=False).mean()
        ema26 = df["c"].ewm(span=26, adjust=False).mean()
        dif = ema12 - ema26
        dea = dif.ewm(span=9, adjust=False).mean()
        df["MACD_H"] = 2 * (dif - dea)
        
        # RSI (过滤极端行情)
        delta = df["c"].diff()
        gain = delta.where(delta > 0, 0)
        loss = -delta.where(delta < 0, 0)
        avg_gain = gain.rolling(14).mean()
        avg_loss = loss.rolling(14).mean()
        rs = avg_gain / avg_loss
        df["RSI"] = 100 - (100 / (1 + rs))
        
        # ATR & 成交量均值
        tr = pd.concat([df["h"]-df["l"], (df["h"]-df["c"].shift(1)).abs(), (df["l"]-df["c"].shift(1)).abs()], axis=1).max(axis=1)
        df["ATR"] = tr.rolling(14).mean()
        df["Vol_MA"] = df["v"].rolling(20).mean()
        
        df = df.dropna().iloc[-2:] # 仅分析最新两根K线
        if len(df) < 2: continue
        
        prev, last = df.iloc[0], df.iloc[1]
        sig_key = f"{sym}_{tf}_{int(last['ts'])}"
        
        # 🔒 防重复推送：同一币种同一周期同一根K线只推一次
        if sig_key in st.session_state.signaled_keys:
            continue
            
        # ================= 信号逻辑 =================
        # 1. 趋势过滤
        uptrend = last["c"] > last["EMA200"] and last["EMA50"] > last["EMA200"]
        downtrend = last["c"] < last["EMA200"] and last["EMA50"] < last["EMA200"]
        
        # 2. MACD 金叉/死叉 (动量确认)
        macd_long = prev["MACD_H"] < 0 and last["MACD_H"] > 0
        macd_short = prev["MACD_H"] > 0 and last["MACD_H"] < 0
        
        # 3. 回踩/反弹至EMA50附近 (放宽至 ±1.5%，适应短周期波动)
        near_long = last["l"] <= last["EMA50"] * 1.015 and last["c"] > last["EMA50"]
        near_short = last["h"] >= last["EMA50"] * 0.985 and last["c"] < last["EMA50"]
        
        # 4. 成交量确认 (放量突破/下跌，过滤假信号)
        vol_ok = last["v"] > last["Vol_MA"] * 1.2
        
        # 5. RSI 过滤 (避免追高杀跌)
        rsi_ok_long = last["RSI"] < 65
        rsi_ok_short = last["RSI"] > 35
        
        # ✅ 做多信号
        if uptrend and macd_long and near_long and vol_ok and rsi_ok_long:
            sl = last["l"] - 1.2 * last["ATR"]
            tp = last["c"] + 2.0 * (last["c"] - sl) # 盈亏比 1:2
            msg = f"{sym} 🟢做多\n入场:{last['c']:.2f}\n止损:{sl:.2f}\n止盈:{tp:.2f}"
            results.append({"币种":sym, "方向":"🟢 做多", "入场":f"{last['c']:.2f}", "止损":f"{sl:.2f}", "止盈":f"{tp:.2f}", "盈亏比":"1:2", "触发时间":str(last['dt'])})
            st.session_state.signaled_keys.add(sig_key)
            send_push(msg)
            
        # ✅ 做空信号
        elif downtrend and macd_short and near_short and vol_ok and rsi_ok_short:
            sl = last["h"] + 1.2 * last["ATR"]
            tp = last["c"] - 2.0 * (sl - last["c"])
            msg = f"{sym} 🔴做空\n入场:{last['c']:.2f}\n止损:{sl:.2f}\n止盈:{tp:.2f}"
            results.append({"币种":sym, "方向":"🔴 做空", "入场":f"{last['c']:.2f}", "止损":f"{sl:.2f}", "止盈":f"{tp:.2f}", "盈亏比":"1:2", "触发时间":str(last['dt'])})
            st.session_state.signaled_keys.add(sig_key)
            send_push(msg)
            
    return pd.DataFrame(results) if results else pd.DataFrame(columns=["币种","方向","入场","止损","止盈","盈亏比","触发时间"])

# --- 4. 界面渲染 ---
if st.button("🔄 立即扫描信号", type="primary"):
    with st.spinner(f"正在计算 {len(SYMBOLS)} 个币种的 {timeframe} 信号..."):
        df_sig = scan_signals(timeframe)

    st.subheader(f"📡 {timeframe} 策略信号")
    if df_sig.empty:
        st.info("✅ 当前无高胜率信号。策略已过滤震荡市与假突破。建议等待K线收盘确认。")
    else:
        st.dataframe(df_sig.style.applymap(
            lambda v: "color: #00C853; font-weight: bold" if "多" in str(v) else ("color: #FF1744; font-weight: bold" if "空" in str(v) else ""),
            subset=["方向"]
        ), use_container_width=True, hide_index=True)
        st.success(f"已发现 {len(df_sig)} 个信号，推送已发送至您的手机！")

    # 🧹 清理过期记录（仅保留1小时内信号，防止内存堆积）
    current_ts = int(time.time() * 1000)
    st.session_state.signaled_keys = {k for k in st.session_state.signaled_keys if current_ts - int(k.split("_")[-1]) < 3600000}

st.divider()
st.caption("⚠️ 风险提示：本工具仅为技术面辅助，不构成投资建议。短周期波动大，请严格设置止损。Streamlit 免费云端有休眠机制，建议配合本地运行或第三方监控服务。")
