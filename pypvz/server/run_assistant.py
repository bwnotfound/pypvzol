import logging
from threading import Thread, Event, Lock
import concurrent.futures
import time
import pickle
import os
import shutil

from .file_man import FileManager
from ..ui.user.usersettings import UserSettings, get_usersettings
from .assistant_user import AssistantAccount
from ..ui.message import IOLogger


class UserManager:
    def __init__(self):
        self.all_account_list: list[AssistantAccount] = []
        self.account_id2account: dict[int, AssistantAccount] = {}
        self.waiting_account_id_list = []
        self.running_account_id_list = []
        self.lock = Lock()

    def register_finish_callback(self, callback):
        with self.lock:
            self.finish_callback = callback

    def load_account_list(self, account_list: list[AssistantAccount]):
        with self.lock:
            self.all_account_list = account_list
            self.account_id2account = {}
            for account in account_list:
                self.account_id2account[account.id] = account
        return 0

    def get_next_account(self) -> AssistantAccount:
        with self.lock:
            if len(self.waiting_account_id_list) == 0:
                return None
            account_id = self.waiting_account_id_list.pop(0)
            account = self.account_id2account[account_id]
            self.running_account_id_list.append(account_id)
            return account

    def add_account(self, account: AssistantAccount):
        with self.lock:
            if account.id in self.account_id2account:
                return
            self.all_account_list.append(account)
            self.account_id2account[account.id] = account

    def finish_account(self, account_id):
        with self.lock:
            if account_id not in self.account_id2account:
                return
            for i, account in enumerate(self.all_account_list):
                if account.id == account_id:
                    break
            else:
                return
            try:
                self.running_account_id_list.remove(account.id)
            except:
                pass
            if hasattr(self, "finish_callback"):
                self.finish_callback(account_id)

    def remove_account(self, account_id):
        with self.lock:
            if account_id not in self.account_id2account:
                return 1
            for i, account in enumerate(self.all_account_list):
                if account.id == account_id:
                    break
            else:
                return 2
            account.usersettings_stop_channel.put(None)
            self.all_account_list.pop(i)
            self.account_id2account.pop(account_id)
            try:
                self.waiting_account_id_list.remove(account.id)
            except:
                pass
            try:
                self.running_account_id_list.remove(account.id)
            except:
                pass
            return 0

    def is_running(self):
        return (
            len(self.running_account_id_list) > 0
            or len(self.waiting_account_id_list) > 0
        )

    def clear_working_account(self):
        with self.lock:
            self.waiting_account_id_list = []
            self.running_account_id_list = []

    def load_working_account(self):
        self.clear_working_account()
        with self.lock:
            for account in self.all_account_list:
                self.waiting_account_id_list.append(account.id)

    def get_working_account_id_list(self):
        with self.lock:
            return self.running_account_id_list + self.waiting_account_id_list

    def get_running_account_id_list(self):
        with self.lock:
            return self.running_account_id_list

    def get_waiting_account_id_list(self):
        with self.lock:
            return self.waiting_account_id_list

    def get_account(self, account_id):
        with self.lock:
            return self.account_id2account.get(account_id, None)


class AssistantManager:
    def __init__(self, file_man: FileManager, logger: logging.Logger):
        self.file_man = file_man
        self.logger = logger
        self.pool_max = 1
        self.stop_circle_event = Event()
        self.stop_loop_event = Event()
        self.run_circle_thread = None
        self.run_loop_thread = None
        self.circle_account_man = UserManager()
        self.loop_account_man = UserManager()

    def get_usersettings_from_cfg(
        self, cfg, data: bytes, need_save=True, account_id=None
    ) -> UserSettings:
        if account_id is not None:
            user_dir = self.file_man.format_usersettings_save_dir(account_id)
        else:
            user_dir = None
        usersettings = get_usersettings(
            cfg, user_dir, extra_logger=self.logger, need_logs=need_save
        )
        usersettings.import_data(data)
        return usersettings

    def get_usersettings_from_bytes(
        self, data: bytes, need_save=True, account_id=None
    ) -> UserSettings:
        try:
            data = pickle.loads(data)
            cfg, data = data["config"], data["data"]
            usersettings = self.get_usersettings_from_cfg(
                cfg, data, need_save=need_save, account_id=account_id
            )
            return usersettings
        except Exception as e:
            # self.logger.warning(e)
            return None

    def run_user(self, account: AssistantAccount, settings=None):
        usersettings = self.get_usersettings_from_bytes(
            account.data, account_id=account.id
        )
        if usersettings is None:
            self.logger.warning("Account数据为空")
            return
        usersettings.exit_if_nothing_todo = True
        if settings is not None:
            if "serverbattle_all" in settings and settings["serverbattle_all"]:
                usersettings.serverbattle_man.rest_challenge_num_limit = 0
        usersettings._start(account.usersettings_stop_channel)

    def get_user_extra_data(self, data: bytes):
        assert isinstance(data, bytes)
        usersettings = self.get_usersettings_from_bytes(data, need_save=False)
        if usersettings is None:
            return {
                "code": 1,
                "message": "用户数据错误",
            }
        return {
            "code": 0,
            "message": "用户信息读取成功",
            "result": {
                "name": usersettings.user.name,
                "cookie": usersettings.cfg.cookie,
            },
        }

    def get_account_logs(self, account_id):
        log_dir = os.path.join(
            self.file_man.format_usersettings_save_dir(account_id), "logs"
        )
        log_path_list = IOLogger.get_account_logs(log_dir)
        if log_path_list is None:
            return {
                "code": 1,
                "message": "日志文件夹不存在，可能是因为账号未运行过",
            }
        result = []
        for log_path in log_path_list:
            with open(log_path, "r", encoding="utf-8") as f:
                s = f.read()
            result.append({"logName": os.path.basename(log_path), "content": s})
        return {"code": 0, "message": "所有日志读取成功", "result": result}

    def _run_one_cycle(self, settings):
        if self.stop_circle_event.is_set():
            return
        future_list = []

        def pop_one_result():
            futures = [future for future, _ in future_list]
            for future in concurrent.futures.as_completed(futures):
                index = futures.index(future)
                account_id = future_list[index][1]
                try:
                    future.result()
                except Exception as e:
                    self.logger.warning(e)
                self.circle_account_man.finish_account(account_id)
                break
            future_list.pop(index)

        with concurrent.futures.ThreadPoolExecutor(
            max_workers=self.pool_max
        ) as executor:
            while True:
                if self.stop_circle_event.is_set():
                    executor.shutdown(wait=False)
                    return
                account = self.circle_account_man.get_next_account()
                if account is None:
                    break
                while account.usersettings_stop_channel.qsize() > 0:
                    account.usersettings_stop_channel.get()
                future_list.append(
                    (
                        executor.submit(
                            self.run_user,
                            account,
                            settings,
                        ),
                        account.id,
                    )
                )
                if len(future_list) >= self.pool_max:
                    pop_one_result()
            while len(future_list) > 0:
                if self.stop_circle_event.is_set():
                    executor.shutdown(wait=False)
                    return
                pop_one_result()
        self.run_circle_thread = None

    def _run_loop(self):
        while not self.stop_loop_event.is_set():
            if self.stop_loop_event.is_set():
                return
            future_list = []

            def pop_one_result():
                futures = [future for future, _ in future_list]
                for future in concurrent.futures.as_completed(futures):
                    index = futures.index(future)
                    account_id = future_list[index][1]
                    try:
                        future.result()
                    except Exception as e:
                        self.logger.warning(e)
                    self.loop_account_man.finish_account(account_id)
                    break
                future_list.pop(index)

            with concurrent.futures.ThreadPoolExecutor(
                max_workers=self.pool_max
            ) as executor:
                while True:
                    if self.stop_loop_event.is_set():
                        executor.shutdown(wait=False)
                        return
                    account = self.loop_account_man.get_next_account()
                    if account is None:
                        break
                    while account.usersettings_stop_channel.qsize() > 0:
                        account.usersettings_stop_channel.get()
                    future_list.append(
                        (
                            executor.submit(
                                self.run_user,
                                account,
                            ),
                            account.id,
                        )
                    )
                    if len(future_list) >= self.pool_max:
                        pop_one_result()
                while len(future_list) > 0:
                    if self.stop_loop_event.is_set():
                        executor.shutdown(wait=False)
                        return
                    pop_one_result()
            self.run_circle_thread = None
            if self.stop_loop_event.is_set():
                break
            time.sleep(2)

    def run_one_cycle(self, settings):
        if self.run_circle_thread is not None:
            return None
        self.stop_circle_event.clear()
        self.run_circle_thread = Thread(target=self._run_one_cycle, args=(settings,))
        self.run_circle_thread.start()
        return self.run_circle_thread

    def run_loop(self):
        if self.run_loop_thread is not None:
            return None
        self.stop_loop_event.clear()
        self.run_loop_thread = Thread(target=self._run_loop)
        self.run_loop_thread.start()
        return self.run_loop_thread

    def stop_circle_running(self):
        if self.run_circle_thread is not None:
            self.stop_circle_event.set()
            for account_id in self.circle_account_man.get_working_account_id_list():
                account = self.circle_account_man.get_account(account_id)
                if account is None:
                    continue
                account.usersettings_stop_channel.put(None)
            self.run_circle_thread.join()
            self.run_circle_thread = None

    def stop_loop_running(self):
        if self.run_loop_thread is not None:
            self.stop_loop_event.set()
            for account_id in self.loop_account_man.get_working_account_id_list():
                account = self.loop_account_man.get_account(account_id)
                if account is None:
                    continue
                account.usersettings_stop_channel.put(None)
            self.run_loop_thread.join()
            self.run_loop_thread = None

    def remove_account(self, account_id):
        self.circle_account_man.remove_account(account_id)
        self.loop_account_man.remove_account(account_id)
        shutil.rmtree(
            self.file_man.format_usersettings_save_dir(account_id), ignore_errors=True
        )
