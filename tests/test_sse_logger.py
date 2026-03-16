"""
Tests for the SSE log handler additions to src/utils/logger.py.

Covers: SSELogHandler, get_sse_queue, enable_sse_logging, and
interaction with the existing SensitiveDataFilter.
"""

import logging
import queue
import sys
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

import utils.logger as logger_mod
from utils.logger import (
    SSELogHandler,
    SensitiveDataFilter,
    enable_sse_logging,
    get_sse_queue,
)


class TestSSELogHandler(unittest.TestCase):

    def setUp(self):
        self.q = queue.Queue(maxsize=10)
        self.handler = SSELogHandler(self.q)
        self.handler.setFormatter(logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s"))

    def test_emit_puts_entry_on_queue(self):
        record = logging.LogRecord(
            name="test",
            level=logging.INFO,
            pathname="",
            lineno=0,
            msg="hello world",
            args=(),
            exc_info=None,
        )
        self.handler.emit(record)
        self.assertFalse(self.q.empty())
        entry = self.q.get_nowait()
        self.assertEqual(entry["level"], "INFO")
        self.assertEqual(entry["message"], "hello world")

    def test_emit_captures_module(self):
        record = logging.LogRecord(
            name="mymod",
            level=logging.WARNING,
            pathname="mymod.py",
            lineno=42,
            msg="oops",
            args=(),
            exc_info=None,
        )
        self.handler.emit(record)
        entry = self.q.get_nowait()
        self.assertEqual(entry["level"], "WARNING")

    def test_emit_silently_drops_on_full_queue(self):
        small_q = queue.Queue(maxsize=1)
        handler = SSELogHandler(small_q)
        handler.setFormatter(logging.Formatter("%(message)s"))

        rec1 = logging.LogRecord("t", logging.INFO, "", 0, "first", (), None)
        rec2 = logging.LogRecord("t", logging.INFO, "", 0, "second", (), None)
        handler.emit(rec1)
        handler.emit(rec2)  # should not raise

        self.assertEqual(small_q.qsize(), 1)
        self.assertEqual(small_q.get_nowait()["message"], "first")

    def test_handler_level_defaults_to_debug(self):
        self.assertEqual(self.handler.level, logging.DEBUG)


class TestGetSSEQueue(unittest.TestCase):

    def setUp(self):
        logger_mod._sse_log_queue = None

    def test_creates_queue_on_first_call(self):
        q = get_sse_queue()
        self.assertIsInstance(q, queue.Queue)
        self.assertEqual(q.maxsize, 500)

    def test_returns_same_queue_on_subsequent_calls(self):
        q1 = get_sse_queue()
        q2 = get_sse_queue()
        self.assertIs(q1, q2)


class TestEnableSSELogging(unittest.TestCase):

    def setUp(self):
        logger_mod._sse_log_queue = None
        self.root = logging.getLogger()
        self._original_handlers = self.root.handlers[:]

    def tearDown(self):
        self.root.handlers = self._original_handlers
        logger_mod._sse_log_queue = None

    def test_returns_queue(self):
        q = enable_sse_logging()
        self.assertIsInstance(q, queue.Queue)

    def test_attaches_handler_to_root_logger(self):
        enable_sse_logging()
        sse_handlers = [h for h in self.root.handlers if isinstance(h, SSELogHandler)]
        self.assertGreaterEqual(len(sse_handlers), 1)

    def test_handler_has_sensitive_filter(self):
        enable_sse_logging()
        sse_handler = [h for h in self.root.handlers if isinstance(h, SSELogHandler)][0]
        filter_types = [type(f) for f in sse_handler.filters]
        self.assertIn(SensitiveDataFilter, filter_types)

    def test_logs_flow_into_queue(self):
        q = enable_sse_logging()
        test_logger = logging.getLogger("sse_test")
        test_logger.setLevel(logging.DEBUG)
        test_logger.info("integration check")

        found = False
        while not q.empty():
            entry = q.get_nowait()
            if entry["message"] == "integration check":
                found = True
                break
        self.assertTrue(found, "Log message did not reach the SSE queue")


if __name__ == "__main__":
    unittest.main()
