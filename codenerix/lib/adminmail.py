"""
 Mitigation Email Throttler for Django

Designed for high-load scenarios (DB crashes, cascade failures) where
hundreds of errors/second could trigger thousands of emails.

Strategy:
- Atomic counters (cache.incr) for zero race conditions
- Fixed time windows (simpler and faster than sliding)
- Fail-open always (never lose critical errors)
- Minimal memory footprint under stress

Usage:
    LOGGING = {
        'handlers': {
            'mail_admins': {
                'class': 'codenerix.lib.adminmail.ThrottledAdminEmailHandler',
                # Cache configuration$
                "cache_window_seconds": 300,  # Cache window of 5 minutes$
                "cache_max_emails_per_error": 5,  # Max 3 emails per error type$
                "cache_max_emails_total": 20,  # Max 10 total emails$
                # Fallback when no cache (per worker)$
                "fallback_window_seconds": 60,  # Cache window of 1 minute$
                "fallback_max_emails_per_error": 2,  # Max 2 emails per error type$
                "fallback_max_emails_total": 5,  # Max 5 total emails$
                # Others$
                "group_by_error_type": True,  # Group emails by error type$
            }
        }
    }
"""  # noqa: E501

import hashlib
import logging
import threading
import time
from typing import TypedDict

from django.core.cache import (  # type:ignore # pylint: disable=import-error
    cache,
)
from django.core.cache.backends.dummy import DummyCache
from django.utils.log import (  # type: ignore # pylint: disable=import-error
    AdminEmailHandler,
)


class ThrottleEntry(TypedDict):
    """Structure for memory storage entries."""

    count: int
    expires: float


logger = logging.getLogger(__name__)


class ThrottledAdminEmailHandler(  # pylint: disable=too-many-instance-attributes,too-few-public-methods # noqa: E501
    AdminEmailHandler,
):
    """
    Ultra-robust email throttler optimized for  scenarios.

    Uses atomic counters instead of timestamp arrays for:
    - Zero race conditions under high load
    - Minimal Redis memory usage
    - Fast O(1) operations

    Gracefully degrades to in-memory throttling if cache unavailable.
    """

    # === CACHE MODE (Redis/Memcache available) ===
    CACHE_WINDOW_SECONDS = 300  # 5 minutes fixed window
    CACHE_MAX_EMAILS_PER_ERROR = 5  # Per error type globally
    CACHE_MAX_EMAILS_TOTAL = 20  # Total across all errors

    # === FALLBACK MODE (no cache) ===
    FALLBACK_WINDOW_SECONDS = 60  # 1 minute fixed window
    FALLBACK_MAX_EMAILS_PER_ERROR = 2  # Per error type per worker
    FALLBACK_MAX_EMAILS_TOTAL = 5  # Total per worker
    FALLBACK_CLEANUP_INTERVAL = 300  # Clean expired entries every 5 min

    # === SHARED ===
    GROUP_BY_ERROR_TYPE = True
    CACHE_KEY_PREFIX = "email_throttle"

    # === FALLBACK STATE ===
    # Structure: {error_key: {'count': int, 'expires': float}}
    _memory_storage: dict[str, ThrottleEntry]
    _memory_lock = threading.Lock()
    _last_cleanup = time.time()
    _cache_available = None

    def __init__(  # pylint: disable=too-many-arguments
        self,
        *,
        cache_window_seconds=None,
        cache_max_emails_per_error=None,
        cache_max_emails_total=None,
        fallback_window_seconds=None,
        fallback_max_emails_per_error=None,
        fallback_max_emails_total=None,
        group_by_error_type=None,
        **kwargs,
    ):
        """
        Initialize with optional configuration overrides.

        All parameters can be overridden via LOGGING configuration.
        """
        super().__init__(**kwargs)

        # Apply configuration overrides for CACHE MODE
        if cache_window_seconds is not None:
            self.CACHE_WINDOW_SECONDS = (  # pylint: disable=invalid-name
                cache_window_seconds
            )
        if cache_max_emails_per_error is not None:
            self.CACHE_MAX_EMAILS_PER_ERROR = (  # pylint: disable=invalid-name
                cache_max_emails_per_error
            )
        if cache_max_emails_total is not None:
            self.CACHE_MAX_EMAILS_TOTAL = (  # pylint: disable=invalid-name
                cache_max_emails_total
            )

        # Apply configuration overrides for FALLBACK MODE
        if fallback_window_seconds is not None:
            self.FALLBACK_WINDOW_SECONDS = (  # pylint: disable=invalid-name
                fallback_window_seconds
            )
        if fallback_max_emails_per_error is not None:
            self.FALLBACK_MAX_EMAILS_PER_ERROR = (  # pylint: disable=invalid-name # noqa: E501
                fallback_max_emails_per_error
            )
        if fallback_max_emails_total is not None:
            self.FALLBACK_MAX_EMAILS_TOTAL = (  # pylint: disable=invalid-name
                fallback_max_emails_total
            )

        # Apply shared configuration
        if group_by_error_type is not None:
            self.GROUP_BY_ERROR_TYPE = (  # pylint: disable=invalid-name
                group_by_error_type
            )

        # Detect cache availability once per class
        if ThrottledAdminEmailHandler._cache_available is None:
            ThrottledAdminEmailHandler._cache_available = self._detect_cache()
            self._log_initialization()

    def _detect_cache(self) -> bool:
        """
        Detect functional cache backend.

        Returns:
            bool: True if real cache available, False if DummyCache
        """
        if isinstance(cache, DummyCache):
            return False

        # Verify cache actually works
        test_key = f"{self.CACHE_KEY_PREFIX}:health"
        try:
            cache.set(test_key, 1, timeout=1)
            result = cache.get(test_key)
            cache.delete(test_key)
            return result == 1
        except Exception as e:
            logger.warning(
                f"Cache detection failed: {e}. Using fallback mode.",
            )
            return False

    def _log_initialization(self):
        """Log active throttling mode for operational visibility."""
        if self._cache_available:
            logger.info(
                f"ThrottledAdminEmailHandler: CACHE MODE active. "
                f"Window: {self.CACHE_WINDOW_SECONDS}s. "
                f"Limits: {self.CACHE_MAX_EMAILS_PER_ERROR} per error type, "
                f"{self.CACHE_MAX_EMAILS_TOTAL} "
                "total (global across workers).",
            )
        else:
            logger.warning(
                f"ThrottledAdminEmailHandler: FALLBACK MODE active. "
                f"Window: {self.FALLBACK_WINDOW_SECONDS}s. "
                f"Limits: {self.FALLBACK_MAX_EMAILS_PER_ERROR} "
                "per error type, "
                f"{self.FALLBACK_MAX_EMAILS_TOTAL} total (PER WORKER). "
                f"With multiple workers, actual limit = "
                "configured × worker_count. "
                f"Configure Redis/Memcache for true global throttling.",
            )

    def _get_error_signature(self, record) -> str:
        """
        Generate unique identifier for error grouping.

        Groups by exception type + file location for effective throttling
        of identical errors while allowing different errors through.

        Args:
            record: LogRecord instance

        Returns:
            str: 16-char hash identifying this error type, or "global" if
                 GROUP_BY_ERROR_TYPE is False
        """
        if not self.GROUP_BY_ERROR_TYPE:
            return "global"

        # Build signature from error identity
        exc_type = (
            record.exc_info[0].__name__
            if record.exc_info
            else record.levelname
        )
        signature = f"{exc_type}:{record.pathname}:{record.lineno}"

        # Hash with error handling for special characters
        return hashlib.md5(
            signature.encode("utf-8", errors="replace"),
            usedforsecurity=False,
        ).hexdigest()[:16]

    def _check_cache_throttle(self, error_key: str) -> tuple[bool, bool]:
        """
        Atomic cache-based throttling using INCR.

        Uses two independent counters:
        - Per-error counter: Prevents spam from same error type
        - Total counter: Caps overall email volume

        Both use fixed time windows with atomic increments.
        Email is allowed only if BOTH limits are satisfied.

        Args:
            error_key: Unique error identifier

        Returns:
            tuple: (allowed_per_error: bool, allowed_total: bool)
        """
        error_count_key = f"{self.CACHE_KEY_PREFIX}:err:{error_key}"
        total_count_key = f"{self.CACHE_KEY_PREFIX}:total"

        try:
            # Atomic increment for per-error counter
            try:
                error_count = cache.incr(error_count_key)
            except ValueError:
                # Key doesn't exist - initialize with TTL
                cache.set(
                    error_count_key,
                    1,
                    timeout=self.CACHE_WINDOW_SECONDS,
                )
                error_count = 1

            # Atomic increment for total counter
            try:
                total_count = cache.incr(total_count_key)
            except ValueError:
                cache.set(
                    total_count_key,
                    1,
                    timeout=self.CACHE_WINDOW_SECONDS,
                )
                total_count = 1

            # Check both limits
            error_allowed = error_count <= self.CACHE_MAX_EMAILS_PER_ERROR
            total_allowed = total_count <= self.CACHE_MAX_EMAILS_TOTAL

            return error_allowed, total_allowed

        except Exception as e:
            # Cache failure - fail open (allow email)
            logger.error(f"Cache throttling error: {e}. Allowing email.")
            return True, True

    def _check_memory_throttle(self, error_key: str) -> tuple[bool, bool]:
        """
        Thread-safe in-memory throttling with intelligent cleanup.

        Periodically removes expired entries to prevent memory leaks
        without clearing active counters.

        Args:
            error_key: Unique error identifier

        Returns:
            tuple: (allowed_per_error: bool, allowed_total: bool)
        """
        now = time.time()

        with self._memory_lock:
            # Periodic cleanup of expired entries
            if now - self._last_cleanup > self.FALLBACK_CLEANUP_INTERVAL:
                self._cleanup_expired_entries(now)
                self._last_cleanup = now

            # Get or initialize per-error counter
            error_data = self._memory_storage.get(error_key)
            if not error_data or now > error_data["expires"]:
                # New window for this error
                error_data = {
                    "count": 1,
                    "expires": now + self.FALLBACK_WINDOW_SECONDS,
                }
                self._memory_storage[error_key] = error_data
            else:
                # Increment existing counter
                error_data["count"] += 1

            # Get or initialize total counter (using special key)
            total_data = self._memory_storage.get("__total__")
            if not total_data or now > total_data["expires"]:
                # New total window
                total_data = {
                    "count": 1,
                    "expires": now + self.FALLBACK_WINDOW_SECONDS,
                }
                self._memory_storage["__total__"] = total_data
            else:
                # Increment total counter
                total_data["count"] += 1

            # Check both limits
            error_allowed = (
                error_data["count"] <= self.FALLBACK_MAX_EMAILS_PER_ERROR
            )
            total_allowed = (
                total_data["count"] <= self.FALLBACK_MAX_EMAILS_TOTAL
            )

            return error_allowed, total_allowed

    def _cleanup_expired_entries(self, current_time: float):
        """
        Remove expired entries from memory storage.

        Only removes entries outside their time window, preserving
        active counters. Prevents unbounded memory growth.

        Args:
            current_time: Current timestamp
        """
        expired_keys = [
            key
            for key, data in self._memory_storage.items()
            if current_time > data["expires"]
        ]

        for key in expired_keys:
            del self._memory_storage[key]

        if expired_keys:
            logger.debug(
                f"Cleaned {len(expired_keys)} expired throttle entries",
            )

    def emit(self, record):
        """
        Emit log record with -proof throttling.

        Flow:
        1. Generate error signature (grouped or global based on config)
        2. Check throttle limits (cache or memory mode)
        3. Block if EITHER per-error OR total limit exceeded
        4. Send email if both limits allow

        Always fails open on errors to avoid losing critical alerts.

        Args:
            record: LogRecord from Python logging
        """
        try:
            # Identify error type
            error_key = self._get_error_signature(record)

            # Check throttle limits
            if self._cache_available:
                error_allowed, total_allowed = self._check_cache_throttle(
                    error_key,
                )
            else:
                error_allowed, total_allowed = self._check_memory_throttle(
                    error_key,
                )

            # Block if either limit exceeded
            if not error_allowed or not total_allowed:
                # Silently suppress ( mitigation goal achieved)
                return

            # Send email
            super().emit(record)

        except Exception as e:
            # Emergency fallback - never lose critical errors
            logger.exception(
                f"Throttling logic failed: {e}. Sending email "
                "without throttle.",
            )
            super().emit(record)
