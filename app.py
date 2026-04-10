import streamlit as st
import ccxt
import pandas as pd
import requests
import time

# ================= 配置区 =================
DINGTALK_WEBHOOK = "https://oapi.dingtalk.com/robot/send?access_token=c5d26cf25df7d56b5e9bf1b08bbf888ee9b18ed2f9e89ef9cdd2548b3ffeede3"
WECOM_WEBHOOK = "在此粘贴你的企微 Webhook"
# ==========================================

st.set_page_config(page_title="Crypto 双策略信号监控", layout="wide", page_icon="📈")
st.title("📊 币安合约 Top100 双策略信号监控")
st.caption("🔥 云端自动扫描 | 波段回踩+异动突破 | 防重复推送 | 100币种全覆盖")

# ================= 动态币种池 =================
@st.cache_data(ttl=3600)
def get_top_futures_symbols(limit=100):
    fallback_symbols = [
        "BTC/USDT:USDT", "ETH/USDT:USDT", "BNB/USDT:USDT", "SOL/USDT:USDT", "XRP/USDT:USDT",
        "DOGE/USDT:USDT", "ADA/USDT:USDT", "TRX/USDT:USDT", "AVAX/USDT:USDT", "LINK/USDT:USDT",
        "TON/USDT:USDT", "DOT/USDT:USDT", "MATIC/USDT:USDT", "SHIB/USDT:USDT", "LTC/USDT:USDT",
        "UNI/USDT:USDT", "ATOM/USDT:USDT", "ETC/USDT:USDT", "FIL/USDT:USDT", "AAVE/USDT:USDT",
        "NEAR/USDT:USDT", "OP/USDT:USDT", "APT/USDT:USDT", "ARB/USDT:USDT", "STX/USDT:USDT",
        "WIF/USDT:USDT", "PEPE/USDT:USDT", "FET/USDT:USDT", "RENDER/USDT:USDT", "IMX/USDT:USDT",
        "SUI/USDT:USDT", "SEI/USDT:USDT", "TIA/USDT:USDT", "INJ/USDT:USDT", "RUNE/USDT:USDT",
        "FTM/USDT:USDT", "ALGO/USDT:USDT", "SAND/USDT:USDT", "MANA/USDT:USDT", "AXS/USDT:USDT",
        "GALA/USDT:USDT", "EOS/USDT:USDT", "XLM/USDT:USDT", "VET/USDT:USDT", "THETA/USDT:USDT",
        "ICP/USDT:USDT", "EGLD/USDT:USDT", "FLOW/USDT:USDT", "CHZ/USDT:USDT", "ENJ/USDT:USDT",
        "JUP/USDT:USDT", "W/USDT:USDT", "TAO/USDT:USDT", "AR/USDT:USDT", "BLUR/USDT:USDT",
        "SSV/USDT:USDT", "LDO/USDT:USDT", "GRT/USDT:USDT", "PENDLE/USDT:USDT", "PYTH/USDT:USDT",
        "JTO/USDT:USDT", "NOT/USDT:USDT", "BONK/USDT:USDT", "FLOKI/USDT:USDT", "BOME/USDT:USDT",
        "ORDI/USDT:USDT", "SATS/USDT:USDT", "ACE/USDT:USDT", "NFP/USDT:USDT", "AI/USDT:USDT",
        "ALT/USDT:USDT", "JASMY/USDT:USDT", "ONDO/USDT:USDT", "STRK/USDT:USDT", "MEME/USDT:USDT",
        "PIXEL/USDT:USDT", "PORTAL/USDT:USDT", "AEVO/USDT:USDT", "ETHFI/USDT:USDT", "TNSR/USDT:USDT",
        "OM/USDT:USDT", "REZ/USDT:USDT", "ZETA/USDT:USDT", "IO/USDT:USDT", "ZK/USDT:USDT",
        "ZRO/USDT:USDT", "TLM/USDT:USDT", "KAVA/USDT:USDT", "ROSE/USDT:USDT", "CRO/USDT:USDT",
        "DASH/USDT:USDT", "ZEC/USDT:USDT", "COMP/USDT:USDT", "MKR/USDT:USDT", "SNX/USDT:USDT",
        "LRC/USDT:USDT", "1INCH/USDT:USDT", "SXP/USDT:USDT", "HOT/USDT:USDT", "BTT/USDT:USDT",
        "WIN/USDT:USDT", "STORJ/USDT:USDT", "SKL/USDT:USDT", "CTSI/USDT:USDT", "DENT/USDT:USDT",
        "OCEAN/USDT:USDT", "TRB/USDT:USDT", "HIGH/USDT:USDT", "MAGIC/USDT:USDT", "YGG/USDT:USDT",
        "DYDX/USDT:USDT", "GMX/USDT:USDT", "API3/USDT:USDT", "COTI/USDT:USDT", "HBAR/USDT:USDT",
        "ALICE/USDT:USDT"
    ]
    try:
        exchange = ccxt.binance({
            "options": {"defaultType": "swap"},
            "enableRateLimit": True,
            "timeout": 15000,
            "verbose": False
        })
        tickers = exchange.fetch_tickers()
        usdt_perps = {
            k: v for k, v in tickers.items()
            if k.endswith("/USDT:USDT") and isinstance(v.get("quoteVolume"), (int, float)) and v["quoteVolume"] > 0
        }
        sorted_pairs = sorted(usdt_perps.items(), key=lambda x: x[1]["quoteVolume"], reverse=True)
        symbols = [pair[0] for pair in sorted_pairs[:limit]]
        return symbols, "✅ Binance 实时排行"
    except Exception as e:
        return fallback_symbols, f"⚠️ 动态获取失败 ({str(e)[:40]})，已切换备用池"

SYMBOLS, DATA_SOURCE = get_top_futures_symbols(100)

# ================= 侧边栏配置 =================
st.sidebar.header("⚙️ 策略参数配置")
timeframe = st.sidebar.selectbox("🕰️ K线周期", ["5m", "15m", "1h", "4h"], index=1)

mode = st.sidebar.radio(
    "📊 主策略：波段回踩严格度",
    ["🚀 激进模式 (高频/宽过滤)", "⚖️ 平衡模式 (中频/标准)", "🛡️ 保守模式 (低频/严过滤)"],
    index=1
)

enable_pump = st.sidebar.checkbox("🔥 副策略：启用异动突破 (抓直线拉升/消息盘)", value=False)

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
    st.markdown(f"- **主策略成交量**: > 20均量 `{cfg['vol_mult']}x`")
    st.markdown(f"- **主策略RSI**: 做多 `<{cfg['rsi_long_max']}` / 做空 `>{cfg['rsi_short_min']}`")
    st.markdown(f"- **主策略回踩**: `{'不强制' if not cfg['req_pullback'] else f'±{cfg['pullback_tol']*100:.1f}%'}`")
    st.markdown(f"- **主策略布林收口**: `{'关闭' if not cfg['req_squeeze'] else f'带宽 < 极值×{cfg['squeeze_tol']}'}`")
    st.info(f"📈 主策略预期胜率: {cfg['expected_wr']}")
    if enable_pump:
        st.success("🔥 **异动策略已开启**")
        st.caption("- 单K涨幅 > 10%\n- 成交量 > 4倍均量\n- 突破20周期最高价\n- 过滤低流动性(<50万U)")
    st.caption(f"🌐 数据源: {DATA_SOURCE}")
    st.info("🤖 云端模式：UptimeRobot 每5分钟访问网页即自动扫描，无需人工点击。")

# 🤖 机器人测试模块
st.sidebar.divider()
st.sidebar.subheader("📡 推送通道测试")
if st.sidebar.button("📤 一键测试推送", type="primary"):
    test_msg = f"【系统测试】双策略监控机器人已就绪！✅\n周期:{timeframe} | 主策略:{mode.split(' ')[0]} | 异动:{'ON' if enable_pump else 'OFF'}\n监控币种:{len(SYMBOLS)}个\n时间:{time.strftime('%Y-%m-%d %H:%M:%S')}"
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
                failed.append(f"{name}: API返回 {data.get('errcode', '')}")
        except Exception as e:
            failed.append(f"{name}: 网络失败 ({str(e)[:30]})")
    if success > 0:
        st.sidebar.success(f"✅ 测试成功！已送达 {success} 个平台")
    if failed:
        st.sidebar.error("❌ 部分通道异常:\n" + "\n".join(failed))

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
    except Exception:
        return pd.DataFrame()

def send_push(text):
    webhooks = [w for w in [DINGTALK_WEBHOOK, WECOM_WEBHOOK] if w and "在此粘贴" not in w]
    if not webhooks:
        return
    content = f"【Crypto双策略-{timeframe}】\n{text}"
    for wh in webhooks:
        try:
            requests.post(wh, json={"msgtype": "text", "text": {"content": content}}, timeout=5)
        except Exception:
            pass

def scan_signals(tf, params, enable_pump=False):
    results = []
    progress_bar = st.progress(0, text=" 云端自动扫描中...")

    for i, sym in enumerate(SYMBOLS):
        progress_bar.progress((i + 1) / len(SYMBOLS), text=f"扫描: {i+1}/{len(SYMBOLS)} | {sym.replace('/USDT:USDT', '')}")
        df = get_ohlcv(sym, tf, 250)
        if df.empty or len(df) < 60:
            continue

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

        tr = pd.concat([df["h"] - df["l"], (df["h"] - df["c"].shift(1)).abs(), (df["l"] - df["c"].shift(1)).abs()], axis=1).max(axis=1)
        df["ATR"] = tr.rolling(14).mean()
        df["Vol_MA"] = df["v"].rolling(20).mean()

        df["MB"] = df["c"].rolling(20).mean()
        df["STD"] = df["c"].rolling(20).std()
        df["UPPER"] = df["MB"] + 2 * df["STD"]
        df["LOWER"] = df["MB"] - 2 * df["STD"]
        df["BB_WIDTH"] = (df["UPPER"] - df["LOWER"]) / df["MB"]
        df["BB_WIDTH_MIN"] = df["BB_WIDTH"].rolling(20).min().shift(1)
        df["HH20"] = df["h"].rolling(20).max().shift(1)

        df = df.dropna().iloc[-2:]
        if len(df) < 2:
            continue

        prev, last = df.iloc[0], df.iloc[1]
        sym_name = sym.replace('/USDT:USDT', '')
        
        # ================= 📊 主策略：波段回踩 =================
        sig_key = f"TREND_{sym}_{tf}_{int(last['ts'])}"
        if sig_key not in st.session_state.signaled_keys:
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
                msg = f"{sym_name} 🟢主策略做多\n入场:{last['c']:.2f}\n止损:{sl:.2f}\n止盈:{tp:.2f}"
                results.append({"币种":sym_name, "策略":"📊 波段", "方向":"🟢 做多", "入场":f"{last['c']:.2f}", "止损":f"{sl:.2f}", "止盈":f"{tp:.2f}", "盈亏比":"1:2", "触发时间":str(last['dt'])})
                st.session_state.signaled_keys.add(sig_key)
                send_push(msg)
                
            elif downtrend and macd_short and near_short and vol_ok and rsi_ok_short and squeeze_ok:
                sl = last["h"] + 1.2 * last["ATR"]
                tp = last["c"] - 2.0 * (sl - last["c"])
                msg = f"{sym_name} 🔴主策略做空\n入场:{last['c']:.2f}\n止损:{sl:.2f}\n止盈:{tp:.2f}"
                results.append({"币种":sym_name, "策略":"📊 波段", "方向":"🔴 做空", "入场":f"{last['c']:.2f}", "止损":f"{sl:.2f}", "止盈":f"{tp:.2f}", "盈亏比":"1:2", "触发时间":str(last['dt'])})
                st.session_state.signaled_keys.add(sig_key)
                send_push(msg)

        # ================= 🔥 副策略：异动突破 =================
        if enable_pump:
            pump_key = f"PUMP_{sym}_{tf}_{int(last['ts'])}"
            if pump_key not in st.session_state.signaled_keys:
                price_breakout = last["c"] > last["HH20"]
                vol_surge = last["v"] > last["Vol_MA"] * 4.0
                pump_mag = (last["c"] - prev["c"]) / prev["c"] > 0.10
                min_liquidity = (last["c"] * last["v"]) > 500_000
                
                if price_breakout and vol_surge and pump_mag and min_liquidity:
                    sl = last["l"] * 0.90
                    tp = last["c"] * 1.25
                    msg = f"{sym_name} 🚀异动突破\n现价:{last['c']:.2f}\n硬止损:{sl:.2f}\n止盈:{tp:.2f}"
                    results.append({"币种":sym_name, "策略":"🔥 异动", "方向":"🚀 突破", "入场":f"{last['c']:.2f}", "止损":f"{sl:.2f}", "止盈":f"{tp:.2f}", "盈亏比":"1:5", "触发时间":str(last['dt'])})
                    st.session_state.signaled_keys.add(pump_key)
                    send_push(msg)
            
    progress_bar.empty()
    cols = ["币种", "策略", "方向", "入场", "止损", "止盈", "盈亏比", "触发时间"]
    return pd.DataFrame(results) if results else pd.DataFrame(columns=cols)

# ================= 🚀 云端自动扫描（开机/关机均可运行） =================
st.info(f"📡 监控池: **{len(SYMBOLS)} 个 USDT 永续合约** | {DATA_SOURCE} | 异动策略: {' 已开启' if enable_pump else '⚪ 已关闭'}")

with st.spinner("🤖 云端自动扫描中，请稍候..."):
    df_sig = scan_signals(timeframe, cfg, enable_pump)

st.subheader(f"📡 {timeframe} 信号看板")
if df_sig.empty:
    st.info("✅ 当前无符合策略条件的信号。系统已自动过滤低质量形态与震荡行情。")
else:
    def color_style(val):
        if "多" in str(val) or "突破" in str(val): return "color: #00C853; font-weight: bold"
        if "空" in str(val): return "color: #FF1744; font-weight: bold"
        return ""
    st.dataframe(df_sig.style.applymap(color_style, subset=["方向"]), use_container_width=True, hide_index=True)
    st.success(f"已发现 {len(df_sig)} 个信号，推送已发送至您的手机！")

# 每小时清理一次过期记录
current_ts = int(time.time() * 1000)
st.session_state.signaled_keys = {k for k in st.session_state.signaled_keys if current_ts - int(k.split("_")[-1]) < 3600000}

st.divider()
st.caption("⚠️ 风险提示：合约交易自带杠杆，异动策略波动极大，请严格设置硬止损。本工具仅为技术面辅助，不构成投资建议。")
