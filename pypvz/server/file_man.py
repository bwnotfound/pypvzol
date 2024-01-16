from threading import Event
import logging
import os

from .. import Config


class FileManager:
    def __init__(self, data_dir, logger: logging.Logger):
        self.data_dir = data_dir
        self.logger = logger
        self.usersettings_root_dir = os.path.join(data_dir, 'usersettings')

    def format_usersettings_save_dir(self, cfg: Config):
        return os.path.join(
            self.usersettings_root_dir, "{}_{}".format(cfg.username, hash(cfg.cookie))
        )