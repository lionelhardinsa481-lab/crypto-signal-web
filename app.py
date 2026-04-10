import streamlit as st
import ccxt
import pandas as pd
import requests
import time
import json
import os

# ================= 配置区 =================
DINGTALK_WEBHOOK = "https://oapi.dingtalk.com/robot/send?access_token=c5d26cf25df7d56b5e9bf1b08bbf888ee9b18ed2f9e89ef9cdd2548b3ffeede3"
WECOM_WEBHOOK = "在此粘贴你的企微 Webhook"
CACHE_FILE = "/tmp/signal_cache.json"  # 云端持久化去重文件
# ==========================================

st.set_page_config(page_title="Crypto 实战信号监控", layout="wide", page_icon="📈")
st.title("📊 币安合约 Top100 实战信号监控")
st.caption("🔥 实盘优化版 | 独立双策略 | 云端防重复 | 带自检日志")

# ================= 持久化去重模块 =================
def load_cache():
    if os.path.exists(CACHE_FILE):
        try:
            with open(CACHE_FILE, "r") as f: return json.load(f)
        except: return {}
    return {}

def save_cache(data):
    with open(CACHE_FILE, "w") as f: json.dump(data, f)

cache = load_cache()
# 清理1小时前的记录
now = time.time()
cache = {k: v for k, v in cache.items() if now - v < 3600}
save_cache(cache)

# ================= 动态币种池 =================
@st.cache_data(ttl=3600)
def get_top_futures_symbols(limit=100):
    fallback = [
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
        ex = ccxt.binance({"options": {"defaultType": "swap"}, "enableRateLimit": True, "timeout": 15000})
        tickers = ex.fetch_tickers()
        valid = {k: v for k, v in tickers.items() if k.endswith("/USDT:USDT") and isinstance(v.get("quoteVolume"), (int, float)) and v["quoteVolume"] > 0}
        sorted_p = sorted(valid.items(), key=lambda x: x[1]["quoteVolume"], reverse=True)
        return [p[0] for p in sorted_p[:limit]], "✅ Binance 实时排行"
    except Exception as e:
        return fallback, f"⚠️ API降级 ({str(e)[:30]})"

SYMBOLS, DATA_SRC = get_top_futures_symbols(100)

# ================= 侧边栏配置 =================
st.sidebar.header("⚙️ 策略参数")
tf = st.sidebar.selectbox("🕰️ K线周期", ["5m", "15m", "1h", "4h"], index=1)
enable_trend = st.sidebar.checkbox("📈 启用趋势策略", value=True)
enable_pump = st.sidebar.checkbox("🚀 启用异动策略", value=True)

# 动态阈值（按周期自适应）
TF_THRESHOLDS = {
    "5m": {"pump_pct": 0.03, "vol_mult": 3.0, "trend_vol": 1.5},
    "15m": {"pump_pct": 0.04, "vol_mult": 2.5, "trend_vol": 1.5},
    "1h": {"pump_pct": 0.06, "vol_mult": 2.0, "trend_vol": 1.3},
    "4h": {"pump_pct": 0.08, "vol_mult": 1.8, "trend_vol": 1.2}
}
cfg = TF_THRESHOLDS[tf]

with st.sidebar.expander("📊 实时阈值", expanded=True):
    st.markdown(f"- **异动涨幅要求**: `>{cfg['pump_pct']*100:.0f}%`")
    st.markdown(f"- **异动量能要求**: `>{cfg['vol_mult']}x` 均量")
    st.markdown(f"- **趋势量能要求**: `>{cfg['trend_vol']}x` 均量")
    st.caption("💡 阈值已按周期自动优化，避免过度过滤")

# 🧪 推送自检模块
st.sidebar.divider()
st.sidebar.subheader("🔍 通道自检")
if st.sidebar.button("🧪 模拟推送测试", type="primary"):
    test_msg = f"【通道正常】Crypto监控已激活\n周期:{tf} | 监控:{len(SYMBOLS)}币种\n时间:{time.strftime('%H:%M:%S')}"
    ok, err = 0, []
    for name, url in [("钉钉", DINGTALK_WEBHOOK), ("企微", WECOM_WEBHOOK)]:
        if "在此粘贴" in url or not url:
            err.append(f"{name}: 未配置")
            continue
        try:
            r = requests.post(url, json={"msgtype":"text","text":{"content":test_msg}}, timeout=5)
            if r.status_code==200 and r.json().get("errcode",-1)==0: ok+=1
            else: err.append(f"{name}: 返回 {r.json().get('errcode')}")
        except Exception as e:
            err.append(f"{name}: {str(e)[:20]}")
    if ok: st.sidebar.success(f"✅ 成功 {ok} 个通道")
    if err: st.sidebar.error("❌ 失败:\n"+"\n".join(err))

# 初始化防重复缓存
if "pushed_keys" not in st.session_state:
    st.session_state.pushed_keys = set(cache.keys())

# ================= 核心扫描函数 =================
@st.cache_data(ttl=15)
def get_ohlcv(sym, tf, limit=250):
    try:
        ex = ccxt.binance({"options": {"defaultType": "swap"}, "enableRateLimit": True, "timeout": 10000})
        return pd.DataFrame(ex.fetch_ohlcv(sym, timeframe=tf, limit=limit), columns=["ts","o","h","l","c","v"])
    except: return pd.DataFrame()

def send_push(text):
    webhooks = [w for w in [DINGTALK_WEBHOOK, WECOM_WEBHOOK] if w and "在此粘贴" not in w]
    for wh in webhooks:
        try: requests.post(wh, json={"msgtype":"text","text":{"content":f"【Crypto-{tf}】\n{text}"}}, timeout=5)
        except: pass

def scan(tf, t_cfg, trend_on, pump_on):
    results, logs = [], {"total":0, "trend_pass":0, "pump_pass":0, "blocked":0}
    progress = st.progress(0, text="扫描中...")
    
    for i, sym in enumerate(SYMBOLS):
        progress.progress((i+1)/len(SYMBOLS), text=f"{i+1}/{len(SYMBOLS)} | {sym.split('/')[0]}")
        df = get_ohlcv(sym, tf, 250)
        if df.empty or len(df)<60: continue
        logs["total"] += 1
        
        df["dt"] = pd.to_datetime(df["ts"], unit="ms")
        df["EMA50"] = df["c"].ewm(50).mean()
        df["EMA200"] = df["c"].ewm(200).mean()
        
        # MACD
        e12, e26 = df["c"].ewm(12).mean(), df["c"].ewm(26).mean()
        dif, dea = e12-e26, (e12-e26).ewm(9).mean()
        df["MACD_H"] = 2*(dif-dea)
        
        # 量能 & 前高
        df["Vol_MA"] = df["v"].rolling(20).mean()
        df["HH20"] = df["h"].rolling(20).max().shift(1)
        df["Change"] = df["c"].pct_change()
        
        df = df.dropna().iloc[-2:]
        if len(df)<2: continue
        
        prev, last = df.iloc[0], df.iloc[1]
        candle_ts = int(last["ts"])
        sym_name = sym.split("/")[0]
        
        # 📈 趋势策略 (独立判断)
        if trend_on:
            key_t = f"T_{sym_name}_{tf}_{candle_ts}"
            if key_t not in st.session_state.pushed_keys:
                uptrend = last["c"]>last["EMA200"] and last["EMA50"]>last["EMA200"]
                macd_cross = prev["MACD_H"]<0 and last["MACD_H"]>0
                vol_ok = last["v"] > last["Vol_MA"] * t_cfg["trend_vol"]
                
                if uptrend and macd_cross and vol_ok:
                    sl = last["l"] - 1.5* (last["h"]-last["l"])
                    tp = last["c"] + 2.0*(last["c"]-sl)
                    msg = f"{sym_name} 🟢趋势多\n入:{last['c']:.2f} 损:{sl:.2f} 盈:{tp:.2f}"
                    results.append({"币种":sym_name, "策略":"📈 趋势", "方向":"🟢 多", "入场":f"{last['c']:.2f}", "止损":f"{sl:.2f}", "止盈":f"{tp:.2f}", "时间":str(last['dt'])})
                    st.session_state.pushed_keys.add(key_t)
                    cache[key_t] = time.time()
                    send_push(msg)
                    logs["trend_pass"] += 1
                    
                elif not uptrend and prev["MACD_H"]>0 and last["MACD_H"]<0 and vol_ok:
                    sl = last["h"] + 1.5*(last["h"]-last["l"])
                    tp = last["c"] - 2.0*(sl-last["c"])
                    msg = f"{sym_name} 🔴趋势空\n入:{last['c']:.2f} 损:{sl:.2f} 盈:{tp:.2f}"
                    results.append({"币种":sym_name, "策略":"📈 趋势", "方向":"🔴 空", "入场":f"{last['c']:.2f}", "止损":f"{sl:.2f}", "止盈":f"{tp:.2f}", "时间":str(last['dt'])})
                    st.session_state.pushed_keys.add(key_t)
                    cache[key_t] = time.time()
                    send_push(msg)
                    logs["trend_pass"] += 1

        # 🚀 异动策略 (独立判断)
        if pump_on:
            key_p = f"P_{sym_name}_{tf}_{candle_ts}"
            if key_p not in st.session_state.pushed_keys:
                breakout = last["c"] > last["HH20"]
                vol_surge = last["v"] > last["Vol_MA"] * t_cfg["vol_mult"]
                pump_ok = last["Change"] > t_cfg["pump_pct"]
                
                if breakout and vol_surge and pump_ok:
                    sl = last["l"] * 0.92
                    tp = last["c"] * 1.15
                    msg = f"{sym_name} 🚀异动突破\n现:{last['c']:.2f} 损:{sl:.2f} 盈:{tp:.2f}"
                    results.append({"币种":sym_name, "策略":"🚀 异动", "方向":"🚀 突破", "入场":f"{last['c']:.2f}", "止损":f"{sl:.2f}", "止盈":f"{tp:.2f}", "时间":str(last['dt'])})
                    st.session_state.pushed_keys.add(key_p)
                    cache[key_p] = time.time()
                    send_push(msg)
                    logs["pump_pass"] += 1

    progress.empty()
    save_cache(cache)
    return pd.DataFrame(results) if results else pd.DataFrame(columns=["币种","策略","方向","入场","止损","止盈","时间"]), logs

# ================= 界面渲染 =================
st.info(f"📡 监控池: {len(SYMBOLS)} 合约 | {DATA_SRC} | 状态: {'🟢 运行中' if (enable_trend or enable_pump) else '⚪ 策略已关闭'}")

with st.spinner("🤖 扫描中..."):
    df_sig, log_data = scan(tf, cfg, enable_trend, enable_pump)

st.subheader("📡 信号看板")
if df_sig.empty:
    st.info("✅ 本轮无信号。系统已自动过滤低质量形态。")
else:
    st.dataframe(df_sig.style.applymap(
        lambda v: "color:#00C853;font-weight:bold" if "多" in str(v) or "突破" in str(v) else ("color:#FF1744;font-weight:bold" if "空" in str(v) else ""),
        subset=["方向"]
    ), use_container_width=True, hide_index=True)
    st.success(f"📲 已推送 {len(df_sig)} 个信号至手机")

# 🔍 调试日志（帮你排查为什么没信号）
with st.expander("📊 本轮扫描诊断日志 (点击展开)", expanded=False):
    st.write(f"- 总检测币种: `{log_data['total']}`")
    st.write(f"- 趋势策略触发: `{log_data['trend_pass']}` 次")
    st.write(f"- 异动策略触发: `{log_data['pump_pass']}` 次")
    st.write(f"- 防重复拦截: `{len(st.session_state.pushed_keys) - log_data['trend_pass'] - log_data['pump_pass']}` 次")
    if log_data['total'] == 0:
        st.warning("⚠️ 未获取到任何K线数据，请检查网络或币安API状态")
    elif log_data['trend_pass'] == 0 and log_data['pump_pass'] == 0:
        st.info("💡 当前市场处于震荡/无突破状态，符合过滤逻辑。建议切至 5m/15m 周期提高频率。")

st.divider()
st.caption("⚠️ 风险提示：合约杠杆交易风险极高，本工具仅为技术面辅助。请严格设置止损，切勿重仓扛单。")
