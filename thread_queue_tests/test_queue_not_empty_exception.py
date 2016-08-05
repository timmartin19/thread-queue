from __future__ import absolute_import
from __future__ import division
from __future__ import print_function
from __future__ import unicode_literals

import unittest

from thread_queue import QueueNotEmptyException, ThreadTaskException


class TestQueueNotEmptyException(unittest.TestCase):
    def test_all_unprocessed_tasks(self):
        exc_task = ThreadTaskException('blah', Exception(), task='task_blah')
        exc = Exception('something')
        exc_task_ignored = ThreadTaskException('blah2', Exception())
        queue_exc = QueueNotEmptyException('blah', ['something'], [exc, exc_task, exc_task_ignored])
        self.assertListEqual(['something', 'task_blah'], queue_exc.all_unprocessed_tasks)

    def test_unattempted_tasks(self):
        exc_task = ThreadTaskException('blah', Exception(), task='task_blah')
        exc = Exception('something')
        exc_task_ignored = ThreadTaskException('blah2', Exception())
        queue_exc = QueueNotEmptyException('blah', ['something'], [exc, exc_task, exc_task_ignored])
        self.assertListEqual(['something'], queue_exc.unattempted_tasks)

    def test_thread_exceptions(self):
        exc_task = ThreadTaskException('blah', Exception(), task='task_blah')
        exc = Exception('something')
        exc_task_ignored = ThreadTaskException('blah2', Exception())
        queue_exc = QueueNotEmptyException('blah', ['something'], [exc, exc_task, exc_task_ignored])
        self.assertListEqual([exc, exc_task, exc_task_ignored], queue_exc.thread_exceptions)
