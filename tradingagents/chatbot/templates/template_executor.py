"""
模板执行引擎

按模板结构化执行分析，支持单维度和全面分析。
"""
import logging
from typing import Optional, List, Callable, TYPE_CHECKING

from .analysis_templates import ANALYSIS_TEMPLATES, ANALYSIS_ORDER

if TYPE_CHECKING:
    from ..agents.unified_agent import UnifiedAgent

logger = logging.getLogger(__name__)


class TemplateExecutor:
    """
    模板执行引擎

    负责按照预定义的模板结构执行分析，并通过进度回调
    向用户反馈分析进度。
    """

    def __init__(self, agent: "UnifiedAgent"):
        """
        初始化模板执行引擎

        Args:
            agent: UnifiedAgent 实例，用于执行实际的分析
        """
        self.agent = agent

    def execute_template(
        self,
        template_key: str,
        stock_code: str,
        stock_name: str,
        progress_callback: Optional[Callable[[str, str], None]] = None
    ) -> str:
        """
        执行单个分析模板

        Args:
            template_key: 模板键值（如 "business", "valuation"）
            stock_code: 股票代码
            stock_name: 股票名称（用于提示词）
            progress_callback: 进度回调函数 (event_type, content)

        Returns:
            str: 分析结果（Markdown 格式）
        """
        template = ANALYSIS_TEMPLATES.get(template_key)
        if not template:
            logger.warning(f"未知的模板键值: {template_key}")
            return f"未知的分析维度: {template_key}"

        def emit(event_type: str, content: str):
            """发送进度事件"""
            if progress_callback:
                try:
                    progress_callback(event_type, content)
                except Exception as e:
                    logger.error(f"进度回调失败: {e}")

        # 发送进度：开始分析
        emit("section_start", f"{template['icon']} {template['name']}")

        # 构建提示词
        prompt = template["prompt"].format(company=stock_name)

        try:
            # 调用 Agent 执行
            result = self.agent.run(prompt, [])

            # 发送进度：分析完成
            emit("section_complete", template["name"])

            # 返回格式化结果
            return f"## {template['icon']} {template['name']}\n\n{result}\n\n---\n\n"

        except Exception as e:
            logger.error(f"模板执行失败 [{template_key}]: {e}")
            emit("section_error", f"{template['name']} 分析失败")
            return f"## {template['icon']} {template['name']}\n\n分析失败: {str(e)}\n\n---\n\n"

    def execute_dimensions(
        self,
        dimensions: List[str],
        stock_code: str,
        stock_name: str,
        progress_callback: Optional[Callable[[str, str], None]] = None
    ) -> str:
        """
        执行多个分析维度

        Args:
            dimensions: 要执行的维度列表
            stock_code: 股票代码
            stock_name: 股票名称
            progress_callback: 进度回调函数

        Returns:
            str: 合并后的分析结果
        """
        def emit(event_type: str, content: str):
            if progress_callback:
                try:
                    progress_callback(event_type, content)
                except Exception as e:
                    logger.error(f"进度回调失败: {e}")

        # 开始全面分析
        emit("analysis_start", f"开始分析 {stock_name}，共 {len(dimensions)} 个维度")

        results = []
        for i, key in enumerate(dimensions, 1):
            emit("progress", f"正在分析: {ANALYSIS_TEMPLATES[key]['name']} ({i}/{len(dimensions)})")

            section = self.execute_template(
                key, stock_code, stock_name, progress_callback
            )
            results.append(section)

        # 分析完成
        emit("analysis_complete", f"{stock_name} 分析完成")

        # 添加标题
        header = f"# 📊 {stock_name} 深度分析报告\n\n"
        return header + "".join(results)

    def execute_full_analysis(
        self,
        stock_code: str,
        stock_name: str,
        progress_callback: Optional[Callable[[str, str], None]] = None
    ) -> str:
        """
        执行完整深度分析（8个维度）

        Args:
            stock_code: 股票代码
            stock_name: 股票名称
            progress_callback: 进度回调函数

        Returns:
            str: 完整的分析报告
        """
        return self.execute_dimensions(
            ANALYSIS_ORDER,
            stock_code,
            stock_name,
            progress_callback
        )

    def execute_quick_command(
        self,
        command: str,
        stock_code: str,
        stock_name: str,
        progress_callback: Optional[Callable[[str, str], None]] = None
    ) -> str:
        """
        执行快捷命令

        Args:
            command: 快捷命令对应的模板键值或 "full_analysis"
            stock_code: 股票代码
            stock_name: 股票名称
            progress_callback: 进度回调函数

        Returns:
            str: 分析结果
        """
        if command == "full_analysis":
            return self.execute_full_analysis(stock_code, stock_name, progress_callback)
        else:
            return self.execute_template(command, stock_code, stock_name, progress_callback)
