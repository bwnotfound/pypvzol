from time import localtime, strftime, sleep
import logging
from queue import Queue
from collections import deque
import threading
import os


class Logger:
    def __init__(self, logger: logging.Logger, info_channel: Queue):
        self.logger = logger
        self._info_channel = info_channel

    def _log_str_format(self, msg):
        msg = str(msg)
        result = ""
        result += strftime("%Y-%m-%d %H:%M:%S ", localtime())
        result += msg
        return result

    def log(self, msg, log_info=True):
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
        self._info_channel.put(msg)
        if log_info:
            self.logger.info(message)
            logging.info(message)

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
        logging.info(message)
        if log_info:
            self._info_channel.put(msg)


class _IOLoggerThread(threading.Thread):
    def __init__(
        self,
        info_channel: Queue,
        stop_channel: Queue,
        info_list: deque,
        new_info_list: deque,
        lock: threading.Lock,
        max_info_capacity,
        trigger,
    ):
        super().__init__()
        self.info_channel = info_channel
        self.stop_channel = stop_channel
        self.lock = lock
        self.info_list = info_list
        self.new_info_list = new_info_list
        self.max_info_capacity = max_info_capacity
        self.trigger = trigger

    def run(self):
        while self.stop_channel.qsize() == 0:
            if self.info_channel.qsize() == 0:
                # 程序休眠
                sleep(0.2)
                continue
            self.lock.acquire()
            while self.info_channel.qsize() > 0:
                info = self.info_channel.get()
                self.info_list.appendleft(info)
                self.new_info_list.appendleft(info)
            num = len(self.info_list)
            while num > self.max_info_capacity:
                self.info_list.pop()
                num -= 1
            num = len(self.new_info_list)
            while num > self.max_info_capacity:
                self.new_info_list.pop()
                num -= 1
            self.lock.release()
            self.trigger()


class IOLogger:
    def __init__(self, save_dir, signal=None, max_info_capacity=100, max_file_num=4):
        self.save_dir = save_dir
        self.max_file_num = max_file_num
        self.signal = signal
        self.save_path = os.path.join(
            save_dir,
            "日志_起始时间{}.txt".format(strftime("%Y-%m-%d_%H-%M-%S", localtime())),
        )
        self._check_file_num()
        self.max_info_capacity = max_info_capacity
        self.info_channel = Queue()
        self._stop_channel = Queue()
        self._info_list = deque()
        self._new_info_list = deque()
        self._lock = threading.Lock()
        self._thread_logger = _IOLoggerThread(
            self.info_channel,
            self._stop_channel,
            self._info_list,
            self._new_info_list,
            self._lock,
            max_info_capacity,
            self.trigger,
        )
        _logger = logging.Logger("IOLogger", level=logging.INFO)
        file_handler = logging.FileHandler(self.save_path, encoding="utf-8")
        formatter = logging.Formatter("%(asctime)s - %(levelname)s - %(message)s")
        file_handler.setFormatter(formatter)
        _logger.addHandler(file_handler)
        self.logger = Logger(_logger, self.info_channel)
        self._thread_logger.start()

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

    def get_logger(self):
        return self.logger

    def trigger(self):
        if self.signal is not None:
            self.signal.emit()

    def set_signal(self, signal):
        assert signal is not None and hasattr(signal, "emit")
        self.signal = signal

    def get_new_infos(self):
        self._lock.acquire()
        result = list(self._new_info_list)
        self._new_info_list.clear()
        self._lock.release()
        return result

    def close(self):
        self._stop_channel.put(1)
        self._thread_logger.join()

    def save(self):
        raise NotImplementedError
        # self._lock.acquire()
        # with open(self.save_path, "a", encoding="utf-8") as f:
        #     for info in self._info_list:
        #         f.write(info + "\n")
        # self._lock.release()

    def load(self):
        raise NotImplementedError
        # self._lock.acquire()
        # self._lock.release()
