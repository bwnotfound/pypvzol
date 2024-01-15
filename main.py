import os
import logging
import warnings
import time

from pypvz.server.file_man import FileManager
from pypvz.server.communicate import start_communicator, terminate_communicator
from pypvz.server.run_assistant import AssistantManager

warnings.filterwarnings("ignore", category=DeprecationWarning)


def get_logger(log_type, log_name=None):
    if log_name is None:
        log_name = "log.txt"
    log_now_dir = os.path.join(log_root_dir, log_type, time.strftime("%Y-%m-%d"))
    logger_handler = logging.FileHandler(os.path.join(log_now_dir, log_name))
    logger = logging.Logger()
    logger.addHandler(logger_handler)
    return logger


if __name__ == "__main__":
    # 设置logging监听等级为INFO
    logging.basicConfig(level=logging.INFO)  # 如果不想让控制台输出那么多信息，可以将这一行注释掉
    # 取root_dir为可执行文件的目录
    root_dir = os.getcwd()
    data_dir = os.path.join(root_dir, "data")
    log_root_dir = os.path.join(root_dir, "logs")
    os.makedirs(data_dir, exist_ok=True)
    os.makedirs(os.path.join(data_dir, "config"), exist_ok=True)
    # TODO: 加入运行循环
    file_logger = get_logger("file")
    assistant_logger = get_logger("assistant")
    communicator_logger = get_logger("communicator")
    file_man = FileManager(data_dir, file_logger)
    assistant_man = AssistantManager(file_man, assistant_logger)
    # start_communicator(assistant_man, communicator_logger)
    # terminate_communicator()
