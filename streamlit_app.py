import streamlit as st
import yfinance as yf
import pandas as pd
import openai
from datetime import datetime, timedelta

# --- 页面配置 ---
st.set_page_config(page_title="PCCI v6 - 因果智能引擎", layout="wide")

# --- 侧边栏：配置与输入 ---
with st.sidebar:
    st.title("⚙️ PCCI 配置")
    
    # 优先从 Secrets 读取，否则留空
    default_key = st.secrets.get("AI_API_KEY", "")
    default_url = st.secrets.get("AI_BASE_URL", "https://api.openai.com/v1")
    default_model = st.secrets.get("AI_MODEL", "gpt-4o")

    api_key = st.text_input("API Key", type="password", value=default_key)
    base_url = st.text_input("Base URL", value=default_url)
    model = st.text_input("Model Name", value=default_model)
    
    # --- AI 连通性测试功能 ---
    if st.button("⚡ 测试 AI 连接"):
        if not api_key:
            st.error("请输入 API Key")
        else:
            try:
                client = openai.OpenAI(api_key=api_key, base_url=base_url)
                # 发送一个极其简单的请求测试连通性
                test_resp = client.chat.completions.create(
                    model=model,
                    messages=[{"role": "user", "content": "hi"}],
                    max_tokens=5
                )
                st.success("✅ 联通测试成功！")
            except Exception as e:
                st.error(f"❌ 连接失败: {str(e)}")
    
    st.divider()
    mode = st.radio("选择分析模式", ["单标的透视", "事件推演", "组合体检"])

# --- 后端逻辑：财务数据抓取 ---
def get_hard_data(ticker_symbol):
    try:
        t = yf.Ticker(ticker_symbol)
        info = t.info
        # 获取价格 (兼容不同市场的字段)
        price = info.get('currentPrice') or info.get('regularMarketPrice') or info.get('previousClose', 'N/A')
        
        region = "Global"
        market = "SPY"
        if ".SS" in ticker_symbol or ".SZ" in ticker_symbol: 
            region, market = "China A-Share", "000001.SS"
        elif ".HK" in ticker_symbol: 
            region, market = "Hong Kong", "^HSI"

        # 获取历史数据计算相关性
        end = datetime.now()
        start = end - timedelta(days=365)
        # 抓取标的和对应的大盘、美债、黄金
        tickers_to_watch = [ticker_symbol, market, "^TNX", "GLD"]
        data = yf.download(tickers_to_watch, start=start, end=end, progress=False)['Close']
        
        # 确保数据对齐
        df = data.ffill().pct_change().dropna()
        corrs = {}
        if ticker_symbol.upper() in df.columns:
            corrs = df.corr()[ticker_symbol.upper()].to_dict()

        return {
            "symbol": ticker_symbol,
            "fundamentals": {
                "price": price, 
                "pe": info.get('trailingPE', 'N/A'), 
                "peg": info.get('pegRatio', 'N/A'), 
                "region": region
            },
            "factors": corrs
        }
    except Exception as e:
        return {"error": f"数据抓取失败: {str(e)}"}

# --- 主界面 ---
st.title("🧠 PCCI v6 因果智能引擎")

if mode == "单标的透视":
    ticker = st.text_input("输入资产代码 (如 NVDA, 600036.SS, BTC-USD)", value="NVDA").upper().strip()
    
    if st.button("开始双轨分析"):
        if not api_key:
            st.warning("⚠️ 请先在侧边栏配置 API Key")
        else:
            # 使用 st.status 展示步骤 (更现代的加载方式)
            with st.status("正在进行全维分析...", expanded=True) as status:
                st.write("正在从 Yahoo Finance 获取实时硬数据...")
                hard_data = get_hard_data(ticker)
                
                if "error" in hard_data:
                    st.error(hard_data["error"])
                    status.update(label="数据获取失败", state="error")
                else:
                    st.write("硬数据获取成功，正在调用 AI 进行因果推演...")
                    
                    # 准备展示硬数据指标
                    col1, col2, col3, col4 = st.columns(4)
                    col1.metric("价格", hard_data['fundamentals']['price'])
                    col2.metric("PEG", hard_data['fundamentals']['peg'])
                    col3.metric("地区", hard_data['fundamentals']['region'])
                    # 提取利率相关性
                    rate_corr = hard_data['factors'].get('^TNX', 'N/A')
                    col4.metric("利率相关性", f"{rate_corr:.2f}" if isinstance(rate_corr, float) else "N/A")

                    # 调用 AI
                    client = openai.OpenAI(api_key=api_key, base_url=base_url)
                    prompt = f"""分析标的: {ticker}
                    硬数据快照: {hard_data}
                    
                    请输出两部分内容，中间用 ||| 分隔。
                    
                    第一部分：【传统金融评估】
                    基于 PE/PEG 估值、Beta、利率和汇率相关性等硬数据给出客观评价。
                    
                    第二部分：【PCCI 因果智能推演】
                    1. 资产身份定位。
                    2. 完美世界假设（上涨需要什么情景）。
                    3. 脆弱性分析 (Kill Switch)。
                    
                    中文输出，使用 Markdown。"""
                    
                    try:
                        response = client.chat.completions.create(
                            model=model,
                            messages=[{"role": "user", "content": prompt}]
                        )
                        full_res = response.choices[0].message.content
                        
                        if "|||" in full_res:
                            parts = full_res.split("|||")
                        else:
                            parts = [full_res, "AI 未按格式输出第二部分"]
                            
                        status.update(label="分析完成！", state="complete", expanded=False)
                        
                        # 展示结果
                        st.subheader("📊 传统金融评估")
                        st.info(parts[0])
                        
                        st.subheader("🔮 PCCI 因果智能")
                        st.success(parts[1])
                        
                    except Exception as e:
                        st.error(f"AI 推演阶段出错: {str(e)}")
                        status.update(label="AI 推演失败", state="error")

elif mode == "事件推演":
    st.info("此功能正在集成中，逻辑同单标的透视。")

elif mode == "组合体检":
    st.info("此功能正在集成中。")