"""
分析模板模块

提供结构化分析模板和执行引擎。
"""
from .analysis_templates import ANALYSIS_TEMPLATES, QUICK_COMMANDS
from .template_executor import TemplateExecutor

__all__ = [
    "ANALYSIS_TEMPLATES",
    "QUICK_COMMANDS",
    "TemplateExecutor",
]
