from __future__ import absolute_import
from __future__ import division
from __future__ import print_function
from __future__ import unicode_literals

import unittest

from mock import patch, Mock

from thread_queue import _do_work, _worker_loop, Queue, empty_queue


class TestWorkerLoops(unittest.TestCase):
    @patch('thread_queue._worker_loop')
    def test_initialize_thread(self, worker_loop):
        initialize_thread = Mock(return_value='blah')
        _do_work(Mock(), initialize_thread, Mock(), [], {}, None, Mock(), Mock())
        self.assertEqual(worker_loop.call_args[1]['extra'], 'blah')
        self.assertTrue(worker_loop.call_args[1]['has_extra'])

    @patch('thread_queue._worker_loop')
    def test_cleanup_thread__when_initialize_thread(self, worker_loop):
        initialize_thread = Mock(return_value='blah')
        cleanup_thread = Mock()
        _do_work(Mock(), initialize_thread, Mock(), [], {}, cleanup_thread, Mock(), Mock())
        self.assertTrue(cleanup_thread.called)
        self.assertEqual(cleanup_thread.call_args[0][0], 'blah')

    @patch('thread_queue._worker_loop')
    def test_cleanup_thread__when_no_initialize_thread(self, worker_loop):
        cleanup_thread = Mock()
        _do_work(Mock(), None, Mock(), [], {}, cleanup_thread, Mock(), Mock())
        self.assertTrue(cleanup_thread.called)
        self.assertTupleEqual(cleanup_thread.call_args[0], tuple())
        self.assertDictEqual(cleanup_thread.call_args[1], {})

    @patch('thread_queue._worker_loop')
    def test_initialize_thread__exception_in_initialize_thread(self, worker_loop):
        initialize_thread = Mock(side_effect=Exception('e'))
        exc_queue = Queue()
        self.assertRaises(Exception, _do_work, Mock(), initialize_thread, Mock(), [], {}, None, exc_queue, Mock())
        excs = empty_queue(exc_queue)
        self.assertEqual(excs[0], initialize_thread.side_effect)

    def test_worker_loop__when_has_extra(self):
        queue = Queue()
        queue.put([[1], {}])
        queue.put(None)
        worker = Mock(return_value='blah2')
        resp_queue = Queue()
        _worker_loop(queue, worker, resp_queue, extra='blah', has_extra=True)
        self.assertTupleEqual(worker.call_args[0], ('blah', 1))
        responses = empty_queue(resp_queue)
        self.assertListEqual(['blah2'], responses)

    def test_worker_loop__when_not_has_extra(self):
        queue = Queue()
        queue.put([[1], {}])
        queue.put(None)
        worker = Mock(return_value='blah2')
        resp_queue = Queue()
        _worker_loop(queue, worker, resp_queue, has_extra=False)
        self.assertTupleEqual(worker.call_args[0], (1,))
        responses = empty_queue(resp_queue)
        self.assertListEqual(['blah2'], responses)

