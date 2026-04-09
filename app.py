import streamlit as st
import ccxt
import pandas as pd
import requests
SYMBOLS = ["MEGA/USDT","ENJ/USDT","AGT/USDT"]
# ================= 配置区 =================
# 1. 监控币种（可自由增减，注意保持 "币种/USDT" 格式）
SYMBOLS = ["BTC/USDT", "ETH/USDT", "SOL/USDT", "BNB/USDT", "AVAX/USDT", "LINK/USDT", "XRP/USDT"]
DINGTALK_WEBHOOK =https://oapi.dingtalk.com/robot/send?access_token=c5d26cf25df7d56b5e9bf1b08bbf888ee9b18ed2f9e89ef9cdd2548b3ffeede3
# 2. 推送链接（二填一，另一个留空即可）
DINGTALK_WEBHOOK = "在此粘贴钉钉Webhook链接"
WECOM_WEBHOOK = "在此粘贴企业微信Webhook链接"
# ==========================================

st.set_page_config(page_title="Crypto信号监控", layout="wide", page_icon="📈")
st.title("📊 主流虚拟货币实时交易信号监控")
st.caption("策略：4H趋势 + EMA回调 + MACD翻转 + K线形态 | 支持手机弹窗推送")

# 会话状态管理（防止同一信号重复推送）
if "last_push_time" not in st.session_state:
    st.session_state.last_push_time = ""

def send_push(text):
    """发送钉钉或企微通知"""
    if not DINGTALK_WEBHOOK and not WECOM_WEBHOOK:
        return
    
    # 钉钉必须包含关键词"信号"才能发送成功
    content = f"【信号提醒】\n{text}"
    
    if DINGTALK_WEBHOOK:
        try:
            requests.post(DINGTALK_WEBHOOK, json={"msgtype":"text","text":{"content":content}}, timeout=5)
        except: pass
    if WECOM_WEBHOOK:
        try:
            requests.post(WECOM_WEBHOOK, json={"msgtype":"text","text":{"content":content}}, timeout=5)
        except: pass

def get_signals():
    exchange = ccxt.binance({"enableRateLimit": True})
    results = []
    
    for sym in SYMBOLS:
        try:
            ohlcv = exchange.fetch_ohlcv(sym, timeframe="4h", limit=250)
            df = pd.DataFrame(ohlcv, columns=["ts","o","h","l","c","v"])
            df["dt"] = pd.to_datetime(df["ts"], unit="ms")
            
            # 指标计算
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
            
            # 趋势 + 动能 + 位置 + 形态 四重过滤
            uptrend = last["c"] > last["EMA200"] and last["EMA50"] > last["EMA200"]
            downtrend = last["c"] < last["EMA200"] and last["EMA50"] < last["EMA200"]
            macd_long = prev["MACD_H"] < 0 and last["MACD_H"] > 0
            macd_short = prev["MACD_H"] > 0 and last["MACD_H"] < 0
            near_long = last["l"] <= last["EMA50"]*1.008 and last["c"] > last["EMA50"]
            near_short = last["h"] >= last["EMA50"]*0.992 and last["c"] < last["EMA50"]
            bull_eng = prev["c"] < prev["o"] and last["c"] > last["o"] and last["o"] <= prev["c"] and last["c"] >= prev["o"]
            bear_eng = prev["c"] > prev["o"] and last["c"] < last["o"] and last["o"] >= prev["c"] and last["c"] <= prev["o"]
            
            if uptrend and near_long and macd_long and bull_eng:
                sl = last["l"] - 1.2*last["ATR"]
                tp = last["c"] + 1.5*(last["c"]-sl)
                sig_time = str(last["dt"])
                results.append({"币种":sym, "方向":"🟢 做多", "入场":f"{last['c']:.2f}", "止损":f"{sl:.2f}", "止盈":f"{tp:.2f}", "赔率":"1:1.5", "时间":sig_time})
                
                if sig_time != st.session_state.last_push_time:
                    send_push(f"{sym} 触发做多信号\n入场:{last['c']:.2f} 止损:{sl:.2f} 止盈:{tp:.2f}")
                    st.session_state.last_push_time = sig_time
                    
            elif downtrend and near_short and macd_short and bear_eng:
                sl = last["h"] + 1.2*last["ATR"]
                tp = last["c"] - 1.5*(sl-last["c"])
                sig_time = str(last["dt"])
                results.append({"币种":sym, "方向":"🔴 做空", "入场":f"{last['c']:.2f}", "止损":f"{sl:.2f}", "止盈":f"{tp:.2f}", "赔率":"1:1.5", "时间":sig_time})
                
                if sig_time != st.session_state.last_push_time:
                    send_push(f"{sym} 触发做空信号\n入场:{last['c']:.2f} 止损:{sl:.2f} 止盈:{tp:.2f}")
                    st.session_state.last_push_time = sig_time
        except:
            continue
            
    return pd.DataFrame(results) if results else pd.DataFrame(columns=["币种","方向","入场","止损","止盈","赔率","时间"])

# 界面显示
c1, c2, c3 = st.columns(3)
c1.metric("监控币种", f"{len(SYMBOLS)} 个")
c2.metric("策略周期", "4H K线")
c3.metric("推送状态", "✅ 已配置" if (DINGTALK_WEBHOOK or WECOM_WEBHOOK) else "⚪ 未填链接")

st.subheader("📡 最新交易信号")
df = get_signals()

if df.empty:
    st.info("⏳ 当前无高胜率信号。系统正在监控中...")
else:
    def color_dir(val):
        if "多" in str(val): return "color: #00C853; font-weight: bold"
        if "空" in str(val): return "color: #FF1744; font-weight: bold"
        return ""
    st.dataframe(df.style.applymap(color_dir, subset=["方向"]), use_container_width=True, hide_index=True)

st.markdown("---")
# 🧪 测试推送按钮（验证通过后请删除此段）
if st.button("🧪 点击测试推送功能"):
    send_push("🎉 测试成功！机器人已连通，信号触发时将自动推送到此手机。")
    st.success("✅ 推送请求已发送，请查看手机钉钉/企微")
    st.caption("⚠️ 提示：Streamlit云端需页面刷新才会触发推送。建议手机浏览器安装 Auto Refresh 插件（设置5分钟刷新），或手动下拉刷新。严格止损，仓位≤2%。")
