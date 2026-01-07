"""
TradingAgents 结构化日志配置模块

提供:
1. 统一的日志格式
2. 多输出目标（控制台、文件）
3. 日志级别管理
4. JSON格式日志（用于分析）
"""

import logging
import logging.handlers
import os
import json
from datetime import datetime
from pathlib import Path
from typing import Optional, Dict, Any


# 默认日志目录
DEFAULT_LOG_DIR = Path.home() / "Documents" / "TradingAgents" / "logs"


class JSONFormatter(logging.Formatter):
    """JSON格式日志格式化器"""

    def format(self, record: logging.LogRecord) -> str:
        log_data = {
            "timestamp": datetime.utcnow().isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "module": record.module,
            "function": record.funcName,
            "line": record.lineno,
        }

        # 添加额外字段
        if hasattr(record, 'ticker'):
            log_data['ticker'] = record.ticker
        if hasattr(record, 'api_source'):
            log_data['api_source'] = record.api_source
        if hasattr(record, 'duration_ms'):
            log_data['duration_ms'] = record.duration_ms
        if hasattr(record, 'error_category'):
            log_data['error_category'] = record.error_category

        # 异常信息
        if record.exc_info:
            log_data['exception'] = self.formatException(record.exc_info)

        return json.dumps(log_data, ensure_ascii=False)


class ColoredConsoleFormatter(logging.Formatter):
    """带颜色的控制台日志格式化器"""

    COLORS = {
        'DEBUG': '\033[36m',      # Cyan
        'INFO': '\033[32m',       # Green
        'WARNING': '\033[33m',    # Yellow
        'ERROR': '\033[31m',      # Red
        'CRITICAL': '\033[35m',   # Magenta
    }
    RESET = '\033[0m'

    def format(self, record: logging.LogRecord) -> str:
        color = self.COLORS.get(record.levelname, self.RESET)

        # 简化的控制台格式
        timestamp = datetime.now().strftime('%H:%M:%S')
        level = record.levelname[:4]
        name = record.name.split('.')[-1][:15]
        message = record.getMessage()

        return f"{color}[{timestamp}] {level:4} [{name:15}] {message}{self.RESET}"


def setup_logging(
    log_level: str = "INFO",
    log_dir: Optional[Path] = None,
    enable_console: bool = True,
    enable_file: bool = True,
    enable_json: bool = False,
    log_file_name: str = "tradingagents.log"
) -> logging.Logger:
    """
    配置TradingAgents日志系统

    Args:
        log_level: 日志级别 (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        log_dir: 日志目录
        enable_console: 是否启用控制台输出
        enable_file: 是否启用文件输出
        enable_json: 是否启用JSON格式日志
        log_file_name: 日志文件名

    Returns:
        配置好的根logger
    """
    log_dir = log_dir or DEFAULT_LOG_DIR
    log_dir.mkdir(parents=True, exist_ok=True)

    # 获取根logger
    root_logger = logging.getLogger("tradingagents")
    root_logger.setLevel(getattr(logging, log_level.upper(), logging.INFO))

    # 清除现有handler
    root_logger.handlers.clear()

    # 控制台输出
    if enable_console:
        console_handler = logging.StreamHandler()
        console_handler.setFormatter(ColoredConsoleFormatter())
        console_handler.setLevel(logging.INFO)
        root_logger.addHandler(console_handler)

    # 文件输出（普通格式）
    if enable_file:
        file_handler = logging.handlers.RotatingFileHandler(
            log_dir / log_file_name,
            maxBytes=10 * 1024 * 1024,  # 10MB
            backupCount=5,
            encoding='utf-8'
        )
        file_handler.setFormatter(logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        ))
        file_handler.setLevel(logging.DEBUG)
        root_logger.addHandler(file_handler)

    # JSON格式日志（用于分析）
    if enable_json:
        json_handler = logging.handlers.RotatingFileHandler(
            log_dir / "tradingagents.json.log",
            maxBytes=10 * 1024 * 1024,
            backupCount=5,
            encoding='utf-8'
        )
        json_handler.setFormatter(JSONFormatter())
        json_handler.setLevel(logging.DEBUG)
        root_logger.addHandler(json_handler)

    return root_logger


def get_logger(name: str) -> logging.Logger:
    """
    获取模块专用logger

    Args:
        name: logger名称（通常使用__name__）

    Returns:
        配置好的logger

    Example:
        logger = get_logger(__name__)
        logger.info("Processing ticker", extra={'ticker': '600036'})
    """
    return logging.getLogger(f"tradingagents.{name}")


class LogContext:
    """日志上下文管理器，用于添加额外信息"""

    def __init__(self, logger: logging.Logger, **context):
        self.logger = logger
        self.context = context

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        pass

    def _log(self, level: int, message: str, **kwargs):
        extra = {**self.context, **kwargs}
        self.logger.log(level, message, extra=extra)

    def debug(self, message: str, **kwargs):
        self._log(logging.DEBUG, message, **kwargs)

    def info(self, message: str, **kwargs):
        self._log(logging.INFO, message, **kwargs)

    def warning(self, message: str, **kwargs):
        self._log(logging.WARNING, message, **kwargs)

    def error(self, message: str, **kwargs):
        self._log(logging.ERROR, message, **kwargs)


# 便捷函数：API调用日志
def log_api_call(
    logger: logging.Logger,
    api_name: str,
    ticker: str,
    success: bool,
    duration_ms: float,
    error: Optional[str] = None
):
    """
    记录API调用日志

    Args:
        logger: logger实例
        api_name: API名称
        ticker: 股票代码
        success: 是否成功
        duration_ms: 耗时（毫秒）
        error: 错误信息（如有）
    """
    extra = {
        'ticker': ticker,
        'api_source': api_name,
        'duration_ms': duration_ms,
    }

    if success:
        logger.info(
            f"API调用成功: {api_name}({ticker}) - {duration_ms:.0f}ms",
            extra=extra
        )
    else:
        extra['error_category'] = 'api_error'
        logger.error(
            f"API调用失败: {api_name}({ticker}) - {error}",
            extra=extra
        )


# 模块级别logger配置
_root_logger = None

def init_logging(log_level: str = "INFO", **kwargs):
    """初始化全局日志系统"""
    global _root_logger
    if _root_logger is None:
        _root_logger = setup_logging(log_level=log_level, **kwargs)
    return _root_logger
