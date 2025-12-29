# Epic Technical Specification: P14-5 Code Standardization

Date: 2025-12-29
Author: Claude (AI-Generated)
Epic ID: P14-5
Status: Draft
Priority: P3

---

## Overview

Epic P14-5 addresses code standardization across the backend, creating reusable patterns and utilities to reduce duplication and improve consistency. The epic focuses on:

1. Creating a `@singleton` decorator to replace manual singleton implementations
2. Creating a centralized backoff/retry utility
3. Standardizing service initialization patterns
4. Other consistency fixes identified in technical debt backlog

## Current State Analysis

### Singleton Pattern Usage

Currently, 10+ services implement the singleton pattern manually:

| Service | Instance Variable | Getter Function | Reset Function |
|---------|------------------|-----------------|----------------|
| `adaptive_sampler.py` | `_adaptive_sampler` | `get_adaptive_sampler()` | `reset_adaptive_sampler()` |
| `audio_extractor.py` | `_audio_extractor` | `get_audio_extractor()` | `reset_audio_extractor()` |
| `correlation_service.py` | `_correlation_service` | `get_correlation_service()` | `reset_correlation_service()` |
| `face_embedding_service.py` | `_face_embedding_service` | `get_face_embedding_service()` | - |
| `frame_extractor.py` | `_frame_extractor` | `get_frame_extractor()` | `reset_frame_extractor()` |
| `mqtt_service.py` | `_mqtt_service` | `get_mqtt_service()` | - |
| `vagueness_detector.py` | `_vagueness_detector` | `get_vagueness_detector()` | - |
| `vehicle_detection_service.py` | `_vehicle_detection_service` | `get_vehicle_detection_service()` | - |
| `websocket_manager.py` | `manager` | - | - |

**Typical Pattern (50+ lines per service):**
```python
# Singleton instance
_service: Optional[Service] = None

def get_service() -> Service:
    """Get the singleton Service instance."""
    global _service
    if _service is None:
        _service = Service()
    return _service

def reset_service() -> None:
    """Reset the singleton instance (useful for testing)."""
    global _service
    _service = None
```

### Retry Pattern Usage

**Tenacity (clip_service.py only):**
```python
from tenacity import (
    retry, stop_after_attempt, wait_exponential,
    retry_if_exception_type
)

@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=1, max=10),
    retry=retry_if_exception_type(...)
)
async def download_clip(...):
    ...
```

**Manual Retry (event_processor.py, ai_service.py):**
```python
for attempt in range(max_retries):
    try:
        result = await operation()
        return result
    except Exception as e:
        if attempt < max_retries - 1:
            delay = (2 ** attempt)  # Exponential backoff
            await asyncio.sleep(delay)
        else:
            raise
```

## Objectives and Scope

### In Scope

- Create `@singleton` decorator with reset support
- Create centralized retry/backoff utility
- Update 10+ services to use new patterns
- Standardize service initialization
- Document new patterns in codebase

### Out of Scope

- Major service refactoring
- Architectural changes
- New feature development
- Performance optimization

## Detailed Design

### Story P14-5.1: Create @singleton Decorator

**Create:** `backend/app/core/decorators.py`

```python
"""
Reusable decorators for service patterns.

Provides standardized implementations of common patterns like
singleton services with test reset support.
"""

from functools import wraps
from typing import TypeVar, Callable, Optional
import threading

T = TypeVar('T')


class SingletonMeta(type):
    """
    Thread-safe singleton metaclass.

    Usage:
        class MyService(metaclass=SingletonMeta):
            pass

        # Always returns same instance
        service1 = MyService()
        service2 = MyService()
        assert service1 is service2

        # Reset for testing
        MyService._reset_instance()
    """
    _instances: dict = {}
    _lock: threading.Lock = threading.Lock()

    def __call__(cls, *args, **kwargs):
        if cls not in cls._instances:
            with cls._lock:
                if cls not in cls._instances:
                    instance = super().__call__(*args, **kwargs)
                    cls._instances[cls] = instance
        return cls._instances[cls]

    def _reset_instance(cls) -> None:
        """Reset the singleton instance (for testing)."""
        with cls._lock:
            cls._instances.pop(cls, None)


def singleton(cls: type[T]) -> type[T]:
    """
    Decorator to make a class a singleton.

    Thread-safe lazy initialization with test reset support.

    Usage:
        @singleton
        class MyService:
            def __init__(self):
                self.data = []

        # Get singleton instance
        service = MyService()

        # Reset for testing
        MyService._reset_instance()

    Example migration:
        # Before:
        _my_service: Optional[MyService] = None

        def get_my_service() -> MyService:
            global _my_service
            if _my_service is None:
                _my_service = MyService()
            return _my_service

        def reset_my_service() -> None:
            global _my_service
            _my_service = None

        # After:
        @singleton
        class MyService:
            pass

        # Usage:
        service = MyService()  # Always same instance
        MyService._reset_instance()  # For testing
    """
    # Store original __init__
    original_init = cls.__init__

    # Track instance and lock
    cls._instance: Optional[T] = None
    cls._lock = threading.Lock()

    @wraps(original_init)
    def __init__(self, *args, **kwargs):
        # Only initialize once
        if not hasattr(self, '_initialized'):
            original_init(self, *args, **kwargs)
            self._initialized = True

    def __new__(cls, *args, **kwargs):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = object.__new__(cls)
        return cls._instance

    @classmethod
    def _reset_instance(cls) -> None:
        """Reset the singleton instance (for testing)."""
        with cls._lock:
            if cls._instance is not None:
                # Clean up if instance has cleanup method
                if hasattr(cls._instance, 'cleanup'):
                    cls._instance.cleanup()
            cls._instance = None

    @classmethod
    def _get_instance(cls) -> Optional[T]:
        """Get current instance without creating."""
        return cls._instance

    cls.__init__ = __init__
    cls.__new__ = __new__
    cls._reset_instance = _reset_instance
    cls._get_instance = _get_instance

    return cls
```

**Migration Example:**

```python
# Before (adaptive_sampler.py):
class AdaptiveSampler:
    def __init__(self):
        self._strategies = {}

_adaptive_sampler: Optional[AdaptiveSampler] = None

def get_adaptive_sampler() -> AdaptiveSampler:
    global _adaptive_sampler
    if _adaptive_sampler is None:
        _adaptive_sampler = AdaptiveSampler()
    return _adaptive_sampler

def reset_adaptive_sampler() -> None:
    global _adaptive_sampler
    _adaptive_sampler = None

# After:
from app.core.decorators import singleton

@singleton
class AdaptiveSampler:
    def __init__(self):
        self._strategies = {}

# Usage:
sampler = AdaptiveSampler()  # Always same instance

# Testing:
AdaptiveSampler._reset_instance()
```

### Story P14-5.2: Create Backoff Utility

**Create:** `backend/app/core/retry.py`

```python
"""
Centralized retry/backoff utilities.

Provides consistent retry behavior across all services with
configurable strategies and proper logging.
"""

import asyncio
import logging
from functools import wraps
from typing import Callable, TypeVar, Any, Sequence, Optional
from datetime import datetime, timezone

logger = logging.getLogger(__name__)

T = TypeVar('T')


class RetryConfig:
    """Configuration for retry behavior."""

    def __init__(
        self,
        max_attempts: int = 3,
        base_delay: float = 1.0,
        max_delay: float = 30.0,
        exponential_base: float = 2.0,
        jitter: bool = True,
        retryable_exceptions: Sequence[type[Exception]] = (Exception,),
    ):
        """
        Initialize retry configuration.

        Args:
            max_attempts: Maximum number of attempts (including first)
            base_delay: Initial delay between retries in seconds
            max_delay: Maximum delay between retries
            exponential_base: Base for exponential backoff
            jitter: Whether to add random jitter to delays
            retryable_exceptions: Exception types that trigger retry
        """
        self.max_attempts = max_attempts
        self.base_delay = base_delay
        self.max_delay = max_delay
        self.exponential_base = exponential_base
        self.jitter = jitter
        self.retryable_exceptions = tuple(retryable_exceptions)


# Pre-configured strategies
RETRY_QUICK = RetryConfig(max_attempts=2, base_delay=0.5, max_delay=2.0)
RETRY_STANDARD = RetryConfig(max_attempts=3, base_delay=1.0, max_delay=10.0)
RETRY_PERSISTENT = RetryConfig(max_attempts=5, base_delay=2.0, max_delay=60.0)
RETRY_AI_PROVIDER = RetryConfig(
    max_attempts=3,
    base_delay=1.0,
    max_delay=30.0,
    retryable_exceptions=(ConnectionError, TimeoutError),
)


def calculate_delay(
    attempt: int,
    config: RetryConfig,
) -> float:
    """Calculate delay for a given attempt number."""
    import random

    delay = min(
        config.base_delay * (config.exponential_base ** attempt),
        config.max_delay
    )

    if config.jitter:
        # Add ±25% jitter
        jitter_range = delay * 0.25
        delay += random.uniform(-jitter_range, jitter_range)

    return max(0, delay)


async def retry_async(
    func: Callable[..., T],
    *args,
    config: RetryConfig = RETRY_STANDARD,
    operation_name: Optional[str] = None,
    **kwargs,
) -> T:
    """
    Execute an async function with retry logic.

    Args:
        func: Async function to execute
        *args: Positional arguments for func
        config: Retry configuration
        operation_name: Name for logging (defaults to func name)
        **kwargs: Keyword arguments for func

    Returns:
        Result of successful function call

    Raises:
        Last exception if all retries fail
    """
    op_name = operation_name or func.__name__
    last_exception: Optional[Exception] = None

    for attempt in range(config.max_attempts):
        try:
            return await func(*args, **kwargs)
        except config.retryable_exceptions as e:
            last_exception = e

            if attempt < config.max_attempts - 1:
                delay = calculate_delay(attempt, config)
                logger.warning(
                    f"{op_name} failed (attempt {attempt + 1}/{config.max_attempts}), "
                    f"retrying in {delay:.1f}s: {e}",
                    extra={
                        "event_type": "retry_attempt",
                        "operation": op_name,
                        "attempt": attempt + 1,
                        "max_attempts": config.max_attempts,
                        "delay_seconds": delay,
                        "error": str(e),
                    }
                )
                await asyncio.sleep(delay)
            else:
                logger.error(
                    f"{op_name} failed after {config.max_attempts} attempts: {e}",
                    extra={
                        "event_type": "retry_exhausted",
                        "operation": op_name,
                        "attempts": config.max_attempts,
                        "final_error": str(e),
                    }
                )

    raise last_exception


def with_retry(
    config: RetryConfig = RETRY_STANDARD,
    operation_name: Optional[str] = None,
):
    """
    Decorator to add retry behavior to async functions.

    Usage:
        @with_retry(config=RETRY_AI_PROVIDER)
        async def call_ai_api(prompt: str) -> str:
            ...

        @with_retry(operation_name="download_clip")
        async def download(url: str) -> bytes:
            ...
    """
    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        op_name = operation_name or func.__name__

        @wraps(func)
        async def wrapper(*args, **kwargs) -> T:
            return await retry_async(
                func, *args,
                config=config,
                operation_name=op_name,
                **kwargs
            )
        return wrapper
    return decorator
```

**Migration Example:**

```python
# Before (ai_service.py):
async def _describe_with_openai(self, images, prompt):
    max_retries = 3
    for attempt in range(max_retries):
        try:
            response = await client.chat.completions.create(...)
            return response.choices[0].message.content
        except Exception as e:
            if attempt < max_retries - 1:
                delay = 2 ** attempt
                await asyncio.sleep(delay)
            else:
                raise

# After:
from app.core.retry import with_retry, RETRY_AI_PROVIDER

@with_retry(config=RETRY_AI_PROVIDER)
async def _describe_with_openai(self, images, prompt):
    response = await client.chat.completions.create(...)
    return response.choices[0].message.content
```

### Story P14-5.3-P14-5.10: Migrate Services

**Services to Migrate to @singleton:**

| Story | Service | Priority |
|-------|---------|----------|
| P14-5.3 | `adaptive_sampler.py` | P3 |
| P14-5.4 | `correlation_service.py` | P3 |
| P14-5.5 | `frame_extractor.py` | P3 |
| P14-5.6 | `audio_extractor.py` | P3 |
| P14-5.7 | `mqtt_service.py` | P3 |
| P14-5.8 | `face_embedding_service.py` | P3 |
| P14-5.9 | `vehicle_detection_service.py` | P3 |
| P14-5.10 | `vagueness_detector.py` | P3 |

**Services to Migrate to Retry Utility:**

| Service | Current Pattern | Target Config |
|---------|-----------------|---------------|
| `event_processor.py` | Manual loop | `RETRY_STANDARD` |
| `ai_service.py` | Manual loop | `RETRY_AI_PROVIDER` |
| `protect_service.py` | Various | `RETRY_STANDARD` |
| `webhook_service.py` | Manual | `RETRY_PERSISTENT` |
| `push_notification_service.py` | Manual | `RETRY_STANDARD` |

### Story P14-5.11: Standardize Service Initialization

**Problem:** Services initialize differently - some in `main.py` lifespan, some lazily.

**Solution:** Create consistent initialization pattern:

```python
# backend/app/core/service_registry.py

from typing import Dict, Any, Callable
import logging

logger = logging.getLogger(__name__)

_services: Dict[str, Any] = {}
_initializers: Dict[str, Callable] = {}


def register_service(name: str, initializer: Callable):
    """Register a service initializer."""
    _initializers[name] = initializer


def get_service(name: str) -> Any:
    """Get an initialized service by name."""
    if name not in _services:
        if name in _initializers:
            _services[name] = _initializers[name]()
        else:
            raise KeyError(f"Unknown service: {name}")
    return _services[name]


async def initialize_all():
    """Initialize all registered services."""
    for name, init in _initializers.items():
        if name not in _services:
            logger.info(f"Initializing service: {name}")
            _services[name] = init()


async def shutdown_all():
    """Shutdown all services gracefully."""
    for name, service in _services.items():
        if hasattr(service, 'shutdown'):
            logger.info(f"Shutting down service: {name}")
            await service.shutdown()
    _services.clear()
```

## APIs and Interfaces

### New Utilities

| Module | Function/Class | Purpose |
|--------|----------------|---------|
| `app.core.decorators` | `@singleton` | Thread-safe singleton pattern |
| `app.core.decorators` | `SingletonMeta` | Metaclass alternative |
| `app.core.retry` | `retry_async()` | Async retry with backoff |
| `app.core.retry` | `@with_retry` | Decorator for retry |
| `app.core.retry` | `RetryConfig` | Configuration class |
| `app.core.retry` | `RETRY_*` | Pre-configured strategies |

## Acceptance Criteria

### AC-1: Singleton Decorator
- [ ] `@singleton` decorator created in `app/core/decorators.py`
- [ ] Thread-safe implementation
- [ ] `_reset_instance()` method available for testing
- [ ] Documentation with examples

### AC-2: Retry Utility
- [ ] `retry_async()` function created in `app/core/retry.py`
- [ ] `@with_retry` decorator available
- [ ] Pre-configured strategies (QUICK, STANDARD, PERSISTENT, AI_PROVIDER)
- [ ] Proper logging of retry attempts

### AC-3: Service Migration
- [ ] 8+ services migrated to `@singleton`
- [ ] 5+ services migrated to retry utility
- [ ] All existing tests pass
- [ ] Code reduction of 200+ lines

### AC-4: Documentation
- [ ] Docstrings on all new utilities
- [ ] Usage examples in docstrings
- [ ] Migration examples documented

## Test Strategy

### Unit Tests

```python
# tests/test_core/test_decorators.py

class TestSingletonDecorator:
    def test_returns_same_instance(self):
        @singleton
        class TestService:
            def __init__(self):
                self.value = 0

        s1 = TestService()
        s2 = TestService()
        assert s1 is s2

    def test_reset_creates_new_instance(self):
        @singleton
        class TestService:
            pass

        s1 = TestService()
        TestService._reset_instance()
        s2 = TestService()
        assert s1 is not s2

    def test_thread_safe(self):
        import threading

        @singleton
        class TestService:
            pass

        instances = []

        def get_instance():
            instances.append(TestService())

        threads = [threading.Thread(target=get_instance) for _ in range(10)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert all(i is instances[0] for i in instances)


# tests/test_core/test_retry.py

class TestRetryAsync:
    async def test_succeeds_on_first_attempt(self):
        call_count = 0

        async def operation():
            nonlocal call_count
            call_count += 1
            return "success"

        result = await retry_async(operation)
        assert result == "success"
        assert call_count == 1

    async def test_retries_on_failure(self):
        attempts = []

        async def operation():
            attempts.append(1)
            if len(attempts) < 3:
                raise ConnectionError("Failed")
            return "success"

        result = await retry_async(operation, config=RETRY_QUICK)
        assert result == "success"
        assert len(attempts) == 3

    async def test_raises_after_exhausted(self):
        async def always_fails():
            raise ValueError("Always fails")

        with pytest.raises(ValueError):
            await retry_async(always_fails, config=RETRY_QUICK)
```

## Risks and Mitigations

| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| Breaking existing singleton users | Medium | High | Maintain backward-compatible API |
| Thread safety issues | Low | High | Thorough testing with concurrent access |
| Retry logic differences | Medium | Medium | Test each migration individually |

---

_Tech spec generated for Phase 14 Epic P14-5: Code Standardization_
