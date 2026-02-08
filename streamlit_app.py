import streamlit as st
import yfinance as yf
import pandas as pd
import openai
from datetime import datetime, timedelta

# --- 1. 页面配置与样式 ---
st.set_page_config(page_title="PCCI v6.5 - 因果智能引擎", layout="wide")

st.markdown("""
    <style>
    .report-card { background: white; padding: 1.5rem; border-radius: 1rem; border: 1px solid #e2e8f0; margin-bottom: 1rem; }
    .status-text { font-size: 0.8rem; font-weight: bold; }
    .stMetric { background: #f8fafc; padding: 10px; border-radius: 10px; border: 1px solid #f1f5f9; }
    </style>
""", unsafe_allow_html=True)

# --- 2. 初始化 Session State (存储配置与状态) ---
if "api_ready" not in st.session_state:
    st.session_state.api_ready = False

# --- 3. 核心工具函数 ---

def check_api_connection(key, url, model):
    """自动检测 API 是否通畅"""
    if not key:
        return False
    try:
        client = openai.OpenAI(api_key=key, base_url=url)
        # 极简请求，仅用 1 个 token 测试
        client.chat.completions.create(model=model, messages=[{"role": "user", "content": "1"}], max_tokens=1)
        return True
    except:
        return False

def get_hard_data(ticker_symbol):
    """抓取 Python 后端硬数据"""
    try:
        ticker_symbol = ticker_symbol.upper().strip()
        t = yf.Ticker(ticker_symbol)
        info = t.info
        price = info.get('currentPrice') or info.get('regularMarketPrice') or info.get('previousClose', 'N/A')
        
        # 自动识别市场
        cfg = {"name": "Global", "market": "SPY", "rate": "^TNX", "cur": "DX-Y.NYB"}
        if ticker_symbol.endswith(".SS") or ticker_symbol.endswith(".SZ"):
            cfg = {"name": "A-Share", "market": "000001.SS", "rate": "^TNX", "cur": "CNY=X"}
        elif ticker_symbol.endswith(".HK"):
            cfg = {"name": "Hong Kong", "market": "^HSI", "rate": "^TNX", "cur": "CNY=X"}

        # 抓取相关性数据
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
        return {"error": f"Data Error: {str(e)}"}

# --- 4. 侧边栏：配置与导航 ---

with st.sidebar:
    st.title("🧠 PCCI v6.5")
    
    # API 状态灯逻辑
    status_icon = "🟢" if st.session_state.api_ready else "🔴"
    status_label = "在线" if st.session_state.api_ready else "离线/未配置"
    
    st.markdown(f"**API 状态:** {status_icon} <span class='status-text'>{status_label}</span>", unsafe_allow_html=True)
    
    # 折叠式设置面板
    with st.expander("🔧 模型配置 (点击展开)"):
        # 自动获取默认值 (Secrets -> 用户输入)
        def_key = st.secrets.get("AI_API_KEY", "")
        def_url = st.secrets.get("AI_BASE_URL", "https://api.openai.com/v1")
        def_model = st.secrets.get("AI_MODEL", "gpt-4o")

        api_key = st.text_input("API Key", type="password", value=def_key, help="输入后点击下方测试按钮")
        base_url = st.text_input("Base URL", value=def_url)
        model_name = st.text_input("Model Name", value=def_model)
        
        if st.button("⚡ 测试并保存"):
            with st.spinner("正在联通测试..."):
                is_ok = check_api_connection(api_key, base_url, model_name)
                st.session_state.api_ready = is_ok
                if is_ok:
                    st.success("连接成功！")
                else:
                    st.error("连接失败，请检查参数")

    st.divider()
    mode = st.radio("功能模块", ["单标的透视", "事件推演", "组合体检"])
    
    st.caption("v6.5 Final Beta | Powered by yfinance & LLM")

# --- 5. 主页面逻辑 ---

client = openai.OpenAI(api_key=api_key, base_url=base_url) if st.session_state.api_ready else None

if mode == "单标的透视":
    st.subheader("🎯 单标的全维因子透视")
    ticker = st.text_input("输入资产代码", value="NVDA").upper().strip()
    
    if st.button("运行双轨分析"):
        if not client:
            st.error("请先在左侧配置并测试 API 联通性")
        else:
            with st.status("正在进行深度分析...", expanded=True) as status:
                st.write("获取实时硬数据...")
                hd = get_hard_data(ticker)
                
                if "error" in hd:
                    st.error(hd["error"])
                else:
                    st.write("因果逻辑推演中...")
                    # 因子数据摘要
                    c1, c2, c3 = st.columns(3)
                    c1.metric("价格", hd['fundamentals']['price'])
                    c2.metric("PEG", hd['fundamentals']['peg'])
                    c3.metric("利率相关性", f"{hd['factors'].get('^TNX', 0):.2f}")

                    prompt = f"分析资产: {ticker}\n硬数据: {hd}\n要求：双轨输出（1.传统金融评估 2.PCCI因果推演），中间用 ||| 分隔。中文。"
                    resp = client.chat.completions.create(model=model_name, messages=[{"role": "user", "content": prompt}])
                    
                    res_txt = resp.choices[0].message.content
                    parts = res_txt.split("|||") if "|||" in res_txt else [res_txt, "逻辑推演生成失败"]
                    
                    st.markdown("### 📊 传统金融评估")
                    st.info(parts[0])
                    st.markdown("### 🔮 PCCI 因果智能")
                    st.success(parts[1])
                    status.update(label="分析完成", state="complete")

elif mode == "事件推演":
    st.subheader("⚡ 现实事件因果推演")
    event_input = st.text_area("输入新闻事件、财报摘要或政策变动", height=150, placeholder="例如：美联储非农数据超预期，暗示高利率将维持更久...")
    focus_assets = st.text_input("关注的资产 (可选)", placeholder="例如：黄金, 纳指100, 招商银行")
    
    if st.button("执行推演"):
        if not client:
            st.error("API 未就绪")
        else:
            with st.spinner("构建多世界因果链条..."):
                prompt = f"""
                现实事件: {event_input}
                目标资产: {focus_assets if focus_assets else '自动识别前五大影响资产'}
                
                任务：
                1. 识别该事件激活的“市场叙事”或“世界状态”。
                2. 分析对 利率、美元、风险偏好、流动性 四大因子的驱动方向。
                3. 推演对目标资产的 短/中/长期 影响矩阵。
                
                请用 Markdown 格式中文回答。
                """
                resp = client.chat.completions.create(model=model_name, messages=[{"role": "user", "content": prompt}])
                st.markdown(resp.choices[0].message.content)

elif mode == "组合体检":
    st.subheader("🩺 投资组合脆弱性诊断")
    portfolio_text = st.text_area("输入当前持仓清单 (每行一个)", height=150, placeholder="NVDA\n600036.SS\nBTC-USD\nGLD")
    
    if st.button("开始诊断"):
        if not client:
            st.error("API 未就绪")
        else:
            with st.spinner("分析因子暴露与反向开关..."):
                prompt = f"""
                资产清单:
                {portfolio_text}
                
                任务：
                对于列表中的每个资产，分析：
                1. 它的“因子指纹”：它最怕什么？（例如对利率敏感、对汇率敏感）。
                2. 隐含的世界观：买入它意味着你此刻在赌一个什么样的未来？
                3. 致命弱点 (Kill Switch)：发生什么具体宏观情境，该组合会发生系统性回撤？
                
                请用 Markdown 格式中文回答。
                """
                resp = client.chat.completions.create(model=model_name, messages=[{"role": "user", "content": prompt}])
                st.markdown(resp.choices[0].message.content)