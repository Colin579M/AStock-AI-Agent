"""
API重试工具和统一错误处理模块

提供:
1. 指数退避重试装饰器
2. 统一的响应结构
3. 错误分类和处理
"""

import time
import functools
import logging
from typing import Any, Callable, Optional, TypeVar, Union
from dataclasses import dataclass, field
from enum import Enum

logger = logging.getLogger(__name__)


class ErrorCategory(Enum):
    """错误类别枚举"""
    NETWORK = "network"           # 网络连接错误
    RATE_LIMIT = "rate_limit"     # API限流
    AUTH = "auth"                 # 认证失败
    NOT_FOUND = "not_found"       # 数据不存在
    INVALID_PARAM = "invalid_param"  # 参数错误
    TIMEOUT = "timeout"           # 超时
    SERVER = "server"             # 服务端错误
    UNKNOWN = "unknown"           # 未知错误


@dataclass
class DataResponse:
    """
    统一的数据响应结构

    Attributes:
        success: 是否成功
        data: 成功时的数据
        error: 错误信息
        error_category: 错误类别
        retried: 重试次数
        source: 数据来源（如 tushare, akshare）
    """
    success: bool
    data: Any = None
    error: Optional[str] = None
    error_category: Optional[ErrorCategory] = None
    retried: int = 0
    source: Optional[str] = None

    def to_str(self) -> str:
        """转换为字符串格式（向后兼容）"""
        if self.success:
            if isinstance(self.data, str):
                return self.data
            return str(self.data) if self.data else ""
        else:
            return f"[{self.error_category.value if self.error_category else 'error'}] {self.error}"

    @classmethod
    def ok(cls, data: Any, source: Optional[str] = None) -> "DataResponse":
        """创建成功响应"""
        return cls(success=True, data=data, source=source)

    @classmethod
    def fail(
        cls,
        error: str,
        category: ErrorCategory = ErrorCategory.UNKNOWN,
        source: Optional[str] = None
    ) -> "DataResponse":
        """创建失败响应"""
        return cls(
            success=False,
            error=error,
            error_category=category,
            source=source
        )


def classify_error(error: Exception) -> ErrorCategory:
    """
    根据异常类型分类错误

    Args:
        error: 异常对象

    Returns:
        ErrorCategory: 错误类别
    """
    error_str = str(error).lower()
    error_type = type(error).__name__

    # 网络相关
    if any(x in error_type for x in ['Connection', 'Network', 'Socket']):
        return ErrorCategory.NETWORK
    if any(x in error_str for x in ['connection', 'network', 'socket', 'refused']):
        return ErrorCategory.NETWORK

    # 超时
    if 'timeout' in error_str or 'Timeout' in error_type:
        return ErrorCategory.TIMEOUT

    # 限流
    if any(x in error_str for x in ['rate limit', 'too many requests', '429', '限流']):
        return ErrorCategory.RATE_LIMIT

    # 认证
    if any(x in error_str for x in ['auth', 'token', '401', '403', 'credential', '权限']):
        return ErrorCategory.AUTH

    # 参数错误
    if any(x in error_str for x in ['invalid', 'parameter', 'argument', '参数']):
        return ErrorCategory.INVALID_PARAM

    # 服务端错误
    if any(x in error_str for x in ['500', '502', '503', '504', 'server']):
        return ErrorCategory.SERVER

    # 未找到
    if any(x in error_str for x in ['not found', '404', '不存在', '无数据']):
        return ErrorCategory.NOT_FOUND

    return ErrorCategory.UNKNOWN


def should_retry(error_category: ErrorCategory) -> bool:
    """
    判断是否应该重试

    可重试的错误类型：
    - 网络错误
    - 超时
    - 限流（需要等待）
    - 服务端错误（临时性）

    不可重试的错误类型：
    - 认证错误
    - 参数错误
    - 数据不存在
    """
    retryable = {
        ErrorCategory.NETWORK,
        ErrorCategory.TIMEOUT,
        ErrorCategory.RATE_LIMIT,
        ErrorCategory.SERVER,
    }
    return error_category in retryable


T = TypeVar('T')


def retry_with_backoff(
    max_retries: int = 3,
    initial_delay: float = 1.0,
    max_delay: float = 30.0,
    backoff_factor: float = 2.0,
    retryable_exceptions: tuple = (Exception,),
    on_retry: Optional[Callable[[Exception, int], None]] = None
):
    """
    指数退避重试装饰器

    Args:
        max_retries: 最大重试次数
        initial_delay: 初始延迟（秒）
        max_delay: 最大延迟（秒）
        backoff_factor: 退避因子
        retryable_exceptions: 可重试的异常类型
        on_retry: 重试时的回调函数

    Example:
        @retry_with_backoff(max_retries=3, initial_delay=1.0)
        def fetch_data(ticker):
            return api.get(ticker)
    """
    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        @functools.wraps(func)
        def wrapper(*args, **kwargs) -> T:
            delay = initial_delay
            last_exception = None

            for attempt in range(max_retries + 1):
                try:
                    return func(*args, **kwargs)
                except retryable_exceptions as e:
                    last_exception = e
                    error_category = classify_error(e)

                    # 检查是否应该重试
                    if not should_retry(error_category):
                        logger.warning(
                            f"{func.__name__} 失败且不可重试: {e} "
                            f"(category: {error_category.value})"
                        )
                        raise

                    # 最后一次尝试，不再重试
                    if attempt == max_retries:
                        logger.error(
                            f"{func.__name__} 在{max_retries}次重试后仍失败: {e}"
                        )
                        raise

                    # 限流错误，使用更长的延迟倍数（单独计算，避免重复乘以 backoff_factor）
                    if error_category == ErrorCategory.RATE_LIMIT:
                        effective_delay = min(delay * 2, max_delay)
                    else:
                        effective_delay = delay

                    logger.warning(
                        f"{func.__name__} 第{attempt + 1}次失败，"
                        f"{effective_delay:.1f}秒后重试: {e}"
                    )

                    # 执行重试回调
                    if on_retry:
                        on_retry(e, attempt + 1)

                    time.sleep(effective_delay)
                    # 更新基础延迟（指数退避）
                    delay = min(delay * backoff_factor, max_delay)

            # 不应该到达这里
            raise last_exception

        return wrapper
    return decorator


def safe_api_call(
    func: Callable[..., T],
    *args,
    source: Optional[str] = None,
    default_on_error: Any = None,
    **kwargs
) -> DataResponse:
    """
    安全的API调用包装器

    自动捕获异常并返回统一的DataResponse

    Args:
        func: 要调用的函数
        *args: 函数参数
        source: 数据来源标识
        default_on_error: 错误时的默认值
        **kwargs: 函数关键字参数

    Returns:
        DataResponse: 统一的响应结构

    Example:
        result = safe_api_call(get_stock_data, "600036", source="tushare")
        if result.success:
            print(result.data)
        else:
            print(f"Error: {result.error}")
    """
    try:
        data = func(*args, **kwargs)

        # 检查空数据
        if data is None or (isinstance(data, str) and not data.strip()):
            return DataResponse.fail(
                "返回数据为空",
                ErrorCategory.NOT_FOUND,
                source
            )

        return DataResponse.ok(data, source)

    except Exception as e:
        category = classify_error(e)
        logger.error(f"API调用失败 [{source}]: {e}")

        return DataResponse(
            success=False,
            data=default_on_error,
            error=str(e),
            error_category=category,
            source=source
        )


# 便捷函数：格式化错误消息
def format_error_message(
    context: str,
    error: Optional[str] = None,
    suggestions: Optional[list] = None
) -> str:
    """
    格式化错误消息

    Args:
        context: 上下文说明
        error: 具体错误
        suggestions: 建议列表

    Returns:
        str: 格式化的错误消息
    """
    lines = [f"[数据获取失败] {context}"]

    if error:
        lines.append(f"错误信息: {error}")

    if suggestions:
        lines.append("可能的原因/建议:")
        for i, suggestion in enumerate(suggestions, 1):
            lines.append(f"  {i}. {suggestion}")

    return "\n".join(lines)


# Tushare特定的错误处理
TUSHARE_ERROR_SUGGESTIONS = {
    ErrorCategory.AUTH: [
        "检查TUSHARE_TOKEN环境变量是否设置正确",
        "确认token是否有效（可在tushare.pro官网验证）",
        "部分接口需要更高级别的token权限"
    ],
    ErrorCategory.RATE_LIMIT: [
        "Tushare有访问频率限制，请稍后重试",
        "建议使用缓存减少API调用次数",
        "考虑升级Tushare会员以获取更高配额"
    ],
    ErrorCategory.NOT_FOUND: [
        "确认股票代码格式正确（如 600036）",
        "该股票可能已退市或代码变更",
        "指定的日期范围内可能没有数据"
    ],
    ErrorCategory.NETWORK: [
        "检查网络连接是否正常",
        "Tushare服务可能暂时不可用",
        "尝试使用VPN或更换网络环境"
    ]
}


def get_tushare_error_message(
    ticker: str,
    api_name: str,
    error: Exception
) -> str:
    """
    生成Tushare特定的错误消息
    """
    category = classify_error(error)
    suggestions = TUSHARE_ERROR_SUGGESTIONS.get(category, [
        "请检查输入参数是否正确",
        "重试或联系Tushare支持"
    ])

    return format_error_message(
        f"获取{ticker}的{api_name}数据失败",
        str(error),
        suggestions
    )
