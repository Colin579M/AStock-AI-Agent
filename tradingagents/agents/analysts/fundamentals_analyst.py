from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
import time
import json
from tradingagents.agents.utils.agent_utils import is_china_stock


def create_fundamentals_analyst(llm, toolkit):
    def fundamentals_analyst_node(state):
        current_date = state["trade_date"]
        ticker = state["company_of_interest"]
        company_name = state["company_of_interest"]

        # 根据市场类型选择工具
        if is_china_stock(ticker):
            # 中国A股使用 Tushare Pro 基本面工具（高质量数据）+ 机构观点工具
            tools = [
                toolkit.get_tushare_stock_basic,           # 首先获取股票基本信息（准确名称）
                toolkit.get_tushare_financial_statements,  # 财务三表
                toolkit.get_tushare_financial_indicators,  # 150+财务指标
                toolkit.get_tushare_daily_basic,           # 每日估值指标
                toolkit.get_tushare_forecast,              # 业绩预告
                toolkit.get_tushare_dividend,              # 分红历史
                toolkit.get_tushare_fundamentals_comprehensive,  # 综合数据包
                # === Phase 2.2 新增工具：机构观点整合 ===
                toolkit.get_tushare_stk_surv,              # 机构调研数据
                toolkit.get_tushare_report_rc,             # 券商研报数据
                toolkit.get_tushare_index_member,          # 行业成分股（用于同行对比）
            ]
            system_message = """您是一位专业的中国A股基本面分析师，负责深入分析上市公司的财务状况和投资价值。

【重要】您必须使用 Tushare 系列工具获取数据，这些是最准确的数据源：
1. **首先调用 get_tushare_stock_basic** 获取股票基本信息，确认股票的准确名称
2. 调用 get_tushare_financial_statements 获取财务三表（利润表、资产负债表、现金流量表）
3. 调用 get_tushare_financial_indicators 获取150+财务指标（ROE/ROA/毛利率/净利率等）
4. 调用 get_tushare_daily_basic 获取最新估值数据（PE/PB/PS/市值/换手率）
5. 调用 get_tushare_forecast 获取业绩预告信息
6. 调用 get_tushare_dividend 获取分红历史
7. 或直接调用 get_tushare_fundamentals_comprehensive 获取综合数据包
8. **新增** 调用 get_tushare_stk_surv 获取机构调研数据
9. **新增** 调用 get_tushare_report_rc 获取券商研报和目标价
10. **新增** 调用 get_tushare_index_member 获取行业成分股列表（用于同行对比）

【股票代码格式】Tushare使用的格式：
- 上海股票：股票代码.SH（如 601899.SH）
- 深圳股票：股票代码.SZ（如 000001.SZ）
- 行业指数：399318.SZ（国证有色）、399986.SZ（中证银行）

分析要点：
- **盈利能力分析**: 分析ROE、毛利率、净利率的趋势和行业对比
- **估值水平评估**: 分析PE、PB是否处于合理区间，与历史估值对比
- **成长性分析**: 分析营收增长率、净利润增长率，评估增长质量
- **财务健康度**: 分析资产负债率、流动比率、速动比率，评估偿债能力
- **现金流质量**: 分析经营性现金流是否健康，是否能覆盖投资需求
- **业绩预期**: 分析业绩预告信息，评估未来增长预期

【新增】机构观点整合分析：

1. **券商研报分析**（使用 get_tushare_report_rc）:
   - 近30天研报数量和评级分布
   - 目标价变化趋势（上调/下调）
   - 核心研报观点摘要
   - 一致预期盈利调整方向
   - 引用数据示例："近30天X家券商覆盖，Y家买入/Z家持有，平均目标价N元"

2. **机构调研追踪**（使用 get_tushare_stk_surv）:
   - 近期机构调研次数
   - 参与调研的机构类型（公募/私募/保险/外资）
   - 调研密度变化（调研增多通常是关注度提升）
   - 引用数据示例："近6个月共X次机构调研，公募基金参与Y家次"

3. **行业对比分析**（使用 get_tushare_index_member）:
   - 获取同行业成分股列表
   - 与龙头公司估值对比（PE/PB/市值）
   - 龙头溢价率计算
   - 相对估值是否合理
   - 引用数据示例："行业PE均值X倍，公司PE Y倍，溢价/折价Z%"

4. **估值历史分位**:
   - 当前PE处于近3年的百分位
   - PB处于近3年的百分位
   - 估值分位>80%需提示高估风险，<20%可能被低估
   - 引用数据示例："当前PE X倍，处于近3年Y%分位"

中国A股特色考虑：
- 季报披露时间节点（4月、8月、10月）
- 年报预约披露时间
- 商誉减值风险
- 大股东质押比例
- 限售股解禁压力

请撰写详细的中文基本面分析报告，在报告标题中使用从 get_tushare_stock_basic 获取的准确股票名称。

报告必须包含以下内容：
1. 核心财务指标分析（ROE/ROA/毛利率/净利率）
2. 估值水平及历史分位
3. 券商评级汇总和目标价统计
4. 机构调研情况
5. 行业对比分析

报告末尾附上两个Markdown表格：

表1：关键财务指标
| 指标 | 最新值 | 同比变化 | 行业均值 | 评价 |
|------|--------|---------|---------|------|

表2：机构观点汇总
| 维度 | 数据 | 判断 |
|------|------|------|
| 券商评级 | 买入X家/持有Y家 | 一致看好/存在分歧 |
| 平均目标价 | X元 | 较现价上涨/下跌Y% |
| 机构调研 | 近6月X次 | 关注度高/一般/低 |
| 估值分位 | X% | 高估/合理/低估 |

【数据缺失处理】
如果某些数据无法获取，请按以下方式处理：
1. **必需数据**（财务报表、基本指标）：如缺失，需明确说明"数据暂不可用"，并标注分析置信度降低
2. **补充数据**（券商研报、机构调研）：如缺失，可跳过该部分，在报告末尾注明
3. **对比数据**（行业均值、历史分位）：如缺失，使用"暂无对比基准"代替，不做臆测

置信度评估（在报告末尾标注）：
- 高置信度：所有必需数据齐全
- 中置信度：缺失部分补充数据
- 低置信度：缺失必需数据，建议谨慎参考"""
        elif toolkit.config["online_tools"]:
            tools = [toolkit.get_fundamentals_openai]
            system_message = (
                "You are a researcher tasked with analyzing fundamental information over the past week about a company. Please write a comprehensive report of the company's fundamental information such as financial documents, company profile, basic company financials, company financial history, insider sentiment and insider transactions to gain a full view of the company's fundamental information to inform traders. Make sure to include as much detail as possible. Do not simply state the trends are mixed, provide detailed and finegrained analysis and insights that may help traders make decisions."
                + " Make sure to append a Markdown table at the end of the report to organize key points in the report, organized and easy to read."
            )
        else:
            tools = [
                toolkit.get_finnhub_company_insider_sentiment,
                toolkit.get_finnhub_company_insider_transactions,
                toolkit.get_simfin_balance_sheet,
                toolkit.get_simfin_cashflow,
                toolkit.get_simfin_income_stmt,
            ]
            system_message = (
                "You are a researcher tasked with analyzing fundamental information over the past week about a company. Please write a comprehensive report of the company's fundamental information such as financial documents, company profile, basic company financials, company financial history, insider sentiment and insider transactions to gain a full view of the company's fundamental information to inform traders. Make sure to include as much detail as possible. Do not simply state the trends are mixed, provide detailed and finegrained analysis and insights that may help traders make decisions."
                + " Make sure to append a Markdown table at the end of the report to organize key points in the report, organized and easy to read."
            )

        prompt = ChatPromptTemplate.from_messages(
            [
                (
                    "system",
                    "You are a helpful AI assistant, collaborating with other assistants."
                    " Use the provided tools to progress towards answering the question."
                    " If you are unable to fully answer, that's OK; another assistant with different tools"
                    " will help where you left off. Execute what you can to make progress."
                    " If you or any other assistant has the FINAL TRANSACTION PROPOSAL: **BUY/HOLD/SELL** or deliverable,"
                    " prefix your response with FINAL TRANSACTION PROPOSAL: **BUY/HOLD/SELL** so the team knows to stop."
                    " You have access to the following tools: {tool_names}.\n{system_message}"
                    "For your reference, the current date is {current_date}. The company we want to look at is {ticker}",
                ),
                MessagesPlaceholder(variable_name="messages"),
            ]
        )

        prompt = prompt.partial(system_message=system_message)
        prompt = prompt.partial(tool_names=", ".join([tool.name for tool in tools]))
        prompt = prompt.partial(current_date=current_date)
        prompt = prompt.partial(ticker=ticker)

        chain = prompt | llm.bind_tools(tools)

        result = chain.invoke(state["messages"])

        report = ""

        if len(result.tool_calls) == 0:
            report = result.content

        return {
            "messages": [result],
            "fundamentals_report": report,
        }

    return fundamentals_analyst_node
