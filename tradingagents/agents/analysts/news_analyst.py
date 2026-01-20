from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
import time
import json
from tradingagents.agents.utils.agent_utils import is_china_stock


def create_news_analyst(llm, toolkit):
    def news_analyst_node(state):
        current_date = state["trade_date"]
        ticker = state["company_of_interest"]

        # 根据市场类型选择工具
        if is_china_stock(ticker):
            # 中国A股只使用国内新闻源（Tushare + akshare）
            # 注意：不使用 Google News，因为国内访问很慢
            tools = [
                toolkit.get_tushare_stock_basic,   # 首先获取股票基本信息（准确名称）
                toolkit.get_china_stock_news,      # akshare 个股新闻
                toolkit.get_tushare_cctv_news,     # Tushare 新闻联播（政策风向）
                toolkit.get_tushare_market_news,   # Tushare 市场新闻（整合新闻联播+重大新闻）
                toolkit.get_tushare_pmi,           # Tushare PMI 采购经理指数
                # === Phase 2.3 新增工具：概念板块 ===
                toolkit.get_tushare_concept,       # 概念板块分析（热点主题挖掘）
                # === 概念关联度验证工具（2026-01 新增）===
                toolkit.get_investor_qa,           # 互动易/e互动投资者问答
                toolkit.get_announcement_search,   # 公告搜索
                toolkit.get_concept_validation,    # 概念关联度综合验证
            ]
            system_message = """您是一位专业的中国财经新闻分析师，负责收集和分析与目标股票相关的新闻资讯和宏观经济数据。

═══════════════════════════════════════════════════════════════
【A股术语保护声明】请用中文思考和输出
═══════════════════════════════════════════════════════════════

请用中文思考和输出，保留A股市场的完整语境。
以下术语请勿翻译或英文化，直接使用中文原文：
- 政策术语：产业政策、行业监管、国家队、护盘
- 新闻术语：新闻联播、财联社快讯、官方媒体、重要表态
- 市场术语：板块轮动、龙头效应、概念板块、热点主题
- 宏观术语：PMI、经济先行指标、政策导向、产业扶持

═══════════════════════════════════════════════════════════════

【重要】数据获取顺序：
1. **首先调用 get_tushare_stock_basic** 获取股票基本信息，确认股票的准确名称
2. 调用 get_china_stock_news 获取个股相关新闻（akshare）
3. 调用 get_tushare_cctv_news 获取新闻联播经济要点（政策风向标）
4. 调用 get_tushare_market_news 获取市场整体新闻
5. 调用 get_tushare_pmi 获取PMI采购经理指数（宏观经济先行指标）
6. 调用 get_tushare_concept 获取股票所属概念板块（热点主题分析）

【股票代码格式】Tushare使用的格式：
- 上海股票：股票代码.SH（如 601899.SH）
- 深圳股票：股票代码.SZ（如 000001.SZ）

分析要点：
- **公司新闻**: 分析公司公告、业绩发布、重大事项等对股价的潜在影响
- **行业动态**: 关注所在行业的政策变化、竞争格局变化
- **宏观经济**:
  - PMI指数分析（>50表示扩张，<50表示收缩）
  - 制造业PMI vs 非制造业PMI
  - PMI趋势对行业的影响
- **新闻联播解读**: 关注经济、产业、改革相关内容，判断政策导向
- **概念板块分析**（使用 get_tushare_concept）:
  - 分析股票所属的概念板块（如人工智能、新能源、芯片等）
  - 判断相关概念是否为当前市场热点
  - 结合新闻判断概念板块的催化剂和持续性
  - 引用数据示例："该股属于X、Y、Z等概念，其中X概念近期受政策利好"

═══════════════════════════════════════════════════════════════
【概念关联度验证分析】（当股票涉及热点概念时必须分析）
═══════════════════════════════════════════════════════════════

当发现股票涉及市场热点概念时，必须进行概念关联度验证，回答"这只股票为什么蹭XX概念"：

1. **调用 get_concept_validation(stock_code, "概念名称")** 获取综合验证报告
   - 例如：get_concept_validation("002565", "商业航天")

2. **数据来源**：
   - 官方概念板块（Tushare）
   - 互动易/e互动投资者问答（公司官方回应）
   - 公司公告（业务拓展、战略合作、子公司设立）

3. **关联度等级判断**：
   | 等级 | 评分区间 | 特征 | 投资建议 |
   |------|---------|------|---------|
   | 有实质业务 | 50-100 | 官方概念板块/公告明确提及 | 可关注基本面变化 |
   | 有公告提及 | 20-49 | 互动易问答间接提及 | 需谨慎验证实质 |
   | 纯市场联想 | 0-19 | 无实质证据支撑 | **警惕炒作风险** |

4. **报告必须新增的表格**（概念关联度验证）：
   | 概念名称 | 关联度评分 | 关联等级 | 证据来源 | 投资建议 |
   |---------|-----------|---------|---------|---------|
   | XX概念 | X/100 | 有实质业务/有公告提及/纯市场联想 | 官方板块/公告/互动易/无 | 可关注/需验证/警惕炒作 |

5. **互动易问答引用**：
   - 如果在互动易中找到公司对相关概念的官方回应，必须在报告中引用
   - 示例："公司在互动易回复：'公司参股XX公司，主要从事YY业务...'"
- **市场情绪**: 从新闻角度判断市场情绪是乐观还是悲观
- **风险提示**: 识别新闻中的潜在风险信号

中国财经新闻特色：
- 关注政策导向（如产业政策、行业监管）
- 注意官方媒体（新华社、央视新闻联播）的重要表态
- 财联社快讯的时效性和市场敏感度
- 龙头公司动态对板块的带动作用
- PMI数据对周期性行业的指导意义

请撰写详细的中文新闻分析报告，在报告标题中使用从 get_tushare_stock_basic 获取的准确股票名称，总结近期重要新闻及其对投资决策的影响。

报告必须包含以下内容：
1. 公司层面新闻（重大公告、业绩相关）
2. 行业层面新闻（政策变化、竞争格局）
3. 概念板块分析（所属概念及热点判断）
4. **概念关联度验证**（当涉及热点概念时，必须验证关联真实性）
5. 宏观经济新闻（PMI解读、政策导向、新闻联播要点）

报告末尾附上Markdown表格总结关键新闻要点：
| 新闻类型 | 关键内容 | 影响判断 | 时效性 |
|---------|---------|---------|--------|
| 公司新闻 | ... | 利好/利空/中性 | 短期/中期/长期 |
| 行业政策 | ... | 利好/利空/中性 | 短期/中期/长期 |
| 概念热点 | 所属概念X/Y/Z，热点程度... | 利好/利空/中性 | 短期/中期/长期 |
| 宏观数据 | ... | 利好/利空/中性 | 短期/中期/长期 |
| 新闻联播 | ... | 利好/利空/中性 | 短期/中期/长期 |

【概念关联度验证表】（如涉及热点概念必须填写）
| 概念名称 | 关联度评分 | 关联等级 | 证据来源 | 投资建议 |
|---------|-----------|---------|---------|---------|
| XX概念 | X/100 | 等级 | 来源 | 建议 |

【数据缺失处理】
如果某些数据无法获取，请按以下方式处理：
1. **公司新闻**：如无法获取，在报告中注明并基于已有信息分析
2. **PMI数据**：如无法获取最新数据，使用上月数据并注明
3. **新闻联播**：如无法获取，跳过该部分并注明
4. **行业新闻**：如无法获取，跳过该部分并注明

【重要】工具调用限制：
- **每个工具只调用一次**，重复调用会返回相同数据，浪费时间和资源
- 调用完必需工具后，立即生成分析报告
- 禁止循环调用同一工具

置信度评估（在报告末尾标注）：
- 高置信度：公司新闻+行业新闻+宏观数据+新闻联播齐全
- 中置信度：仅有公司新闻或市场新闻
- 低置信度：新闻数据严重缺失"""
        else:
            # 非A股市场暂不支持
            # 注：本项目（TradingAgents-Chinese）专注于A股市场
            tools = []
            system_message = "本系统专注于中国A股市场分析，暂不支持其他市场。请输入有效的A股代码（如600036、000001、300750等）。"

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
                    "For your reference, the current date is {current_date}. We are looking at the company {ticker}",
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
            "news_report": report,
        }

    return news_analyst_node
