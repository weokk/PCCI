import streamlit as st
import yfinance as yf
import pandas as pd
import openai
from datetime import datetime, timedelta

# --- 页面配置 ---
st.set_page_config(page_title="PCCI v6 - 因果智能引擎", layout="wide")

# --- 注入自定义 CSS 让 UI 更好看 ---
st.markdown("""
    <style>
    .main { background-color: #f8fafc; }
    .stButton>button { width: 100%; border-radius: 12px; font-weight: bold; }
    .report-card { background: white; padding: 2rem; border-radius: 1.5rem; border: 1px solid #e2e8f0; box-shadow: 0 4px 6px -1px rgb(0 0 0 / 0.1); }
    .causal-header { color: #4f46e5; border-bottom: 2px solid #e2e8f0; padding-bottom: 0.5rem; }
    </style>
""", unsafe_allow_html=True)

# --- 后端逻辑：财务数据抓取 ---
def get_hard_data(ticker_symbol):
    try:
        t = yf.Ticker(ticker_symbol)
        info = t.info
        price = info.get('currentPrice') or info.get('regularMarketPrice', 'N/A')
        
        # 简易区域识别
        region = "Global"
        market = "SPY"
        if ".SS" in ticker_symbol or ".SZ" in ticker_symbol: 
            region, market = "China A-Share", "000001.SS"
        elif ".HK" in ticker_symbol: 
            region, market = "Hong Kong", "^HSI"

        # 计算简易相关性
        end = datetime.now()
        start = end - timedelta(days=365)
        data = yf.download([ticker_symbol, market, "^TNX", "GLD"], start=start, end=end, progress=False)['Close']
        df = data.ffill().pct_change().dropna()
        
        corrs = df.corr()[ticker_symbol.upper()].to_dict() if ticker_symbol.upper() in df.columns else {}

        return {
            "symbol": ticker_symbol,
            "fundamentals": {"price": price, "pe": info.get('trailingPE', 'N/A'), "peg": info.get('pegRatio', 'N/A'), "region": region},
            "factors": corrs
        }
    except Exception as e:
        return {"error": str(e)}

# --- 侧边栏：配置与输入 ---
with st.sidebar:
    st.title("⚙️ PCCI 配置")
    api_key = st.text_input("OpenAI/DeepSeek API Key", type="password", value=st.secrets.get("AI_API_KEY", ""))
    base_url = st.text_input("Base URL", value=st.secrets.get("AI_BASE_URL", "https://api.openai.com/v1"))
    model = st.text_input("Model Name", value=st.secrets.get("AI_MODEL", "gpt-4o"))
    
    st.divider()
    mode = st.radio("选择分析模式", ["单标的透视", "事件推演", "组合体检"])

# --- 主界面逻辑 ---
st.title("🧠 PCCI v6 因果智能引擎")

if mode == "单标的透视":
    ticker = st.text_input("输入资产代码 (如 NVDA, 600036.SS, BTC-USD)", placeholder="NVDA").upper()
    
    if st.button("开始双轨分析"):
        if not api_key:
            st.error("请先在侧边栏填入 API Key")
        else:
            with st.spinner("🚀 正在从 Python 后端调取硬数据并生成报告..."):
                # 1. 获取硬数据
                data = get_hard_data(ticker)
                
                # 2. 展示硬数据仪表盘
                if "error" not in data:
                    col1, col2, col3 = st.columns(3)
                    col1.metric("当前价格", data['fundamentals']['price'])
                    col2.metric("PEG 估值", data['fundamentals']['peg'])
                    col3.metric("市场区域", data['fundamentals']['region'])
                    
                    with st.expander("查看详细因子相关性"):
                        st.json(data['factors'])
                
                # 3. 调用 AI 进行双轨分析
                client = openai.OpenAI(api_key=api_key, base_url=base_url)
                prompt = f"""分析标的: {ticker}\n数据背景: {data}\n
                请输出两部分内容，中间用 ||| 分隔。
                第一部分：【传统金融评估】基于PE/PEG和相关性数据的硬核评价。
                第二部分：【PCCI 因果智能】分析资产本质、完美世界假设和致命弱点(Kill Switch)。
                中文输出，使用Markdown。"""
                
                try:
                    response = client.chat.completions.create(
                        model=model,
                        messages=[{"role": "user", "content": prompt}]
                    )
                    full_res = response.choices[0].message.content
                    parts = full_res.split("|||")
                    
                    # 4. 双轨结果展示
                    st.subheader("📊 传统金融评估 (Hard Analysis)")
                    st.markdown(f'<div class="report-card">{parts[0]}</div>', unsafe_allow_html=True)
                    
                    st.markdown("---")
                    
                    st.subheader("🔮 PCCI 因果智能 (Causal Intelligence)")
                    st.markdown(f'<div class="report-card" style="border-left: 5px solid #4f46e5;">{parts[1] if len(parts)>1 else "AI 逻辑生成失败"}</div>', unsafe_allow_html=True)
                except Exception as e:
                    st.error(f"AI 调用失败: {str(e)}")

elif mode == "事件推演":
    event_text = st.text_area("输入现实事件内容", placeholder="例如：美联储宣布降息...")
    target = st.text_input("关注资产 (可选)")
    if st.button("运行推演"):
        # 逻辑同上，仅 Prompt 不同
        st.info("事件推演报告生成中...")

elif mode == "组合体检":
    assets = st.text_area("输入资产清单 (每行一个)", placeholder="NVDA\nBTC-USD\n600036.SS")
    if st.button("运行诊断"):
        st.info("组合脆弱性诊断中...")