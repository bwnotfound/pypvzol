import logging
import os
import hashlib

from .. import Config


class FileManager:
    def __init__(self, data_dir, logger: logging.Logger):
        self.data_dir = data_dir
        self.logger = logger
        self.usersettings_root_dir = os.path.join(data_dir, 'usersettings')

    def format_usersettings_save_dir(self, cfg):
        config = Config(cfg)
        return os.path.join(
            self.usersettings_root_dir,
            "{}_{}".format(
                config.username, hashlib.md5(config.cookie.encode()).hexdigest()
            ),
        )
