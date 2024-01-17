from threading import Thread, Event
import logging
import time

from py4j.java_gateway import JavaGateway, CallbackServerParameters

from .run_assistant import AssistantManager


class Communicator:
    def __init__(
        self,
        assistant_man: AssistantManager,
        java_instance: JavaGateway,
        logger: logging.Logger,
    ):
        self.assistant_man = assistant_man
        java_instance = java_instance
        self.logger = logger
        java_instance.entry_point.setPyCommunicator(self)

    def test(self):
        msg = "Hello from Python!"
        print(msg)
        return msg

    def add_user(self, data):
        assert isinstance(data, bytes)
        self.assistant_man.add_user(data)
        
    def get_user_extra_data(self, data):
        assert isinstance(data, bytes)
        result = self.assistant_man.get_user_extra_data(data)
        result['gameName'] = result.pop('name')
        return result
        
    class Java:
        implements = ["com.bwnotfound.pvzol_server.pyassistant.PyCommunicator"]


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
        return True
    else:
        logging.warning("Communicator already started, please shutdown it first.")
        return False


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
