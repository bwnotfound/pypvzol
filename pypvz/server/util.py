# from multiprocessing import Process
# import multiprocessing
# import dill


# def _run(in_queue, out_queue):
#     while True:
#         data = in_queue.get()
#         if data is None:
#             break
#         func, args, kwargs = data
#         out_queue.put(dill.dumps(func(*args, **kwargs)))


# class RunProcess:
#     def __init__(self):
#         manager = multiprocessing.Manager()
#         self.in_queue = manager.Queue(maxsize=32)
#         self.out_queue = manager.Queue()
#         self.is_running = False

#     def run_block(self, func, *args, **kwargs):
#         self.in_queue.put((func, args, kwargs))
#         return dill.loads(self.out_queue.get())

#     def close(self):
#         self.in_queue.put(None)
#         if hasattr(self, "p"):
#             self.p.join()
#         self.is_running = False
#         del self.p

#     def run(self):
#         if self.is_running:
#             raise RuntimeError("Process already running")
#         self.is_running = True

#         p = Process(target=_run, args=(self.in_queue, self.out_queue))
#         p.start()
#         self.p = p


from queue import Queue
from threading import Thread


def _run(in_queue, out_queue):
    while True:
        data = in_queue.get()
        if data is None:
            break
        func, args, kwargs = data
        out_queue.put(func(*args, **kwargs))


class RunProcess:
    def __init__(self):
        self.in_queue = Queue(maxsize=32)
        self.out_queue = Queue()
        self.is_running = False

    def run_block(self, func, *args, **kwargs):
        self.in_queue.put((func, args, kwargs))
        return self.out_queue.get()

    def close(self):
        self.in_queue.put(None)
        if hasattr(self, "p"):
            self.t.join()
        self.is_running = False
        del self.t

    def run(self):
        if self.is_running:
            raise RuntimeError("Thread already running")
        self.is_running = True

        t = Thread(target=_run, args=(self.in_queue, self.out_queue))
        t.start()
        self.t = t
