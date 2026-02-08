import streamlit as st
import yfinance as yf
import pandas as pd
import openai
from datetime import datetime, timedelta

# --- 1. 页面配置 ---
st.set_page_config(page_title="PCCI v6.6 - 因果智能引擎", layout="wide")

# 自定义样式：优化表格和报告显示
st.markdown("""
    <style>
    .report-card { background: white; padding: 1.5rem; border-radius: 1rem; border: 1px solid #e2e8f0; margin-bottom: 1rem; }
    .status-text { font-size: 0.85rem; font-weight: bold; margin-left: 5px; }
    /* 强制渲染的 Markdown 样式微调 */
    .stMarkdown h1, .stMarkdown h2, .stMarkdown h3 { color: #1e293b; margin-top: 1rem; }
    .stMarkdown table { width: 100% !important; border-collapse: collapse; }
    </style>
""", unsafe_allow_html=True)

# --- 2. 状态与配置管理逻辑 ---

def check_api_connection(key, url, model):
    """底层 API 连通性测试"""
    if not key: return False
    try:
        client = openai.OpenAI(api_key=key, base_url=url)
        client.chat.completions.create(model=model, messages=[{"role": "user", "content": "1"}], max_tokens=1)
        return True
    except:
        return False

# 初始化状态
if "api_ready" not in st.session_state:
    # 首次启动：静默测试环境变量中的 Secrets
    def_key = st.secrets.get("AI_API_KEY", "")
    def_url = st.secrets.get("AI_BASE_URL", "https://api.openai.com/v1")
    def_model = st.secrets.get("AI_MODEL", "gpt-4o")
    st.session_state.api_ready = check_api_connection(def_key, def_url, def_model)

# 获取当前有效的配置 (手动覆盖优先于环境变量)
def get_current_config():
    # 获取手动输入的值
    manual_key = st.session_state.get("manual_api_key", "")
    manual_url = st.session_state.get("manual_base_url", "")
    manual_model = st.session_state.get("manual_model_name", "")
    
    # 融合逻辑
    current_key = manual_key if manual_key else st.secrets.get("AI_API_KEY", "")
    current_url = manual_url if manual_url else st.secrets.get("AI_BASE_URL", "https://api.openai.com/v1")
    current_model = manual_model if manual_model else st.secrets.get("AI_MODEL", "gpt-4o")
    
    return current_key, current_url, current_model

# --- 3. 核心工具函数 ---

@st.cache_data(ttl=3600)
def get_hard_data(ticker_symbol):
    """抓取 Python 后端硬数据"""
    try:
        ticker_symbol = ticker_symbol.upper().strip()
        t = yf.Ticker(ticker_symbol)
        info = t.info
        price = info.get('currentPrice') or info.get('regularMarketPrice') or info.get('previousClose', 'N/A')
        
        cfg = {"name": "Global", "market": "SPY", "rate": "^TNX", "cur": "DX-Y.NYB"}
        if ticker_symbol.endswith(".SS") or ticker_symbol.endswith(".SZ"):
            cfg = {"name": "A-Share", "market": "000001.SS", "rate": "^TNX", "cur": "CNY=X"}
        elif ticker_symbol.endswith(".HK"):
            cfg = {"name": "Hong Kong", "market": "^HSI", "rate": "^TNX", "cur": "CNY=X"}

        end = datetime.now()
        start = end - timedelta(days=365)
        data = yf.download([ticker_symbol, cfg['market'], cfg['rate'], cfg['cur']], start=start, end=end, progress=False)['Close']
        df = data.ffill().pct_change().dropna()
        corrs = df.corr()[ticker_symbol].to_dict() if ticker_symbol in df.columns else {}

        return {
            "symbol": ticker_symbol,
            "fundamentals": {"price": price, "pe": info.get('trailingPE', 'N/A'), "peg": info.get('pegRatio', 'N/A'), "region": cfg['name']},
            "factors": corrs
        }
    except Exception as e:
        return {"error": f"数据抓取失败: {str(e)}"}

# --- 4. 侧边栏与配置 ---

with st.sidebar:
    st.title("🧠 PCCI v6.6")
    
    # API 状态灯 (实时显示当前配置的连通性)
    status_icon = "🟢" if st.session_state.api_ready else "🔴"
    status_label = "在线" if st.session_state.api_ready else "离线"
    st.markdown(f"**API 状态:** {status_icon} <span class='status-text'>{status_label}</span>", unsafe_allow_html=True)
    
    with st.expander("🔧 手动覆盖配置 (仅需修改时填写)"):
        st.caption("留空则默认使用系统环境变量")
        new_key = st.text_input("API Key Overwrite", type="password", key="manual_api_key_input")
        new_url = st.text_input("Base URL Overwrite", key="manual_base_url_input")
        new_model = st.text_input("Model Name Overwrite", key="manual_model_name_input")
        
        if st.button("⚡ 测试并应用新配置"):
            # 将输入保存到 session_state
            st.session_state.manual_api_key = new_key
            st.session_state.manual_base_url = new_url
            st.session_state.manual_model_name = new_model
            
            # 测试新组合
            c_key, c_url, c_model = get_current_config()
            with st.spinner("正在验证..."):
                st.session_state.api_ready = check_api_connection(c_key, c_url, c_model)
                if st.session_state.api_ready:
                    st.success("配置更新并联通！")
                else:
                    st.error("联通失败，请检查输入")

    st.divider()
    mode = st.radio("功能模块", ["单标的透视", "事件推演", "组合体检"])

# --- 5. 主页面逻辑 ---

# 获取实时有效配置
cur_key, cur_url, cur_model = get_current_config()
client = openai.OpenAI(api_key=cur_key, base_url=cur_url) if st.session_state.api_ready else None

if mode == "单标的透视":
    st.subheader("🎯 单标的全维因子透视")
    ticker = st.text_input("输入代码 (如 NVDA, 600519.SH)", value="NVDA").upper().strip()
    
    if st.button("运行分析"):
        if not client: st.error("请先确保 API 状态为在线")
        else:
            with st.status("正在进行全维透视...", expanded=True) as status:
                st.write("获取硬数据...")
                hd = get_hard_data(ticker)
                if "error" in hd: st.error(hd["error"])
                else:
                    st.write("调用 AI 推演...")
                    # 仪表盘
                    c1, c2, c3 = st.columns(3)
                    c1.metric("价格", hd['fundamentals']['price'])
                    c2.metric("PEG", hd['fundamentals']['peg'])
                    c3.metric("市场", hd['fundamentals']['region'])

                    prompt = f"分析资产: {ticker}\n硬数据: {hd}\n要求：双轨输出（1.传统金融评估 2.PCCI因果推演），中间用 ||| 分隔。中文。"
                    resp = client.chat.completions.create(model=cur_model, messages=[{"role": "user", "content": prompt}])
                    
                    res_txt = resp.choices[0].message.content
                    parts = res_txt.split("|||") if "|||" in res_txt else [res_txt, "推演失败"]
                    
                    st.markdown("### 📊 传统金融评估")
                    st.info(parts[0])
                    st.markdown("### 🔮 PCCI 因果智能")
                    st.success(parts[1])
                    status.update(label="分析完成", state="complete")

elif mode == "事件推演":
    st.subheader("⚡ 现实事件因果推演")
    event_input = st.text_area("事件内容", height=150, placeholder="例如：中东局势升级导致原油供应担忧...")
    focus_assets = st.text_input("关注资产 (可选)", placeholder="例如：原油, 黄金, 航空股")
    
    if st.button("开始推演"):
        if not client: st.error("API 离线")
        else:
            with st.spinner("AI 正在构建因果链条..."):
                prompt = f"事件: {event_input}\n关注资产: {focus_assets}\n任务：识别叙事、分析驱动因子、推演影响矩阵。中文 Markdown。"
                resp = client.chat.completions.create(model=cur_model, messages=[{"role": "user", "content": prompt}])
                # 强制 Markdown 渲染
                st.markdown(resp.choices[0].message.content)

elif mode == "组合体检":
    st.subheader("🩺 投资组合脆弱性诊断")
    portfolio_text = st.text_area("持仓列表 (每行一个)", height=150, placeholder="NVDA\nAAPL\nBTC-USD")
    
    if st.button("开始诊断"):
        if not client: st.error("API 离线")
        else:
            with st.spinner("AI 正在扫描风险开关..."):
                prompt = f"资产清单: {portfolio_text}\n任务：分析因子指纹、隐含世界观、致命弱点 (Kill Switch)。中文 Markdown。"
                resp = client.chat.completions.create(model=cur_model, messages=[{"role": "user", "content": prompt}])
                # 强制 Markdown 渲染
                st.markdown(resp.choices[0].message.content)