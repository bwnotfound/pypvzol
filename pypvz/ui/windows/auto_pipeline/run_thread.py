import threading
from queue import Queue

from ...user.auto_pipeline import PipelineScheme


class RunSchemeThread(threading.Thread):
    def __init__(
        self,
        scheme: PipelineScheme,
        stop_queue: Queue,
        finish_signal,
        rest_event: threading.Event,
        stop_after_finish,
    ):
        super().__init__()
        self.scheme = scheme
        self.stop_queue = stop_queue
        self.finish_signal = finish_signal
        self.rest_event = rest_event
        self.stop_after_finish = stop_after_finish

    def run(self):
        try:
            self.scheme.run(self.stop_queue, stop_after_finish=self.stop_after_finish)
        finally:
            self.finish_signal.emit()
            self.rest_event.set()
