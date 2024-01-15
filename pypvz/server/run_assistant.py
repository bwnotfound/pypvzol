import logging

from file_man import FileManager
from ..ui.user.usersettings import UserSettings, get_usersettings


class AssistantManager:
    def __init__(self, file_man: FileManager, logger: logging.Logger):
        self.file_man = file_man
        self.logger = logger

    def get_next_user(self):
        pass
