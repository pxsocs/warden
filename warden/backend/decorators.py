import collections
import functools
import hashlib
import inspect
import os
import time
import logging
from functools import wraps
from glob import glob
from backend.utils import home_path

from backend.utils import pickle_it


class memoized(object):
    # Decorator. Caches a function's return value each time it is called.
    # If called later with the same arguments, the cached value is returned
    # (not reevaluated).
    def __init__(self, func):
        # Initiliaze Memoization for this function
        self.func = func
        self.cache = {}

    def __call__(self, *args):
        if not isinstance(args, collections.Hashable):
            # uncacheable. a list, for instance.
            # better to not cache than blow up.
            return self.func(*args)
        if args in self.cache:
            return self.cache[args]
        else:
            value = self.func(*args)
            self.cache[args] = value
            return value

    def __repr__(self):
        return self.func.__doc__

    def __get__(self, obj, objtype):
        return functools.partial(self.__call__, obj)

    # Clears the cache - called when there are changes that may affect the result
    # of the function
    def clear(self):
        self.cache = {}


class MWT(object):
    # Decorator that caches the result of a function until a given timeout (in seconds)
    # Helpful when running complicated calculations that are used more than once
    # Source: http://code.activestate.com/recipes/325905-memoize-decorator-with-timeout/
    _caches = {}
    _timeouts = {}

    def __init__(self, timeout=2):
        self.timeout = timeout

    def collect(self):
        # Clear cache of results which have timed out
        for func in self._caches:
            cache = {}
            for key in self._caches[func]:
                if (time.time() -
                        self._caches[func][key][1]) < self._timeouts[func]:
                    cache[key] = self._caches[func][key]
            self._caches[func] = cache

    def __call__(self, f):
        self.cache = self._caches[f] = {}
        self._timeouts[f] = self.timeout

        def func(*args, **kwargs):
            kw = sorted(kwargs.items())
            key = (args, tuple(kw))
            try:
                # Using memoized function only if still on time
                v = self.cache[key]
                if (time.time() - v[1]) > self.timeout:
                    raise KeyError
            except (KeyError, TypeError):
                # Need to recalculate
                try:
                    v = self.cache[key] = f(*args, **kwargs), time.time()
                except TypeError:  # Some args passed as list return TypeError, skip
                    return (f(*args, **kwargs))
            return v[0]

        func.func_name = f.__name__

        return func


def timing(method):

    def timed(*args, **kw):
        try:
            print('\033[1;37;40m[TIMING STARTED] \033[92mFunction ',
                  method.__name__)
            print('                 Args: ', *args)
            ts = time.time()
            result = method(*args, **kw)
            te = time.time()
            print('\033[1;37;40m[TIME RESULT] \033[92mFunction ',
                  method.__name__, '\033[95mtime:', round((te - ts) * 1000,
                                                          1), 'ms')

            print("\033[1;37;40m")
            return result
        except Exception:
            pass

    return timed
