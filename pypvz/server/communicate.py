from threading import Thread, Event
import logging
import time

from py4j.java_gateway import JavaGateway, CallbackServerParameters
from py4j.java_collections import MapConverter, ListConverter

from .run_assistant import AssistantManager
from .assistant_user import AssistantAccount


class Communicator:
    def __init__(
        self,
        assistant_man: AssistantManager,
        java_instance: JavaGateway,
        logger: logging.Logger,
    ):
        self.assistant_man = assistant_man
        self.java_instance = java_instance
        self.logger = logger
        java_instance.entry_point.setPyCommunicator(self)
        self.map_converter = MapConverter()
        self.list_converter = ListConverter()
        java_instance.entry_point.initAfterConnection()
        self.assistant_man.loop_account_man.register_finish_callback(
            self.on_loop_account_finish
        )
        self.assistant_man.circle_account_man.register_finish_callback(
            self.on_circle_account_finish
        )
    
    def on_loop_account_finish(self, account_id):
        self.java_instance.entry_point.onLoopAccountFinish(account_id)
        
    def on_circle_account_finish(self, account_id):
        self.java_instance.entry_point.onCircleAccountFinish(account_id)

    def map_convert(self, data):
        return self.map_converter.convert(
            data, self.java_instance.entry_point._gateway_client
        )

    def list_convert(self, data):
        return self.list_converter.convert(
            data, self.java_instance.entry_point._gateway_client
        )

    def test(self):
        msg = "Hello from Python!"
        print(msg)
        return msg

    def add_circle_account(self, id, data):
        assert isinstance(data, bytes)
        account = AssistantAccount(id, data)
        self.assistant_man.circle_account_man.add_account(account)

    def add_loop_account(self, id, data):
        assert isinstance(data, bytes)
        account = AssistantAccount(id, data)
        self.assistant_man.loop_account_man.add_account(account)

    def get_account_extra_data(self, data):
        assert isinstance(data, bytes)
        result = self.assistant_man.get_user_extra_data(data)
        if result['code'] == 0:
            result['result']['gameName'] = result['result'].pop('name')
            result['result'] = self.map_convert(result['result'])
        result = self.map_convert(result)
        return result

    def remove_circle_account(self, account_id):
        code = self.assistant_man.circle_account_man.remove_account(account_id)
        if code == 0:
            return self.map_convert(
                {
                    "code": 0,
                    "message": "账号删除成功",
                }
            )
        if code == 1 or code == 2:
            return self.map_convert(
                {
                    "code": code,
                    "message": "账号不存在",
                }
            )

    def remove_loop_account(self, account_id):
        code = self.assistant_man.loop_account_man.remove_account(account_id)
        if code == 0:
            return self.map_convert(
                {
                    "code": 0,
                    "message": "账号删除成功",
                }
            )
        if code == 1 or code == 2:
            return self.map_convert(
                {
                    "code": code,
                    "message": "账号不存在",
                }
            )

    def reload_account_list_to_circle(self, account_map_list: list):
        account_list = list(
            map(
                lambda x: AssistantAccount(x.get("id"), x.get("data")), account_map_list
            )
        )
        code = self.assistant_man.circle_account_man.load_account_list(account_list)
        if code == 0:
            return self.map_convert(
                {
                    "code": 0,
                    "message": "账号列表加载成功",
                }
            )

    def reload_account_list_to_loop(self, account_map_list: list):
        account_list = list(
            map(
                lambda x: AssistantAccount(x.get("id"), x.get("data")), account_map_list
            )
        )
        code = self.assistant_man.loop_account_man.load_account_list(account_list)
        if code == 0:
            return self.map_convert(
                {
                    "code": 0,
                    "message": "账号列表加载成功",
                }
            )

    def get_circle_working_account_id_list(self):
        working_account_list = (
            self.assistant_man.circle_account_man.get_working_account_id_list()
        )
        return self.map_convert(
            {
                "code": 0,
                "message": "",
                "result": self.list_convert(working_account_list),
            }
        )

    def get_loop_working_account_id_list(self):
        working_account_list = (
            self.assistant_man.loop_account_man.get_working_account_id_list()
        )
        return self.map_convert(
            {
                "code": 0,
                "message": "",
                "result": self.list_convert(working_account_list),
            }
        )

    def get_circle_running_account_id_list(self):
        running_account_list = (
            self.assistant_man.circle_account_man.get_running_account_id_list()
        )
        return self.map_convert(
            {
                "code": 0,
                "message": "",
                "result": self.list_convert(running_account_list),
            }
        )

    def get_loop_running_account_id_list(self):
        running_account_list = (
            self.assistant_man.loop_account_man.get_running_account_id_list()
        )
        return self.map_convert(
            {
                "code": 0,
                "message": "",
                "result": self.list_convert(running_account_list),
            }
        )

    def get_circle_waiting_account_id_list(self):
        waiting_account_list = (
            self.assistant_man.circle_account_man.get_waiting_account_id_list()
        )
        return self.map_convert(
            {
                "code": 0,
                "message": "",
                "result": self.list_convert(waiting_account_list),
            }
        )

    def get_loop_waiting_account_id_list(self):
        waiting_account_list = (
            self.assistant_man.loop_account_man.get_waiting_account_id_list()
        )
        return self.map_convert(
            {
                "code": 0,
                "message": "",
                "result": self.list_convert(waiting_account_list),
            }
        )

    def circle_is_running(self):
        return self.map_convert(
            {
                "code": 0,
                "message": "",
                "result": self.assistant_man.circle_account_man.is_running(),
            }
        )

    def loop_is_running(self):
        return self.map_convert(
            {
                "code": 0,
                "message": "",
                "result": self.assistant_man.loop_account_man.is_running(),
            }
        )

    def stop_circle_running(self):
        self.assistant_man.stop_circle_running()
        return self.map_convert(
            {
                "code": 0,
                "message": "",
            }
        )

    def stop_loop_running(self):
        self.assistant_man.stop_loop_running()
        return self.map_convert(
            {
                "code": 0,
                "message": "",
            }
        )

    def start_one_circle(self):
        thread = self.assistant_man.run_one_cycle()
        if thread is None:
            return self.map_convert(
                {
                    "code": 1,
                    "message": "已经在运行",
                }
            )
        return self.map_convert(
            {
                "code": 0,
                "message": "成功开始循环",
            }
        )

    def start_loop(self):
        thread = self.assistant_man.run_loop()
        if thread is None:
            return self.map_convert(
                {
                    "code": 1,
                    "message": "已经在运行",
                }
            )
        return self.map_convert(
            {
                "code": 0,
                "message": "成功开始循环",
            }
        )

    def load_account_to_circle_waiting_list(self):
        if self.assistant_man.circle_account_man.is_running():
            return self.map_convert(
                {
                    "code": 1,
                    "message": "已经在运行",
                }
            )
        self.assistant_man.circle_account_man.load_working_account()
        return self.map_convert(
            {
                "code": 0,
                "message": "成功加入等待队列",
            }
        )

    def load_account_to_loop_waiting_list(self):
        if self.assistant_man.loop_account_man.is_running():
            return self.map_convert(
                {
                    "code": 1,
                    "message": "已经在运行",
                }
            )
        self.assistant_man.loop_account_man.load_working_account()
        return self.map_convert(
            {
                "code": 0,
                "message": "成功加入等待队列",
            }
        )

    def clear_circle_working_account(self):
        self.assistant_man.circle_account_man.clear_working_account()
        return self.map_convert(
            {
                "code": 0,
                "message": "成功清空等待队列",
            }
        )

    def clear_loop_working_account(self):
        self.assistant_man.loop_account_man.clear_working_account()
        return self.map_convert(
            {
                "code": 0,
                "message": "成功清空等待队列",
            }
        )
        
    class Java:
        implements = ["com.bwnotfound.pvzol_server.pyassistant.python.PyCommunicator"]


class CommunicatorThread(Thread):
    def __init__(self, assistant_man, java_instance, logger, stop_event: Event):
        super().__init__()
        self.communicator = Communicator(assistant_man, java_instance, logger)
        self.stop_event = stop_event

    def run(self):
        while not self.stop_event.is_set():
            time.sleep(0.1)


_communicator_thread = None
_stop_event = Event()


def start_communicator(assistant_man, logger):
    global _communicator_thread
    if _communicator_thread is None:
        java_instance = JavaGateway(
            callback_server_parameters=CallbackServerParameters()
        )
        _stop_event.clear()
        _communicator_thread = CommunicatorThread(
            assistant_man, java_instance, logger, _stop_event
        )
        _communicator_thread.start()
        return _communicator_thread
    else:
        logging.warning("Communicator already started, please shutdown it first.")
        return None


def terminate_communicator():
    global _communicator_thread
    if _communicator_thread is None:
        logging.warning("Communicator not started, please start it first.")
        return False
    else:
        _stop_event.set()
        _communicator_thread.join()
        _communicator_thread = None
        return True
