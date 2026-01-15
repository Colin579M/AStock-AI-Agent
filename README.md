# TradingAgents-Chinese

基于 [TradingAgents](https://github.com/TauricResearch/TradingAgents) 的中国A股多智能体交易分析框架。

## 项目简介

TradingAgents-Chinese 是一个专为中国A股市场优化的多智能体 LLM 交易分析框架。系统模拟真实交易机构的运作模式，部署多个专业化的 AI 代理协同分析市场，包括基本面分析师、情绪分析师、技术分析师、交易员和风险管理团队。

### 核心特性

- **中国A股数据源**: 集成 AKShare、TuShare Pro、通达信 API
- **多 LLM 提供商支持**: OpenAI、Anthropic、阿里云通义千问、Ollama 本地部署
- **决策记忆系统**: 基于 ChromaDB 的历史决策追踪与反思
- **实时行情**: 支持盘中实时数据获取和分析
- **智能缓存**: MongoDB + Redis + 文件三级缓存架构

## 系统架构

```
┌─────────────────────────────────────────────────────────────┐
│                      分析师团队                              │
├───────────────┬───────────────┬───────────────┬─────────────┤
│  基本面分析师  │   情绪分析师   │   新闻分析师   │  技术分析师  │
│  (财务/估值)   │  (社交媒体)    │   (宏观事件)   │  (MACD/RSI) │
└───────┬───────┴───────┬───────┴───────┬───────┴──────┬──────┘
        │               │               │              │
        └───────────────┼───────────────┴──────────────┘
                        ▼
┌─────────────────────────────────────────────────────────────┐
│                      研究员团队                              │
│              ┌─────────────┬─────────────┐                  │
│              │   多头研究员  │   空头研究员  │                  │
│              └──────┬──────┴──────┬──────┘                  │
│                     │   辩论协商   │                         │
│                     └──────┬──────┘                         │
└────────────────────────────┼────────────────────────────────┘
                             ▼
┌─────────────────────────────────────────────────────────────┐
│                       交易员                                 │
│              综合报告 → 交易计划制定                          │
└────────────────────────────┼────────────────────────────────┘
                             ▼
┌─────────────────────────────────────────────────────────────┐
│                    风险管理团队                               │
│    ┌──────────┬──────────┬──────────┐                       │
│    │ 激进分析师 │ 中性分析师 │ 保守分析师 │                       │
│    └────┬─────┴────┬─────┴────┬─────┘                       │
│         │    三方辩论    │         │                         │
│         └────────┬───────┘         │                         │
│                  ▼                                           │
│           风险评估裁决 → 最终决策                              │
└─────────────────────────────────────────────────────────────┘
```

## 快速开始

### 1. 环境配置

```bash
# 克隆仓库
git clone https://github.com/your-repo/TradingAgents-Chinese.git
cd TradingAgents-Chinese

# 创建虚拟环境
conda create -n tradingagents python=3.11
conda activate tradingagents

# 安装依赖
pip install -r requirements.txt
```

### 2. 配置 API 密钥

复制环境变量模板并填写你的 API 密钥：

```bash
cp .env.example .env
```

编辑 `.env` 文件：

```bash
# LLM API（至少配置一个）
OPENAI_API_KEY=your_openai_key
DASHSCOPE_API_KEY=your_dashscope_key  # 阿里云通义千问

# 数据源（推荐配置 TuShare）
TUSHARE_TOKEN=your_tushare_token
FINNHUB_API_KEY=your_finnhub_key  # 可选，用于美股
```

### 3. 运行 CLI

```bash
python -m cli.main
```

## 使用方式

### CLI 交互界面

CLI 提供完整的交互式分析界面：

1. 输入股票代码（如 `600036` 或 `000001`）
2. 选择分析日期
3. 选择 LLM 提供商和模型
4. 查看实时分析进度和最终决策

### Python API

```python
from tradingagents.graph.trading_graph import TradingAgentsGraph
from tradingagents.default_config import DEFAULT_CONFIG

# 初始化
config = DEFAULT_CONFIG.copy()
config["llm_provider"] = "dashscope"  # 使用通义千问
config["deep_think_llm"] = "qwen-max"
config["quick_think_llm"] = "qwen-plus"

ta = TradingAgentsGraph(debug=True, config=config)

# 分析股票
_, decision = ta.propagate("600036", "2025-01-10")
print(decision)
```

### 配置选项

| 配置项 | 说明 | 默认值 |
|--------|------|--------|
| `llm_provider` | LLM 提供商 | `openai` |
| `deep_think_llm` | 深度思考模型 | `gpt-4o` |
| `quick_think_llm` | 快速思考模型 | `gpt-4o-mini` |
| `max_debate_rounds` | 辩论轮数 | `1` |
| `online_tools` | 使用在线数据 | `True` |

## 数据源

| 数据源 | 用途 | 免费额度 |
|--------|------|----------|
| AKShare | A股行情、新闻、情绪 | 无限制 |
| TuShare Pro | 财务数据、研报 | 每日 500 次 |
| 通达信 | 实时行情 | 无限制 |
| FinnHub | 美股数据 | 每分钟 60 次 |

## 项目结构

```
TradingAgents-Chinese/
├── cli/                    # 命令行界面
├── tradingagents/
│   ├── agents/            # AI 代理实现
│   │   ├── analysts/      # 分析师（基本面、情绪、新闻、技术）
│   │   ├── researchers/   # 研究员（多头、空头）
│   │   ├── managers/      # 管理者（风险、研究）
│   │   └── utils/         # 工具（记忆系统）
│   ├── dataflows/         # 数据获取层
│   │   ├── akshare_utils.py
│   │   ├── tushare_utils.py
│   │   └── tdx_utils.py
│   ├── graph/             # LangGraph 工作流
│   └── llm_adapters/      # LLM 适配器
├── web-app/               # Web 界面（开发中）
└── requirements.txt
```

## 注意事项

- 本框架仅供研究和学习使用
- 交易决策受多种因素影响，包括 LLM 选择、数据质量等
- **不构成任何投资建议**

## 致谢

- [TradingAgents](https://github.com/TauricResearch/TradingAgents) - 原始框架
- [AKShare](https://github.com/akfamily/akshare) - A股数据源
- [TuShare](https://tushare.pro/) - 金融数据接口

## License

MIT License
