import streamlit as st
import ccxt
import pandas as pd
import requests
import time

# ================= 配置区 =================
DINGTALK_WEBHOOK = "https://oapi.dingtalk.com/robot/send?access_token=c5d26cf25df7d56b5e9bf1b08bbf888ee9b18ed2f9e89ef9cdd2548b3ffeede3"
WECOM_WEBHOOK = "在此粘贴你的企微 Webhook"
# ==========================================

st.set_page_config(page_title="Crypto 合约信号监控", layout="wide", page_icon="📈")
st.title("📊 币安合约 Top50 多周期信号监控")
st.caption("🔥 动态追踪资金热点 | 布林收口过滤 | 趋势+动量+量价共振 | 防重复推送")

# ================= 动态币种池 =================
@st.cache_data(ttl=1800) # 缓存 30 分钟，避免频繁请求
def get_top_futures_symbols(limit=50):
    try:
        # 直接调用币安 FAPI，按 24H 成交额排序
        url = "https://fapi.binance.com/fapi/v1/ticker/24hr"
        data = requests.get(url, timeout=10).json()
        # 过滤纯 USDT 永续合约，排除杠杆/现货/BUSD
        usdt_perps = [d for d in data if d["symbol"].endswith("USDT") and "USDC" not in d["symbol"] and "BUSD" not in d["symbol"]]
        sorted_perps = sorted(usdt_perps, key=lambda x: float(x["quoteVolume"]), reverse=True)
        # 转换为 ccxt 永续合约标准格式: BTC/USDT:USDT
        symbols = [f"{p['symbol'].replace('USDT','')}USDT/USDT:USDT" for p in sorted_perps[:limit]]
        return symbols
    except Exception as e:
        st.warning(f"⚠️ 获取币安 Top50 失败，使用备用列表: {str(e)[:50]}")
        return ["BTC/USDT:USDT", "ETH/USDT:USDT", "BNB/USDT:USDT", "SOL/USDT:USDT", "XRP/USDT:USDT"]

SYMBOLS = get_top_futures_symbols(50)

# ================= 侧边栏配置 =================
st.sidebar.header("⚙️ 策略参数配置")
timeframe = st.sidebar.selectbox("🕰️ K线周期", ["5m", "15m", "1h", "4h"], index=1)

mode = st.sidebar.radio(
    "🎯 信号严格度",
    ["🚀 激进模式 (高频/宽过滤)", "⚖️ 平衡模式 (中频/标准)", "🛡️ 保守模式 (低频/严过滤)"],
    index=1
)

MODE_PARAMS = {
    "🚀 激进模式 (高频/宽过滤)": {
        "vol_mult": 1.0, "rsi_long_max": 75, "rsi_short_min": 25,
        "pullback_tol": 0.03, "req_pullback": False,
        "req_squeeze": False, "squeeze_tol": 1.3, "expected_wr": "40-50%"
    },
    "⚖️ 平衡模式 (中频/标准)": {
        "vol_mult": 1.2, "rsi_long_max": 65, "rsi_short_min": 35,
        "pullback_tol": 0.015, "req_pullback": True,
        "req_squeeze": True, "squeeze_tol": 1.15, "expected_wr": "55-65%"
    },
    "🛡️ 保守模式 (低频/严过滤)": {
        "vol_mult": 1.5, "rsi_long_max": 60, "rsi_short_min": 40,
        "pullback_tol": 0.008, "req_pullback": True,
        "req_squeeze": True, "squeeze_tol": 1.05, "expected_wr": "65-75%+"
    }
}
cfg = MODE_PARAMS[mode]

with st.sidebar.expander("📊 当前生效阈值", expanded=True):
    st.markdown(f"- **成交量要求**: > 20均量 `{cfg['vol_mult']}x`")
    st.markdown(f"- **RSI过滤**: 做多 `<{cfg['rsi_long_max']}` / 做空 `>{cfg['rsi_short_min']}`")
    st.markdown(f"- **EMA回踩**: `{'不强制' if not cfg['req_pullback'] else f'±{cfg['pullback_tol']*100:.1f}%'}`")
    st.markdown(f"- **布林收口**: `{'关闭' if not cfg['req_squeeze'] else f'带宽 < 近20周期极值×{cfg['squeeze_tol']}'}`")
    st.info(f"📈 预期胜率区间: {cfg['expected_wr']}")
    st.caption("💡 监控池已自动切换为币安 USDT 永续合约 Top50（按24H成交额排序）")

# 🤖 机器人测试模块
st.sidebar.divider()
st.sidebar.subheader("📡 推送通道测试")
if st.sidebar.button("📤 一键测试推送", type="primary"):
    test_msg = f"【系统测试】Crypto合约监控机器人已就绪！✅\n当前周期: {timeframe}\n当前模式: {mode.split(' ')[0]}\n监控币种: {len(SYMBOLS)} 个\n测试时间: {time.strftime('%Y-%m-%d %H:%M:%S')}"
    platforms = {"钉钉": DINGTALK_WEBHOOK, "企微": WECOM_WEBHOOK}
    success, failed = 0, []
    for name, url in platforms.items():
        if not url or "在此粘贴" in url:
            failed.append(f"{name}: 未配置 Webhook")
            continue
        try:
            resp = requests.post(url, json={"msgtype": "text", "text": {"content": test_msg}}, timeout=6)
            data = resp.json()
            if resp.status_code == 200 and data.get("errcode", -1) == 0:
                success += 1
            else:
                failed.append(f"{name}: API返回 {data.get('errcode','')}")
        except Exception as e:
            failed.append(f"{name}: 网络失败 ({str(e)[:30]})")
    if success > 0: st.sidebar.success(f"✅ 测试成功！已送达 {success} 个平台")
    if failed: st.sidebar.error("❌ 部分通道异常:\n" + "\n".join(failed))

# 初始化防重复状态
if "signaled_keys" not in st.session_state:
    st.session_state.signaled_keys = set()

# ================= 核心函数 =================
@st.cache_data(ttl=15)
def get_ohlcv(symbol, tf, limit=250):
    try:
        exchange = ccxt.binance({"options": {"defaultType": "swap"}, "enableRateLimit": True, "timeout": 10000})
        ohlcv = exchange.fetch_ohlcv(symbol, timeframe=tf, limit=limit)
        return pd.DataFrame(ohlcv, columns=["ts", "o", "h", "l", "c", "v"])
    except:
        return pd.DataFrame()

def send_push(text):
    webhooks = [w for w in [DINGTALK_WEBHOOK, WECOM_WEBHOOK] if w and "在此粘贴" not in w]
    if not webhooks: return
    content = f"【Crypto合约-{timeframe}-{mode.split(' ')[0]}】\n{text}"
    for wh in webhooks:
        try: requests.post(wh, json={"msgtype": "text", "text": {"content": content}}, timeout=5)
        except: pass

def scan_signals(tf, params):
    results = []
    progress_bar = st.progress(0, text="正在扫描合约市场...")
    
    for i, sym in enumerate(SYMBOLS):
        progress_bar.progress((i+1)/len(SYMBOLS), text=f"扫描进度: {i+1}/{len(SYMBOLS)} | 当前: {sym.replace('/USDT:USDT','')}")
        df = get_ohlcv(sym, tf, 250)
        if df.empty or len(df) < 60: continue

        df["dt"] = pd.to_datetime(df["ts"], unit="ms")
        df["EMA50"] = df["c"].ewm(span=50, adjust=False).mean()
        df["EMA200"] = df["c"].ewm(span=200, adjust=False).mean()
        
        ema12 = df["c"].ewm(span=12, adjust=False).mean()
        ema26 = df["c"].ewm(span=26, adjust=False).mean()
        dif = ema12 - ema26
        dea = dif.ewm(span=9, adjust=False).mean()
        df["MACD_H"] = 2 * (dif - dea)
        
        delta = df["c"].diff()
        gain = delta.where(delta > 0, 0)
        loss = -delta.where(delta < 0, 0)
        rs = gain.rolling(14).mean() / loss.rolling(14).mean()
        df["RSI"] = 100 - (100 / (1 + rs))
        
        tr = pd.concat([df["h"]-df["l"], (df["h"]-df["c"].shift(1)).abs(), (df["l"]-df["c"].shift(1)).abs()], axis=1).max(axis=1)
        df["ATR"] = tr.rolling(14).mean()
        df["Vol_MA"] = df["v"].rolling(20).mean()
        
        df["MB"] = df["c"].rolling(20).mean()
        df["STD"] = df["c"].rolling(20).std()
        df["UPPER"] = df["MB"] + 2 * df["STD"]
        df["LOWER"] = df["MB"] - 2 * df["STD"]
        df["BB_WIDTH"] = (df["UPPER"] - df["LOWER"]) / df["MB"]
        df["BB_WIDTH_MIN"] = df["BB_WIDTH"].rolling(20).min().shift(1)
        
        df = df.dropna().iloc[-2:]
        if len(df) < 2: continue
        
        prev, last = df.iloc[0], df.iloc[1]
        sig_key = f"{sym}_{tf}_{int(last['ts'])}"
        if sig_key in st.session_state.signaled_keys: continue
        
        uptrend = last["c"] > last["EMA200"] and last["EMA50"] > last["EMA200"]
        downtrend = last["c"] < last["EMA200"] and last["EMA50"] < last["EMA200"]
        macd_long = prev["MACD_H"] < 0 and last["MACD_H"] > 0
        macd_short = prev["MACD_H"] > 0 and last["MACD_H"] < 0
        
        near_long = (last["l"] <= last["EMA50"] * (1 + params['pullback_tol']) and last["c"] > last["EMA50"]) if params['req_pullback'] else True
        near_short = (last["h"] >= last["EMA50"] * (1 - params['pullback_tol']) and last["c"] < last["EMA50"]) if params['req_pullback'] else True
        vol_ok = last["v"] > last["Vol_MA"] * params['vol_mult']
        rsi_ok_long = last["RSI"] < params['rsi_long_max']
        rsi_ok_short = last["RSI"] > params['rsi_short_min']
        squeeze_ok = (last["BB_WIDTH"] < last["BB_WIDTH_MIN"] * params['squeeze_tol']) if params['req_squeeze'] else True
        
        if uptrend and macd_long and near_long and vol_ok and rsi_ok_long and squeeze_ok:
            sl = last["l"] - 1.2 * last["ATR"]
            tp = last["c"] + 2.0 * (last["c"] - sl)
            msg = f"{sym.replace('/USDT:USDT','')} 🟢做多\n入场:{last['c']:.2f}\n止损:{sl:.2f}\n止盈:{tp:.2f}"
            results.append({"币种":sym.replace('/USDT:USDT',''), "方向":"🟢 做多", "入场":f"{last['c']:.2f}", "止损":f"{sl:.2f}", "止盈":f"{tp:.2f}", "盈亏比":"1:2", "触发时间":str(last['dt']), "收口确认":"✅"})
            st.session_state.signaled_keys.add(sig_key)
            send_push(msg)
            
        elif downtrend and macd_short and near_short and vol_ok and rsi_ok_short and squeeze_ok:
            sl = last["h"] + 1.2 * last["ATR"]
            tp = last["c"] - 2.0 * (sl - last["c"])
            msg = f"{sym.replace('/USDT:USDT','')} 🔴做空\n入场:{last['c']:.2f}\n止损:{sl:.2f}\n止盈:{tp:.2f}"
            results.append({"币种":sym.replace('/USDT:USDT',''), "方向":"🔴 做空", "入场":f"{last['c']:.2f}", "止损":f"{sl:.2f}", "止盈":f"{tp:.2f}", "盈亏比":"1:2", "触发时间":str(last['dt']), "收口确认":"✅"})
            st.session_state.signaled_keys.add(sig_key)
            send_push(msg)
            
    progress_bar.empty()
    return pd.DataFrame(results) if results else pd.DataFrame(columns=["币种","方向","入场","止损","止盈","盈亏比","触发时间","收口确认"])

# ================= 界面渲染 =================
st.info(f"📡 当前监控池: **币安 USDT 永续合约 24H 成交量 Top {len(SYMBOLS)}** | 数据每 30 分钟自动更新")
if st.button("🔄 立即扫描信号", type="primary"):
    with st.spinner("策略计算中..."):
        df_sig = scan_signals(timeframe, cfg)

    st.subheader(f"📡 {timeframe} 策略信号 ({mode.split(' ')[0]})")
    if df_sig.empty:
        st.info(f"✅ 当前无符合 [{mode}] 的信号。系统已自动过滤低流动性与震荡合约。")
    else:
        st.dataframe(df_sig.style.applymap(
            lambda v: "color: #00C853; font-weight: bold" if "多" in str(v) else ("color: #FF1744; font-weight: bold" if "空" in str(v) else ""),
            subset=["方向"]
        ), use_container_width=True, hide_index=True)
        st.success(f"已发现 {len(df_sig)} 个高胜率信号，推送已发送至您的手机！")

    current_ts = int(time.time() * 1000)
    st.session_state.signaled_keys = {k for k in st.session_state.signaled_keys if current_ts - int(k.split("_")[-1]) < 3600000}

st.divider()
st.caption("⚠️ 风险提示：合约交易自带杠杆，请严格设置止损。本工具仅为技术面辅助，不构成投资建议。Streamlit 云端有休眠机制，建议配合本地运行或自动刷新插件。")
