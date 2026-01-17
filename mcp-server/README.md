# A股智能分析 MCP Server

为 Claude Desktop 提供 A 股个股深度分析能力的 MCP Server。

## 功能

- **analyze_stock** - 执行完整的个股分析（技术面、基本面、资金面、新闻面）
- **resolve_ticker** - 股票名称转代码（支持简称如"茅台"→"600519"）
- **check_analysis_env** - 检查运行环境配置
- **read_stock_report** - 读取已生成的分析报告
- **list_analysis_history** - 查看历史分析记录

## 安装

### 1. 安装依赖

```bash
cd /Users/qm/TradingAgents-Chinese/mcp-server
pip install mcp
```

### 2. 配置环境变量

在你的 shell 配置文件（`~/.zshrc` 或 `~/.bashrc`）中添加：

```bash
# A股数据接口（必需）
export TUSHARE_TOKEN="your_tushare_token"

# LLM API 密钥（至少配置一个）
export ANTHROPIC_API_KEY="your_anthropic_key"    # 推荐
# 或
export DASHSCOPE_API_KEY="your_dashscope_key"   # 阿里云通义千问
# 或
export OPENAI_API_KEY="your_openai_key"         # OpenAI
```

### 3. 配置 Claude Desktop

编辑 Claude Desktop 配置文件：

**macOS**: `~/Library/Application Support/Claude/claude_desktop_config.json`

**Windows**: `%APPDATA%\Claude\claude_desktop_config.json`

添加以下配置：

```json
{
  "mcpServers": {
    "a-share-analyzer": {
      "command": "python",
      "args": ["/Users/qm/TradingAgents-Chinese/mcp-server/server.py"],
      "env": {
        "TUSHARE_TOKEN": "your_tushare_token",
        "ANTHROPIC_API_KEY": "your_anthropic_key"
      }
    }
  }
}
```

> **注意**: 将 `your_tushare_token` 和 `your_anthropic_key` 替换为你的实际密钥。

### 4. 重启 Claude Desktop

配置完成后，完全退出并重新启动 Claude Desktop。

## 使用方法

在 Claude Desktop 中直接对话：

```
分析一下招商银行

帮我看看茅台最近怎么样

深度分析 600036

查看 600519 的技术面报告
```

## 可用命令示例

| 用户说 | Claude 会做 |
|-------|------------|
| "分析招商银行" | 调用 analyze_stock，执行完整分析 |
| "茅台代码是多少" | 调用 resolve_ticker，返回 600519 |
| "检查分析环境" | 调用 check_analysis_env |
| "显示 600036 的基本面报告" | 调用 read_stock_report |
| "600519 有哪些历史分析" | 调用 list_analysis_history |

## 分析深度

| 深度 | 辩论轮数 | 耗时 | 适用场景 |
|------|---------|------|---------|
| shallow | 1轮 | 3-5分钟 | 快速参考 |
| medium | 3轮 | 5-8分钟 | 日常分析（默认） |
| deep | 5轮 | 8-15分钟 | 重大决策 |

## 输出报告

分析完成后，报告保存在：
```
/Users/qm/TradingAgents-Chinese/results/{股票代码}/{日期}/reports/
├── market_report.md          # 技术面分析
├── sentiment_report.md       # 资金面分析
├── news_report.md            # 新闻分析
├── fundamentals_report.md    # 基本面分析
├── trader_investment_plan.md # 交易计划
├── final_trade_decision.md   # 最终决策
└── consolidation_report.md   # 综合研报
```

## 故障排除

### MCP Server 未显示

1. 检查配置文件路径是否正确
2. 检查 Python 路径是否正确（可用 `which python` 确认）
3. 查看 Claude Desktop 日志

### 分析失败

1. 运行环境检查：在 Claude 中说"检查分析环境"
2. 确认 TUSHARE_TOKEN 有效且积分充足
3. 确认 LLM API 密钥正确

### 超时

- 使用 `shallow` 深度进行快速分析
- 检查网络连接

## 技术架构

```
Claude Desktop
     ↓ MCP Protocol
MCP Server (server.py)
     ↓
TradingAgentsGraph
     ↓
┌─────────────────────┐
│ Analyst Team        │
│ Research Team       │
│ Trading Team        │
│ Risk Management     │
└─────────────────────┘
     ↓
分析报告 (BUY/SELL/HOLD)
```
