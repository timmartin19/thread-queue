from __future__ import absolute_import
from __future__ import division
from __future__ import print_function
from __future__ import unicode_literals

import logging
from threading import Thread
try:
    from queue import Queue, Empty
except ImportError:
    from Queue import Queue, Empty

__author__ = 'Tim Martin'
__email__ = 'tim@timmartin.me'
__version__ = '0.2.3'

LOG = logging.getLogger(__name__)

t = Thread()


class QueueNotEmptyException(Exception):
    """
    Raised when items from the queue have not
    been processed, likely due to an error in
    the underlying threads
    """
    def __init__(self, message, items, exceptions):
        self._unattempted_tasks = items
        self.thread_exceptions = exceptions
        super(QueueNotEmptyException, self).__init__(message)

    @property
    def all_unprocessed_tasks(self):
        tasks = list(self.unattempted_tasks)
        thread_task_excs = [exc.task for exc in self.thread_exceptions
                            if isinstance(exc, ThreadTaskException) and exc.task is not None]
        return tasks + thread_task_excs

    @property
    def unattempted_tasks(self):
        return [task for task in self._unattempted_tasks if task is not None]


class ThreadTaskException(Exception):
    """
    Wrapper for exceptions that occur within the
    underlying threads
    """
    def __init__(self, message, exc, task=None):
        self.__cause__ = exc
        self.task = task
        super(ThreadTaskException, self).__init__(message)


class ThreadQueue(object):
    """
    An object for safely processing a queue
    using a fixed number of threads

    Example:

    ..code-block:: python

        from thread_queue import ThreadQueue

        def worker(arg, keyword=5):
            print('arg = {0}, keyword = {1}'.format(arg, keyword))

        with ThreadQueue(worker) as tq:
            for i in range(10):
                tq.load(i, i*10)

        # Would print in no particular order (because it's threaded)
        # arg = 0, keyword = 0
        # arg = 1, keyword = 10
        # arg = 2, keyword = 20
        # ...
        # arg = 9, keyword = 90
    """
    def __init__(self, worker,
                 thread_count=10,
                 initialize_thread=None,
                 initialization_args=None,
                 initialization_kwargs=None,
                 cleanup_thread=None,
                 queue=None,
                 response_queue=None):
        """
        :param function worker: The function to call from the
            generated threads.  This will take the same arguments
            as are added to the ``ThreadQueue.load`` method.  If you
            call ``ThreadQueue(my_job).load(1, keyword=2)`` this
            function would be effectively equivalent to calling
            ``my_job(1, keyword=2)``.  The one caveat is if
            ``initialize_thread`` is set.  In that case the return
            value will be prepended to the arguments.
            ``ThreadQueue(my_job, initialize_thread=lambda: 'initial').load(1, keyword=2)``
            is equivalent to ``my_job('initial', 1, keyword=2)
        :param int thread_count: The number of threads to instantiate
        :param function initialize_thread: A function to call immediately
            after a thread has been initialized.  The return value will
            be prepended to the args sent to worker
        :param tuple initialization_args: Arguments to pass to the ``initialize_thread``
            function
        :param dict initialization_kwargs: Keyword arguments to pass to
            ``initialize_thread``
        :param function cleanup_thread: Called when the thread is about
            to finish.  It will always be called even in the event of an exception.
            If ``initialize_thread`` is set, then the return value of that function
            will be passed to ``cleanup_thread``
        :param Queue queue: Defaults to ``queue.Queue()``. An
            object that implements a ``Queue`` like interface.
            It must include at least ``get``, ``put``, and ``join``
            methods.
        """
        self.thread_count = thread_count
        self._queue = queue or Queue()
        self.response_queue = queue or Queue()
        self._exc_queue = None
        self.initialize_thread = initialize_thread
        self.worker = worker
        self.initialization_args = initialization_args or []
        self.initialization_kwargs = initialization_kwargs or {}
        self.cleanup_thread = cleanup_thread
        self._threads = []

    def __enter__(self):
        self.start()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()

    def start(self):
        """
        Initializes the threads that the queue will be using
        """
        LOG.debug('Starting ThreadQueue threads')
        self._exc_queue = Queue()
        for i in range(self.thread_count):
            worker_args = [self._queue, self.initialize_thread,
                           self.worker, self.initialization_args,
                           self.initialization_kwargs, self.cleanup_thread,
                           self._exc_queue, self.response_queue]
            thread = Thread(target=_do_work, args=worker_args)
            thread.start()
            self._threads.append(thread)

    def load(self, *args, **kwargs):
        """
        Loads a set of arguments to pass to the threads
        via the queue.  The arguments will be passed to
        the ``worker`` function exactly as specified here unless
        ``initiliaze_thread`` is set.  In which case, the return
        value from initialize_thread will be prepended to the arguments

        :param tuple args:
        :param dict kwargs:
        """
        self._queue.put(tuple([args, kwargs]))

    def close(self):
        """
        Waits for the queue to empty and then
        joins the threads
        """
        for i in range(self.thread_count):
            self._queue.put(None)
        for thread in self._threads:
            thread.join()

        unfinished_tasks = empty_queue(self._queue)
        thread_errors = empty_queue(self._exc_queue)
        if unfinished_tasks or thread_errors:
            raise QueueNotEmptyException('The ThreadQueue did not finish all tasks',
                                         unfinished_tasks, thread_errors)

        LOG.debug('Closed all ThreadQueue threads')


def empty_queue(queue):
    """

    :param Queue queue:
    :return:
    :rtype: list
    """
    all_items = []
    while True:
        try:
            all_items.append(queue.get_nowait())
        except Empty:
            return all_items


def _do_work(q, initialize_thread, worker, args, kwargs, cleanup_thread, exc_queue, response_queue):
    try:
        extra = None
        if initialize_thread:
            LOG.debug('Initializing thread')
            extra = initialize_thread(*args, **kwargs)
        else:
            LOG.debug('Skipping thread initialization')
        try:
            _worker_loop(q, worker, response_queue,
                         extra=extra, has_extra=initialize_thread is not None)
        finally:
            if cleanup_thread is not None:
                LOG.debug('Cleaning up thread')
                if initialize_thread:
                    cleanup_thread(extra)
                else:
                    cleanup_thread()
    except Exception as exc:
        LOG.warning('Exception in ThreadQueue thread', exc_info=True)
        exc_queue.put(exc)
        raise


def _worker_loop(queue, worker, response_queue, extra=None, has_extra=False):
    while True:
        item = queue.get()
        try:
            if item is None:
                LOG.debug('Found break request from parent.  Finishing work')
                break
            LOG.debug('Beginning task')
            if has_extra:
                resp = worker(extra, *item[0], **item[1])
            else:
                resp = worker(*item[0], **item[1])
            response_queue.put(resp)
            LOG.debug('Finished task')
            queue.task_done()
        except Exception as exc:
            raise ThreadTaskException('An exception occurred while processing a task',
                                      exc, task=item)
