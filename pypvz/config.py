import json


class Config:
    def __init__(self, config_path):
        with open(config_path, 'r', encoding='utf-8') as f:
            self.config = json.load(f)

    @property
    def cookie(self):
        return self.config['cookie']
    
    @property
    def region(self):
        return self.config['region']