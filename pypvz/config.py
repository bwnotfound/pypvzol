import json


class Config:
    def __init__(self, config_path):
        if isinstance(config_path, str):
            with open(config_path, 'r', encoding='utf-8') as f:
                self.config = json.load(f)
        elif isinstance(config_path, dict):
            self.config = config_path
        else:
            raise TypeError('config_path must be str or dict')
            
    @property
    def username(self):
        return self.config['username']

    @property
    def cookie(self):
        return self.config['cookie']
    
    @property
    def region(self):
        return self.config['region']