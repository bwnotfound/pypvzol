import requests
import os
from hashlib import sha256
import shutil
from time import perf_counter
import logging
import asyncio
import aiohttp
import threading
from queue import Queue

from .config import Config


# last_time = perf_counter()
class LogTimeDecorator(object):
    def __init__(self, func, log_level=logging.INFO, is_async=False):
        self.func = func
        self.log_level = log_level
        self.is_async = is_async

    def __get__(self, instance, owner):
        if self.is_async:

            async def wrapper(*args, **kwargs):
                start_time = perf_counter()
                result = await self.func(instance, *args, **kwargs)
                end_time = perf_counter()
                logging.log(
                    self.log_level,
                    f"Url: {args[0]}\n\tTime cost: {end_time - start_time:.3f}s",
                )

                # global last_time
                # logging.log(self.log_level, f"Time Gap: {end_time - last_time:.3f}s")
                # last_time = end_time

                return result

        else:

            def wrapper(*args, **kwargs):
                start_time = perf_counter()
                result = self.func(instance, *args, **kwargs)
                end_time = perf_counter()
                logging.log(
                    self.log_level,
                    f"Url: {args[0]}\n\tTime cost: {end_time - start_time:.3f}s",
                )

                # global last_time
                # logging.log(self.log_level, f"Time Gap: {end_time - last_time:.3f}s")
                # last_time = end_time

                return result

        return wrapper


def logTimeDecorator(log_level=logging.INFO, is_async=False):
    def decorator(func):
        return LogTimeDecorator(func, log_level, is_async)

    return decorator


class WebRequest:
    def __init__(self, cfg: Config, cache_dir=None):
        self.cfg = cfg
        self.user_agent = "Mozilla/4.0 (compatible; MSIE 7.0; Windows NT 6.2; WOW64; Trident/7.0; .NET4.0C; .NET4.0E; .NET CLR 2.0.50727; .NET CLR 3.0.30729; .NET CLR 3.5.30729; Zoom 3.6.0)"
        self.cache_dir = cache_dir

    def init_header(self, header):
        header["user-agent"] = self.user_agent
        header["cookie"] = self.cfg.cookie
        header["host"] = f"s{self.cfg.region}.youkia.pvz.youkia.com"

    def hash(self, s):
        assert isinstance(s, str)
        return sha256(s.encode("utf-8")).hexdigest()

    @logTimeDecorator()
    def get(self, url, need_region=True, use_cache=False, init_header=True, **kwargs):
        def check_status(status_code):
            if status_code != 200:
                raise RuntimeError(f"Request Get Error: {status_code} Url: {url}")

        if need_region:
            url = url.format(self.cfg.region)
        if init_header:
            if kwargs.get("headers") is None:
                kwargs["headers"] = {}
            self.init_header(kwargs["headers"])

        if not use_cache:
            resp = requests.get(url, **kwargs)
            check_status(resp.status_code)
            return resp.content

        assert self.cache_dir is not None
        url_hash = self.hash(url)
        if os.path.exists(os.path.join(self.cache_dir, url_hash)):
            with open(os.path.join(self.cache_dir, url_hash), "rb") as f:
                content = f.read()
        else:
            resp = requests.get(url, **kwargs)
            check_status(resp.status_code)
            content = resp.content
            with open(os.path.join(self.cache_dir, url_hash), "wb") as f:
                f.write(content)
        return content

    @logTimeDecorator(is_async=True)
    async def get_async(
        self, url, need_region=True, use_cache=False, init_header=True, **kwargs
    ):
        def check_status(status_code):
            if status_code != 200:
                raise RuntimeError(f"Async Request Get Error: {status_code} Url: {url}")

        if need_region:
            url = url.format(self.cfg.region)
        if init_header:
            if kwargs.get("headers") is None:
                kwargs["headers"] = {}
            self.init_header(kwargs["headers"])

        if not use_cache:
            async with aiohttp.ClientSession() as session:
                async with session.get(url, **kwargs) as response:
                    check_status(response.status)
                    return await response.read()

        assert self.cache_dir is not None
        url_hash = self.hash(url)
        if os.path.exists(os.path.join(self.cache_dir, url_hash)):
            with open(os.path.join(self.cache_dir, url_hash), "rb") as f:
                content = f.read()
        else:
            async with aiohttp.ClientSession() as session:
                async with session.get(url, **kwargs) as response:
                    check_status(response.status)
                    content = await response.read()
                    with open(os.path.join(self.cache_dir, url_hash), "wb") as f:
                        f.write(content)
        return content

    def get_async_gather(self, arg_list):
        single_flag = False
        if not isinstance(arg_list[0], list):
            single_flag = True
            arg_list = [arg_list]

        async def run():
            task_list = [asyncio.create_task(self.get_async(*arg)) for arg in arg_list]
            done, _ = await asyncio.wait(task_list, return_when=asyncio.ALL_COMPLETED)
            results, exceptions = [None] * len(task_list), [None] * len(task_list)
            for task in done:
                index = task_list.index(task)
                try:
                    result = task.result()
                    results[index] = result
                except Exception as e:
                    exceptions[index] = e
            return results, exceptions

        class RunThread(threading.Thread):
            def __init__(self, channel: Queue):
                super().__init__()
                self.channel = channel

            def run(self):
                self.channel.put(asyncio.run(run()))

        channel = Queue()
        RunThread(channel).start()
        item = channel.get()
        results, exceptions = item
        if single_flag:
            results, exceptions = results[0], exceptions[0]
        return results, exceptions

    @logTimeDecorator()
    def post(self, url, need_region=True, use_cache=False, init_header=True, **kwargs):
        def check_status(status_code):
            if status_code != 200:
                raise RuntimeError(f"Request Post Error: {status_code} Url: {url}")

        if need_region:
            url = url.format(self.cfg.region)
        if init_header:
            if kwargs.get("headers") is None:
                kwargs["headers"] = {}
            self.init_header(kwargs["headers"])

        if not use_cache:
            resp = requests.post(url, **kwargs)
            check_status(resp.status_code)
            return resp.content

        assert self.cache_dir is not None
        url_hash = self.hash(url)
        if os.path.exists(os.path.join(self.cache_dir, url_hash)):
            with open(os.path.join(self.cache_dir, url_hash), "rb") as f:
                content = f.read()
        else:
            resp = requests.post(url, **kwargs)
            check_status(resp.status_code)
            content = resp.content
            with open(os.path.join(self.cache_dir, url_hash), "wb") as f:
                f.write(content)

        return content

    def clear_cache(self):
        assert self.cache_dir is not None
        if os.path.exists(self.cache_dir):
            shutil.rmtree(self.cache_dir)
            os.mkdir(self.cache_dir)
