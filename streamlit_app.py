import streamlit as st
import yfinance as yf
import pandas as pd
import openai
from datetime import datetime, timedelta
import re

# --- 1. 页面配置与持久化初始化 ---
st.set_page_config(page_title="PCCI v7.1 - 容错增强版", layout="wide")

state_keys =[
    "api_ready", "profiler_res", "event_res", "diag_res", 
    "manual_api_key", "manual_base_url", "manual_model_name", "hard_data_cache"
]
for key in state_keys:
    if key not in st.session_state:
        st.session_state[key] = None if "res" in key else False

st.markdown("""
    <style>
    .stMarkdown code { background-color: transparent !important; color: #e11d48 !important; font-family: monospace; }
    .status-text { font-size: 0.85rem; font-weight: bold; margin-left: 5px; }
    .report-card { background: white; padding: 2rem; border-radius: 1.5rem; border: 1px solid #e2e8f0; box-shadow: 0 4px 6px -1px rgba(0,0,0,0.1); }
    h1, h2, h3 { color: #1e293b !important; }
    </style>
""", unsafe_allow_html=True)

# --- 2. 核心工具函数 ---

def terminal_clean_markdown(text):
    if not text: return ""
    text = text.strip()
    text = re.sub(r'^```[a-zA-Z]*\n?', '', text, flags=re.IGNORECASE)
    text = re.sub(r'\n?```$', '', text)
    return text.strip()

def check_api_connection(key, url, model):
    if not key: return False
    try:
        client = openai.OpenAI(api_key=key, base_url=url)
        client.chat.completions.create(model=model, messages=[{"role": "user", "content": "1"}], max_tokens=1, timeout=5)
        return True
    except:
        return False

@st.cache_data(ttl=3600)
def get_hard_data(ticker_symbol):
    """【重构】防封禁与优雅降级的硬数据获取"""
    ticker_symbol = ticker_symbol.upper().strip()
    if ticker_symbol.isdigit() and len(ticker_symbol) == 6:
        return {"error": f"代码不全。上海: {ticker_symbol}.SS | 深圳: {ticker_symbol}.SZ"}

    cfg = {"name": "Global", "market": "SPY", "rate": "^TNX", "cur": "DX-Y.NYB"}
    if ticker_symbol.endswith(".SS") or ticker_symbol.endswith(".SZ"):
        cfg = {"name": "A-Share", "market": "000001.SS", "rate": "^TNX", "cur": "CNY=X"}
    elif ticker_symbol.endswith(".HK"):
        cfg = {"name": "Hong Kong", "market": "^HSI", "rate": "^TNX", "cur": "CNY=X"}

    # 1. 优先获取历史行情 (yf.download 不容易被限流)
    try:
        end = datetime.now()
        start = end - timedelta(days=365)
        data = yf.download([ticker_symbol, cfg['market'], cfg['rate'], cfg['cur']], 
                           start=start, end=end, progress=False)['Close']
        if data.empty or ticker_symbol not in data.columns:
            return {"error": f"找不到该标的行情: {ticker_symbol}"}
            
        df = data.ffill().pct_change().dropna()
        corrs = df.corr()[ticker_symbol].to_dict() if ticker_symbol in df.columns else {}
        
        # 尝试从历史数据提取最新价格作为兜底
        fallback_price = round(data[ticker_symbol].dropna().iloc[-1], 2)
    except Exception as e:
        return {"error": f"Yahoo API 历史行情限流或报错: {str(e)}"}

    # 2. 尝试获取基本面 (t.info 极易被限流，放入独立 try-except)
    price, pe, peg = fallback_price, "N/A", "N/A"
    try:
        t = yf.Ticker(ticker_symbol)
        info = t.info
        price = info.get('currentPrice') or info.get('regularMarketPrice') or fallback_price
        pe = info.get('trailingPE', 'N/A')
        peg = info.get('pegRatio', 'N/A')
    except:
        pass # 如果 info 被限流，忽略报错，使用 fallback_price 和 N/A

    return {
        "symbol": ticker_symbol, 
        "fundamentals": {"price": price, "pe": pe, "peg": peg, "region": cfg['name']}, 
        "factors": corrs
    }

# --- 3. 初始化与侧边栏 ---

if st.session_state.api_ready is False:
    def_key = st.secrets.get("AI_API_KEY", "")
    def_url = st.secrets.get("AI_BASE_URL", "https://api.openai.com/v1")
    def_model = st.secrets.get("AI_MODEL", "gpt-4o")
    if check_api_connection(def_key, def_url, def_model):
        st.session_state.api_ready = True

def get_current_config():
    mk, mu, mm = st.session_state.manual_api_key, st.session_state.manual_base_url, st.session_state.manual_model_name
    return (mk or st.secrets.get("AI_API_KEY", ""), 
            mu or st.secrets.get("AI_BASE_URL", "https://api.openai.com/v1"), 
            mm or st.secrets.get("AI_MODEL", "gpt-4o"))

with st.sidebar:
    st.title("🧠 PCCI v7.1")
    st.markdown(f"**API 状态:** {'🟢 在线' if st.session_state.api_ready else '🔴 离线'}")
    
    with st.expander("🔧 设置"):
        new_key = st.text_input("API Key", type="password")
        new_url = st.text_input("Base URL")
        new_model = st.text_input("Model Name")
        if st.button("测试并应用"):
            st.session_state.manual_api_key, st.session_state.manual_base_url, st.session_state.manual_model_name = new_key, new_url, new_model
            ck, cu, cm = get_current_config()
            st.session_state.api_ready = check_api_connection(ck, cu, cm)
            st.rerun()

    st.divider()
    mode = st.radio("模块",["单标的透视", "事件推演", "组合体检"])
    if st.button("🗑️ 清空当前结果"):
        st.session_state.profiler_res = st.session_state.event_res = st.session_state.diag_res = None
        st.session_state.hard_data_cache = None
        st.rerun()

# --- 4. 业务逻辑 ---

cur_key, cur_url, cur_model = get_current_config()
client = openai.OpenAI(api_key=cur_key, base_url=cur_url) if st.session_state.api_ready else None

if mode == "单标的透视":
    st.subheader("🎯 单标的全维因子透视")
    ticker = st.text_input("输入代码", value="NVDA", placeholder="示例: 600036.SS | 0700.HK | BTC-USD").upper().strip()
    
    if st.button("运行分析"):
        if not client: st.error("请先配置 API")
        else:
            with st.status("分析中...", expanded=True) as status:
                # 1. 获取硬数据
                hd = get_hard_data(ticker)
                
                # 2. 优雅降级逻辑
                if "error" in hd:
                    st.warning(f"⚠️ Yahoo 数据限流: {hd['error']}。系统将自动降级为纯 AI 知识库推演。")
                    st.session_state.hard_data_cache = None
                    hd_context = "因接口限流，无法获取实时硬数据。请完全基于你的知识库对该资产进行评估。"
                else:
                    st.session_state.hard_data_cache = hd
                    hd_context = str(hd)

                # 3. AI 推演
                prompt = f"分析资产: {ticker}\n硬数据/环境: {hd_context}\n要求：双轨输出（1.传统评估 2.PCCI推演），中间用 ||| 分隔。中文。"
                try:
                    resp = client.chat.completions.create(model=cur_model, messages=[{"role": "user", "content": prompt}])
                    st.session_state.profiler_res = terminal_clean_markdown(resp.choices[0].message.content)
                    status.update(label="分析完成", state="complete")
                except Exception as e:
                    status.update(label="推演失败", state="error")
                    st.error(f"AI 接口报错: {e}")
    
    # 渲染硬数据看板
    if st.session_state.hard_data_cache:
        hd = st.session_state.hard_data_cache
        c1, c2, c3 = st.columns(3)
        c1.metric("价格", hd['fundamentals']['price'])
        c2.metric("PEG", hd['fundamentals']['peg'])
        c3.metric("市场", hd['fundamentals']['region'])
    
    # 渲染双轨报告
    if st.session_state.profiler_res:
        parts = st.session_state.profiler_res.split("|||")
        st.markdown("### 📊 传统金融评估")
        st.info(parts[0])
        if len(parts) > 1:
            st.markdown("### 🔮 PCCI 因果智能")
            st.success(parts[1])

elif mode == "事件推演":
    st.subheader("⚡ 现实事件因果推演")
    event_input = st.text_area("事件内容", height=150, placeholder="例如：美联储降息 50bp...")
    focus_assets = st.text_input("关注资产", placeholder="例如: 黄金, 300122.SZ")
    
    if st.button("开始推演"):
        if not client: st.error("API 离线")
        else:
            with st.spinner("AI 正在构建因果链条..."):
                prompt = f"事件: {event_input}\n关注资产: {focus_assets}\n任务：识别市场叙事、分析驱动因子、推演影响矩阵。中文。"
                resp = client.chat.completions.create(model=cur_model, messages=[{"role": "user", "content": prompt}])
                st.session_state.event_res = terminal_clean_markdown(resp.choices[0].message.content)
    
    if st.session_state.event_res:
        st.markdown("---")
        st.markdown(st.session_state.event_res)

elif mode == "组合体检":
    st.subheader("🩺 投资组合脆弱性诊断")
    portfolio_text = st.text_area("持仓列表 (每行一个)", height=150, placeholder="示例：\nNVDA\n600036.SS\nBTC-USD")
    
    if st.button("开始体检"):
        if not client: st.error("API 离线")
        else:
            with st.spinner("AI 正在扫描风险开关..."):
                prompt = f"资产清单: {portfolio_text}\n任务：分析因子指纹、隐含世界观、致命弱点 (Kill Switch)。中文。"
                resp = client.chat.completions.create(model=cur_model, messages=[{"role": "user", "content": prompt}])
                st.session_state.diag_res = terminal_clean_markdown(resp.choices[0].message.content)
    
    if st.session_state.diag_res:
        st.markdown("---")
        st.markdown(st.session_state.diag_res)
