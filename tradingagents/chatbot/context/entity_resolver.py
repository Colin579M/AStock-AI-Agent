"""
实体解析器

负责解析用户输入中的实体：
- 股票名称 → 股票代码
- 日期表达 → 具体日期
"""
import re
import logging
from datetime import datetime, timedelta
from typing import Optional, Dict, List, Any

logger = logging.getLogger(__name__)


# 常见股票别名映射（快速查找）
STOCK_ALIASES = {
    # 银行
    "招商银行": "600036",
    "招行": "600036",
    "平安银行": "000001",
    "工商银行": "601398",
    "工行": "601398",
    "建设银行": "601939",
    "建行": "601939",
    "农业银行": "601288",
    "农行": "601288",
    "中国银行": "601988",
    "中行": "601988",
    "光大银行": "601818",
    "光大": "601818",
    "兴业银行": "601166",
    "兴业": "601166",
    "民生银行": "600016",
    "民生": "600016",
    "浦发银行": "600000",
    "浦发": "600000",
    "中信银行": "601998",
    "交通银行": "601328",
    "交行": "601328",
    "邮储银行": "601658",
    "宁波银行": "002142",
    "招商": "600036",

    # 白酒
    "贵州茅台": "600519",
    "茅台": "600519",
    "五粮液": "000858",
    "泸州老窖": "000568",
    "老窖": "000568",
    "山西汾酒": "600809",
    "汾酒": "600809",
    "洋河股份": "002304",
    "洋河": "002304",
    "古井贡酒": "000596",
    "古井": "000596",

    # 科技
    "宁德时代": "300750",
    "宁德": "300750",
    "比亚迪": "002594",
    "隆基绿能": "601012",
    "隆基": "601012",
    "中芯国际": "688981",
    "中芯": "688981",
    "海康威视": "002415",
    "海康": "002415",
    "立讯精密": "002475",
    "立讯": "002475",
    "汇川技术": "300124",
    "汇川": "300124",

    # 消费
    "伊利股份": "600887",
    "伊利": "600887",
    "海天味业": "603288",
    "海天": "603288",
    "美的集团": "000333",
    "美的": "000333",
    "格力电器": "000651",
    "格力": "000651",
    "三一重工": "600031",
    "三一": "600031",

    # 医药
    "恒瑞医药": "600276",
    "恒瑞": "600276",
    "药明康德": "603259",
    "药明": "603259",
    "迈瑞医疗": "300760",
    "迈瑞": "300760",
    "片仔癀": "600436",

    # 保险
    "中国平安": "601318",
    "平安": "601318",
    "中国人寿": "601628",
    "人寿": "601628",
    "中国太保": "601601",
    "太保": "601601",
    "新华保险": "601336",

    # 其他
    "腾讯控股": "00700",
    "腾讯": "00700",
    "阿里巴巴": "09988",
    "阿里": "09988",
    "中国石油": "601857",
    "中石油": "601857",
    "中国石化": "600028",
    "中石化": "600028",
    "万科A": "000002",
    "万科": "000002",
}


# 常见指数别名映射
INDEX_ALIASES = {
    # 上证指数
    "大盘": "000001.SH",
    "上证指数": "000001.SH",
    "上证": "000001.SH",
    "沪指": "000001.SH",
    "上证综指": "000001.SH",
    "上证综合指数": "000001.SH",

    # 深证成指
    "深证成指": "399001.SZ",
    "深成指": "399001.SZ",
    "深指": "399001.SZ",
    "深圳成指": "399001.SZ",

    # 创业板指
    "创业板": "399006.SZ",
    "创业板指": "399006.SZ",
    "创指": "399006.SZ",

    # 沪深300
    "沪深300": "000300.SH",
    "沪深三百": "000300.SH",
    "HS300": "000300.SH",

    # 上证50
    "上证50": "000016.SH",
    "上证五十": "000016.SH",

    # 中证500
    "中证500": "000905.SH",
    "中证五百": "000905.SH",

    # 科创50
    "科创50": "000688.SH",
    "科创五十": "000688.SH",
    "科创板": "000688.SH",

    # 中证1000
    "中证1000": "000852.SH",
    "中证一千": "000852.SH",
}


class EntityResolver:
    """
    实体解析器

    解析用户输入中的股票名称、日期等实体。
    """

    def __init__(self, use_tushare: bool = True):
        """
        初始化解析器

        Args:
            use_tushare: 是否使用 Tushare 获取完整股票列表
        """
        self.use_tushare = use_tushare
        self._stock_cache: Dict[str, str] = {}

        # 初始化本地别名
        self._stock_cache.update(STOCK_ALIASES)

        logger.info("EntityResolver 初始化完成")

    def resolve_ticker(self, text: str) -> Optional[str]:
        """
        解析股票代码

        支持以下输入格式：
        - 纯数字代码: "600036" → "600036"
        - 带后缀代码: "600036.SH" → "600036"
        - 股票名称: "招商银行" → "600036"
        - 股票简称: "招行" → "600036"

        Args:
            text: 用户输入文本

        Returns:
            6位股票代码（不含后缀），或 None
        """
        text = text.strip()

        # 1. 纯数字代码
        if re.match(r'^\d{6}$', text):
            return text

        # 2. 带后缀代码
        match = re.match(r'^(\d{6})\.(SH|SZ|BJ)$', text.upper())
        if match:
            return match.group(1)

        # 3. 本地别名缓存
        if text in self._stock_cache:
            return self._stock_cache[text]

        # 4. Tushare 完整列表查找
        if self.use_tushare:
            code = self._search_in_tushare(text)
            if code:
                self._stock_cache[text] = code
                return code

        return None

    def resolve_index(self, text: str) -> Optional[str]:
        """
        解析指数名称为指数代码

        支持以下输入格式：
        - 指数代码: "000001.SH" → "000001.SH"
        - 指数名称: "上证指数" → "000001.SH"
        - 通俗名称: "大盘" → "000001.SH"

        Args:
            text: 用户输入文本

        Returns:
            带后缀的指数代码（如 000001.SH），或 None
        """
        text = text.strip()

        # 1. 检查是否已经是指数代码格式 (6位数字.交易所后缀)
        if re.match(r'^\d{6}\.(SH|SZ)$', text.upper()):
            return text.upper()

        # 2. 查找指数别名
        if text in INDEX_ALIASES:
            return INDEX_ALIASES[text]

        return None

    def _search_in_tushare(self, name: str) -> Optional[str]:
        """
        在 Tushare 股票列表中搜索

        注意：此功能已禁用以提升性能。
        Tushare API 加载全国股票列表需要 5-20 秒，严重影响响应速度。
        请使用本地 STOCK_ALIASES 字典添加股票别名。

        Args:
            name: 股票名称

        Returns:
            None（已禁用）
        """
        # 性能优化：禁用 Tushare 股票列表加载
        # 原因：首次调用会同步阻塞 5-20 秒加载全国所有股票
        # 解决方案：只使用本地 STOCK_ALIASES 字典
        return None

    def resolve_date(self, text: str) -> Optional[str]:
        """
        解析日期表达

        支持以下格式：
        - "今天" → 当天日期
        - "昨天" → 昨天日期
        - "前天" → 前天日期
        - "上周五" → 上周五日期
        - "20260112" → 20260112
        - "2026-01-12" → 20260112
        - "1月12日" → 当年1月12日

        Args:
            text: 日期文本

        Returns:
            YYYYMMDD 格式日期字符串，或 None
        """
        text = text.strip()
        today = datetime.now()

        # 相对日期
        relative_dates = {
            "今天": 0,
            "今日": 0,
            "昨天": -1,
            "昨日": -1,
            "前天": -2,
            "前日": -2,
            "大前天": -3,
        }

        if text in relative_dates:
            target = today + timedelta(days=relative_dates[text])
            return target.strftime("%Y%m%d")

        # 上周X
        weekday_map = {
            "一": 0, "二": 1, "三": 2, "四": 3, "五": 4, "六": 5, "日": 6, "天": 6
        }
        match = re.match(r'^上周([一二三四五六日天])$', text)
        if match:
            target_weekday = weekday_map[match.group(1)]
            days_back = today.weekday() + 7 - target_weekday
            if days_back <= 0:
                days_back += 7
            target = today - timedelta(days=days_back)
            return target.strftime("%Y%m%d")

        # 本周X
        match = re.match(r'^(这|本)周([一二三四五六日天])$', text)
        if match:
            target_weekday = weekday_map[match.group(2)]
            days_diff = target_weekday - today.weekday()
            target = today + timedelta(days=days_diff)
            return target.strftime("%Y%m%d")

        # YYYYMMDD 格式
        if re.match(r'^\d{8}$', text):
            return text

        # YYYY-MM-DD 格式
        match = re.match(r'^(\d{4})-(\d{2})-(\d{2})$', text)
        if match:
            return f"{match.group(1)}{match.group(2)}{match.group(3)}"

        # X月X日 格式
        match = re.match(r'^(\d{1,2})月(\d{1,2})[日号]?$', text)
        if match:
            month = int(match.group(1))
            day = int(match.group(2))
            year = today.year
            # 如果月份大于当前月份，可能指去年
            if month > today.month:
                year -= 1
            return f"{year}{month:02d}{day:02d}"

        return None

    def extract_entities(self, text: str) -> Dict[str, Any]:
        """
        从文本中提取所有实体

        Args:
            text: 用户输入文本

        Returns:
            包含提取实体的字典
        """
        entities = {
            "tickers": [],
            "indices": [],
            "dates": [],
            "raw_text": text
        }

        # 提取股票代码（6位数字）
        codes = re.findall(r'\b(\d{6})\b', text)
        for code in codes:
            entities["tickers"].append(code)

        # 提取股票名称
        for name in STOCK_ALIASES.keys():
            if name in text:
                code = STOCK_ALIASES[name]
                if code not in entities["tickers"]:
                    entities["tickers"].append(code)

        # 提取指数名称
        for name in INDEX_ALIASES.keys():
            if name in text:
                index_code = INDEX_ALIASES[name]
                if index_code not in entities["indices"]:
                    entities["indices"].append(index_code)

        # 提取日期
        date_patterns = [
            r'今[天日]', r'昨[天日]', r'前[天日]',
            r'上周[一二三四五六日天]',
            r'[这本]周[一二三四五六日天]',
            r'\d{8}',
            r'\d{4}-\d{2}-\d{2}',
            r'\d{1,2}月\d{1,2}[日号]?'
        ]

        for pattern in date_patterns:
            matches = re.findall(pattern, text)
            for match in matches:
                date = self.resolve_date(match)
                if date and date not in entities["dates"]:
                    entities["dates"].append(date)

        return entities

    def get_ticker_with_suffix(self, code: str) -> str:
        """
        为股票代码添加交易所后缀

        Args:
            code: 6位股票代码

        Returns:
            带后缀的代码（如 600036.SH）
        """
        if not code or len(code) != 6:
            return code

        # 上海：6开头
        if code.startswith('6'):
            return f"{code}.SH"
        # 深圳：0、3开头
        elif code.startswith('0') or code.startswith('3'):
            return f"{code}.SZ"
        # 北交所：4、8开头
        elif code.startswith('4') or code.startswith('8'):
            return f"{code}.BJ"
        else:
            return code


# 单例
_resolver_instance: Optional[EntityResolver] = None


def get_entity_resolver() -> EntityResolver:
    """获取 EntityResolver 单例"""
    global _resolver_instance
    if _resolver_instance is None:
        _resolver_instance = EntityResolver()
    return _resolver_instance
