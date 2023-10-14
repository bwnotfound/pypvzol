import json
import logging


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