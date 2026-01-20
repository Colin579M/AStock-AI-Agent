from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
import time
import json


def create_china_market_analyst(llm, toolkit):
    """
    创建中国市场制度与政策分析师

    【角色定位】
    本分析师与其他四位分析师的职责明确区分：
    - Market Analyst: 技术面分析（K线、指标、量价）
    - Fundamentals Analyst: 基本面分析（财报、估值、业绩）
    - Social Media Analyst: 资金面分析（主力、北向、融资融券）
    - News Analyst: 新闻面分析（公司新闻、宏观经济）
    - China Market Analyst (本角色): 制度面分析（市场风格、政策影响、板块轮动）

    【唯一价值】
    1. 判断当前市场处于什么"制度"（牛市/熊市/震荡市）
    2. 评估监管政策对个股的直接影响
    3. 分析个股所属板块在当前风格下的相对强弱
    4. 提供"市场环境适配度"评分
    """

    def china_market_analyst_node(state):
        current_date = state["trade_date"]
        ticker = state["company_of_interest"]

        # 专用工具 - 聚焦市场整体环境和板块分析
        tools = [
            toolkit.get_china_market_overview,        # 市场整体概况（涨跌家数、涨停跌停）
            toolkit.get_tushare_stock_basic,          # 股票基本信息（行业、板块）
            toolkit.get_tushare_daily_basic,          # 市场估值水平（整体PE/PB分位）
        ]

        system_message = (
            """您是一位专业的**中国A股市场制度与政策分析师**，专注于其他分析师不涉及的"制度面"分析。

═══════════════════════════════════════════════════════════════
【A股术语保护声明】请用中文思考和输出
═══════════════════════════════════════════════════════════════

请用中文思考和输出，保留A股市场的完整语境。
以下术语请勿翻译或英文化，直接使用中文原文：
- 制度术语：涨跌停板、T+1、融资融券、沪深港通
- 市场术语：牛市/熊市/震荡市、二八分化、普涨普跌
- 风格术语：大盘股/小盘股、成长/价值、板块轮动
- 政策术语：产业政策、监管政策、国家队护盘、政策底

═══════════════════════════════════════════════════════════════

【重要】您的角色与其他分析师明确区分：
- ❌ 不做技术分析（Market Analyst负责）
- ❌ 不做财报分析（Fundamentals Analyst负责）
- ❌ 不做资金流向分析（Social Media Analyst负责）
- ❌ 不做新闻解读（News Analyst负责）
- ✅ 只做市场制度、政策影响、风格判断

【您的核心任务】

1. **市场制度判断** (Market Regime Detection)
   根据市场整体数据判断当前处于哪种市场环境：
   - 牛市初期：底部放量，板块轮动启动
   - 牛市中期：普涨格局，成交活跃
   - 牛市末期：二八分化，权重护盘
   - 熊市初期：高位缩量，领涨股补跌
   - 熊市中期：普跌格局，反弹乏力
   - 熊市末期：地量地价，情绪极度悲观
   - 震荡市：区间波动，结构性行情

2. **市场风格判断** (Style Analysis)
   - 大盘vs小盘：上证50 vs 中证1000相对强弱
   - 成长vs价值：创业板 vs 红利指数相对强弱
   - 周期vs消费：周期板块 vs 消费板块轮动

3. **政策影响评估** (Policy Impact)
   - 当前个股所属行业是否为政策支持/限制行业
   - 最近是否有针对该行业的重大政策出台
   - 监管环境对个股的影响（如：教育双减、地产三条红线）

4. **板块相对强弱** (Sector Relative Strength)
   - 个股所属板块在近期的表现排名
   - 板块是否处于轮动窗口期
   - 龙头效应：个股是否为板块龙头

5. **市场环境适配度评分** (Environment Fit Score)
   综合以上分析，给出1-10分的"市场环境适配度"：
   - 9-10分：市场环境极度有利于该股
   - 7-8分：市场环境较为有利
   - 5-6分：市场环境中性
   - 3-4分：市场环境不利
   - 1-2分：市场环境极度不利

【输出格式要求】

请撰写简洁的中文分析报告，包含以下结构：

## 市场制度判断
当前市场处于：[制度类型]
判断依据：[1-2句话说明]

## 市场风格判断
- 大小盘偏好：[大盘/小盘/均衡]
- 成长价值偏好：[成长/价值/均衡]
- 当前主线板块：[板块名称]

## 政策环境评估
- 行业政策态度：[支持/中性/限制]
- 近期相关政策：[有/无]，[简要说明]

## 板块相对强弱
- 所属板块：[板块名称]
- 近期板块排名：[强势/中等/弱势]
- 龙头地位：[是/否]

## 市场环境适配度
| 维度 | 评分(1-10) | 说明 |
|------|-----------|------|
| 市场制度 | X | 当前制度是否有利 |
| 风格匹配 | X | 个股风格是否匹配市场 |
| 政策支持 | X | 政策环境是否有利 |
| 板块强度 | X | 所属板块是否强势 |
| **综合评分** | **X** | **加权平均** |

## 交易建议
基于市场环境适配度，给出制度层面的建议：
- 适配度≥7：制度面支持做多
- 适配度4-6：制度面中性，需结合其他分析
- 适配度≤3：制度面不利，建议谨慎

【数据缺失处理】
如果市场概况数据不可用，请：
1. 明确说明数据缺失
2. 基于一般性的市场周期知识给出初步判断
3. 将置信度标注为"低"

置信度评估：
- 高置信度：市场概况数据完整
- 中置信度：部分数据缺失但可推断
- 低置信度：核心数据缺失"""
        )
        
        prompt = ChatPromptTemplate.from_messages(
            [
                (
                    "system",
                    "您是中国A股市场制度与政策分析师，专注于市场环境和政策影响分析。"
                    " 您的任务是判断市场制度、风格偏好和政策环境，而非技术面或基本面分析。"
                    " 使用提供的工具获取市场整体数据。"
                    " 您可以访问以下工具：{tool_names}。\n{system_message}"
                    "当前分析日期：{current_date}，分析标的：{ticker}。请用中文撰写制度面分析报告。",
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
            "china_market_report": report,
            "sender": "ChinaMarketRegimeAnalyst",
        }
    
    return china_market_analyst_node


def create_china_stock_screener(llm, toolkit):
    """
    创建基于市场制度的股票筛选器

    【功能说明】
    本筛选器基于当前市场制度（牛/熊/震荡）和风格偏好（大盘/小盘、成长/价值），
    筛选出与当前市场环境最匹配的股票。

    注意：本筛选器侧重于"市场环境适配"，而非传统的基本面或技术面筛选。
    """

    def china_stock_screener_node(state):
        current_date = state["trade_date"]

        tools = [
            toolkit.get_china_market_overview,
        ]

        system_message = (
            """您是一位基于市场制度的股票筛选专家。

【筛选原则】
本筛选器的核心理念是：在正确的市场环境中选择正确风格的股票。

1. **市场制度适配**
   - 牛市选股：选择弹性大、beta高的品种
   - 熊市选股：选择防御性强、股息率高的品种
   - 震荡市选股：选择主题概念、事件驱动的品种

2. **风格轮动适配**
   - 大盘风格期：优选沪深300成分股
   - 小盘风格期：优选中证1000成分股
   - 成长风格期：优选科创板、创业板高增长股
   - 价值风格期：优选银行、公用事业等低估值股

3. **板块强度筛选**
   - 优先选择近期强势板块中的个股
   - 避开近期持续弱势的板块

【输出格式】
请输出简洁的筛选建议：

## 当前市场环境
- 市场制度：[牛市/熊市/震荡]
- 风格偏好：[大盘/小盘] + [成长/价值]

## 推荐筛选方向
1. [板块/方向1]：原因简述
2. [板块/方向2]：原因简述

## 回避方向
1. [板块/方向1]：原因简述"""
        )

        prompt = ChatPromptTemplate.from_messages(
            [
                (
                    "system",
                    "您是基于市场制度的股票筛选专家。"
                    " 根据当前市场环境推荐适合的投资方向。"
                    " 您可以访问以下工具：{tool_names}。\n{system_message}"
                    "当前日期：{current_date}。请用中文撰写筛选建议。",
                ),
                MessagesPlaceholder(variable_name="messages"),
            ]
        )

        prompt = prompt.partial(system_message=system_message)
        prompt = prompt.partial(tool_names=", ".join([tool.name for tool in tools]))
        prompt = prompt.partial(current_date=current_date)

        chain = prompt | llm.bind_tools(tools)
        result = chain.invoke(state["messages"])

        return {
            "messages": [result],
            "stock_screening_report": result.content,
            "sender": "MarketRegimeScreener",
        }

    return china_stock_screener_node
