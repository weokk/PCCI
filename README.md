# PCCI
PCCI is a white-box investment analysis framework designed to move beyond simple "up or down" predictions. It empowers investors to understand the **causal chains** behind market movements and the **fragility** of their portfolios across different macro scenarios.
# PCCI: Portfolio-Centric Causal Intelligence 🧠📈

[English](README.md) | [中文](README_zh.md)



## 🌟 Key Features

- **Dual-Track Analysis**: Every report is split into a data-driven "Traditional Evaluation" and a logic-driven "Causal Intelligence" deduction.
- **Hard Data Integration**: Real-time extraction of PE, PEG, and cross-asset correlations (Market Beta, Rates, FX, Gold) using Python's `yfinance`.
- **Causal Reasoning (Multi-Worlds)**: Deduces the "Perfect World" assumed by an asset and identifies the "Kill Switch" (vulnerability) that could collapse the thesis.
- **Cross-Market Support**: Native support for US Equities, HK Stocks, and China A-Shares (SSE/SZSE).
- **Streamlit Powered**: A clean, professional UI deployable to the cloud in minutes.

## 🏗️ Architecture: The PCCI Logic

1. **Reality Event / Asset Input**: Capture macro news or specific tickers.
2. **Hard Data Core (Python)**: Calculate quantitative factors and regime correlations.
3. **Causal Deduction (LLM)**: Map hard data into causal chains and simulate potential world states.
4. **Dual-Track Output**: Visualize the conflict and synergy between hard numbers and soft logic.

## 🚀 Quick Start

### 1. Prerequisites
- Python 3.9+
- An OpenAI-compatible API Key (OpenAI, DeepSeek, etc.)

### 2. Local Installation
```bash
# Clone the repository
git clone https://github.com/your-username/pcci-intelligence.git
cd pcci-intelligence

# Install dependencies
pip install -r requirements.txt

# Run the app
streamlit run streamlit_app.py
```

### 3. Deployment (Streamlit Cloud)
1. Fork this repository.
2. Connect your GitHub account to [Streamlit Cloud](https://share.streamlit.io/).
3. Add your secrets in the app settings:
   ```toml
   AI_API_KEY = "your_key_here"
   AI_BASE_URL = "https://api.openai.com/v1"
   AI_MODEL = "gpt-4o"
   ```

## 🛠️ Tech Stack
- **Language**: Python
- **Finance Data**: `yfinance`, `pandas`
- **AI Orchestration**: `OpenAI SDK`
- **Frontend**: `Streamlit`

## 📖 Methodology
PCCI stands for:
- **P**ortfolio-Centric: Analysis starts with what you own, not just what's in the news.
- **C**ausal **I**ntelligence: Focuses on the "Why" and the "Regime Change" rather than historical price patterns alone.

## ⚠️ Disclaimer
This tool is for **informational and research purposes only**. It does not constitute financial advice. Investment involves significant risk. Always perform your own due diligence.

