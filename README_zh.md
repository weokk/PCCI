---
[English](README.md) | [中文](README_zh.md)

PCCI (以投资组合为中心的因果智能) 是下一代投资分析引擎。它结合了实时金融硬数据（通过 yfinance）与大语言模型（LLM）的推理能力，提供“双轨制”洞察：传统金融评估与因果逻辑推演。与黑盒预测工具不同，PCCI 专注于解释市场波动的“因果逻辑”以及投资假设的“脆弱性”。

## 🌟 核心亮点

- **双轨分析机制**：每一份报告都包含基于数据的“传统金融评估”与基于逻辑的“PCCI 因果推演”。
- **硬数据集成**：利用 Python `yfinance` 实时提取 PE、PEG 以及跨资产相关性（大盘 Beta、利率敏感度、汇率敏感度、黄金对冲）。
- **因果推理（多世界）**：分析资产背后的“完美世界”假设，并识别触发逻辑坍塌的“反转开关”（脆弱性分析）。
- **全市场覆盖**：原生支持美股、港股及 A 股（沪深交易所）。
- **Streamlit 驱动**：极其简洁专业的 UI，支持一键部署至云端。

## 🏗️ PCCI 核心逻辑

1. **现实事件/资产输入**：获取宏观新闻或特定标的。
2. **硬数据核心 (Python)**：计算量化因子与市场环境相关性。
3. **因果推演 (LLM)**：将硬数据转化为因果链条，模拟潜在的世界演化状态。
4. **双轨输出**：可视化展示硬性数据与软性逻辑之间的冲突与共鸣。

## 🚀 快速开始

### 1. 准备工作
- Python 3.9+
- 兼容 OpenAI 接口的 API Key (OpenAI, DeepSeek, 豆包等)

### 2. 本地运行
```bash
git clone https://github.com/your-username/pcci-intelligence.git
cd pcci-intelligence
pip install -r requirements.txt
streamlit run streamlit_app.py
```

### 3. 云端部署 (Streamlit Cloud)
1. Fork 本仓库。
2. 在 [Streamlit Cloud](https://share.streamlit.io/) 导入仓库。
3. 在 Advanced Settings 中配置 Secrets (API Key, Base URL等)。

## ⚠️ 免责声明
本工具仅供**信息参考与研究使用**，不构成任何投资建议。投资有风险，决策需谨慎。
```

---
