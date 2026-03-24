import streamlit as st
import yfinance as yf
import pandas as pd
import openai
from datetime import datetime, timedelta
import re

# ==========================================
# 1. 页面配置与持久化初始化
# ==========================================
st.set_page_config(page_title="PCCI v7.2 - 因果智能引擎", layout="wide")

# 初始化 Session State，防止页面刷新导致结果丢失
state_keys =[
    "api_ready", "profiler_res", "event_res", "diag_res", 
    "manual_api_key", "manual_base_url", "manual_model_name", "hard_data_cache"
]
for key in state_keys:
    if key not in st.session_state:
        st.session_state[key] = None if "res" in key else False

# 全局 CSS 样式优化
st.markdown("""
    <style>
    .stMarkdown code { background-color: transparent !important; color: #e11d48 !important; font-family: monospace; font-size: 0.9em; }
    .status-text { font-size: 0.85rem; font-weight: bold; margin-left: 5px; }
    .report-card { background: white; padding: 2rem; border-radius: 1.5rem; border: 1px solid #e2e8f0; box-shadow: 0 4px 6px -1px rgba(0,0,0,0.1); }
    .stMarkdown h1, .stMarkdown h2, .stMarkdown h3 { color: #1e293b !important; padding-top: 1rem !important; border-bottom: none !important; }
    .stMarkdown table { width: 100%; border-collapse: collapse; margin-top: 1rem; margin-bottom: 1rem; }
    .stMarkdown th { background-color: #f8fafc; text-align: left; padding: 8px; border: 1px solid #e2e8f0; }
    .stMarkdown td { padding: 8px; border: 1px solid #e2e8f0; }
    </style>
""", unsafe_allow_html=True)

# ==========================================
# 2. PCCI 框架级 System Prompts (严密思维链)
# ==========================================
PROMPTS = {
    "profiler": """Role: 金融双轨分析师（PCCI 框架）。
任务：结合传入的 Python【实时硬数据】和【PCCI 因果框架】，对目标资产进行深度透视。
必须严格分为两部分输出，中间用 |||SEPARATOR||| 分隔。

第一部分：【传统金融评估】(客观、数据驱动)
- 估值水位：基于传入的 PE/PEG 等硬数据，判断估值是透支、合理还是低估？
- 因子暴露：基于传入的相关性数据，解读其对大盘、全球利率(US 10Y)、汇率的真实敏感度。
- 简要结论：仅从纯数据角度看，当前位置的安全边际如何？

|||SEPARATOR|||

第二部分：【PCCI 因果智能推演】(洞察、逻辑驱动)
- 🎯 身份锚定：一句话定义其金融属性（如：“高贝塔的AI周期期权”或“防守型通胀保值资产”）。
- 🚀 完美世界假设 (Bull Thesis)：买入该资产的人，此刻隐含在赌一个什么样的宏观/行业剧本？
- ⚠️ 致命弱点 (Kill Switch)：发生什么具体的宏观情境或基本面反转，会彻底击碎该资产的看涨逻辑？
- 🛡️ 协同与对冲：它跌的时候通常谁会跟着跌？用什么可以对冲它的单点风险？

注意：全部使用中文 Markdown 输出。""",

    "event": """Role: PCCI (以投资组合为中心的因果智能) 核心推演引擎。
任务：基于用户输入的【现实事件】，构建多世界叙事，并通过市场因子传导，推演其对不同时间尺度下资产的影响。

工作流 (必须严格按照以下结构输出)：
### 1. 核心世界构建 (The World State)
- **事件定性**：一句话概括事件本质。
- **激活世界**：定义当前的主导世界叙事 (如: "预防性宽松世界") 和潜在风险世界 (如: "衰退恐慌世界")。
- **因子变化盘面**：用表格展示该事件对四大核心因子 (实际利率、美元强弱、市场流动性、风险偏好) 的影响方向 (↑/↓/⚪) 及强度。

### 2. 多维资产推演矩阵 (The Matrix)
用 Markdown 表格列出受影响的代表性资产或行业。必须包含以下列：
| 资产/行业 | 时间尺度 (短/中/长) | 影响方向 (🟢/🔴/⚪) | PCCI 核心因果逻辑 |

### 3. 投资叙事总结 (Narrative)
- **机会提示**：当前世界状态下的因子共振机会。
- **关注反转点 (Kill Switch)**：发生什么后续事件，会导致上述世界状态坍塌或推演失效？

注意：全部使用中文 Markdown 输出。如用户未指定资产，请自动推演受影响最显著的 5 大资产。""",

    "diagnostic": """Role: 资深组合风险经理 (PCCI Diagnostic Mode)。
任务：对用户提供的【资产清单/投资组合】进行深度因子暴露分析与系统性脆弱性体检。不要做简单的涨跌预测，而是分析其“性格”和“底牌”。

请按以下结构输出中文分析报告：

### 一、 资产个体解剖
对组合中的【每一个资产】，提炼核心逻辑：
- **[资产名称]**：
  - 🧩 因子指纹：它最受哪 2-3 个宏观因子支配？
  - 🚀 隐含世界观：持有它，意味着在赌什么未来？
  - ⚠️ 致命弱点 (Kill Switch)：什么黑天鹅会引发它的暴跌？

### 二、 组合系统性风险评估 (Portfolio Synthesis)
- **因子拥挤度 (Factor Crowding)**：审视整个组合，是否存在“同质化对赌”？（例如：表面上买了科技股和比特币，本质上都在赌“流动性泛滥和降息”，一旦利率反弹，组合将面临全线崩溃）。
- **缺失的拼图 (Hedge Suggestion)**：针对当前组合的共同弱点，强烈建议补充什么类型的资产来形成“全天候”保护？

注意：全部使用中文 Markdown 输出。"""
}

# ==========================================
# 3. 核心工具函数 (数据获取与清洗)
# ==========================================
def terminal_clean_markdown(text):
    """彻底剥离 LLM 自动添加的 Markdown 代码块包装"""
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
    """【优雅降级版】抓取硬数据，防 Yahoo 封禁"""
    ticker_symbol = ticker_symbol.upper().strip()
    if ticker_symbol.isdigit() and len(ticker_symbol) == 6:
        return {"error": f"代码不全。上海: {ticker_symbol}.SS | 深圳: {ticker_symbol}.SZ"}

    cfg = {"name": "Global", "market": "SPY", "rate": "^TNX", "cur": "DX-Y.NYB"}
    if ticker_symbol.endswith(".SS") or ticker_symbol.endswith(".SZ"):
        cfg = {"name": "A-Share", "market": "000001.SS", "rate": "^TNX", "cur": "CNY=X"}
    elif ticker_symbol.endswith(".HK"):
        cfg = {"name": "Hong Kong", "market": "^HSI", "rate": "^TNX", "cur": "CNY=X"}

    # 1. 优先获取历史行情 (不易被封禁)
    try:
        end = datetime.now()
        start = end - timedelta(days=365)
        data = yf.download([ticker_symbol, cfg['market'], cfg['rate'], cfg['cur']], 
                           start=start, end=end, progress=False)['Close']
        if data.empty or ticker_symbol not in data.columns:
            return {"error": f"找不到该标的行情: {ticker_symbol}"}
            
        df = data.ffill().pct_change().dropna()
        corrs = df.corr()[ticker_symbol].to_dict() if ticker_symbol in df.columns else {}
        fallback_price = round(data[ticker_symbol].dropna().iloc[-1], 2)
    except Exception as e:
        return {"error": f"Yahoo 行情限流或报错: {str(e)}"}

    # 2. 尝试获取基本面 (极易被封禁，失败则使用降级数据)
    price, pe, peg = fallback_price, "N/A", "N/A"
    try:
        t = yf.Ticker(ticker_symbol)
        info = t.info
        price = info.get('currentPrice') or info.get('regularMarketPrice') or fallback_price
        pe = info.get('trailingPE', 'N/A')
        peg = info.get('pegRatio', 'N/A')
    except:
        pass # 静默处理，使用 fallback 数据

    return {
        "symbol": ticker_symbol, 
        "fundamentals": {"price": price, "pe": pe, "peg": peg, "region": cfg['name']}, 
        "factors": corrs
    }

# ==========================================
# 4. 初始化与侧边栏配置
# ==========================================
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
    st.title("🧠 PCCI v7.2")
    st.markdown(f"**API 状态:** {'🟢 在线' if st.session_state.api_ready else '🔴 离线'}")
    
    with st.expander("🔧 手动配置覆盖"):
        new_key = st.text_input("API Key", type="password")
        new_url = st.text_input("Base URL", placeholder="https://api.openai.com/v1")
        new_model = st.text_input("Model Name", placeholder="gpt-4o")
        if st.button("测试并应用"):
            st.session_state.manual_api_key, st.session_state.manual_base_url, st.session_state.manual_model_name = new_key, new_url, new_model
            ck, cu, cm = get_current_config()
            st.session_state.api_ready = check_api_connection(ck, cu, cm)
            st.rerun()

    st.divider()
    mode = st.radio("系统功能模块", ["单标的透视", "事件推演", "组合体检"])
    
    st.divider()
    if st.button("🗑️ 清空当前推演缓存"):
        st.session_state.profiler_res = st.session_state.event_res = st.session_state.diag_res = None
        st.session_state.hard_data_cache = None
        st.rerun()

# ==========================================
# 5. 核心业务逻辑与渲染
# ==========================================
cur_key, cur_url, cur_model = get_current_config()
client = openai.OpenAI(api_key=cur_key, base_url=cur_url) if st.session_state.api_ready else None

# --- 模块 1: 单标的透视 ---
if mode == "单标的透视":
    st.subheader("🎯 单标的全维因子透视")
    ticker = st.text_input("输入资产代码", value="NVDA", placeholder="示例: NVDA | 600036.SS | 0700.HK | BTC-USD").upper().strip()
    
    if st.button("运行透视分析"):
        if not client: st.error("⚠️ 请先在侧边栏配置 API 并在连通测试后使用。")
        else:
            with st.status("执行因果推演引擎...", expanded=True) as status:
                # 1. 抓取硬数据
                st.write("1. 正在调取量化硬数据...")
                hd = get_hard_data(ticker)
                
                # 2. 容错处理
                if "error" in hd:
                    st.warning(f"⚠️ 无法获取实时数据 ({hd['error']})。引擎将自动降级为「纯常识逻辑推演」。")
                    st.session_state.hard_data_cache = None
                    hd_context = "当前由于接口限流，无法获取实时量化数据。请完全基于大模型的内部知识库对该资产进行逻辑评估。"
                else:
                    st.session_state.hard_data_cache = hd
                    hd_context = str(hd)

                # 3. 构造框架 Prompt
                st.write("2. 正在进行多世界推演与反转点分析...")
                prompt = f"分析资产: {ticker}\n硬数据/环境: {hd_context}\n\n请严格遵守 System Prompt 的结构和分隔符要求进行输出。"
                
                try:
                    resp = client.chat.completions.create(
                        model=cur_model, 
                        messages=[{"role": "system", "content": PROMPTS["profiler"]}, {"role": "user", "content": prompt}]
                    )
                    st.session_state.profiler_res = terminal_clean_markdown(resp.choices[0].message.content)
                    status.update(label="分析完成！", state="complete")
                except Exception as e:
                    status.update(label="推演失败", state="error")
                    st.error(f"大模型接口报错: {e}")
    
    # 渲染结果 (利用 Session State 持久化)
    if st.session_state.hard_data_cache:
        hd = st.session_state.hard_data_cache
        c1, c2, c3 = st.columns(3)
        c1.metric("当前价格", hd['fundamentals']['price'])
        c2.metric("PEG 估值水位", hd['fundamentals']['peg'])
        c3.metric("对比基准市场", hd['fundamentals']['region'])
    
    if st.session_state.profiler_res:
        parts = st.session_state.profiler_res.split("|||SEPARATOR|||")
        st.markdown("### 📊 传统金融量化评估")
        st.info(terminal_clean_markdown(parts[0]))
        if len(parts) > 1:
            st.markdown("### 🔮 PCCI 因果智能推演")
            st.success(terminal_clean_markdown(parts[1]))

# --- 模块 2: 事件推演 ---
elif mode == "事件推演":
    st.subheader("⚡ 现实事件因果推演")
    event_input = st.text_area("输入现实事件/新闻/公告", height=150, placeholder="例如：美国 CPI 数据超预期反弹，美联储鹰派发声...")
    focus_assets = st.text_input("特别关注资产 (选填)", placeholder="例如: 黄金, 美债, 纳指")
    
    if st.button("开始事件推演"):
        if not client: st.error("⚠️ API 离线，请检查侧边栏配置。")
        else:
            with st.spinner("AI 正在构建多世界因果链条..."):
                prompt = f"现实事件: {event_input}\n特别关注资产: {focus_assets if focus_assets else '自动匹配关联资产'}"
                try:
                    resp = client.chat.completions.create(
                        model=cur_model, 
                        messages=[{"role": "system", "content": PROMPTS["event"]}, {"role": "user", "content": prompt}]
                    )
                    st.session_state.event_res = terminal_clean_markdown(resp.choices[0].message.content)
                except Exception as e:
                    st.error(f"调用失败: {e}")
    
    if st.session_state.event_res:
        st.markdown("---")
        st.markdown(st.session_state.event_res, unsafe_allow_html=True)

# --- 模块 3: 组合体检 ---
elif mode == "组合体检":
    st.subheader("🩺 投资组合脆弱性诊断")
    portfolio_text = st.text_area("输入当前持仓资产清单 (每行一个)", height=150, placeholder="NVDA\n600036.SS\nBTC-USD\nTLT")
    
    if st.button("开始全量体检"):
        if not client: st.error("⚠️ API 离线，请检查侧边栏配置。")
        else:
            with st.spinner("AI 正在扫描组合系统性风险与因子拥挤度..."):
                prompt = f"资产清单:\n{portfolio_text}"
                try:
                    resp = client.chat.completions.create(
                        model=cur_model, 
                        messages=[{"role": "system", "content": PROMPTS["diagnostic"]}, {"role": "user", "content": prompt}]
                    )
                    st.session_state.diag_res = terminal_clean_markdown(resp.choices[0].message.content)
                except Exception as e:
                    st.error(f"调用失败: {e}")
    
    if st.session_state.diag_res:
        st.markdown("---")
        st.markdown(st.session_state.diag_res, unsafe_allow_html=True)        if data.empty or ticker_symbol not in data.columns:
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
