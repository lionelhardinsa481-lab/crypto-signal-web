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
CACHE_FILE = "/tmp/signal_cache.json" 
PORTFOLIO_FILE = "/tmp/portfolio.json"
HISTORY_FILE = "/tmp/history.json"
# ==========================================

st.set_page_config(page_title="Crypto 实战信号监控", layout="wide", page_icon="📈")
st.title("📊 币安/OKX 合约 Top100 实战信号监控")
st.caption("🔥 自动优选线路 | 独立双策略 | 模拟盘实时追踪")

# ================= 数据持久化辅助 =================
def load_json(filepath, default):
    if os.path.exists(filepath):
        try:
            with open(filepath, "r") as f: return json.load(f)
        except: return default
    return default

def save_json(filepath, data):
    try:
        with open(filepath, "w") as f: json.dump(data, f)
    except: pass

# ================= 模拟盘状态管理 =================
# 初始化时加载
if "portfolio" not in st.session_state:
    st.session_state.portfolio = load_json(PORTFOLIO_FILE, [])
if "history" not in st.session_state:
    st.session_state.history = load_json(HISTORY_FILE, [])
if "cache_data" not in st.session_state:
    st.session_state.cache_data = load_json(CACHE_FILE, {})

# 清理过期缓存 (1小时)
now = time.time()
st.session_state.cache_data = {k: v for k, v in st.session_state.cache_data.items() if now - v < 3600}

def save_portfolio_state():
    save_json(PORTFOLIO_FILE, st.session_state.portfolio)
    save_json(HISTORY_FILE, st.session_state.history)
    save_json(CACHE_FILE, st.session_state.cache_data)

# 强制清理旧数据按钮 (如果报错可以使用)
if st.sidebar.button("🗑️ 重置模拟盘数据", type="secondary"):
    st.session_state.portfolio = []
    st.session_state.history = []
    st.session_state.cache_data = {}
    save_portfolio_state()
    st.experimental_rerun()

# ================= 智能交易所连接 =================
@st.cache_resource
def get_smart_exchange():
    try:
        ex_okx = ccxt.okx({"options": {"defaultType": "swap"}, "enableRateLimit": True, "timeout": 10000})
        ex_okx.fetch_ticker("BTC/USDT:USDT")
        return ex_okx, "OKX (欧易)"
    except Exception: pass
        
    try:
        ex_binance = ccxt.binance({"options": {"defaultType": "swap"}, "enableRateLimit": True, "timeout": 10000,
            "urls": {"api": {"public": "https://api.binance.vision", "private": "https://api.binance.vision"}}})
        ex_binance.fetch_ticker("BTC/USDT:USDT")
        return ex_binance, "Binance (备用线路)"
    except Exception:
        return None, "连接失败"

EXCHANGE, EXCHANGE_NAME = get_smart_exchange()

# ================= 核心币种列表 =================
CORE_SYMBOLS = [
    "BTC/USDT:USDT", "ETH/USDT:USDT", "BNB/USDT:USDT", "SOL/USDT:USDT", "XRP/USDT:USDT",
    "DOGE/USDT:USDT", "ADA/USDT:USDT", "TRX/USDT:USDT", "AVAX/USDT:USDT", "LINK/USDT:USDT",
    "TON/USDT:USDT", "DOT/USDT:USDT", "MATIC/USDT:USDT", "SHIB/USDT:USDT", "LTC/USDT:USDT",
    "UNI/USDT:USDT", "ATOM/USDT:USDT", "ETC/USDT:USDT", "FIL/USDT:USDT", "AAVE/USDT:USDT",
    "NEAR/USDT:USDT", "OP/USDT:USDT", "APT/USDT:USDT", "ARB/USDT:USDT", "STX/USDT:USDT",
    "WIF/USDT:USDT", "PEPE/USDT:USDT", "FET/USDT:USDT", "RENDER/USDT:USDT", "IMX/USDT:USMT",
    "SUI/USDT:USDT", "SEI/USDT:USDT", "TIA/USDT:USDT", "INJ/USDT:USDT", "RUNE/USDT:USDT",
    "FTM/USDT:USDT", "ALGO/USDT:USDT", "SAND/USDT:USDT", "MANA/USDT:USDT", "AXS/USDT:USDT",
    "GALA/USDT:USDT", "EOS/USDT:USDT", "XLM/USDT:USDT", "VET/USDT:USDT", "THETA/USDT:USDT",
    "ICP/USDT:USDT", "EGLD/USDT:USDT", "FLOW/USDT:USDT", "CHZ/USDT:USDT", "ENJ/USDT:USDT",
    "JUP/USDT:USDT", "W/USDT:USDT", "TAO/USDT:USDT", "AR/USDT:USDT", "BLUR/USDT:USDT",
    "SSV/USDT:USDT", "LDO/USDT:USDT", "GRT/USDT:USDT", "PENDLE/USDT:USDT", "PYTH/USDT:USDT",
    "JTO/USDT:USDT", "NOT/USDT:USDT", "BONK/USDT:USDT", "FLOKI/USDT:USDT", "BOME/USDT:USDT",
    "ORDI/USDT:USDT", "SATS/USDT:USDT", "ACE/USDT:USDT", "NFP/USDT:USDT", "AI/USDT:USDT",
    "ALT/USDT:USDT", "JASMY/USDT:USDT", "ONDO/USDT:USDT", "STRK/USDT:USDT", "MEME/USDT:USMT",
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
SYMBOLS = CORE_SYMBOLS

# ================= 辅助函数 =================
def fmt_price(price):
    if price < 0.01: return f"{price:.6f}"
    if price < 1: return f"{price:.4f}"
    if price < 100: return f"{price:.2f}"
    return f"{price:.1f}"

def send_push(text):
    webhooks = [w for w in [DINGTALK_WEBHOOK, WECOM_WEBHOOK] if w and "在此粘贴" not in w]
    for wh in webhooks:
        try: requests.post(wh, json={"msgtype":"text","text":{"content":f"【Crypto-Sim】\n{text}"}}, timeout=5)
        except: pass

# ================= 侧边栏配置 =================
st.sidebar.header("⚙️ 策略参数")
tf = st.sidebar.selectbox("🕰️ K线周期", ["5m", "15m", "1h", "4h"], index=1)
enable_trend = st.sidebar.checkbox("📈 启用趋势策略", value=True)
enable_pump = st.sidebar.checkbox("🚀 启用异动策略", value=True)

# 增加一个开关：是否允许做空 (很多人只喜欢做多)
allow_short = st.sidebar.checkbox("📉 允许做空 (趋势策略)", value=True)

TF_THRESHOLDS = {
    "5m": {"pump_pct": 0.03, "vol_mult": 3.0, "trend_vol": 1.5},
    "15m": {"pump_pct": 0.04, "vol_mult": 2.5, "trend_vol": 1.5},
    "1h": {"pump_pct": 0.06, "vol_mult": 2.0, "trend_vol": 1.3},
    "4h": {"pump_pct": 0.08, "vol_mult": 1.8, "trend_vol": 1.2}
}
cfg = TF_THRESHOLDS[tf]

# ================= 核心扫描与模拟盘逻辑 =================
def get_ohlcv(sym, tf, limit=250):
    try:
        if not EXCHANGE: return pd.DataFrame()
        ohlcv = EXCHANGE.fetch_ohlcv(sym, timeframe=tf, limit=limit)
        if not ohlcv: return pd.DataFrame()
        return pd.DataFrame(ohlcv, columns=["ts","o","h","l","c","v"])
    except Exception: return pd.DataFrame()

def scan_and_manage_portfolio(tf, t_cfg, trend_on, pump_on, short_allowed):
    new_signals = []
    logs = {"total":0, "trend_pass":0, "pump_pass":0}
    
    if not EXCHANGE: return pd.DataFrame(), logs

    with st.status(f"正在扫描 & 管理模拟盘...", expanded=False) as status:
        # 合并所有需要扫描的币种：监控池 + 当前持仓
        portfolio_symbols = [p['symbol'] + "/USDT:USDT" for p in st.session_state.portfolio]
        scan_list = list(set(SYMBOLS + portfolio_symbols))
        
        # 标记哪些持仓已经被处理过（用于平仓逻辑）
        processed_positions = set()

        for i, sym in enumerate(scan_list):
            if i % 10 == 0: status.update(label=f"进度: {i}/{len(scan_list)}")
            
            df = get_ohlcv(sym, tf, 250)
            if df.empty or len(df) < 60: continue
            
            logs["total"] += 1
            last = df.iloc[-1]
            prev = df.iloc[-2]
            c, h, l = float(last["c"]), float(last["h"]), float(last["l"])
            sym_name = sym.split("/")[0]
            candle_ts = int(last["ts"])
            
            # --- A. 检查持仓是否触发平仓 ---
            # 遍历当前所有持仓
            for p in list(st.session_state.portfolio): # list() 拷贝一份防止遍历时修改报错
                if p['symbol'] == sym_name and p['status'] == 'open':
                    processed_positions.add(sym_name)
                    exit_price = None
                    reason = ""
                    
                    # 检查止损/止盈 (使用 High/Low 检查是否穿过)
                    if p['direction'] == 'long':
                        if l <= p['sl']: exit_price, reason = p['sl'], "触及止损"
                        elif h >= p['tp']: exit_price, reason = p['tp'], "触及止盈"
                    else: # short
                        if h >= p['sl']: exit_price, reason = p['sl'], "触及止损"
                        elif l <= p['tp']: exit_price, reason = p['tp'], "触及止盈"
                    
                    if exit_price:
                        # 计算盈亏
                        if p['direction'] == 'long':
                            pnl_pct = (exit_price - p['entry']) / p['entry']
                        else:
                            pnl_pct = (p['entry'] - exit_price) / p['entry']
                        
                        record = {
                            "symbol": sym_name, "direction": p['direction'], 
                            "entry": p['entry'], "exit": exit_price, 
                            "pnl_pct": pnl_pct, "reason": reason,
                            "time": time.strftime("%Y-%m-%d %H:%M")
                        }
                        st.session_state.history.insert(0, record)
                        
                        # 从持仓中移除
                        st.session_state.portfolio.remove(p)
                        
                        # 推送平仓通知
                        emoji = "🎉" if pnl_pct > 0 else "💔"
                        msg = f"{emoji} {sym_name} {p['direction'].upper()} 平仓\n{reason}\n盈亏: {pnl_pct*100:.2f}%"
                        send_push(msg)
            
            # --- B. 寻找新信号 ---
            # 只有当这个币种没有持仓时，才开新仓
            has_position = any(p['symbol'] == sym_name for p in st.session_state.portfolio)
            
            if not has_position:
                # 计算指标
                df["EMA50"] = df["c"].ewm(span=50, adjust=False).mean()
                df["EMA200"] = df["c"].ewm(span=200, adjust=False).mean()
                e12, e26 = df["c"].ewm(span=12, adjust=False).mean(), df["c"].ewm(span=26, adjust=False).mean()
                dif, dea = e12-e26, (e12-e26).ewm(span=9, adjust=False).mean()
                df["MACD_H"] = 2*(dif-dea)
                df["Vol_MA"] = df["v"].rolling(20).mean()
                df["HH20"] = df["h"].rolling(20).max().shift(1)
                df["Change"] = df["c"].pct_change()
                
                df_clean = df.dropna().iloc[-2:]
                if len(df_clean) >= 2:
                    prev_row, last_row = df_clean.iloc[0], df_clean.iloc[1]
                    
                    # 过滤微小波动 (增加最小波动要求，防止震荡市频繁开单)
                    volatility = (float(last_row["h"]) - float(last_row["l"])) / float(last_row["c"])
                    # 5m周期要求波动至少 0.8%，15m 要求 1%
                    min_vol_req = 0.008 if tf == "5m" else 0.01
                    
                    if volatility >= min_vol_req:
                        
                        # 趋势策略
                        if trend_on:
                            key_t = f"T_{sym_name}_{tf}_{candle_ts}"
                            if key_t not in st.session_state.cache_data:
                                c_val, ema50, ema200 = float(last_row["c"]), float(last_row["EMA50"]), float(last_row["EMA200"])
                                macd_curr, macd_prev = float(last_row["MACD_H"]), float(prev_row["MACD_H"])
                                vol_curr, vol_ma = float(last_row["v"]), float(last_row["Vol_MA"])
                                h_val, l_val = float(last_row["h"]), float(last_row["l"])
                                
                                uptrend = c_val > ema200 and ema50 > ema200
                                macd_cross = macd_prev < 0 and macd_curr > 0
                                macd_dead_cross = macd_prev > 0 and macd_curr < 0
                                vol_ok = vol_curr > vol_ma * t_cfg["trend_vol"]
                                
                                # 做多逻辑
                                if uptrend and macd_cross and vol_ok:
                                    # 优化止损：至少要有 1% 的止损空间，或者基于 ATR
                                    sl_dist = max(l_val * 0.01, 1.5 * (h_val - l_val))
                                    sl = l_val - sl_dist
                                    tp = c_val + 2.0 * (c_val - sl)
                                    vol_ratio = vol_curr / vol_ma
                                    
                                    new_signals.append({"币种":sym_name, "策略":"📈 趋势", "方向":"🟢 多", "入场":fmt_price(c_val), "止损":fmt_price(sl), "止盈":fmt_price(tp)})
                                    
                                    st.session_state.portfolio.append({
                                        "symbol": sym_name, "direction": "long", 
                                        "entry": c_val, "sl": sl, "tp": tp, 
                                        "time": time.strftime("%H:%M"), "status": "open"
                                    })
                                    
                                    st.session_state.cache_data[key_t] = time.time()
                                    send_push(f"{sym_name} 🟢趋势多\n逻辑: 均线多头+MACD金叉+放量({vol_ratio:.1f}x)\n入:{fmt_price(c_val)} 损:{fmt_price(sl)} 盈:{fmt_price(tp)}")
                                    logs["trend_pass"] += 1
                                    
                                # 做空逻辑 (只有允许做空且满足条件)
                                elif short_allowed and (not uptrend) and macd_dead_cross and vol_ok:
                                    sl_dist = max(h_val * 0.01, 1.5 * (h_val - l_val))
                                    sl = h_val + sl_dist
                                    tp = c_val - 2.0 * (sl - c_val)
                                    vol_ratio = vol_curr / vol_ma
                                    
                                    new_signals.append({"币种":sym_name, "策略":"📈 趋势", "方向":"🔴 空", "入场":fmt_price(c_val), "止损":fmt_price(sl), "止盈":fmt_price(tp)})
                                    
                                    st.session_state.portfolio.append({
                                        "symbol": sym_name, "direction": "short", 
                                        "entry": c_val, "sl": sl, "tp": tp, 
                                        "time": time.strftime("%H:%M"), "status": "open"
                                    })
                                    
                                    st.session_state.cache_data[key_t] = time.time()
                                    send_push(f"{sym_name} 🔴趋势空\n逻辑: 均线空头+MACD死叉+放量({vol_ratio:.1f}x)\n入:{fmt_price(c_val)} 损:{fmt_price(sl)} 盈:{fmt_price(tp)}")
                                    logs["trend_pass"] += 1

                        # 异动策略 (只做多)
                        if pump_on:
                            key_p = f"P_{sym_name}_{tf}_{candle_ts}"
                            if key_p not in st.session_state.cache_data:
                                c_val = float(last_row["c"])
                                hh20 = float(last_row["HH20"])
                                vol_curr, vol_ma = float(last_row["v"]), float(last_row["Vol_MA"])
                                change = float(last_row["Change"])
                                l_val = float(last_row["l"])
                                
                                breakout = c_val > hh20
                                vol_surge = vol_curr > vol_ma * t_cfg["vol_mult"]
                                pump_ok = change > t_cfg["pump_pct"]
                                
                                if breakout and vol_surge and pump_ok:
                                    sl = l_val * 0.92 # 8% 止损
                                    tp = c_val * 1.15 # 15% 止盈
                                    vol_ratio = vol_curr / vol_ma
                                    
                                    new_signals.append({"币种":sym_name, "策略":"🚀 异动", "方向":"🚀 突破", "入场":fmt_price(c_val), "止损":fmt_price(sl), "止盈":fmt_price(tp)})
                                    
                                    st.session_state.portfolio.append({
                                        "symbol": sym_name, "direction": "long", 
                                        "entry": c_val, "sl": sl, "tp": tp, 
                                        "time": time.strftime("%H:%M"), "status": "open"
                                    })
                                    
                                    st.session_state.cache_data[key_p] = time.time()
                                    send_push(f"{sym_name} 🚀异动突破\n逻辑: 突破20日高点+巨量({vol_ratio:.1f}x)+涨幅({change*100:.1f}%)\n现:{fmt_price(c_val)} 损:{fmt_price(sl)} 盈:{fmt_price(tp)}")
                                    logs["pump_pass"] += 1

        status.update(label="扫描完成!", state="complete")

    save_portfolio_state()
    return pd.DataFrame(new_signals) if new_signals else pd.DataFrame(columns=["币种","策略","方向","入场","止损","止盈"]), logs

# ================= 界面渲染 =================
if EXCHANGE:
    st.info(f"📡 监控池: {len(SYMBOLS)} 合约 | 数据源: {EXCHANGE_NAME}")
    
    df_sig, log_data = scan_and_manage_portfolio(tf, cfg, enable_trend, enable_pump, allow_short)

    # --- 模拟盘战绩看板 ---
    st.subheader("💰 模拟盘实时战绩")
    col1, col2, col3, col4 = st.columns(4)
    
    wins = [h for h in st.session_state.history if h['pnl_pct'] > 0]
    losses = [h for h in st.session_state.history if h['pnl_pct'] <= 0]
    total_pnl = sum(h['pnl_pct'] for h in st.session_state.history)
    win_rate = len(wins) / len(st.session_state.history) if st.session_state.history else 0
    
    col1.metric("总交易次数", len(st.session_state.history))
    col2.metric("胜率", f"{win_rate*100:.1f}%")
    col3.metric("总收益率", f"{total_pnl*100:.2f}%", delta=f"{total_pnl*100:.2f}%")
    col4.metric("当前持仓", f"{len(st.session_state.portfolio)} 单")
    
    # 显示持仓列表
    if st.session_state.portfolio:
        st.markdown("📋 **当前持仓**")
        pos_df = pd.DataFrame(st.session_state.portfolio)
        if not pos_df.empty:
            pos_df['方向'] = pos_df['direction'].apply(lambda x: "🟢 多" if x=="long" else "🔴 空")
            # 格式化价格
            pos_df['entry_fmt'] = pos_df['entry'].apply(fmt_price)
            pos_df['sl_fmt'] = pos_df['sl'].apply(fmt_price)
            pos_df['tp_fmt'] = pos_df['tp'].apply(fmt_price)
            
            # 只显示需要的列
            display_cols = ['symbol', '方向', 'entry_fmt', 'sl_fmt', 'tp_fmt', 'time']
            # 重命名列名
            pos_df = pos_df.rename(columns={'entry_fmt': '入场价', 'sl_fmt': '止损价', 'tp_fmt': '止盈价', 'time': '开仓时间'})
            st.dataframe(pos_df[display_cols], use_container_width=True, hide_index=True)

    # 显示历史交易 (修复 KeyError)
    if st.session_state.history:
        st.markdown("📜 **历史平仓记录**")
        hist_df = pd.DataFrame(st.session_state.history)
        
        # 确保列存在
        if 'reason' not in hist_df.columns: hist_df['reason'] = "未知"
        if 'time' not in hist_df.columns: hist_df['time'] = "-"
        
        hist_df['结果'] = hist_df['pnl_pct'].apply(lambda x: " 盈利" if x > 0 else "💔 亏损")
        hist_df['盈亏'] = hist_df['pnl_pct'].apply(lambda x: f"{x*100:.2f}%")
        hist_df['方向'] = hist_df['direction'].apply(lambda x: "🟢 多" if x=="long" else "🔴 空")
        
        display_hist_cols = ['symbol', '方向', 'entry', 'exit', '盈亏', '结果', 'reason', 'time']
        # 过滤掉不存在的列
        safe_cols = [c for c in display_hist_cols if c in hist_df.columns]
        
        st.dataframe(hist_df[safe_cols].head(20), use_container_width=True, hide_index=True)

    # --- 信号看板 ---
    st.divider()
    st.subheader("📡 本轮新信号")
    if df_sig.empty:
        st.info("✅ 本轮无新信号。")
    else:
        st.dataframe(df_sig, use_container_width=True, hide_index=True)

else:
    st.error("❌ 无法连接交易所")

st.caption("⚠️ 模拟盘仅供测试策略，不构成投资建议。")
