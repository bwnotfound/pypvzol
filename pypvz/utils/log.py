import logging
from time import perf_counter

class TimeCounter(object):
    def __init__(self, *args):
        self.name = None
        self.wrapper = None
        if len(args) == 0:
            return
        if len(args) == 1:
            if callable(args[0]):
                fn = args[0]

                def warpper(instance):
                    def _wrapper(*args, **kwargs):
                        start = perf_counter()
                        result = fn(instance, *args, **kwargs)
                        end = perf_counter()
                        self._print(end - start)
                        return result

                    return _wrapper

                self.wrapper = warpper
            elif isinstance(args[0], str):
                self.name = args[0]
            else:
                raise NotImplementedError

    def _print(self, interval):
        if self.name is not None:
            print(f'{self.name} cost time: {interval:.3f}s')
        else:
            print(f'Cost time: {interval:.3f}s')

    def __call__(self, fn):
        def warpper(instance):
            def _wrapper(*args, **kwargs):
                start = perf_counter()
                result = fn(instance, *args, **kwargs)
                end = perf_counter()
                self._print(end - start)
                return result

            return _wrapper

        self.wrapper = warpper
        return self

    def __get__(self, instance, owner):
        return self.wrapper(instance)

    def __enter__(self):
        self.start = perf_counter()

    def __exit__(self, *args):
        end = perf_counter()
        self._print(end - self.start)


class LogTimeDecorator(object):
    def __init__(self, func, log_level=logging.INFO):
        self.func = func
        self.log_level = log_level
        self.start_time = None
        self.end_time = None

    def _log(self, url):
        logging.log(
            self.log_level,
            f"Url: {url}\n\tTime cost: {self.end_time - self.start_time:.3f}s",
        )

    def __get__(self, instance, owner):
        def wrapper(*args, **kwargs):
            self.start_time = perf_counter()
            result = self.func(instance, *args, **kwargs)
            self.end_time = perf_counter()
            self._log(args[0])
            return result

        return wrapper

    def __enter__(self):
        self.start_time = perf_counter()

    def __exit__(self, *args):
        self.end_time = perf_counter()
        self._log(self.func)