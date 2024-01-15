from threading import Event
import logging

class FileManager:
    
    def __init__(self, data_dir, logger: logging.Logger):
        self.data_dir = data_dir
        self.logger = logger
        