import streamlit as st
import ccxt
import pandas as pd
import requests
import time

# ================= 配置区 =================
# 1. 监控币种列表（已扩充至 20 个主流币）
SYMBOLS = [
    "BTC/USDT", "ETH/USDT", "BNB/USDT", "SOL/USDT", "XRP/USDT",
    "DOGE/USDT", "ADA/USDT", "TRX/USDT", "AVAX/USDT", "LINK/USDT",
    "TON/USDT", "DOT/USDT", "MATIC/USDT", "SHIB/USDT", "LTC/USDT",
    "UNI/USDT", "ATOM/USDT", "ETC/USDT", "FIL/USDT", "AAVE/USDT"
]

# 2. 推送链接（填入你的钉钉或企微 Webhook）
DINGTALK_WEBHOOK = "在此粘贴你的钉钉 Webhook" 
WECOM_WEBHOOK = "https://oapi.dingtalk.com/robot/send?access_token=c5d26cf25df7d56b5e9bf1b08bbf888ee9b18ed2f9e89ef9cdd2548b3ffeede3"
# ==========================================

st.set_page_config(page_title="Crypto 信号监控", layout="wide", page_icon="📈")
st.title("📊 主流虚拟货币实时监控 & 信号")
st.caption("包含 20 个主流币种 | 4H 波段策略 | 信号触发自动推送到手机")

# --- 1. 实时价格看板 (解决“看不到价格”的问题) ---
st.subheader(" 实时价格看板")
@st.cache_data(ttl=30) # 缓存 30 秒，避免刷新太快被封 IP
def get_live_prices():
    try:
        exchange = ccxt.binance({"enableRateLimit": True})
        # 只看前 5 个币种作为看板展示，速度更快
        tickers = exchange.fetch_tickers(["BTC/USDT", "ETH/USDT", "SOL/USDT", "BNB/USDT", "XRP/USDT"])
        res = []
        for sym, data in tickers.items():
            last = data["last"]
            change = data["percentage"]
            res.append({"币种": sym, "最新价": f"{last:.2f}", "涨跌幅": f"{change:.2f}%"})
        return pd.DataFrame(res)
    except: return None

df_live = get_live_prices()
if df_live is not None:
    # 根据涨跌显示不同颜色
    def color_change(val):
        color = "green" if "-" in str(val) else "red"
        return f'color: {color}; font-weight: bold'
    st.dataframe(df_live.style.applymap(color_change, subset=["涨跌幅"]), use_container_width=True, hide_index=True)
else:
    st.warning("⏳ 加载实时价格中...")

st.divider()

# --- 2. 推送功能函数 ---
def send_push(text):
    if not DINGTALK_WEBHOOK and not WECOM_WEBHOOK:
        return
    
    content = f"【信号提醒】\n{text}"
    if DINGTALK_WEBHOOK:
        try: requests.post(DINGTALK_WEBHOOK, json={"msgtype":"text","text":{"content":content}}, timeout=5)
        except: pass
    if WECOM_WEBHOOK:
        try: requests.post(WECOM_WEBHOOK, json={"msgtype":"text","text":{"content":content}}, timeout=5)
        except: pass

# --- 3. 核心策略信号扫描 ---
@st.cache_data(ttl=300) # 信号缓存 5 分钟
def scan_signals():
    exchange = ccxt.binance({"enableRateLimit": True})
    results = []
    
    # 只取 SYMBOLS 里的币种进行信号分析
    for sym in SYMBOLS:
        try:
            ohlcv = exchange.fetch_ohlcv(sym, timeframe="4h", limit=250)
            df = pd.DataFrame(ohlcv, columns=["ts","o","h","l","c","v"])
            df["dt"] = pd.to_datetime(df["ts"], unit="ms")
            
            # 指标计算 (EMA, MACD, ATR)
            df["EMA50"] = df["c"].ewm(span=50, adjust=False).mean()
            df["EMA200"] = df["c"].ewm(span=200, adjust=False).mean()
            ema12 = df["c"].ewm(span=12, adjust=False).mean()
            ema26 = df["c"].ewm(span=26, adjust=False).mean()
            dif = ema12 - ema26
            dea = dif.ewm(span=9, adjust=False).mean()
            df["MACD_H"] = 2 * (dif - dea)
            
            tr1 = df["h"] - df["l"]
            tr2 = (df["h"] - df["c"].shift(1)).abs()
            tr3 = (df["l"] - df["c"].shift(1)).abs()
            df["ATR"] = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1).rolling(14).mean()
            
            df = df.dropna()
            if len(df) < 10: continue
            
            last, prev = df.iloc[-1], df.iloc[-2]
            
            # 策略逻辑：趋势 + MACD 翻转 + 回调 + K 线吞没
            uptrend = last["c"] > last["EMA200"] and last["EMA50"] > last["EMA200"]
            downtrend = last["c"] < last["EMA200"] and last["EMA50"] < last["EMA200"]
            macd_long = prev["MACD_H"] < 0 and last["MACD_H"] > 0
            macd_short = prev["MACD_H"] > 0 and last["MACD_H"] < 0
            near_long = last["l"] <= last["EMA50"]*1.008 and last["c"] > last["EMA50"]
            near_short = last["h"] >= last["EMA50"]*0.992 and last["c"] < last["EMA50"]
            bull_eng = prev["c"] < prev["o"] and last["c"] > last["o"] and last["o"] <= prev["c"] and last["c"] >= prev["o"]
            bear_eng = prev["c"] > prev["o"] and last["c"] < last["o"] and last["o"] >= prev["c"] and last["c"] <= prev["o"]
            
            sig_time = str(last["dt"])
            
            # 做多信号
            if uptrend and near_long and macd_long and bull_eng:
                sl = last["l"] - 1.2*last["ATR"]
                tp = last["c"] + 1.5*(last["c"]-sl)
                results.append({"币种":sym, "方向":"🟢 做多", "入场":f"{last['c']:.2f}", "止损":f"{sl:.2f}", "止盈":f"{tp:.2f}", "赔率":"1:1.5", "时间":sig_time})
                send_push(f"{sym} 触发做多\n入场:{last['c']:.2f} 止损:{sl:.2f}")
                
            # 做空信号
            elif downtrend and near_short and macd_short and bear_eng:
                sl = last["h"] + 1.2*last["ATR"]
                tp = last["c"] - 1.5*(sl-last["c"])
                results.append({"币种":sym, "方向":"🔴 做空", "入场":f"{last['c']:.2f}", "止损":f"{sl:.2f}", "止盈":f"{tp:.2f}", "赔率":"1:1.5", "时间":sig_time})
                send_push(f"{sym} 触发做空\n入场:{last['c']:.2f} 止损:{sl:.2f}")
                
        except:
            continue
            
    return pd.DataFrame(results) if results else pd.DataFrame(columns=["币种","方向","入场","止损","止盈","赔率","时间"])

# --- 4. 界面布局 ---
c1, c2, c3 = st.columns(3)
c1.metric("监控币种", f"{len(SYMBOLS)} 个")
c2.metric("策略周期", "4H K 线")
c3.metric("推送状态", "✅ 已配置" if (DINGTALK_WEBHOOK or WECOM_WEBHOOK) else "⚪ 未填")

st.subheader("📡 策略信号 (每 4 小时刷新一次)")
df_sig = scan_signals()

if df_sig.empty:
    st.info(" 当前无信号。策略仅在 4H K 线收盘且满足所有条件时触发。建议每 5 分钟手动刷新页面。")
else:
    def color_dir(val):
        if "多" in str(val): return "color: #00C853; font-weight: bold"
        if "空" in str(val): return "color: #FF1744; font-weight: bold"
        return ""
    st.dataframe(df_sig.style.applymap(color_dir, subset=["方向"]), use_container_width=True, hide_index=True)

st.divider()
st.caption("⚠️ 注意：本页面为静态网页，需手动刷新或安装手机浏览器 Auto Refresh 插件。")

