from threading import Thread, Event
import logging

from py4j.java_gateway import JavaGateway

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


class CommunicatorThread(Thread):
    def __init__(self, assistant_man, java_instance, logger, stop_event: Event):
        self.communicator = Communicator(assistant_man, java_instance, logger)
        self.stop_event = stop_event

    def run(self):
        pass


_communicator_thread = None
_stop_event = Event()


def start_communicator(assistant_man, logger):
    global _communicator_thread
    if _communicator_thread is None:
        java_instance = JavaGateway()
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
