from __future__ import absolute_import
from __future__ import division
from __future__ import print_function
from __future__ import unicode_literals

import math
import time
import random
import unittest
import statistics
from statistics import median

import requests

from thread_queue import ThreadQueue


def _get_page(page):
    resp = requests.get(page)

def _get_page_session(session, page):
    resp = session.get(page)


class Comparator(object):
    def __init__(self):
        self._to_compare = []

    def add_func(self, func, args=(), kwargs=None):
        kwargs = kwargs or {}
        self._to_compare.append(dict(func=func, args=args, kwargs=kwargs))

    def compare(self, num=1000):
        times = {compare['func'].__name__: [] for compare in self._to_compare}
        choices = list(range(len(self._to_compare)))
        for i in range(num):
            choice = self._to_compare[random.choice(choices)]
            start = time.perf_counter()
            choice['func'](*choice['args'], **choice['kwargs'])
            end = time.perf_counter()
            total_time = end - start
            print(total_time)
            func_name = choice['func'].__name__
            times[func_name].append(total_time)
        return times


class ComparatorResult(object):
    def __init__(self, times):
        self.times = times

    @property
    def average(self):
        return statistics.mean(self.times)

    @property
    def max(self):
        return max(self.times)

    @property
    def min(self):
        return min(self.times)

    @property
    def count(self):
        return len(self.times)

    @property
    def median(self):
        return median(self.times)

    @property
    def std_dev(self):
        return statistics.stdev(self.times)


class TestPerformance(unittest.TestCase):
    def test_requests(self):
        count = 5
        page = 'http://www.reddit.com/'
        c = Comparator()
        c.add_func(get_page_synchronously, args=(count, page))
        c.add_func(get_page_parallel, args=(count, page))
        resp = c.compare(10)
        print(resp)
        parallel = ComparatorResult(resp[get_page_parallel.__name__])
        synchronous = ComparatorResult(resp[get_page_synchronously.__name__])
        self.assertLess(parallel.average, synchronous.average)
        print('Without session')
        print('Synchronous: {0}'.format(synchronous.average))
        print('Parallel: {0}'.format(parallel.average))

    def test_requests_with_session(self):
        count = 5
        page = 'http://reddit.com/'
        c = Comparator()
        c.add_func(get_page_synchronously_with_session, args=(count, page))
        c.add_func(get_page_parallel_with_session, args=(count, page))
        resp = c.compare(10)
        print(resp)
        parallel = ComparatorResult(resp[get_page_parallel_with_session.__name__])
        synchronous = ComparatorResult(resp[get_page_synchronously_with_session.__name__])
        self.assertLess(parallel.average, synchronous.average)
        print('With session')
        print('Synchronous: {0}'.format(synchronous.average))
        print('Parallel: {0}'.format(parallel.average))


def get_page_synchronously(count, page):
    for i in range(count):
        _get_page(page)


def get_page_parallel(count, page):
    with ThreadQueue(_get_page, thread_count=2) as tq:
        for i in range(count):
            tq.load(page)


def get_page_synchronously_with_session(count, page):
    s = requests.Session()
    for i in range(count):
        s.get(page)


def get_page_parallel_with_session(count, page):
    with ThreadQueue(_get_page_session, thread_count=count, initialize_thread=lambda: requests.Session()) as tq:
        tq.load(page)
