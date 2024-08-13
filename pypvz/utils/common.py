import math
from threading import Thread, Event
import concurrent.futures

from ..repository import Plant
from .. import Library, Repository
from ..library import attribute2plant_attribute

def format_number(t):
    if isinstance(t, str):
        t = int(t)
    assert isinstance(t, int)
    if t < 1e4:
        result = str(t)
    elif t < 1e8 and t >= 1e4:
        result = "{:.2f}万".format(t / 1e4)
    elif t >= 1e8 and t < 1e12:
        result = "{:.2f}亿".format(t / 1e8)
    elif t >= 1e12:
        t = t / 1e8
        t_exponent = int(math.log10(t))
        t_mantissa = t / math.pow(10, t_exponent)
        result = "{:.2f}x10^{}亿".format(t_mantissa, t_exponent)
    else:
        raise ValueError('t({}) must be positive'.format(t))
    return result


def second2str(t):
    result = "{}秒".format(t % 60)
    t /= 60
    if t == 0:
        return result
    result = "{}分".format(int(t % 60)) + result
    t /= 60
    if t == 0:
        return result
    result = "{}小时".format(int(t % 24)) + result
    return result


def format_plant_info(
    plant: Plant,
    lib: Library,
    repo: Repository = None,
    grade=True,
    quality=True,
    normal_skill=False,
    spec_skill=False,
    chosen_attribute=None,
    show_normal_attribute=False,
    attribute_list=[],
    need_tab=False,
):
    tab = "    " if need_tab else ""
    sep = "\n{}".format(tab)
    if repo is not None:
        if isinstance(plant, str):
            plant = int(plant)
        if isinstance(plant, int):
            plant = repo.get_plant(plant)
    if plant is None:
        return ""
    assert isinstance(plant, Plant)
    msg = "{}".format(plant.name(lib))
    if grade:
        msg += "({})".format(plant.grade)
    if quality:
        msg += "[{}]".format(plant.quality_str)

    if normal_skill:
        for skill_id in plant.skill_id_list:
            skill = lib.get_skill(skill_id)
            msg += "{}{}({}级)".format(sep, skill["name"], skill["grade"])

    if spec_skill:
        if plant.special_skill_id is not None:
            spec_skill = lib.get_spec_skill(plant.special_skill_id)
            msg += "{}专属:{}({}级)".format(
                (" " if not normal_skill else sep),
                spec_skill["name"],
                spec_skill['grade'],
            )

    if chosen_attribute is not None:
        msg += "-{}:{}".format(
            chosen_attribute.replace("特", ""),
            format_number(
                getattr(
                    plant,
                    attribute2plant_attribute[chosen_attribute],
                )
            ),
        )
    if show_normal_attribute:
        attribute_list = [
            "HP",
            "攻击",
            "命中",
            "闪避",
            "穿透",
            "护甲",
            "速度",
        ]
    for attr_name in attribute_list:
        msg += "\n{}{}:{}".format(
            tab,
            attr_name.replace("特", ""),
            format_number(getattr(plant, attribute2plant_attribute[attr_name])),
        )

    return msg


def signal_block_emit(refresh_signal, *args):
    if refresh_signal is None:
        return
    event = Event()
    refresh_signal.emit(*args, event)
    event.wait()


class CommonAsyncThread(Thread):
    def __init__(
        self,
        run_func,
        func_args: list,
        msg,
        repo: Repository,
        logger,
        interrupt_event: Event,
        rest_event: Event,
        finish_signal=None,
        refresh_signal=None,
        error_channel: list = None,
        pool_size=3,
        retry_when_failed=False,
        loop_refresh=True,
    ):
        super().__init__()
        self.func_args = func_args
        self.repo = repo
        self.logger = logger
        self.run_func = self.wrap_run_func(run_func)
        self.msg = msg
        self.finish_signal = finish_signal
        self.interrupt_event = interrupt_event
        self.refresh_signal = refresh_signal
        self.rest_event = rest_event
        self.pool_size = pool_size
        self.retry_when_failed = retry_when_failed
        self.loop_refresh = loop_refresh
        self.error_channel = error_channel

    def wrap_run_func(self, run_func):
        def _run_func(*args, **kwargs):
            result = run_func(*args, **kwargs)
            if self.refresh_signal is not None:
                signal_block_emit(self.refresh_signal)
            return result

        return _run_func

    def _run(self):
        func_args_index_set = set(range(len(self.func_args)))
        while not self.interrupt_event.is_set() and len(func_args_index_set) > 0:
            func_args_index_list = list(func_args_index_set)
            need_unpack = isinstance(
                self.func_args[func_args_index_list[0]], (list, tuple)
            )
            if need_unpack:
                futures = [
                    self.pool.submit(self.run_func, *self.func_args[func_args_index])
                    for func_args_index in func_args_index_list
                ]
            else:
                futures = [
                    self.pool.submit(self.run_func, self.func_args[func_args_index])
                    for func_args_index in func_args_index_list
                ]
            for i, result in enumerate(futures):
                if self.interrupt_event.is_set():
                    break
                try:
                    success = True
                    ret = result.result()
                    if isinstance(ret, dict):
                        if "success" in ret:
                            success = ret["success"]
                        elif "result" in ret:
                            success = ret["result"]
                        if not isinstance(success, bool):
                            success = True
                    if isinstance(ret, bool):
                        success = ret
                    if success:
                        func_args_index_set.remove(func_args_index_list[i])
                except Exception as e:
                    self.logger.log("{}: 出现异常：{}".format(self.msg, str(e)))
                    if not self.retry_when_failed and self.error_channel is not None:
                        self.error_channel.append(
                            "{}: 出现异常：{}".format(self.msg, str(e))
                        )
            if self.loop_refresh:
                self.repo.refresh_repository()
            if self.refresh_signal is not None:
                signal_block_emit(self.refresh_signal)
            if len(func_args_index_set) == 0:
                break
            if not self.retry_when_failed:
                break

    def run(self):
        try:
            self.pool = concurrent.futures.ThreadPoolExecutor(
                max_workers=self.pool_size
            )
            self._run()
        finally:
            self.pool.shutdown()
            if self.finish_signal is not None:
                self.finish_signal.emit()
            self.rest_event.set()


class WaitEventThread(Thread):
    def __init__(self, event, signal):
        super().__init__()
        self.event = event
        self.signal = signal

    def run(self):
        self.event.wait()
        self.signal.emit()
