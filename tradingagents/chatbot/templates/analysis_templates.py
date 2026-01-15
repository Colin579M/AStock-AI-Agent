"""
分析模板定义

受 Google Gemini 股票研究提示启发，定义 8 个核心分析维度。
每个模板包含：
- name: 显示名称
- prompt: 发送给 LLM 的提示词（{company} 会被替换为股票名称）
- tools: 推荐使用的工具列表
- icon: 显示图标
"""
from typing import Dict, List, Any


# 8 个核心分析维度
ANALYSIS_TEMPLATES: Dict[str, Dict[str, Any]] = {
    "business": {
        "name": "业务理解",
        "prompt": "用简单术语解释{company}的业务。它解决什么问题，谁为此付费，为什么客户选择它而不是替代品。避免使用财务术语。",
        "tools": ["get_stock_basic_info"],
        "icon": "🏢",
        "description": "公司做什么，护城河在哪"
    },
    "revenue": {
        "name": "收入分解",
        "prompt": "分解{company}的收入流。哪些业务在增长，哪些在放缓，公司对其主要产品或客户的依赖程度如何？",
        "tools": ["get_stock_fundamentals", "get_financial_indicators"],
        "icon": "📊",
        "description": "哪块业务在增长/放缓"
    },
    "industry": {
        "name": "行业背景",
        "prompt": "解释{company}所在的行业。市场在增长、稳定还是萎缩？什么长期趋势有利或不利于这项业务？",
        "tools": ["get_market_news", "get_stock_ranking"],
        "icon": "🌐",
        "description": "市场趋势对公司的影响"
    },
    "competition": {
        "name": "竞争格局",
        "prompt": "列出{company}的主要竞争对手，从定价能力、产品强度、规模和护城河比较。突出这家公司明显赢或输的地方。",
        "tools": ["get_stock_basic_info", "get_stock_valuation"],
        "icon": "⚔️",
        "description": "与对手的优劣势对比"
    },
    "financials": {
        "name": "财务质量",
        "prompt": "分析{company}近年财务质量。关注收入增长一致性、利润率、债务水平、现金流强度和资本配置。",
        "tools": ["get_financial_indicators", "get_stock_fundamentals"],
        "icon": "💰",
        "description": "收入、利润、现金流健康度"
    },
    "risks": {
        "name": "风险分析",
        "prompt": "识别{company}最大的风险。包括业务风险、财务风险、监管威胁和可能永久损害业务的因素。",
        "tools": ["get_forecast", "get_market_news"],
        "icon": "⚠️",
        "description": "最大的风险是什么"
    },
    "valuation": {
        "name": "估值思考",
        "prompt": "解释投资者可能如何看待{company}的估值。什么假设最重要，什么会证明更高或更低的估值合理？",
        "tools": ["get_stock_valuation", "get_financial_indicators"],
        "icon": "🎯",
        "description": "当前估值是否合理"
    },
    "thesis": {
        "name": "投资论点",
        "prompt": "帮我形成{company}的长期投资论点。总结为什么这可能是好投资，什么必须成功，什么迹象告诉我我错了。",
        "tools": ["get_stock_valuation", "get_stock_fundamentals", "get_forecast"],
        "icon": "📝",
        "description": "牛熊情景 + 长期观点"
    }
}


# 快捷命令映射
QUICK_COMMANDS: Dict[str, str] = {
    "/深度分析": "full_analysis",      # 执行全部8个维度
    "/快速估值": "valuation",          # 只看估值
    "/风险扫描": "risks",              # 只看风险
    "/财务体检": "financials",         # 只看财务
    "/投资论点": "thesis",             # 生成投资论点
    "/业务理解": "business",           # 业务分析
    "/行业分析": "industry",           # 行业背景
    "/竞争分析": "competition",        # 竞争格局
}


# 分析维度顺序（用于全面分析）
ANALYSIS_ORDER: List[str] = [
    "business",     # 1. 先理解业务
    "revenue",      # 2. 收入结构
    "industry",     # 3. 行业背景
    "competition",  # 4. 竞争格局
    "financials",   # 5. 财务质量
    "risks",        # 6. 风险分析
    "valuation",    # 7. 估值思考
    "thesis",       # 8. 最终论点
]


def get_template(key: str) -> Dict[str, Any]:
    """获取指定的分析模板"""
    return ANALYSIS_TEMPLATES.get(key, {})


def get_all_template_keys() -> List[str]:
    """获取所有模板键值"""
    return list(ANALYSIS_TEMPLATES.keys())


def build_analysis_menu(stock_name: str) -> str:
    """
    构建分析维度选择菜单

    Args:
        stock_name: 股票名称

    Returns:
        str: Markdown 格式的菜单
    """
    menu = f"## 📋 {stock_name} 深度分析\n\n"
    menu += "请选择分析维度（回复数字或名称）：\n\n"

    for i, key in enumerate(ANALYSIS_ORDER, 1):
        template = ANALYSIS_TEMPLATES[key]
        menu += f"{i}. {template['icon']} **{template['name']}** - {template['description']}\n"

    menu += "\n9. 🔄 **全部分析**（依次执行以上所有维度）\n"
    menu += "\n💡 提示：也可以直接输入快捷命令，如 `/快速估值 茅台`"

    return menu


def parse_dimension_selection(selection: str) -> List[str]:
    """
    解析用户的维度选择

    Args:
        selection: 用户输入（数字、名称或"全部"）

    Returns:
        List[str]: 要执行的模板键值列表
    """
    selection = selection.strip().lower()

    # 数字选择
    if selection.isdigit():
        idx = int(selection) - 1
        if 0 <= idx < len(ANALYSIS_ORDER):
            return [ANALYSIS_ORDER[idx]]
        elif int(selection) == 9:  # 全部
            return ANALYSIS_ORDER

    # 名称选择
    for key, template in ANALYSIS_TEMPLATES.items():
        if template["name"] in selection or key in selection:
            return [key]

    # 全部分析
    if any(kw in selection for kw in ["全部", "全面", "所有", "all"]):
        return ANALYSIS_ORDER

    return []
