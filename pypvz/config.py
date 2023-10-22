import json
import logging
from threading import Lock
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
            logging.error(f"config.json中缺少{msg}字段。请删除对应登录账号并重新登录。账号数据并不会丢失")
            raise KeyError(f'config.json中缺少{msg}字段。请删除对应登录账号并重新登录。账号数据并不会丢失')
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
    
    def acquire(self):
        self._lock.acquire()
        now = perf_counter()
        if now - self.last_time < self.millsecond_delay / 1000:
            sleep((self.millsecond_delay / 1000) - (now - self.last_time))
        
    def release(self):
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