import requests
import os
from time import sleep
from random import sample
from hashlib import sha256
import shutil
from time import perf_counter
import logging
from time import sleep
import threading
from queue import Queue
from pyamf import DecodeError, remoting, AMF0, AMF3

from .config import Config

proxies = {"http": None, "https": None}
proxies = None
freq_event = threading.Event()
freq_event.set()
_freq_lock = threading.Lock()


def sleep_freq(t):
    try:
        _freq_lock.acquire()
        freq_event.clear()
        sleep(t)
    finally:
        _freq_lock.release()
        freq_event.set()


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
        self.user_agent = ""
        self.cache_dir = cache_dir
        self.session = requests.Session()

    def init_header(self, header):
        user_agent = [
            "Mozilla/5.0 (Windows NT 10.0;............/92.0.4515.131 Safari/537.36 SLBrowser/8.0.1.5162 SLBChan/11",
            "Mozilla/5.0 (Windows N............e Gecko) Chrome/103.0.5060.114 Safari/537.36",
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64............WIFI MicroMessenger/7.0.20.1781(0x6700143B) WindowsWechat(0x63090618) XWEB/8259 Flue",
        ]
        header["user-agent"] = sample(user_agent, 1)[0]
        header["cookie"] = self.cfg.cookie
        header["host"] = self.cfg.host
        # header["Connection"] = "close"

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
                    resp = self.session.get(url, **kwargs, proxies=proxies)
                check_status(resp.status_code)
                return resp.content

            assert self.cache_dir is not None
            url_hash = self.hash(url)
            if os.path.exists(os.path.join(self.cache_dir, url_hash)):
                with open(os.path.join(self.cache_dir, url_hash), "rb") as f:
                    content = f.read()
            else:
                with LogTimeDecorator(url):
                    resp = self.session.get(url, **kwargs, proxies=proxies)
                check_status(resp.status_code)
                content = resp.content
                with open(os.path.join(self.cache_dir, url_hash), "wb") as f:
                    f.write(content)
            return content
        finally:
            self.cfg.release()

    def get_async(self, *args, **kwargs):
        def run():
            return self.get_retry(*args, **kwargs)

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

    def post(
        self,
        url,
        use_cache=False,
        init_header=True,
        url_format=True,
        exit_response=False,
        **kwargs,
    ):
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
                if not exit_response:
                    with LogTimeDecorator(url):
                        resp = self.session.post(url, **kwargs, proxies=proxies)
                    check_status(resp.status_code)
                    return resp.content
                with LogTimeDecorator(url):
                    resp = self.session.post(
                        url,
                        stream=True,
                        **kwargs,
                        proxies=proxies,
                    )
                check_status(resp.status_code)
                for _ in resp.iter_content(chunk_size=16):
                    break
                return

            assert self.cache_dir is not None
            url_hash = self.hash(url)
            if os.path.exists(os.path.join(self.cache_dir, url_hash)):
                with open(os.path.join(self.cache_dir, url_hash), "rb") as f:
                    content = f.read()
            else:
                with LogTimeDecorator(url):
                    resp = self.session.post(url, **kwargs, proxies=proxies)
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

    def get_retry(
        self,
        url,
        use_cache=False,
        init_header=True,
        url_format=True,
        max_retry=15,
        **kwargs,
    ):
        cnt = 0
        while cnt < max_retry:
            cnt += 1
            try:
                response = self.get(
                    url,
                    use_cache=use_cache,
                    init_header=init_header,
                    url_format=url_format,
                    **kwargs,
                )
                break
            except Exception as e:
                logging.info(
                    "重新尝试请求{}，选择等待1秒后重试。最多再等待{}次。异常类型: {}".format(
                        url, max_retry - cnt, type(e).__name__
                    )
                )
                sleep(1)
        else:
            msg = "尝试请求{}失败，超过最大尝试次数{}次".format(url, max_retry)
            logging.info(msg)
            raise RuntimeError(msg)
        return response

    def _amf_post_decode(
        self, url, data, msg, max_retry=3, exit_on_fail=False, exit_response=False
    ):
        cnt = 0
        while cnt < max_retry:
            try:
                resp = self.post(
                    url,
                    data=data,
                    exit_response=exit_response,
                    headers={"Content-Type": "application/x-amf"},
                )
                if exit_response:
                    return
            except requests.exceptions.ConnectTimeout as e:
                if exit_on_fail:
                    raise e
                logging.warning("请求{}超时，选择等待0.5秒后重试".format(msg))
                sleep(0.5)
                cnt += 1
                continue
            try:
                if len(resp) == 0:
                    raise RuntimeError("amf返回结果为空")
                resp_ev = remoting.decode(resp)
                break
            except DecodeError as e:
                if exit_on_fail:
                    raise e
                cnt += 1
                logging.info("重新尝试请求{}，选择等待0.5秒后重试".format(msg))
                sleep(0.5)
            except OSError as e:
                if exit_on_fail:
                    raise e
                cnt += 1
                logging.info("重新尝试请求{}，选择等待0.5秒后重试".format(msg))
                sleep(0.5)
        else:
            raise RuntimeError("请求{}失败，超过最大尝试次数{}次".format(msg, max_retry))
        return resp_ev["/1"]

    def amf_post(
        self,
        body,
        target,
        url,
        msg,
        max_retry=3,
        exit_on_fail=False,
        exit_response=False,
    ):
        req = remoting.Request(target=target, body=body)
        ev = remoting.Envelope(AMF3)
        ev['/1'] = req
        bin_msg = remoting.encode(ev, strict=True)
        try:
            result = self._amf_post_decode(
                url,
                bin_msg.getvalue(),
                msg,
                max_retry,
                exit_on_fail=exit_on_fail,
                exit_response=exit_response,
            )
            if exit_response:
                return
        except Exception as e:
            raise e
        return result

    def amf_post_retry(
        self,
        body,
        target,
        url,
        msg,
        max_retry=15,
        logger=None,
        exit_on_fail=False,
        exit_response=False,
        on_result=False,
    ):
        cnt = 0
        flag = False
        while cnt < max_retry:
            cnt += 1
            try:
                freq_event.wait()
                response = self.amf_post(
                    body,
                    target,
                    url,
                    msg,
                    exit_on_fail=exit_on_fail,
                    exit_response=exit_response,
                )
                if exit_response:
                    return
                if response.status != 0:
                    if "频繁" in response.body.description:
                        if logger is not None:
                            logger.log(
                                "{}过于频繁，选择等待3秒后重试。最多再等待{}次".format(msg, max_retry - cnt)
                            )
                        sleep_freq(3)
                        continue
                    if "更新" in response.body.description:
                        if logger is not None:
                            logger.log(
                                "{}的时候服务器频繁，选择等待5秒后重试。最多再等待{}次".format(
                                    msg, max_retry - cnt
                                )
                            )
                        sleep_freq(5)
                        continue
                    if on_result:
                        if logger is not None:
                            logger.log(
                                "{}失败，失败原因：{}".format(msg, response.body.description)
                            )
                        flag = True
                        raise RuntimeError(f"{msg}失败")
                break
            except RuntimeError as e:
                raise e
            except Exception as e:
                if (flag and exit_on_fail) or isinstance(e, RuntimeError):
                    raise e
                if logger is not None:
                    logger.log(
                        "{}时出现异常，异常类型：{}。选择暂停1秒后重新获取信息，最多再尝试{}次".format(
                            msg, type(e).__name__, max_retry - cnt
                        )
                    )
                sleep(1)
        else:
            msg = "{}失败，超过最大尝试次数{}次".format(msg, max_retry)
            if logger is not None:
                logger.log(msg)
            raise RuntimeError(msg)
        return response
