import json
import logging
from threading import Lock, Event
from time import perf_counter, sleep


class Config:
    def __init__(self, config_path):
        if isinstance(config_path, str):
            with open(config_path, 'r', encoding='utf-8') as f:
                self.config = json.load(f)
        elif isinstance(config_path, dict):
            self.config = config_path
        else:
            raise TypeError('config_path must be str or dict')

        def error(msg):
            logging.error(
                f"config.json中缺少{msg}字段。请删除对应登录账号并重新登录，账号数据并不会丢失"
            )
            raise KeyError(
                f'config.json中缺少{msg}字段。请删除对应登录账号并重新登录，账号数据并不会丢失'
            )

        if 'cookie' not in self.config:
            error("cookie")
        if 'username' not in self.config:
            error("username")
        if 'region' not in self.config:
            error("region")
        if 'host' not in self.config:
            error("host")
        if 'server' not in self.config:
            error("server")
        self.timeout = 7
        self.millsecond_delay = 0
        self._lock = Lock()
        self.last_time = 0
        self.wait_requests_over = False
        self.free_event = Event()
        self.free_event.set()
        self._freq_lock = Lock()

    def sleep_freq(self, t):
        # 避免多线程一直睡睡睡
        if not self.free_event.is_set():
            self.free_event.wait()
            return
        try:
            self._freq_lock.acquire()
            self.free_event.clear()
            sleep(t)
        finally:
            self._freq_lock.release()
            self.free_event.set()

    def acquire(self):
        self._lock.acquire()
        now = perf_counter()
        if now - self.last_time < self.millsecond_delay / 1000:
            sleep((self.millsecond_delay / 1000) - (now - self.last_time))
        if not self.wait_requests_over:
            self._lock.release()
            self.last_time = perf_counter()

    def release(self):
        if self.wait_requests_over:
            self._lock.release()
            self.last_time = perf_counter()

    @property
    def username(self):
        return self.config['username']

    @property
    def cookie(self):
        return self.config['cookie']

    @property
    def region(self):
        return self.config['region']

    @property
    def host(self):
        return self.config['host']

    @property
    def server(self):
        return self.config['server']

    def save(self):
        data = {
            "config": self.config,
            "timeout": self.timeout,
            "millsecond_delay": self.millsecond_delay,
        }
        return data

    def load(self, data):
        for k, v in data.items():
            if hasattr(self, k):
                setattr(self, k, v)
