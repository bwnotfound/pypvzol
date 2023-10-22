import requests
import os
from threading import Lock
from hashlib import sha256
import shutil
from time import perf_counter
import logging
from time import sleep
import threading
from queue import Queue
from pyamf import DecodeError, remoting, AMF0, AMF3

from .config import Config

    
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


def logTimeDecorator(log_level=logging.INFO):
    def decorator(func):
        return LogTimeDecorator(func, log_level)

    return decorator


def async_gather(future_list):
    pass


class WebRequest:
    def __init__(self, cfg: Config, cache_dir=None):
        self.cfg = cfg
        self.user_agent = "Mozilla/4.0 (compatible; MSIE 7.0; Windows NT 6.2; WOW64; Trident/7.0; .NET4.0C; .NET4.0E; .NET CLR 2.0.50727; .NET CLR 3.0.30729; .NET CLR 3.5.30729; Zoom 3.6.0)"
        self.cache_dir = cache_dir

    def init_header(self, header):
        header["user-agent"] = self.user_agent
        header["cookie"] = self.cfg.cookie
        header["host"] = self.cfg.host
        header["Connection"] = "close"

    def hash(self, s):
        assert isinstance(s, str)
        return sha256(s.encode("utf-8")).hexdigest()

    def get_private_cache(self, url):
        if "pvzol" not in url:
            return None
        url = url.replace("http://pvzol.org/", "")
        src_path = os.path.join("./data/cache", url)
        if os.path.exists(src_path) and not os.path.isdir(src_path):
            with open(src_path, "rb") as f:
                return f.read()

    def get(self, url, use_cache=False, init_header=True, url_format=True, **kwargs):
        try:
            self.cfg.acquire()
            if url_format:
                url = "http://" + self.cfg.host + url
            private_cached = self.get_private_cache(url)
            if private_cached is not None:
                return private_cached

            def check_status(status_code):
                if status_code != 200:
                    raise RuntimeError(f"Request Get Error: {status_code} Url: {url}")

            if init_header:
                if kwargs.get("headers") is None:
                    kwargs["headers"] = {}
                self.init_header(kwargs["headers"])
            if "timeout" not in kwargs:
                kwargs["timeout"] = self.cfg.timeout

            if not use_cache:
                with LogTimeDecorator(url):
                    resp = requests.get(url, **kwargs)
                check_status(resp.status_code)
                return resp.content

            assert self.cache_dir is not None
            url_hash = self.hash(url)
            if os.path.exists(os.path.join(self.cache_dir, url_hash)):
                with open(os.path.join(self.cache_dir, url_hash), "rb") as f:
                    content = f.read()
            else:
                with LogTimeDecorator(url):
                    resp = requests.get(url, **kwargs)
                check_status(resp.status_code)
                content = resp.content
                with open(os.path.join(self.cache_dir, url_hash), "wb") as f:
                    f.write(content)
            return content
        finally:
            self.cfg.release()

    def get_async(self, *args, **kwargs):
        def run():
            return self.get(*args, **kwargs)

        return run

    def get_async_gather(self, *args):
        if len(args) == 0:
            raise ValueError("args must not be empty")
        elif len(args) == 1 and isinstance(args[0], tuple) or isinstance(args[0], list):
            func_list = args[0]
        else:
            func_list = args

        class RunThread(threading.Thread):
            def __init__(self, func, q, result):
                super().__init__()
                self.func = func
                self.q = q
                self.result = result

            def run(self):
                self.result.append(self.func())
                self.q.put(1)

        result_list = [[] for _ in range(len(func_list))]
        q = Queue()
        for i, func in enumerate(func_list):
            RunThread(func, q, result_list[i]).start()
        while q.qsize() < len(func_list):
            sleep(0.1)
        return [x[0] for x in result_list]

    def post(self, url, use_cache=False, init_header=True, url_format=True, **kwargs):
        try:
            self.cfg.acquire()
            if url_format:
                url = "http://" + self.cfg.host + url
            private_cached = self.get_private_cache(url)
            if private_cached is not None:
                return private_cached
            
            if "timeout" not in kwargs:
                kwargs["timeout"] = self.cfg.timeout

            def check_status(status_code):
                if status_code != 200:
                    raise RuntimeError(f"Request Post Error: {status_code} Url: {url}")

            if init_header:
                if kwargs.get("headers") is None:
                    kwargs["headers"] = {}
                self.init_header(kwargs["headers"])

            if not use_cache:
                with LogTimeDecorator(url):
                    resp = requests.post(url, **kwargs)
                check_status(resp.status_code)
                return resp.content

            assert self.cache_dir is not None
            url_hash = self.hash(url)
            if os.path.exists(os.path.join(self.cache_dir, url_hash)):
                with open(os.path.join(self.cache_dir, url_hash), "rb") as f:
                    content = f.read()
            else:
                with LogTimeDecorator(url):
                    resp = requests.post(url, **kwargs)
                check_status(resp.status_code)
                content = resp.content
                with open(os.path.join(self.cache_dir, url_hash), "wb") as f:
                    f.write(content)

            return content
        finally:
            self.cfg.release()

    def clear_cache(self):
        assert self.cache_dir is not None
        if os.path.exists(self.cache_dir):
            shutil.rmtree(self.cache_dir)
            os.mkdir(self.cache_dir)
            

    def _amf_post_decode(self, url, data, msg, max_retry=3):
        cnt = 0
        while cnt < max_retry:
            try:
                resp = self.post(url, data=data)
            except requests.exceptions.ConnectTimeout:
                logging.warning("请求{}超时，选择等待0.5秒后重试".format(msg))
                sleep(0.5)
                cnt += 1
                continue
            try:
                resp_ev = remoting.decode(resp)
                break
            except DecodeError:
                cnt += 1
                logging.info("重新尝试请求{}，选择等待0.5秒后重试".format(msg))
                sleep(0.5)
            except OSError:
                cnt += 1
                logging.info("重新尝试请求{}，选择等待0.5秒后重试".format(msg))
                sleep(0.5)
        else:
            raise RuntimeError("请求{}失败，超过最大尝试次数{}次".format(msg, max_retry))
        return resp_ev["/1"]

    def amf_post(self, body, target, url, msg, max_retry=3):
        req = remoting.Request(target=target, body=body)
        ev = remoting.Envelope(AMF3)
        ev['/1'] = req
        bin_msg = remoting.encode(ev, strict=True)
        try:
            result = self._amf_post_decode(url, bin_msg.getvalue(), msg, max_retry)
        except Exception as e:
            raise e
        return result
