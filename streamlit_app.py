import streamlit as st
import yfinance as yf
import pandas as pd
import openai
from datetime import datetime, timedelta
import re

# --- 1. 页面配置 ---
st.set_page_config(page_title="PCCI v6.8 - 因果智能引擎", layout="wide")

# 全局自定义 CSS 优化
st.markdown("""
    <style>
    .report-card { background: white; padding: 1.5rem; border-radius: 1rem; border: 1px solid #e2e8f0; margin-bottom: 1rem; }
    .status-text { font-size: 0.85rem; font-weight: bold; margin-left: 5px; }
    /* 强力重置 Markdown 渲染 */
    .stMarkdown h1, .stMarkdown h2, .stMarkdown h3 { color: #1e293b !important; padding-top: 1rem !important; }
    .stMarkdown p, .stMarkdown li { line-height: 1.7 !important; color: #334155 !important; }
    </style>
""", unsafe_allow_html=True)

# --- 2. 工具函数 ---

def clean_markdown(text):
    """去除 LLM 自动包裹的代码块，确保 Markdown 正常渲染"""
    # 处理开始部分的 ```markdown 或 ```
    text = re.sub(r'^```(markdown)?\s*', '', text, flags=re.IGNORECASE | re.MULTILINE)
    # 处理结尾部分的 ```
    text = re.sub(r'\s*```$', '', text, flags=re.MULTILINE)
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
    """抓取硬数据并包含错误处理"""
    try:
        ticker_symbol = ticker_symbol.upper().strip()
        # 常见错误输入纠正 (如用户输入 600036 但没加后缀)
        if ticker_symbol.isdigit() and len(ticker_symbol) == 6:
            return {"error": f"请输入完整代码。A股请加后缀：{ticker_symbol}.SS 或 {ticker_symbol}.SZ"}

        t = yf.Ticker(ticker_symbol)
        info = t.info
        
        # 校验：yfinance 如果找不到标的，info 字典通常是空的或只有个别字段
        if not info or len(info) < 5 or ('currentPrice' not in info and 'regularMarketPrice' not in info):
            return {"error": f"无法找到标的 '{ticker_symbol}'。请确保代码正确 (如: NVDA, 600036.SS, 0700.HK, BTC-USD)"}

        price = info.get('currentPrice') or info.get('regularMarketPrice') or info.get('previousClose', 'N/A')
        
        cfg = {"name": "Global", "market": "SPY", "rate": "^TNX", "cur": "DX-Y.NYB"}
        if ticker_symbol.endswith(".SS") or ticker_symbol.endswith(".SZ"):
            cfg = {"name": "A-Share", "market": "000001.SS", "rate": "^TNX", "cur": "CNY=X"}
        elif ticker_symbol.endswith(".HK"):
            cfg = {"name": "Hong Kong", "market": "^HSI", "rate": "^TNX", "cur": "CNY=X"}

        end = datetime.now()
        start = end - timedelta(days=365)
        data = yf.download([ticker_symbol, cfg['market'], cfg['rate'], cfg['cur']], start=start, end=end, progress=False)['Close']
        
        if data.empty:
            return {"error": "下载历史行情失败，请稍后重试。"}

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
    manual_key = st.session_state.get("manual_api_key", "")
    manual_url = st.session_state.get("manual_base_url", "")
    manual_model = st.session_state.get("manual_model_name", "")
    current_key = manual_key if manual_key else st.secrets.get("AI_API_KEY", "")
    current_url = manual_url if manual_url else st.secrets.get("AI_BASE_URL", "https://api.openai.com/v1")
    current_model = manual_model if manual_model else st.secrets.get("AI_MODEL", "gpt-4o")
    return current_key, current_url, current_model

with st.sidebar:
    st.title("🧠 PCCI v6.8")
    status_icon = "🟢" if st.session_state.api_ready else "🔴"
    st.markdown(f"**API 状态:** {status_icon} <span class='status-text'>{'在线' if st.session_state.api_ready else '离线'}</span>", unsafe_allow_html=True)
    
    with st.expander("🔧 设置"):
        new_key = st.text_input("API Key Overwrite", type="password")
        new_url = st.text_input("Base URL Overwrite")
        new_model = st.text_input("Model Overwrite")
        if st.button("应用并重启"):
            st.session_state.manual_api_key = new_key
            st.session_state.manual_base_url = new_url
            st.session_state.manual_model_name = new_model
            c_key, c_url, c_model = get_current_config()
            st.session_state.api_ready = check_api_connection(c_key, c_url, c_model)
            st.rerun()

    st.divider()
    mode = st.radio("功能模块", ["单标的透视", "事件推演", "组合体检"])

# --- 4. 主页面逻辑 ---

cur_key, cur_url, cur_model = get_current_config()
client = openai.OpenAI(api_key=cur_key, base_url=cur_url) if st.session_state.api_ready else None

if mode == "单标的透视":
    st.subheader("🎯 单标的全维因子透视")
    ticker = st.text_input("输入代码", value="NVDA", placeholder="例如: AAPL, 600036.SS, BTC-USD").upper().strip()
    if st.button("运行分析"):
        if not client: st.error("请先配置并测试 API 连接")
        else:
            with st.status("正在抓取硬数据并推演...", expanded=True) as status:
                hd = get_hard_data(ticker)
                if "error" in hd:
                    st.error(hd["error"])
                    status.update(label="分析中断", state="error")
                else:
                    c1, c2, c3 = st.columns(3)
                    c1.metric("价格", hd['fundamentals']['price'])
                    c2.metric("PEG", hd['fundamentals']['peg'])
                    c3.metric("地区", hd['fundamentals']['region'])
                    
                    prompt = f"分析资产: {ticker}\n硬数据内容: {hd}\n要求：双轨输出（1.传统金融评估 2.PCCI因果推演），中间用 ||| 分隔。中文。"
                    resp = client.chat.completions.create(model=cur_model, messages=[{"role": "user", "content": prompt}])
                    
                    content = clean_markdown(resp.choices[0].message.content)
                    parts = content.split("|||") if "|||" in content else [content, "推演部分未正确生成"]
                    
                    st.markdown("### 📊 传统金融评估")
                    st.info(parts[0])
                    st.markdown("### 🔮 PCCI 因果智能")
                    st.success(parts[1])
                    status.update(label="透视完成", state="complete")

elif mode == "事件推演":
    st.subheader("⚡ 现实事件因果推演")
    event_input = st.text_area("事件内容", height=150, placeholder="例如：美联储非农数据意外超预期，暗示高利率可能维持更久...")
    focus_assets = st.text_input("关注资产", placeholder="例如：黄金, 纳指100, 招商银行")
    if st.button("开始推演"):
        if not client: st.error("API 离线")
        else:
            with st.spinner("AI 正在构建因果链条..."):
                prompt = f"事件: {event_input}\n关注资产: {focus_assets}\n任务：识别市场叙事、分析驱动因子、推演影响矩阵。中文 Markdown。"
                resp = client.chat.completions.create(model=cur_model, messages=[{"role": "user", "content": prompt}])
                
                # 渲染逻辑
                cleaned_text = clean_markdown(resp.choices[0].message.content)
                st.markdown("---")
                st.markdown(cleaned_text)

elif mode == "组合体检":
    st.subheader("🩺 投资组合脆弱性诊断")
    portfolio_text = st.text_area("持仓列表 (每行一个)", height=150, placeholder="例如：\nNVDA\n600036.SS\nBTC-USD\nGLD")
    if st.button("开始诊断"):
        if not client: st.error("API 离线")
        else:
            with st.spinner("AI 正在扫描风险开关 (Kill Switch)..."):
                prompt = f"资产清单: {portfolio_text}\n任务：分析因子指纹、隐含世界观、致命弱点 (Kill Switch)。中文 Markdown。"
                resp = client.chat.completions.create(model=cur_model, messages=[{"role": "user", "content": prompt}])
                
                # 渲染逻辑
                cleaned_text = clean_markdown(resp.choices[0].message.content)
                st.markdown("---")
                st.markdown(cleaned_text)