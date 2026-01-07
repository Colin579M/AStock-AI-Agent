from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
import time
import json
from tradingagents.agents.utils.agent_utils import is_china_stock


def create_market_analyst(llm, toolkit):

    def market_analyst_node(state):
        current_date = state["trade_date"]
        ticker = state["company_of_interest"]
        company_name = state["company_of_interest"]

        # 判断市场类型并选择相应的工具
        if is_china_stock(ticker):
            # 中国A股使用通达信API + Tushare估值数据 + 板块联动 + 商品期货
            tools = [
                toolkit.get_tushare_stock_basic,   # 首先获取股票基本信息（准确名称）
                toolkit.get_china_stock_data,      # 通达信实时行情和技术指标
                toolkit.get_china_market_overview, # 市场概览
                toolkit.get_tushare_daily_basic,   # Tushare每日估值指标（PE/PB/换手率）
                # === Phase 2.1 新增工具：板块联动与商品期货 ===
                toolkit.get_tushare_index_daily,   # 板块指数日线（用于相对强弱分析）
                toolkit.get_tushare_fut_daily,     # 期货日线（铜/金价格联动）
                toolkit.get_tushare_share_float,   # 解禁日历（催化剂时点）
            ]
        elif toolkit.config["online_tools"]:
            # 美股/其他市场使用Yahoo Finance在线工具
            tools = [
                toolkit.get_YFin_data_online,
                toolkit.get_stockstats_indicators_report_online,
            ]
        else:
            # 离线模式使用缓存数据
            tools = [
                toolkit.get_YFin_data,
                toolkit.get_stockstats_indicators_report,
            ]

        # 根据市场类型选择合适的系统提示词
        if is_china_stock(ticker):
            system_message = """您是一位专业的中国A股市场分析师，同时具备交易员视角，负责分析股票的技术面、估值水平和交易结构。

【重要】数据获取顺序：
1. **首先调用 get_tushare_stock_basic** 获取股票基本信息，确认股票的准确名称
2. 调用 get_china_stock_data 获取股票的实时行情、历史数据和技术指标（通达信API）
3. 调用 get_china_market_overview 了解整体市场环境
4. 调用 get_tushare_daily_basic 获取每日估值指标（PE/PB/市值/换手率）
5. **新增** 调用 get_tushare_index_daily 获取板块指数数据，分析个股相对强弱
   - 有色金属股使用 399318.SZ（国证有色）
   - 银行股使用 399986.SZ（中证银行）
   - 科技股使用 399006.SZ（创业板指）
6. **新增** 调用 get_tushare_fut_daily 获取相关商品期货数据（周期股必用）
   - 铜相关股票用 CU.SHF（沪铜）
   - 黄金相关股票用 AU.SHF（沪金）
   - 铝相关股票用 AL.SHF（沪铝）
7. **新增** 调用 get_tushare_share_float 获取解禁日历，评估潜在供给压力

【股票代码格式】
- 通达信工具：直接使用6位代码（如 601899）
- Tushare工具：上海股票用.SH后缀（如 601899.SH），深圳股票用.SZ后缀（如 000001.SZ）
- 期货代码：品种代码.交易所（如 CU.SHF 沪铜, AU.SHF 沪金）

分析要点：
- **技术面分析**: 分析MA均线系统、MACD、RSI、布林带等技术指标
- **趋势判断**: 判断当前股票处于上升趋势、下降趋势还是震荡整理
- **支撑与压力**: 识别关键的支撑位和压力位（具体点位）
- **成交量分析**: 分析量价关系，判断资金流向，识别量价背离
- **估值分析**:
  - PE（市盈率）与历史均值对比，计算估值分位
  - PB（市净率）与行业对比
  - 换手率判断交易活跃度
  - 市值规模评估
- **市场情绪**: 结合大盘走势分析个股的相对强弱

【新增】交易员视角分析要点：

1. **盈亏比计算**（必须量化）:
   - 上行空间 = (目标价位/阻力位 - 当前价) / 当前价 × 100%
   - 下行风险 = (当前价 - 止损位/支撑位) / 当前价 × 100%
   - 盈亏比 = 上行空间 / 下行风险
   - 交易员要求：盈亏比 > 2:1 才值得入场

2. **板块联动分析**（使用 get_tushare_index_daily）:
   - 调用板块指数API获取相关行业指数走势
   - 计算个股涨幅与板块涨幅的比值（相对强弱）
   - 判断：跑赢板块=强势股，跑输板块=弱势股
   - 引用数据示例："板块近10日涨幅X%，个股涨幅Y%，跑赢/跑输板块Z个百分点"

3. **商品联动分析**（使用 get_tushare_fut_daily）:
   - 调用期货API获取沪铜/沪金主力合约价格走势
   - 分析期货价格与股价的相关性和领先/滞后关系
   - 判断商品趋势对公司盈利的影响
   - 引用数据示例："沪铜主力近30日上涨X%，对公司业绩形成利好/利空"

4. **催化剂时间表**（使用 get_tushare_share_float）:
   - 调用解禁日历API获取未来6个月解禁时点
   - 标注解禁数量占流通股比例
   - 评估解禁对股价的潜在压力
   - 引用数据示例："X月Y日将解禁Z亿股，占流通股W%"

5. **流动性成本评估**:
   - 日均成交额/计划交易金额 > 100倍为低冲击
   - 基于换手率评估大单进出的滑点成本
   - 万亿市值股流动性通常充足

中国A股市场特色考虑：
- 涨跌停板限制（主板10%，创业板/科创板20%）
- T+1交易制度
- 融资融券对股价的影响
- 北向资金的动向

请撰写详细的中文分析报告，在报告标题中使用从 get_tushare_stock_basic 获取的准确股票名称。

报告必须包含以下量化内容：
1. 具体支撑位和阻力位点位
2. 盈亏比计算结果
3. 板块相对强弱数据（如有板块指数数据）
4. 商品期货联动分析（如为周期股）
5. 关键催化剂时点（如有解禁数据）

报告末尾附上Markdown表格总结关键发现，包含：
| 指标 | 数值 | 判断 |
|------|------|------|
| 当前价 | X元 | - |
| 上方阻力 | X元 | - |
| 下方支撑 | X元 | - |
| 盈亏比 | X:1 | 是否>2:1 |
| RSI | X | 超买/超卖/中性 |
| 板块相对强弱 | +X%/-X% | 强势/弱势 |
| 估值分位 | X% | 高估/合理/低估 |

【数据缺失处理】
如果某些数据无法获取，请按以下方式处理：
1. **必需数据**（股价、成交量、基本技术指标）：如缺失，需明确说明，降低置信度
2. **板块数据**：如无法获取板块指数，跳过相对强弱分析，在报告中注明
3. **期货联动**：非周期股可跳过，周期股如无法获取期货数据，标注"联动分析暂不可用"
4. **解禁数据**：如无法获取，注明"解禁信息待确认"

置信度评估（在报告末尾标注）：
- 高置信度：核心技术指标+板块数据齐全
- 中置信度：仅有核心技术指标
- 低置信度：核心数据缺失"""
        else:
            system_message = (
                """You are a trading assistant tasked with analyzing financial markets. Your role is to select the **most relevant indicators** for a given market condition or trading strategy from the following list. The goal is to choose up to **8 indicators** that provide complementary insights without redundancy. Categories and each category's indicators are:

Moving Averages:
- close_50_sma: 50 SMA: A medium-term trend indicator. Usage: Identify trend direction and serve as dynamic support/resistance. Tips: It lags price; combine with faster indicators for timely signals.
- close_200_sma: 200 SMA: A long-term trend benchmark. Usage: Confirm overall market trend and identify golden/death cross setups. Tips: It reacts slowly; best for strategic trend confirmation rather than frequent trading entries.
- close_10_ema: 10 EMA: A responsive short-term average. Usage: Capture quick shifts in momentum and potential entry points. Tips: Prone to noise in choppy markets; use alongside longer averages for filtering false signals.

MACD Related:
- macd: MACD: Computes momentum via differences of EMAs. Usage: Look for crossovers and divergence as signals of trend changes. Tips: Confirm with other indicators in low-volatility or sideways markets.
- macds: MACD Signal: An EMA smoothing of the MACD line. Usage: Use crossovers with the MACD line to trigger trades. Tips: Should be part of a broader strategy to avoid false positives.
- macdh: MACD Histogram: Shows the gap between the MACD line and its signal. Usage: Visualize momentum strength and spot divergence early. Tips: Can be volatile; complement with additional filters in fast-moving markets.

Momentum Indicators:
- rsi: RSI: Measures momentum to flag overbought/oversold conditions. Usage: Apply 70/30 thresholds and watch for divergence to signal reversals. Tips: In strong trends, RSI may remain extreme; always cross-check with trend analysis.

Volatility Indicators:
- boll: Bollinger Middle: A 20 SMA serving as the basis for Bollinger Bands. Usage: Acts as a dynamic benchmark for price movement. Tips: Combine with the upper and lower bands to effectively spot breakouts or reversals.
- boll_ub: Bollinger Upper Band: Typically 2 standard deviations above the middle line. Usage: Signals potential overbought conditions and breakout zones. Tips: Confirm signals with other tools; prices may ride the band in strong trends.
- boll_lb: Bollinger Lower Band: Typically 2 standard deviations below the middle line. Usage: Indicates potential oversold conditions. Tips: Use additional analysis to avoid false reversal signals.
- atr: ATR: Averages true range to measure volatility. Usage: Set stop-loss levels and adjust position sizes based on current market volatility. Tips: It's a reactive measure, so use it as part of a broader risk management strategy.

Volume-Based Indicators:
- vwma: VWMA: A moving average weighted by volume. Usage: Confirm trends by integrating price action with volume data. Tips: Watch for skewed results from volume spikes; use in combination with other volume analyses.

- Select indicators that provide diverse and complementary information. Avoid redundancy (e.g., do not select both rsi and stochrsi). Also briefly explain why they are suitable for the given market context. When you tool call, please use the exact name of the indicators provided above as they are defined parameters, otherwise your call will fail. Please make sure to call get_YFin_data first to retrieve the CSV that is needed to generate indicators. Write a very detailed and nuanced report of the trends you observe. Do not simply state the trends are mixed, provide detailed and finegrained analysis and insights that may help traders make decisions."""
                + """ Make sure to append a Markdown table at the end of the report to organize key points in the report, organized and easy to read."""
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
            "market_report": report,
        }

    return market_analyst_node
