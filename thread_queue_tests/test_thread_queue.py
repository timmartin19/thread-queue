from __future__ import absolute_import
from __future__ import division
from __future__ import print_function
from __future__ import unicode_literals

import unittest

from thread_queue import ThreadQueue, QueueNotEmptyException, ThreadTaskException, \
    empty_queue


def _throw_exception(exc):
    raise exc


def _maybe_throw_exception(throw):
    if throw:
        raise Exception('error')


class TestIntegration(unittest.TestCase):
    def test__when_all_threads_error__closes_all_threads_and_raises_exception(self):
        tq = ThreadQueue(_throw_exception, thread_count=10)
        tq.start()
        for i in range(10):
            tq.load(Exception(i))
        try:
            tq.close()
        except QueueNotEmptyException as exc:
            self.assertEqual(len(exc.thread_exceptions), 10)
            self.assertEqual(0, len(exc.unattempted_tasks))
            self.assertEqual(len(exc.all_unprocessed_tasks), 10)
            for exc in exc.thread_exceptions:
                self.assertIsInstance(exc, ThreadTaskException)

    def test__when_some_threads_error__closes_all_threads_and_raises_exception(self):
        tq = ThreadQueue(_maybe_throw_exception, thread_count=5)
        tq.start()
        for i in range(5):
            tq.load(True)
        for i in range(5):
            tq.load(False)
        try:
            tq.close()
        except QueueNotEmptyException as exc:
            self.assertEqual(len(exc.thread_exceptions), 5)
            self.assertEqual(5, len(exc.unattempted_tasks))
            self.assertEqual(len(exc.all_unprocessed_tasks), 10)

    def test__when_valid__empties_queue_and_returns(self):
        tq = ThreadQueue(lambda: 1, thread_count=10)
        tq.start()
        for i in range(10):
            tq.load()
        tq.close()
        responses = empty_queue(tq.response_queue)
        self.assertEqual(10, len(responses))
        for item in responses:
            self.assertEqual(1, item)
