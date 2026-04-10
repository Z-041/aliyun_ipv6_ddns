"""重试装饰器."""

from __future__ import annotations

import functools
import time
from typing import Any, Callable, TypeVar

from aliyun_ddns.utils.logging import get_logger

logger = get_logger(__name__)

F = TypeVar("F", bound=Callable[..., Any])


def retry(
    max_attempts: int = 3,
    delay: float = 1.0,
    backoff: float = 2.0,
    exceptions: tuple[type[Exception], ...] = (Exception,),
) -> Callable[[F], F]:
    """重试装饰器.

    Args:
        max_attempts: 最大重试次数
        delay: 初始延迟时间（秒）
        backoff: 延迟倍数
        exceptions: 需要重试的异常类型

    Returns:
        装饰器函数
    """

    def decorator(func: F) -> F:
        @functools.wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            attempts = 0
            current_delay = delay

            while attempts < max_attempts:
                try:
                    return func(*args, **kwargs)
                except exceptions as e:
                    attempts += 1
                    if attempts >= max_attempts:
                        logger.debug(
                            f"{func.__name__} 在 {max_attempts} 次尝试后失败: {e}"
                        )
                        raise

                    logger.debug(
                        f"{func.__name__} 第 {attempts} 次尝试失败，{current_delay:.1f}秒后重试: {e}"
                    )
                    time.sleep(current_delay)
                    current_delay *= backoff

            return None  # 理论上不会执行到这里

        return wrapper  # type: ignore[return-value]

    return decorator
