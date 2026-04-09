import streamlit as st
import ccxt
import pandas as pd
import pandas_ta as ta

st.set_page_config(page_title="Crypto信号监控", layout="wide", page_icon="📈")
st.title("📊 主流虚拟货币实时交易信号监控")
st.caption("策略逻辑：4H趋势过滤 + EMA50回调 + MACD动能翻转 + K线形态确认 | 自动计算赔率")

# 缓存5分钟，避免频繁请求被封IP
@st.cache_data(ttl=300)
def scan_signals():
    exchange = ccxt.binance({"enableRateLimit": True})
    symbols = ["BTC/USDT", "ETH/USDT", "SOL/USDT"]
    results = []

    for sym in symbols:
        try:
            ohlcv = exchange.fetch_ohlcv(sym, timeframe="4h", limit=250)
            df = pd.DataFrame(ohlcv, columns=["ts","o","h","l","c","v"])
            df["dt"] = pd.to_datetime(df["ts"], unit="ms")
            
            # 计算指标
            df["EMA50"] = ta.ema(df["c"], length=50)
            df["EMA200"] = ta.ema(df["c"], length=200)
            macd = ta.macd(df["c"], fast=12, slow=26, signal=9)
            df["MACD_H"] = macd["MACDh_12_26_9"]
            df["ADX"] = ta.adx(df["h"], df["l"], df["c"], length=14)["ADX_14"]
            df["ATR"] = ta.atr(df["h"], df["l"], df["c"], length=14)
            
            last, prev = df.iloc[-1], df.iloc[-2]
            
            # 1. 趋势过滤
            uptrend = last["c"] > last["EMA200"] and last["EMA50"] > last["EMA200"]
            downtrend = last["c"] < last["EMA200"] and last["EMA50"] < last["EMA200"]
            if last["ADX"] < 25: continue  # 震荡市跳过
            
            # 2. 动能翻转
            macd_long = prev["MACD_H"] < 0 and last["MACD_H"] > 0
            macd_short = prev["MACD_H"] > 0 and last["MACD_H"] < 0
            
            # 3. 回调至EMA50
            near_long = last["l"] <= last["EMA50"]*1.008 and last["c"] > last["EMA50"]
            near_short = last["h"] >= last["EMA50"]*0.992 and last["c"] < last["EMA50"]
            
            # 4. K线形态（吞没）
            bull_eng = prev["c"] < prev["o"] and last["c"] > last["o"] and last["o"] <= prev["c"]
            bear_eng = prev["c"] > prev["o"] and last["c"] < last["o"] and last["o"] >= prev["c"]
            
            if uptrend and near_long and macd_long and bull_eng:
                sl = last["l"] - 1.2*last["ATR"]
                tp = last["c"] + 1.5*(last["c"]-sl)
                results.append({"币种":sym, "方向":"🟢 做多", "入场":f"{last['c']:.2f}", "止损":f"{sl:.2f}", "止盈":f"{tp:.2f}", "赔率":"1 : 1.5", "时间":str(last["dt"])})
            elif downtrend and near_short and macd_short and bear_eng:
                sl = last["h"] + 1.2*last["ATR"]
                tp = last["c"] - 1.5*(sl-last["c"])
                results.append({"币种":sym, "方向":"🔴 做空", "入场":f"{last['c']:.2f}", "止损":f"{sl:.2f}", "止盈":f"{tp:.2f}", "赔率":"1 : 1.5", "时间":str(last["dt"])})
        except:
            continue
    return pd.DataFrame(results) if results else pd.DataFrame(columns=["币种","方向","入场","止损","止盈","赔率","时间"])

# 界面排版
c1, c2, c3 = st.columns(3)
c1.metric("监控周期", "4小时K线")
c2.metric("策略定位", "高赔率波段")
c3.metric("当前状态", "✅ 运行中")

st.subheader("📡 最新交易信号")
df = scan_signals()

if df.empty:
    st.info("⏳ 当前无高胜率信号。系统将在每次打开时自动扫描最新4小时K线数据。")
    st.markdown("💡 **提示**：震荡市空仓是最佳策略。信号仅在趋势明确+动能切换+形态共振时触发。")
else:
    # 颜色标记
    def color_dir(val):
        if "多" in str(val): return "color: #00C853; font-weight: bold"
        if "空" in str(val): return "color: #FF1744; font-weight: bold"
        return ""
    st.dataframe(df.style.applymap(color_dir, subset=["方向"]), use_container_width=True, hide_index=True)

st.markdown("---")
st.caption("⚠️ 免责声明：本工具仅作技术分析参考，不构成投资建议。加密货币波动极大，请严格设置止损，单笔风险不超过总资金2%。数据每5分钟自动缓存，手动刷新页面可获取最新结果。")
