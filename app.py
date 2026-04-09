import streamlit as st
import ccxt
import pandas as pd

st.set_page_config(page_title="Crypto信号监控", layout="wide", page_icon="📈")
st.title("📊 主流虚拟货币实时交易信号监控")
st.caption("策略：4H趋势 + EMA回调 + MACD翻转 + K线形态 | 纯Pandas计算，稳定运行")

# 缓存5分钟
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
            
            # --- 纯 Pandas 计算指标 (替代 pandas_ta) ---
            
            # 1. EMA
            df["EMA50"] = df["c"].ewm(span=50, adjust=False).mean()
            df["EMA200"] = df["c"].ewm(span=200, adjust=False).mean()
            
            # 2. MACD
            ema12 = df["c"].ewm(span=12, adjust=False).mean()
            ema26 = df["c"].ewm(span=26, adjust=False).mean()
            dif = ema12 - ema26
            dea = dif.ewm(span=9, adjust=False).mean()
            df["MACD_H"] = 2 * (dif - dea) # 柱状图
            
            # 3. ATR (简化计算: TR的简单移动平均)
            tr1 = df["h"] - df["l"]
            tr2 = (df["h"] - df["c"].shift(1)).abs()
            tr3 = (df["l"] - df["c"].shift(1)).abs()
            tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
            df["ATR"] = tr.rolling(window=14).mean()
            
            # -----------------------------------------
            
            # 过滤掉空值
            df = df.dropna()
            if len(df) < 10: continue
            
            last, prev = df.iloc[-1], df.iloc[-2]
            
            # 1. 趋势过滤 (均线多头/空头排列)
            # 去掉了 ADX，直接用均线判断，更稳定
            uptrend = last["c"] > last["EMA200"] and last["EMA50"] > last["EMA200"]
            downtrend = last["c"] < last["EMA200"] and last["EMA50"] < last["EMA200"]
            
            # 2. MACD 动能翻转
            macd_long = prev["MACD_H"] < 0 and last["MACD_H"] > 0
            macd_short = prev["MACD_H"] > 0 and last["MACD_H"] < 0
            
            # 3. 回调至 EMA50 附近
            near_long = last["l"] <= last["EMA50"]*1.008 and last["c"] > last["EMA50"]
            near_short = last["h"] >= last["EMA50"]*0.992 and last["c"] < last["EMA50"]
            
            # 4. K线形态 (吞没)
            # 阳线吞没阴线 (看涨)
            bull_eng = (prev["c"] < prev["o"]) and (last["c"] > last["o"]) and \
                       (last["o"] <= prev["c"]) and (last["c"] >= prev["o"])
            # 阴线吞没阳线 (看跌)
            bear_eng = (prev["c"] > prev["o"]) and (last["c"] < last["o"]) and \
                       (last["o"] >= prev["c"]) and (last["c"] <= prev["o"])
            
            # --- 触发信号 ---
            if uptrend and near_long and macd_long and bull_eng:
                sl = last["l"] - 1.2*last["ATR"]
                tp = last["c"] + 1.5*(last["c"]-sl)
                results.append({
                    "币种": sym, "方向": "🟢 做多", 
                    "入场": f"{last['c']:.2f}", "止损": f"{sl:.2f}", 
                    "止盈": f"{tp:.2f}", "赔率": "1 : 1.5", 
                    "时间": str(last["dt"])
                })
                
            elif downtrend and near_short and macd_short and bear_eng:
                sl = last["h"] + 1.2*last["ATR"]
                tp = last["c"] - 1.5*(sl-last["c"])
                results.append({
                    "币种": sym, "方向": "🔴 做空", 
                    "入场": f"{last['c']:.2f}", "止损": f"{sl:.2f}", 
                    "止盈": f"{tp:.2f}", "赔率": "1 : 1.5", 
                    "时间": str(last["dt"])
                })
        except Exception as e:
            print(f"Error {sym}: {e}")
            continue
            
    return pd.DataFrame(results) if results else pd.DataFrame(columns=["币种","方向","入场","止损","止盈","赔率","时间"])

# 界面显示
c1, c2, c3 = st.columns(3)
c1.metric("监控周期", "4小时K线")
c2.metric("策略定位", "高赔率波段")
c3.metric("状态", "✅ 运行中")

st.subheader("📡 最新交易信号")
df = scan_signals()

if df.empty:
    st.info("⏳ 当前无高胜率信号。系统正在监控中...")
else:
    def color_dir(val):
        if "多" in str(val): return "color: #00C853; font-weight: bold"
        if "空" in str(val): return "color: #FF1744; font-weight: bold"
        return ""
    st.dataframe(df.style.applymap(color_dir, subset=["方向"]), use_container_width=True, hide_index=True)

st.markdown("---")
st.caption("⚠️ 免责声明：本工具仅作技术分析参考。加密货币波动极大，请严格设置止损。")
