import streamlit as st
import yfinance as yf
import pandas as pd
import openai
from datetime import datetime, timedelta
import re

# --- 1. 页面配置 ---
st.set_page_config(page_title="PCCI v6.9 - 因果智能引擎", layout="wide")

# 全局样式增强
st.markdown("""
    <style>
    /* 强制去除 Markdown 源码块的背景干扰 */
    .stMarkdown code { background-color: transparent !important; color: inherit !important; }
    .report-container { background: white; padding: 2rem; border-radius: 1.5rem; border: 1px solid #e2e8f0; box-shadow: 0 4px 6px -1px rgba(0,0,0,0.1); }
    .status-text { font-size: 0.85rem; font-weight: bold; margin-left: 5px; }
    /* 优化标题显示 */
    .stMarkdown h1, .stMarkdown h2, .stMarkdown h3 { color: #1e293b !important; border-bottom: none !important; }
    </style>
""", unsafe_allow_html=True)

# --- 2. 核心工具函数 ---

def terminal_clean_markdown(text):
    """
    终极修复：彻底剥离所有可能的 Markdown 代码块外壳。
    不管 AI 返回的是 ```markdown 还是 ``` 或带有前置空格，全部切除。
    """
    if not text: return ""
    # 1. 移除首尾空白
    text = text.strip()
    # 2. 移除开头的 ```markdown 或 ``` (忽略大小写)
    text = re.sub(r'^```[a-zA-Z]*\n?', '', text, flags=re.IGNORECASE)
    # 3. 移除结尾的 ```
    text = re.sub(r'\n?```$', '', text)
    return text.strip()

def check_api_connection(key, url, model):
    if not key: return False
    try:
        client = openai.OpenAI(api_key=key, base_url=url)
        client.chat.completions.create(model=model, messages=[{"role": "user", "content": "1"}], max_tokens=1)
        return True
    except:
        return False

@st.cache_data(ttl=3600)
def get_hard_data(ticker_symbol):
    """抓取硬数据并包含全球后缀校验"""
    try:
        ticker_symbol = ticker_symbol.upper().strip()
        # 后缀智能检查
        if ticker_symbol.isdigit() and len(ticker_symbol) == 6:
            return {"error": f"请输入完整代码。上海: {ticker_symbol}.SS | 深圳: {ticker_symbol}.SZ"}
        if ticker_symbol.isdigit() and len(ticker_symbol) < 5:
            return {"error": f"请输入完整代码。港股示例: {ticker_symbol.zfill(4)}.HK"}

        t = yf.Ticker(ticker_symbol)
        info = t.info
        
        if not info or len(info) < 5 or ('currentPrice' not in info and 'regularMarketPrice' not in info):
            return {"error": f"找不到标的 '{ticker_symbol}'。请检查后缀：上海 .SS, 深圳 .SZ, 香港 .HK, 日本 .T, 美国无后缀, 加密货币 -USD"}

        price = info.get('currentPrice') or info.get('regularMarketPrice') or info.get('previousClose', 'N/A')
        
        cfg = {"name": "Global", "market": "SPY", "rate": "^TNX", "cur": "DX-Y.NYB"}
        if ticker_symbol.endswith(".SS") or ticker_symbol.endswith(".SZ"):
            cfg = {"name": "A-Share", "market": "000001.SS", "rate": "^TNX", "cur": "CNY=X"}
        elif ticker_symbol.endswith(".HK"):
            cfg = {"name": "Hong Kong", "market": "^HSI", "rate": "^TNX", "cur": "CNY=X"}

        data = yf.download([ticker_symbol, cfg['market'], cfg['rate'], cfg['cur']], 
                           start=(datetime.now() - timedelta(days=365)), 
                           end=datetime.now(), progress=False)['Close']
        
        df = data.ffill().pct_change().dropna()
        corrs = df.corr()[ticker_symbol].to_dict() if ticker_symbol in df.columns else {}
        return {
            "symbol": ticker_symbol, 
            "fundamentals": {"price": price, "pe": info.get('trailingPE', 'N/A'), "peg": info.get('pegRatio', 'N/A'), "region": cfg['name']}, 
            "factors": corrs
        }
    except Exception as e:
        return {"error": f"系统错误: {str(e)}"}

# --- 3. 初始化与侧边栏 ---

if "api_ready" not in st.session_state:
    def_key = st.secrets.get("AI_API_KEY", "")
    def_url = st.secrets.get("AI_BASE_URL", "https://api.openai.com/v1")
    def_model = st.secrets.get("AI_MODEL", "gpt-4o")
    st.session_state.api_ready = check_api_connection(def_key, def_url, def_model)

def get_current_config():
    m_key = st.session_state.get("manual_api_key", "")
    m_url = st.session_state.get("manual_base_url", "")
    m_model = st.session_state.get("manual_model_name", "")
    return (m_key or st.secrets.get("AI_API_KEY", ""), 
            m_url or st.secrets.get("AI_BASE_URL", "https://api.openai.com/v1"), 
            m_model or st.secrets.get("AI_MODEL", "gpt-4o"))

with st.sidebar:
    st.title("🧠 PCCI v6.9")
    st.markdown(f"**API 状态:** {'🟢 在线' if st.session_state.api_ready else '🔴 离线'}", unsafe_allow_html=True)
    
    with st.expander("🔧 修改配置"):
        new_key = st.text_input("API Key", type="password")
        new_url = st.text_input("Base URL")
        new_model = st.text_input("Model Name")
        if st.button("更新并保存"):
            st.session_state.manual_api_key, st.session_state.manual_base_url, st.session_state.manual_model_name = new_key, new_url, new_model
            c_key, c_url, c_model = get_current_config()
            st.session_state.api_ready = check_api_connection(c_key, c_url, c_model)
            st.rerun()

    st.divider()
    mode = st.radio("模块选择", ["单标的透视", "事件推演", "组合体检"])

# --- 4. 业务逻辑 ---

cur_key, cur_url, cur_model = get_current_config()
client = openai.OpenAI(api_key=cur_key, base_url=cur_url) if st.session_state.api_ready else None

if mode == "单标的透视":
    st.subheader("🎯 单标的全维因子透视")
    # 增加详尽的后缀提示
    ticker = st.text_input("输入代码", value="NVDA", 
                           placeholder="后缀提示: 上海.SS | 深圳.SZ | 香港.HK | 日本.T | 加密-USD | 美国无后缀").upper().strip()
    if st.button("运行透视分析"):
        if not client: st.error("请配置 API")
        else:
            with st.status("正在抓取硬数据...", expanded=True) as status:
                hd = get_hard_data(ticker)
                if "error" in hd: st.error(hd["error"])
                else:
                    c1, c2, c3 = st.columns(3)
                    c1.metric("价格", hd['fundamentals']['price'])
                    c2.metric("PEG", hd['fundamentals']['peg'])
                    c3.metric("市场", hd['fundamentals']['region'])
                    
                    prompt = f"分析资产: {ticker}\n硬数据: {hd}\n要求：双轨输出（1.传统金融评估 2.PCCI因果推演），中间用 ||| 分隔。中文。"
                    resp = client.chat.completions.create(model=cur_model, messages=[{"role": "user", "content": prompt}])
                    
                    clean_res = terminal_clean_markdown(resp.choices[0].message.content)
                    parts = clean_res.split("|||") if "|||" in clean_res else [clean_res, "推演未生成"]
                    
                    st.markdown("### 📊 传统金融评估")
                    st.info(parts[0])
                    st.markdown("### 🔮 PCCI 因果智能")
                    st.success(parts[1])
                    status.update(label="透视完成", state="complete")

elif mode == "事件推演":
    st.subheader("⚡ 现实事件因果推演")
    event_input = st.text_area("事件内容", height=150, 
                               placeholder="例如：男性HPV疫苗获批，对智飞生物(300122.SZ)有何长期因果影响？")
    focus_assets = st.text_input("关注资产", placeholder="例如: 300122.SZ, 疫苗板块, 医药ETF")
    
    if st.button("开始推演"):
        if not client: st.error("API 离线")
        else:
            with st.spinner("AI 正在构建因果链条..."):
                prompt = f"事件: {event_input}\n关注资产: {focus_assets}\n任务：识别市场叙事、分析驱动因子、推演影响矩阵。中文。"
                resp = client.chat.completions.create(model=cur_model, messages=[{"role": "user", "content": prompt}])
                
                # 终极修复渲染逻辑
                st.markdown("---")
                output = terminal_clean_markdown(resp.choices[0].message.content)
                st.markdown(output)

elif mode == "组合体检":
    st.subheader("🩺 投资组合脆弱性诊断")
    portfolio_text = st.text_area("持仓列表 (每行一个)", height=150, 
                                   placeholder="示例输入：\nNVDA\n600036.SS\n0700.HK\nBTC-USD")
    if st.button("开始诊断"):
        if not client: st.error("API 离线")
        else:
            with st.spinner("AI 正在扫描风险开关..."):
                prompt = f"资产清单: {portfolio_text}\n任务：分析因子指纹、隐含世界观、致命弱点 (Kill Switch)。中文。"
                resp = client.chat.completions.create(model=cur_model, messages=[{"role": "user", "content": prompt}])
                
                st.markdown("---")