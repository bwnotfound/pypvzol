from time import localtime, strftime
import logging
import os


class EmptyLogger:
    def log(self, msg: str, log_info=True):
        return

    def reverse_log(self, msg: str, log_info=True):
        return


class Logger:
    def __init__(
        self,
        logger: logging.Logger,
        extra_logger: logging.Logger = None,
    ):
        self.logger = logger
        self.extra_logger = extra_logger

    def _log_str_format(self, msg):
        msg = str(msg)
        result = ""
        result += strftime("%Y-%m-%d %H:%M:%S ", localtime())
        result += msg
        return result

    def log(self, msg: str, log_info=True):
        message = self._log_str_format(msg)
        if log_info:
            self.logger.info(message)
            if self.extra_logger is not None:
                self.extra_logger.info(message)

    def reverse_log(self, msg, log_info=True):
        if isinstance(msg, str):
            msg = [(msg, None)]
        msg = [(self._log_str_format(""), None)] + msg
        new_msg = []
        for data in msg:
            if not (isinstance(data, list) or isinstance(data, tuple)):
                data = (data, None)
            assert len(data) == 2
            new_msg.append(data)
        msg = new_msg
        message = "".join([item[0] for item in msg])
        self.logger.info(message)
        if self.extra_logger is not None:
            self.extra_logger.info(message)


class IOLogger:
    def __init__(
        self,
        save_dir=None,
        extra_logger=None,
        max_file_num=2,
    ):
        self.save_dir = save_dir
        if save_dir is None:
            self.logger = EmptyLogger()
            return
        if isinstance(save_dir, logging.Logger):
            self.logger = Logger(save_dir, extra_logger=extra_logger)
            return
        if isinstance(save_dir, str):
            os.makedirs(save_dir, exist_ok=True)

        self.max_file_num = max_file_num
        self.save_path = os.path.join(
            save_dir, "日志_起始时间_{}.txt".format(strftime("%Y-%m-%d", localtime()))
        )
        self._check_file_num()
        _logger = logging.Logger("IOLogger", level=logging.INFO)
        file_handler = logging.FileHandler(self.save_path, encoding="utf-8")
        formatter = logging.Formatter("%(asctime)s - %(levelname)s - %(message)s")
        file_handler.setFormatter(formatter)
        _logger.addHandler(file_handler)
        self.logger = Logger(_logger, extra_logger=extra_logger)

    # 确保save_dir下最多有max_file_num个文件
    def _check_file_num(self):
        file_list = os.listdir(self.save_dir)
        file_list = [
            os.path.join(self.save_dir, file)
            for file in file_list
            if file.endswith(".txt")
        ]
        file_list.sort(key=lambda x: os.path.getmtime(x), reverse=True)
        if len(file_list) > self.max_file_num:
            for file in file_list[self.max_file_num :]:
                os.remove(file)

    @staticmethod
    def get_account_logs(log_dir):
        if not os.path.exists(log_dir):
            return None
        file_list = os.listdir(log_dir)
        file_list = [
            os.path.join(log_dir, file) for file in file_list if file.endswith(".txt")
        ]
        file_list.sort(key=lambda x: os.path.getmtime(x), reverse=True)
        return file_list

    def get_logger(self):
        return self.logger
