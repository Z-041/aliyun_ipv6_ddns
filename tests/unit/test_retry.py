"""重试装饰器单元测试."""

from __future__ import annotations

import time
from unittest.mock import MagicMock, call

import pytest

from aliyun_ddns.utils.retry import retry


class TestRetryDecorator:
    """重试装饰器测试."""

    def test_success_no_retry(self) -> None:
        """测试成功时不重试."""
        mock_func = MagicMock(return_value="success")

        @retry(max_attempts=3, delay=0.1)
        def test_func() -> str:
            return mock_func()

        result = test_func()

        assert result == "success"
        assert mock_func.call_count == 1

    def test_retry_on_failure_then_success(self) -> None:
        """测试失败后重试然后成功."""
        mock_func = MagicMock(side_effect=[Exception("error"), "success"])

        @retry(max_attempts=3, delay=0.1)
        def test_func() -> str:
            return mock_func()

        result = test_func()

        assert result == "success"
        assert mock_func.call_count == 2

    def test_retry_exhausted(self) -> None:
        """测试重试次数耗尽."""
        mock_func = MagicMock(side_effect=Exception("error"))

        @retry(max_attempts=3, delay=0.1)
        def test_func() -> None:
            mock_func()

        with pytest.raises(Exception, match="error"):
            test_func()

        assert mock_func.call_count == 3

    def test_retry_with_backoff(self) -> None:
        """测试指数退避."""
        mock_func = MagicMock(side_effect=Exception("error"))

        @retry(max_attempts=3, delay=0.1, backoff=2.0)
        def test_func() -> None:
            mock_func()

        start_time = time.time()

        with pytest.raises(Exception):
            test_func()

        elapsed = time.time() - start_time

        # 延迟应该是 0.1 + 0.2 = 0.3 秒左右
        assert elapsed >= 0.25
        assert mock_func.call_count == 3

    def test_retry_specific_exception(self) -> None:
        """测试只重试特定异常."""
        mock_func = MagicMock(side_effect=[ValueError("value error"), "success"])

        @retry(max_attempts=3, delay=0.1, exceptions=(ValueError,))
        def test_func() -> str:
            return mock_func()

        result = test_func()

        assert result == "success"
        assert mock_func.call_count == 2

    def test_no_retry_for_other_exceptions(self) -> None:
        """测试其他异常不重试."""
        mock_func = MagicMock(side_effect=TypeError("type error"))

        @retry(max_attempts=3, delay=0.1, exceptions=(ValueError,))
        def test_func() -> None:
            mock_func()

        with pytest.raises(TypeError):
            test_func()

        assert mock_func.call_count == 1

    def test_retry_preserves_function_metadata(self) -> None:
        """测试保留函数元数据."""

        @retry(max_attempts=3)
        def test_function() -> str:
            """Test function docstring."""
            return "result"

        assert test_function.__name__ == "test_function"
        assert test_function.__doc__ == "Test function docstring."

    def test_retry_with_function_arguments(self) -> None:
        """测试带参数的函数重试."""
        mock_func = MagicMock(side_effect=[Exception("error"), "success"])

        @retry(max_attempts=3, delay=0.1)
        def test_func(a: int, b: str, c: int = 0) -> str:
            return mock_func(a, b, c=c)

        result = test_func(1, "test", c=2)

        assert result == "success"
        mock_func.assert_has_calls([call(1, "test", c=2), call(1, "test", c=2)])
