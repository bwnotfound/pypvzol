import requests
from requests.adapters import HTTPAdapter
from urllib.parse import urlparse
import concurrent.futures
from threading import Lock
import pickle
import os
from random import sample
from hashlib import sha256
import shutil
from time import perf_counter, sleep
import logging
import threading
from queue import Queue

from pyamf import remoting, AMF3
import dns.resolver

from .config import Config
from .utils.log import LogTimeDecorator

proxies = {"http": None, "https": None}
proxies = None


class ProxyItem:
    def __init__(self, item_id, proxy, max_use_count=3,test_info=""):
        self.item_id = item_id
        self.proxy = proxy
        self.use_count = 0
        self.max_use_count = max_use_count
        self.test_info = test_info

    def _form_proxy(self):
        if self.proxy is None:
            return None
        return {"http": self.proxy, "https": self.proxy}

    def __str__(self):
        if self.proxy is None:
            return f"本地直连({self.max_use_count}并发)"
        return f"代理地址: {str(self.proxy)}({self.max_use_count}并发) {self.test_info}"

    def __enter__(self, *args, **kwargs):
        self.use_count += 1
        return self._form_proxy()

    def __exit__(self, *args, **kwargs):
        self.use_count -= 1
        pass

    @staticmethod
    def get_local_proxy():
        return ProxyItem(-1, None, max_use_count=99)

    def serialize(self):
        return {
            "item_id": self.item_id,
            "proxy": self.proxy,
            "max_use_count": self.max_use_count,
        }

    @staticmethod
    def deserialize(data):
        item = ProxyItem(data["item_id"], data["proxy"], data["max_use_count"])
        return item


class DNSResolveThread(threading.Thread):
    def __init__(self, hostname, dns_cache):
        super().__init__()
        self.hostname = hostname
        self.dns_cache = dns_cache

    def run(self):
        try:
            answers = self.dns_cache.resolver.resolve(self.hostname)
            ip_list = [i.address for i in answers]
            # 将结果添加到缓存中
            current_time = perf_counter()
            self.dns_cache.cache[self.hostname] = (ip_list, current_time)
        except Exception as e:
            logging.error(f"Failed to resolve {self.hostname}. Exception: {str(e)}")
            raise e


class DNSCache:
    def __init__(self, ttl=30):
        self.resolver = dns.resolver.Resolver()
        self.resolver.nameservers = [
            "180.76.76.76",
            "223.5.5.5",
            "223.6.6.6",
            "119.29.29.29",
        ]
        self.ttl = ttl
        self.cache = {}

    def resolve(self, hostname):
        current_time = perf_counter()
        # 检查缓存是否存在并且没有过期
        if hostname in self.cache:
            ip_list, timestamp = self.cache[hostname]
            try:
                ip = ip_list[0]
            except Exception as e:
                logging.error(
                    f"Failed to resolve {hostname} with ip_list{ip_list}. Exception: {str(e)}"
                )
                raise e
            if current_time - timestamp >= self.ttl:
                DNSResolveThread(hostname, self).start()
            return ip
        else:
            try:
                answers = self.resolver.resolve(hostname)
                ip_list = [i.address for i in answers]
                # 将结果添加到缓存中
                current_time = perf_counter()
                self.cache[hostname] = (ip_list, current_time)
                return self.resolve(hostname)
            except Exception as e:
                logging.error(f"Failed to resolve {hostname}. Exception: {str(e)}")
                raise e


dns_cache = DNSCache()
dns_cache_lock = Lock()


class DNSCacheAdapter(HTTPAdapter):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def get_connection(self, url, proxies=None):
        # 解析主机名并使用缓存的IP地址
        host = self.get_host(url)
        with dns_cache_lock:
            ip = dns_cache.resolve(host)
        url = url.replace(host, ip)
        return super().get_connection(url, proxies)

    def get_host(self, url):
        # 提取URL中的主机名
        return urlparse(url).hostname


class ProxyManager:
    def __init__(self):
        self.proxy_item_list = [ProxyItem.get_local_proxy()]
        self.block_when_no_proxy = (
            False  # 没有可用代理后是否阻塞，不阻塞则不使用代理直接直连
        )
        self._lock = Lock()
        self.id_set = set()
        self.use_dns_cache = False

    def get_adapter(self):
        return DNSCacheAdapter() if self.use_dns_cache else HTTPAdapter()

    def reset_proxy_list(self):
        with self._lock:
            self.proxy_item_list = [ProxyItem.get_local_proxy()]

    def get_proxy_item(self):
        min_use_count = 99999
        min_index = -1
        if len(self.proxy_item_list) == 0:
            raise RuntimeError("没有可用代理")
        while True:
            with self._lock:
                for item in self.proxy_item_list:
                    if (
                        item.max_use_count is not None
                        and item.use_count >= item.max_use_count
                    ):
                        continue
                    if item.use_count < min_use_count:
                        min_use_count = item.use_count
                        min_index = self.proxy_item_list.index(item)
            if min_index == -1:
                if self.block_when_no_proxy:
                    sleep(0.05)
                    continue
                # logging.info("没有可用代理，使用本地直连")
                return ProxyItem.get_local_proxy()
            break
        # logging.info(f"使用代理: {self.proxy_item_list[min_index]}")
        return self.proxy_item_list[min_index]

    def _get_unique_item_id(self):
        with self._lock:
            for item in self.proxy_item_list:
                self.id_set.add(item.item_id)
            for i in range(999999):
                if i not in self.id_set:
                    break
            else:
                raise RuntimeError("无法分配item_id")
            self.id_set.add(i)
            return i

    def get_item(self, item_id):
        with self._lock:
            for item in self.proxy_item_list:
                if item.item_id == item_id:
                    return item
            return None

    def set_item_proxy(self, item_id, proxy):
        item = self.get_item(item_id)
        if item is None:
            return
        with self._lock:
            item.proxy = proxy

    def set_item_max_use_count(self, item_id, max_use_count):
        item = self.get_item(item_id)
        if item is None:
            return
        with self._lock:
            item.max_use_count = max_use_count

    def add_proxy_item(self, proxy, max_use_count=3):
        item_id = self._get_unique_item_id()
        with self._lock:
            self.proxy_item_list.append(
                ProxyItem(item_id, proxy, max_use_count=max_use_count)
            )
        return item_id

    def delete_proxy_item(self, item_id):
        with self._lock:
            for i, item in enumerate(self.proxy_item_list):
                if item.item_id == item_id:
                    self.proxy_item_list.pop(i)
                    break

    def move_up_item(self, item_id):
        with self._lock:
            for i in range(1, len(self.proxy_item_list)):
                if i == 0:
                    continue
                if self.proxy_item_list[i].item_id == item_id:
                    self.proxy_item_list[i], self.proxy_item_list[i - 1] = (
                        self.proxy_item_list[i - 1],
                        self.proxy_item_list[i],
                    )
                    return

    def move_down_item(self, item_id):
        with self._lock:
            for i in range(len(self.proxy_item_list) - 1):
                if i == len(self.proxy_item_list) - 1:
                    continue
                if self.proxy_item_list[i].item_id == item_id:
                    self.proxy_item_list[i], self.proxy_item_list[i + 1] = (
                        self.proxy_item_list[i + 1],
                        self.proxy_item_list[i],
                    )
                    return

    def save(self, save_path):
        os.makedirs(os.path.dirname(save_path), exist_ok=True)
        data = {
            "block_when_no_proxy": self.block_when_no_proxy,
            "proxy_item_list": [item.serialize() for item in self.proxy_item_list],
            "use_dns_cache": self.use_dns_cache,
        }
        with open(save_path, "wb") as f:
            f.write(pickle.dumps(data))

    def load(self, load_path):
        if not os.path.exists(load_path):
            return
        with open(load_path, "rb") as f:
            data = pickle.loads(f.read())
        with self._lock:
            if "block_when_no_proxy" in data:
                self.block_when_no_proxy = data["block_when_no_proxy"]
            if "proxy_item_list" in data:
                self.proxy_item_list = [
                    ProxyItem.deserialize(item) for item in data["proxy_item_list"]
                ]
            if "use_dns_cache" in data:
                self.use_dns_cache = data["use_dns_cache"]


proxy_man = ProxyManager()


def test_proxy_alive(proxy,item_id, test_times):
    s_num = 0
    f_num = 0
    for i in range(test_times):
        try:
            r = requests.get(
                "http://httpbin.org/ip",
                proxies={
                    "http": f"http://{proxy}",
                    "https": f"https://{proxy}",
                },
                timeout=3,
            )
            if r.status_code == 200:
                s_num += 1
            else:
                f_num += 1
        except:
            f_num += 1
    
    proxy_man.get_item(item_id).test_info = f"成功 {s_num}  失败 {f_num}"

    return f"成功次数 {s_num}  失败次数 {f_num}"

class WebRequest:
    def __init__(self, cfg: Config, cache_dir=None):
        self.cfg = cfg
        self.user_agent = ""
        self.cache_dir = cache_dir
        self.session = requests.Session()
        if proxy_man.use_dns_cache:
            self.session.mount("http://", proxy_man.get_adapter())

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
        url = url.replace(f"http://{self.cfg.host}/", "")
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
                if status_code == 502:
                    raise RuntimeError(f"服务器更新中")
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
                    proxy_item = proxy_man.get_proxy_item()
                    with proxy_item as proxy:
                        resp = self.session.get(url, **kwargs, proxies=proxy)
                check_status(resp.status_code)
                return resp.content

            assert self.cache_dir is not None
            url_hash = self.hash(url)
            if os.path.exists(os.path.join(self.cache_dir, url_hash)):
                with open(os.path.join(self.cache_dir, url_hash), "rb") as f:
                    content = f.read()
            else:
                with LogTimeDecorator(url):
                    proxy_item = proxy_man.get_proxy_item()
                    with proxy_item as proxy:
                        resp = self.session.get(url, **kwargs, proxies=proxy)
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
                if status_code == 502:
                    raise RuntimeError(f"服务器更新中")
                if status_code != 200:
                    raise RuntimeError(f"Request Post Error: {status_code} Url: {url}")

            if init_header:
                if kwargs.get("headers") is None:
                    kwargs["headers"] = {}
                self.init_header(kwargs["headers"])

            if not use_cache:
                if not exit_response:
                    with LogTimeDecorator(url):
                        proxy_item = proxy_man.get_proxy_item()
                        with proxy_item as proxy:
                            resp = self.session.post(url, **kwargs, proxies=proxy)
                    check_status(resp.status_code)
                    return resp.content
                with LogTimeDecorator(url):
                    proxy_item = proxy_man.get_proxy_item()
                    with proxy_item as proxy:
                        resp = self.session.post(
                            url,
                            stream=True,
                            **kwargs,
                            proxies=proxy,
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
                    proxy_item = proxy_man.get_proxy_item()
                    with proxy_item as proxy:
                        resp = self.session.post(url, **kwargs, proxies=proxy)
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
        msg,
        use_cache=False,
        init_header=True,
        url_format=True,
        max_retry=50,
        logger=None,
        except_retry=False,
        **kwargs,
    ):
        cnt = 0
        while cnt < max_retry:
            cnt += 1
            try:
                self.cfg.free_event.wait()
                response = self.get(
                    url,
                    use_cache=use_cache,
                    init_header=init_header,
                    url_format=url_format,
                    **kwargs,
                )

                # import random
                # if random.random() < 0.2:

                #     raise requests.ConnectionError("test")

                if len(response) == 0:
                    return None
                try:
                    text = response.decode("utf-8")
                    if "请求过于频繁" in text:
                        warning_msg = "请求{}过于频繁，选择等待3秒后重试".format(msg)
                        cnt -= 1
                        if logger is not None:
                            logger.log(warning_msg)
                        else:
                            logging.warning(warning_msg)
                        self.cfg.sleep_freq(3)
                        continue
                    if "服务器更新" in text:
                        warning_msg = (
                            "请求{}的时候服务器更新，选择等待10秒后重试".format(msg)
                        )
                        cnt -= 1
                        if logger is not None:
                            logger.log(warning_msg)
                        else:
                            logging.warning(warning_msg)
                        self.cfg.sleep_freq(10)
                        continue
                except:
                    pass
                break
            except Exception as e:
                if "429" in str(e):
                    warning_msg = (
                        "请求{}过于频繁，触发ip限流，选择等待10秒后重试".format(msg)
                    )
                    cnt -= 1
                    if logger is not None:
                        logger.log(warning_msg)
                    else:
                        logging.warning(warning_msg)
                    self.cfg.sleep_freq(10)
                    continue
                if "服务器更新" in str(e):
                    warning_msg = "请求{}的时候服务器更新，选择等待10秒后重试".format(
                        msg
                    )
                    cnt -= 1
                    if logger is not None:
                        logger.log(warning_msg)
                    else:
                        logging.warning(warning_msg)
                    self.cfg.sleep_freq(10)
                    continue
                if except_retry:
                    warning_msg = "重新尝试请求{}，选择等待1秒后重试。最多再等待{}次。异常类型: {}".format(
                        msg, max_retry - cnt, type(e).__name__
                    )
                    if logger is not None:
                        logger.log(warning_msg)
                    else:
                        logging.warning(warning_msg)
                    sleep(1)
                    continue
                raise e
        else:
            warning_msg = "尝试请求{}失败，超过最大尝试次数{}次".format(msg, max_retry)
            if logger is not None:
                logger.log(warning_msg)
            else:
                logging.warning(warning_msg)
            raise Exception(warning_msg)
        return response

    def _amf_post_decode(self, url, data, exit_response=False, **kwargs):
        resp = self.post(
            url,
            data=data,
            exit_response=exit_response,
            headers={"Content-Type": "application/x-amf"},
            **kwargs,
        )
        if exit_response:
            return
        if len(resp) == 0:
            raise RuntimeError("amf返回结果为空")
        resp_ev = remoting.decode(resp)

        return resp_ev["/1"]

    def amf_post(
        self,
        body,
        target,
        url,
        exit_response=False,
        **kwargs,
    ):
        req = remoting.Request(target=target, body=body)
        ev = remoting.Envelope(AMF3)
        ev['/1'] = req
        bin_msg = remoting.encode(ev, strict=True)
        result = self._amf_post_decode(
            url,
            bin_msg.getvalue(),
            exit_response=exit_response,
            **kwargs,
        )
        if exit_response:
            return
        return result

    def amf_post_retry(
        self,
        body,
        target,
        url,
        msg,
        max_retry=50,
        logger=None,
        exit_response=False,
        allow_empty=False,
        except_retry=False,
        **kwargs,
    ):
        cnt = 0
        while cnt < max_retry:
            cnt += 1
            try:
                self.cfg.free_event.wait()
                response = self.amf_post(
                    body,
                    target,
                    url,
                    exit_response=exit_response,
                    **kwargs,
                )

                # import random

                # if random.random() < 0.2:
                #     raise requests.ConnectionError("test")

                if exit_response:
                    return
                if response.status != 0:
                    if "频繁" in response.body.description:
                        warning_msg = "{}过于频繁，选择等待3秒后重试".format(msg)
                        cnt -= 1
                        if logger is not None:
                            logger.log(warning_msg)
                        else:
                            logging.warning(warning_msg)
                        self.cfg.sleep_freq(3)
                        continue
                    if "更新" in response.body.description:
                        warning_msg = "{}的时候服务器更新，选择等待10秒后重试".format(
                            msg
                        )
                        cnt -= 1
                        if logger is not None:
                            logger.log(warning_msg)
                        else:
                            logging.warning(warning_msg)
                        self.cfg.sleep_freq(10)
                        continue
                break
            except RuntimeError as e:
                if "429" in str(e):
                    warning_msg = (
                        "请求{}过于频繁，触发ip限流，选择等待10秒后重试".format(msg)
                    )
                    cnt -= 1
                    if logger is not None:
                        logger.log(warning_msg)
                    else:
                        logging.warning(warning_msg)
                    self.cfg.sleep_freq(10)
                    continue
                if "服务器更新" in str(e):
                    warning_msg = "请求{}的时候服务器更新，选择等待10秒后重试".format(
                        msg
                    )
                    cnt -= 1
                    if logger is not None:
                        logger.log(warning_msg)
                    else:
                        logging.warning(warning_msg)
                    self.cfg.sleep_freq(10)
                    continue
                if "amf返回结果为空" in str(e) and allow_empty:
                    return None
                if except_retry:
                    warning_msg = "{}失败，选择等待1秒后重试。最多再等待{}次。异常类型: {}".format(
                        msg, max_retry - cnt, type(e).__name__
                    )
                    if logger is not None:
                        logger.log(warning_msg)
                    else:
                        logging.warning(warning_msg)
                    sleep(1)
                    continue
                raise e
            except Exception as e:
                if except_retry:
                    warning_msg = "{}失败，选择等待1秒后重试。最多再等待{}次。异常类型: {}".format(
                        msg, max_retry - cnt, type(e).__name__
                    )
                    if logger is not None:
                        logger.log(warning_msg)
                    else:
                        logging.warning(warning_msg)
                    sleep(1)
                    continue
                raise e
        else:
            warning_msg = "{}失败，超过最大尝试次数{}次".format(msg, max_retry)
            if logger is not None:
                logger.log(warning_msg)
            else:
                logging.warning(warning_msg)
            raise RuntimeError(warning_msg)
        return response

    def amf_post_retry_async(
        self,
        body,
        target,
        url,
        msg,
        retry_times=1,
        max_pool_size=16,
        max_retry=20,
        logger=None,
        exit_response=False,
        allow_empty=False,
        except_retry=False,
    ):
        def run():
            return self.amf_post_retry(
                body,
                target,
                url,
                msg,
                max_retry=max_retry,
                logger=logger,
                exit_response=exit_response,
                allow_empty=allow_empty,
                except_retry=except_retry,
            )

        result = []
        with concurrent.futures.ThreadPoolExecutor(
            max_workers=min(max_pool_size, retry_times)
        ) as executor:
            for _ in range(retry_times):
                result.append(executor.submit(run))
        return result
