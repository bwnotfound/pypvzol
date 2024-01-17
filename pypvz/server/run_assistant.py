import logging
from threading import Thread
import time
import concurrent.futures
from queue import Queue
import os
import pickle

from .file_man import FileManager
from ..ui.user.usersettings import UserSettings, get_usersettings
from .. import Config
from ..ui.message import IOLogger


class AssistantManager:
    def __init__(self, file_man: FileManager, logger: logging.Logger):
        self.file_man = file_man
        self.logger = logger
        self.config_list = []
        self.pool_max = 2
        self.run_user_queue = Queue()
        self.usersettings_stop_channel = Queue()

    def get_usersettings_from_cfg(self, cfg: Config):
        user_dir = self.file_man.format_usersettings_save_dir(cfg)
        log_dir = os.path.join(user_dir, 'logs')
        setting_dir = os.path.join(user_dir, 'settings')
        os.makedirs(log_dir, exist_ok=True)
        os.makedirs(setting_dir, exist_ok=True)
        io_logger = IOLogger(log_dir)
        usersettings = get_usersettings(cfg, io_logger, setting_dir)
        return usersettings

    def get_usersettings_from_bytes(self, data: bytes):
        data = pickle.loads(data)
        cfg, data = data["config"], data["data"]
        usersettings = self.get_usersettings_from_cfg(Config(cfg))
        usersettings.import_data(data)
        return usersettings

    def run_user(self, data: bytes):
        usersettings = self.get_usersettings_from_bytes(data)
        usersettings._start(self.usersettings_stop_channel)

    def _start(self):
        future_list = []
        with concurrent.futures.ThreadPoolExecutor(
            max_workers=self.pool_max
        ) as self.executor:
            while True:
                if self.run_user_queue.qsize() == 0:
                    time.sleep(0.2)
                    continue
                data = self.run_user_queue.get()
                future_list.append(self.executor.submit(self.run_user, data))
                if (
                    len(future_list) >= self.pool_max
                    or self.run_user_queue.qsize() == 0
                ):
                    for future in concurrent.futures.as_completed(future_list):
                        try:
                            future.result()
                        except Exception as e:
                            self.logger.warning(e)
                        break
                    future_list.remove(future)

    def add_user(self, data):
        self.run_user_queue.put(data)

    def get_user_extra_data(self, data: bytes):
        assert isinstance(data, bytes)
        usersettings = self.get_usersettings_from_bytes(data)
        return {
            "name": usersettings.user.name,
            "cookie": usersettings.cfg.cookie,
        }

    def start(self):
        thread = Thread(target=self._start)
        thread.start()
        return thread
