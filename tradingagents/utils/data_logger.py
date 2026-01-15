"""
工具调用数据记录器 - 解析Markdown表格并保存为CSV

将工具返回的Markdown格式数据解析为结构化CSV，便于后续数据分析。
"""
import csv
import re
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Optional


class ToolDataLogger:
    """解析工具返回的Markdown数据并保存为结构化CSV"""

    # CSV列定义
    CSV_HEADERS = ['timestamp', 'tool_name', 'data_category', 'date',
                   'metric', 'value', 'unit', 'stock_code']

    # 工具名称到数据类别的映射
    CATEGORY_MAP = {
        'stock_basic': '基本信息',
        'daily_basic': '估值指标',
        'moneyflow': '资金流向',
        'margin': '融资融券',
        'holder': '股东信息',
        'pledge': '股权质押',
        'share_float': '解禁日历',
        'forecast': '业绩预告',
        'financial': '财务数据',
        'dividend': '分红数据',
        'index': '指数数据',
        'pmi': '宏观数据',
        'news': '新闻数据',
        'stock_data': '行情数据',
        'market_overview': '市场概览',
        'top_list': '龙虎榜',
        'hsgt': '沪深港通',
        'block_trade': '大宗交易',
        'surv': '机构调研',
        'report_rc': '券商研报',
    }

    # 市场级/宏观级工具（返回的数据不与特定股票关联，跳过记录）
    MARKET_LEVEL_TOOLS = {
        'get_tushare_hsgt_top10',     # 沪深港通十大成交（市场级）
        'get_tushare_index_member',   # 行业成分股（行业级）
        'get_tushare_index_daily',    # 板块指数日线（市场级）
        'get_tushare_pmi',            # PMI宏观数据（宏观级）
        'get_china_market_overview',  # 市场概览（市场级）
        'get_china_market_news',      # 市场新闻（市场级）
        'get_global_news_openai',     # 全球新闻（市场级）
        'get_google_news',            # Google新闻（市场级）
        'get_finnhub_news',           # Finnhub新闻（市场级）
        'get_reddit_news',            # Reddit新闻（市场级）
    }

    def __init__(self, csv_path: Path, stock_code: str):
        """
        初始化数据记录器

        Args:
            csv_path: CSV文件保存路径
            stock_code: 股票代码
        """
        self.csv_path = csv_path
        self.stock_code = stock_code
        self.records: List[Dict] = []
        self.tool_call_map: Dict[str, Dict] = {}  # tool_call_id -> {name, args}
        self._init_csv()

    def _init_csv(self):
        """初始化CSV文件（写入表头）"""
        with open(self.csv_path, 'w', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=self.CSV_HEADERS)
            writer.writeheader()

    def register_tool_call(self, tool_call_id: str, tool_name: str, tool_args: dict):
        """
        注册工具调用（在AIMessage中检测到tool_calls时调用）

        Args:
            tool_call_id: 工具调用ID
            tool_name: 工具名称
            tool_args: 工具参数
        """
        self.tool_call_map[tool_call_id] = {
            'name': tool_name,
            'args': tool_args
        }

    def log_tool_result(self, tool_call_id: str, result: str):
        """
        记录工具调用结果（在ToolMessage中检测到结果时调用）

        Args:
            tool_call_id: 工具调用ID
            result: 工具返回的结果字符串
        """
        # 查找对应的工具调用信息
        tool_info = self.tool_call_map.get(tool_call_id)
        if not tool_info:
            return

        tool_name = tool_info['name']

        # 跳过市场级/宏观级工具（返回的数据不与特定股票关联）
        if tool_name in self.MARKET_LEVEL_TOOLS:
            return

        tool_args = tool_info['args']
        timestamp = datetime.now().strftime('%H:%M:%S')
        category = self._get_category(tool_name)

        # 尝试解析Markdown表格
        records = self._parse_markdown_tables(result, tool_name, category)

        # 如果没有表格，尝试解析键值对
        if not records:
            records = self._parse_key_values(result, tool_name, category)

        # 添加时间戳和股票代码，写入CSV
        for record in records:
            record['timestamp'] = timestamp
            record['stock_code'] = self.stock_code
            self.records.append(record)
            self._write_record(record)

    def _get_category(self, tool_name: str) -> str:
        """根据工具名称判断数据类别"""
        tool_name_lower = tool_name.lower()
        for key, cat in self.CATEGORY_MAP.items():
            if key in tool_name_lower:
                return cat
        return '其他'

    def _parse_markdown_tables(self, text: str, tool_name: str, category: str) -> List[Dict]:
        """
        解析Markdown表格

        Args:
            text: Markdown文本
            tool_name: 工具名称
            category: 数据类别

        Returns:
            解析出的记录列表
        """
        records = []

        # 匹配Markdown表格：表头行 + 分隔行 + 数据行
        table_pattern = r'\|([^|\n]+(?:\|[^|\n]+)+)\|\s*\n\|[-:\s|]+\|\s*\n((?:\|[^|\n]+(?:\|[^|\n]+)+\|\s*\n?)+)'
        matches = re.findall(table_pattern, text, re.MULTILINE)

        for header_row, body in matches:
            # 解析表头
            headers = [h.strip() for h in header_row.split('|') if h.strip()]
            if not headers:
                continue

            # 解析数据行
            rows = [r.strip() for r in body.strip().split('\n') if r.strip()]

            for row in rows:
                cells = [c.strip() for c in row.split('|') if c.strip()]
                if len(cells) < 2:
                    continue

                # 第一列通常是日期或指标名
                first_cell = cells[0]
                is_date_col = self._is_date(first_cell)

                # 处理每一列数据
                for i, header in enumerate(headers):
                    if i >= len(cells):
                        break

                    value = cells[i]
                    # 跳过空值和占位符
                    if not value or value in ['-', 'N/A', '—', '暂无']:
                        continue

                    # 跳过第一列如果它已经被用作日期
                    if i == 0 and is_date_col:
                        continue

                    record = {
                        'tool_name': tool_name,
                        'data_category': category,
                        'date': first_cell if is_date_col else '',
                        'metric': header,
                        'value': self._clean_value(value),
                        'unit': self._extract_unit(header),
                    }
                    records.append(record)

        return records

    def _parse_key_values(self, text: str, tool_name: str, category: str) -> List[Dict]:
        """
        解析键值对格式（如 **名称**: 大为股份）

        Args:
            text: 文本内容
            tool_name: 工具名称
            category: 数据类别

        Returns:
            解析出的记录列表
        """
        records = []

        # 匹配多种键值对格式
        patterns = [
            r'\*\*([^*]+)\*\*[：:]\s*\*?\*?([^\n*]+)',  # **key**: value 或 **key**: **value**
            r'-\s*\*\*([^*]+)\*\*[：:]\s*([^\n]+)',      # - **key**: value
            r'【([^】]+)】[：:]\s*([^\n]+)',              # 【key】: value
        ]

        for pattern in patterns:
            matches = re.findall(pattern, text)
            for key, value in matches:
                value = value.strip()
                # 跳过空值和占位符
                if not value or value in ['-', 'N/A', '—', '暂无', '数据暂不可用']:
                    continue

                records.append({
                    'tool_name': tool_name,
                    'data_category': category,
                    'date': '',
                    'metric': key.strip(),
                    'value': self._clean_value(value),
                    'unit': self._extract_unit(key),
                })

        return records

    def _is_date(self, text: str) -> bool:
        """判断是否为日期格式"""
        text = text.strip()
        # 匹配多种日期格式
        date_patterns = [
            r'^\d{4}[-/]?\d{2}[-/]?\d{2}$',  # 20260106 或 2026-01-06
            r'^\d{4}[-/]\d{2}$',               # 202601 或 2026-01
            r'^\d{4}Q[1-4]$',                  # 2026Q1
            r'^\d{4}H[12]$',                   # 2026H1
        ]
        return any(re.match(p, text) for p in date_patterns)

    def _clean_value(self, value: str) -> str:
        """
        清理数值，保留原始格式但移除多余字符

        Args:
            value: 原始值

        Returns:
            清理后的值
        """
        # 移除Markdown格式
        value = re.sub(r'\*+', '', value)
        # 移除前后空白
        value = value.strip()
        return value

    def _extract_unit(self, header: str) -> str:
        """
        从表头提取单位

        Args:
            header: 表头文本

        Returns:
            单位字符串
        """
        # 匹配括号中的单位
        unit_match = re.search(r'\(([^)]+)\)', header)
        if unit_match:
            return unit_match.group(1)

        # 检测常见单位关键词
        unit_keywords = {
            '%': '%',
            '亿': '亿',
            '万': '万',
            '元': '元',
            '股': '股',
        }
        for keyword, unit in unit_keywords.items():
            if keyword in header:
                return unit

        return ''

    def _write_record(self, record: Dict):
        """写入单条记录到CSV"""
        with open(self.csv_path, 'a', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=self.CSV_HEADERS)
            writer.writerow(record)

    def get_summary(self) -> Dict:
        """获取记录摘要"""
        if not self.records:
            return {'total': 0, 'categories': {}}

        categories = {}
        for record in self.records:
            cat = record.get('data_category', '其他')
            categories[cat] = categories.get(cat, 0) + 1

        return {
            'total': len(self.records),
            'categories': categories,
            'file_path': str(self.csv_path)
        }
