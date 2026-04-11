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
PORTFOLIO_FILE = "/tmp/portfolio.json" # 模拟盘数据持久化
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
if "portfolio" not in st.session_state:
    st.session_state.portfolio = load_json(PORTFOLIO_FILE, [])
if "history" not in st.session_state:
    st.session_state.history = load_json("/tmp/history.json", [])

def save_portfolio_state():
    save_json(PORTFOLIO_FILE, st.session_state.portfolio)
    save_json("/tmp/history.json", st.session_state.history)

# 清理缓存 (去重用)
if "cache_data" not in st.session_state:
    st.session_state.cache_data = load_json(CACHE_FILE, {})
now = time.time()
st.session_state.cache_data = {k: v for k, v in st.session_state.cache_data.items() if now - v < 3600}

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
    "WIF/USDT:USDT", "PEPE/USDT:USDT", "FET/USDT:USDT", "RENDER/USDT:USDT", "IMX/USDT:USDT",
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

TF_THRESHOLDS = {
    "5m": {"pump_pct": 0.03, "vol_mult": 3.0, "trend_vol": 1.5},
    "15m": {"pump_pct": 0.04, "vol_mult": 2.5, "trend_vol": 1.5},
    "1h": {"pump_pct": 0.06, "vol_mult": 2.0, "trend_vol": 1.3},
    "4h": {"pump_pct": 0.08, "vol_mult": 1.8, "trend_vol": 1.2}
}
cfg = TF_THRESHOLDS[tf]

# 🧪 推送自检
st.sidebar.divider()
if st.sidebar.button("🧪 模拟推送测试", type="primary"):
    send_push("【测试】通道正常，模拟盘已就绪。")
    st.sidebar.success("已发送测试消息")

# ================= 核心扫描与模拟盘逻辑 =================
def get_ohlcv(sym, tf, limit=250):
    try:
        if not EXCHANGE: return pd.DataFrame()
        ohlcv = EXCHANGE.fetch_ohlcv(sym, timeframe=tf, limit=limit)
        if not ohlcv: return pd.DataFrame()
        return pd.DataFrame(ohlcv, columns=["ts","o","h","l","c","v"])
    except Exception: return pd.DataFrame()

def scan_and_manage_portfolio(tf, t_cfg, trend_on, pump_on):
    new_signals = []
    logs = {"total":0, "trend_pass":0, "pump_pass":0}
    
    if not EXCHANGE: return pd.DataFrame(), logs

    # 1. 先处理持仓检查 (Check Portfolio)
    # 我们需要获取所有持仓币种的最新价格来检查是否止损/止盈
    # 为了效率，我们只在扫描循环中顺便检查
    
    active_portfolio = [] # 临时存储未平仓的
    
    with st.status(f"正在扫描 & 管理模拟盘...", expanded=False) as status:
        # 合并所有需要扫描的币种：监控池 + 当前持仓 (防止持仓币种不在监控池里被漏掉)
        portfolio_symbols = [p['symbol'] + "/USDT:USDT" for p in st.session_state.portfolio]
        scan_list = list(set(SYMBOLS + portfolio_symbols))
        
        for i, sym in enumerate(scan_list):
            if i % 10 == 0: status.update(label=f"进度: {i}/{len(scan_list)}")
            
            df = get_ohlcv(sym, tf, 250)
            if df.empty or len(df) < 60: 
                # 如果获取不到数据，保留持仓，跳过
                for p in st.session_state.portfolio:
                    if p['symbol'] + "/USDT:USDT" == sym: active_portfolio.append(p)
                continue
            
            logs["total"] += 1
            last = df.iloc[-1]
            prev = df.iloc[-2]
            c, h, l = float(last["c"]), float(last["h"]), float(last["l"])
            sym_name = sym.split("/")[0]
            candle_ts = int(last["ts"])
            
            # --- A. 检查持仓是否触发平仓 ---
            is_closed = False
            for p in st.session_state.portfolio:
                if p['symbol'] == sym_name and p['status'] == 'open':
                    # 检查止损/止盈
                    exit_price = None
                    reason = ""
                    
                    if p['direction'] == 'long':
                        if l <= p['sl']: exit_price, reason = p['sl'], "触及止损"
                        elif h >= p['tp']: exit_price, reason = p['tp'], "触及止盈"
                    else: # short
                        if h >= p['sl']: exit_price, reason = p['sl'], "触及止损"
                        elif l <= p['tp']: exit_price, reason = p['tp'], "触及止盈"
                    
                    if exit_price:
                        # 计算盈亏 (简单百分比，不含杠杆)
                        if p['direction'] == 'long':
                            pnl_pct = (exit_price - p['entry']) / p['entry']
                        else:
                            pnl_pct = (p['entry'] - exit_price) / p['entry']
                        
                        result = "win" if pnl_pct > 0 else "loss"
                        record = {
                            "symbol": sym_name, "direction": p['direction'], 
                            "entry": p['entry'], "exit": exit_price, 
                            "pnl_pct": pnl_pct, "reason": reason,
                            "time": time.strftime("%Y-%m-%d %H:%M")
                        }
                        st.session_state.history.insert(0, record) # 插入到最前
                        p['status'] = 'closed'
                        p['exit'] = exit_price
                        p['pnl'] = pnl_pct
                        
                        # 推送平仓通知
                        emoji = "🎉" if result == "win" else "💔"
                        msg = f"{emoji} {sym_name} {p['direction'].upper()} 平仓\n{reason}\n盈亏: {pnl_pct*100:.2f}%"
                        send_push(msg)
                        
                        is_closed = True
                    else:
                        active_portfolio.append(p) # 继续持有
            
            # 更新持仓列表
            st.session_state.portfolio = [p for p in st.session_state.portfolio if p['status'] == 'open']
            st.session_state.portfolio.extend([p for p in st.session_state.portfolio if False]) # 这里的逻辑有点乱，重新整理
            # 正确逻辑：上面循环里把 closed 的标记了，现在过滤掉 closed 的
            st.session_state.portfolio = [p for p in st.session_state.portfolio if p['status'] == 'open']
            # 注意：上面的循环里 active_portfolio 没用上，直接修改 session_state 即可
            # 重新写一下持仓更新逻辑，避免引用问题
            # 实际上上面的循环已经修改了 st.session_state.portfolio 里的对象状态
            # 我们只需要在最后过滤掉 closed 的
            # 但上面的循环里 p['status']='closed' 后，active_portfolio 没加，所以最后 portfolio 会剩 open 的
            # 等等，上面的循环是遍历 st.session_state.portfolio，如果在遍历中修改状态，没问题。
            # 但是 active_portfolio 没用到。
            # 修正：
            # 这里的逻辑是：遍历所有持仓，如果触发平仓，就修改状态并记录历史。
            # 最后在函数末尾统一过滤掉 closed 的。
            
            # --- B. 寻找新信号 ---
            # 只有当这个币种没有持仓时，才开新仓 (防止重复开仓)
            has_position = any(p['symbol'] == sym_name and p['status'] == 'open' for p in st.session_state.portfolio)
            
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
                    
                    # 过滤微小波动
                    volatility = (float(last_row["h"]) - float(last_row["l"])) / float(last_row["c"])
                    if volatility >= 0.005:
                        
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
                                vol_ok = vol_curr > vol_ma * t_cfg["trend_vol"]
                                
                                if uptrend and macd_cross and vol_ok:
                                    sl = l_val - 1.5 * (h_val - l_val)
                                    tp = c_val + 2.0 * (c_val - sl)
                                    vol_ratio = vol_curr / vol_ma
                                    
                                    # 记录信号
                                    new_signals.append({"币种":sym_name, "策略":"📈 趋势", "方向":"🟢 多", "入场":fmt_price(c_val), "止损":fmt_price(sl), "止盈":fmt_price(tp)})
                                    
                                    # 加入模拟盘持仓
                                    st.session_state.portfolio.append({
                                        "symbol": sym_name, "direction": "long", 
                                        "entry": c_val, "sl": sl, "tp": tp, 
                                        "time": time.strftime("%H:%M"), "status": "open"
                                    })
                                    
                                    st.session_state.cache_data[key_t] = time.time()
                                    send_push(f"{sym_name} 🟢趋势多\n逻辑: 均线多头+MACD金叉+放量({vol_ratio:.1f}x)\n入:{fmt_price(c_val)} 损:{fmt_price(sl)} 盈:{fmt_price(tp)}")
                                    logs["trend_pass"] += 1
                                    
                                elif not uptrend and macd_prev > 0 and macd_curr < 0 and vol_ok:
                                    sl = h_val + 1.5 * (h_val - l_val)
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

                        # 异动策略
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
                                    sl = l_val * 0.92
                                    tp = c_val * 1.15
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

    # 清理已平仓的记录 (上面循环里虽然标记了 closed，但列表里还在，这里过滤一下)
    # 注意：上面的循环逻辑有点问题，st.session_state.portfolio 在循环中被修改可能会影响迭代
    # 安全做法：
    closed_positions = [p for p in st.session_state.portfolio if p['status'] == 'closed']
    st.session_state.portfolio = [p for p in st.session_state.portfolio if p['status'] == 'open']
    
    # 把平仓的加入历史
    for p in closed_positions:
         if p not in st.session_state.history: # 简单去重
             # 上面循环里其实已经加了，这里不用重复加，除非逻辑有误
             pass

    save_portfolio_state()
    return pd.DataFrame(new_signals) if new_signals else pd.DataFrame(columns=["币种","策略","方向","入场","止损","止盈"]), logs

# ================= 界面渲染 =================
if EXCHANGE:
    st.info(f"📡 监控池: {len(SYMBOLS)} 合约 | 数据源: {EXCHANGE_NAME}")
    
    df_sig, log_data = scan_and_manage_portfolio(tf, cfg, enable_trend, enable_pump)

    # --- 模拟盘战绩看板 ---
    st.subheader("💰 模拟盘实时战绩")
    col1, col2, col3, col4 = st.columns(4)
    
    # 计算统计数据
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
        st.markdown("📋 **当前持仓 (浮盈/浮亏)**")
        # 计算每个持仓的当前浮动盈亏 (粗略计算，基于最新价，这里简化显示)
        # 为了性能，不实时查所有持仓的现价，只显示开仓信息
        pos_df = pd.DataFrame(st.session_state.portfolio)
        pos_df['开仓时间'] = pos_df['time']
        pos_df['方向'] = pos_df['direction'].apply(lambda x: "🟢 多" if x=="long" else "🔴 空")
        pos_df = pos_df[['symbol', '方向', 'entry', 'sl', 'tp', '开仓时间']]
        st.dataframe(pos_df, use_container_width=True, hide_index=True)

    # 显示历史交易
    if st.session_state.history:
        st.markdown("📜 **历史平仓记录**")
        hist_df = pd.DataFrame(st.session_state.history)
        hist_df['结果'] = hist_df['pnl_pct'].apply(lambda x: " 盈利" if x > 0 else "💔 亏损")
        hist_df['盈亏'] = hist_df['pnl_pct'].apply(lambda x: f"{x*100:.2f}%")
        hist_df = hist_df[['symbol', '方向', 'entry', 'exit', '盈亏', '结果', 'reason', 'time']]
        st.dataframe(hist_df.head(10), use_container_width=True, hide_index=True) # 只显示最近10条

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
