import pickle
import os
import time
from queue import Queue
import threading
from time import perf_counter
import concurrent.futures

from ...shop import Shop

from ... import (
    Config,
    Repository,
    Library,
    User,
    Task,
    HeritageMan,
)
from ..message import IOLogger, Logger
from ...utils.evolution import PlantEvolution
from ...utils.common import second2str
from .auto_challenge import Challenge4Level
from .manager import (
    AutoSynthesisMan,
    FubenMan,
    TerritoryMan,
    DailyMan,
    GardenMan,
    ServerBattleMan,
    ArenaMan,
    CommandMan,
    SkillStoneMan,
)
from .open_fuben import OpenFubenMan
from .compound import AutoCompoundMan
from . import PipelineMan
from ...shop import PurchaseItem


class UserSettings:
    def __init__(
        self,
        cfg: Config,
        repo: Repository,
        lib: Library,
        user: User,
        logger: Logger,
        save_dir=None,
    ):
        self.cfg = cfg
        self.friendMan = user.friendMan
        self.repo = repo
        self.lib = lib
        self.user = user
        self.save_dir = save_dir
        self.logger = logger
        self.stop_channel = Queue()
        self.start_thread = None

        self.challenge4Level = Challenge4Level(cfg, user, repo, lib, logger=self.logger)
        self.challenge4Level_enabled = True
        self.shop_enabled = False

        self.shop = Shop(cfg)
        self.shop_auto_buy_dict: dict[int, PurchaseItem] = dict()
        self.plant_evolution = PlantEvolution(cfg, repo, lib)
        self.task = Task(cfg)
        self.enable_list = [False for _ in range(4)]
        self.task_enabled = False
        self.garden_cave_list = []
        self.rest_time = 0
        self.arena_enabled = False
        self.arena_man = ArenaMan(cfg, self.logger)
        self.auto_synthesis_man = AutoSynthesisMan(cfg, lib, repo)
        self.heritage_man = HeritageMan(self.cfg, self.lib)
        self.serverbattle_man = ServerBattleMan(self.cfg, logger=self.logger)
        self.serverbattle_enabled = False
        self.auto_compound_man = AutoCompoundMan(cfg, lib, repo, self.logger)
        self.fuben_man = FubenMan(cfg, repo, lib, self.logger)
        self.fuben_enabled = False
        self.territory_man = TerritoryMan(cfg, repo, self.logger)
        self.territory_enabled = False
        self.record_repository_tool_dict = {}
        self.record_ignore_tool_id_set = set()
        self.daily_enabled = False
        self.daily_man = DailyMan(cfg, self.logger)
        self.garden_man = GardenMan(cfg, repo, lib, self.logger)
        self.garden_enabled = False
        self.exit_if_nothing_todo = False
        self.arena_challenge_mode = 0
        self.daily_settings = [True, True, True, True]
        self.pipeline_man = PipelineMan(cfg, lib, repo, user, self.logger)
        self.command_man = CommandMan(cfg, self.logger)
        self.command_enabled = False
        self.open_fuben_man = OpenFubenMan(cfg, repo, lib, self.logger)
        self.skill_stone_man = SkillStoneMan(cfg, lib, self.logger)

    def _start(self, stop_channel: Queue, close_signal=None, finish_signal=None):
        self.repo.refresh_repository(self.logger)
        while stop_channel.qsize() == 0:
            need_continue = False
            enter_time = perf_counter()
            # if self.shop_enabled:
            #     try:
            #         shop_info = self.shop.buy_list(list(self.shop_auto_buy_set), 1)
            #         for good_p_id, amount in shop_info:
            #             self.logger.log(
            #                 f"购买了{amount}个{self.lib.get_tool_by_id(good_p_id).name}"
            #             )
            #         self.logger.log("购买完成")
            #     except Exception as e:
            #         self.logger.log(f"购买失败，异常种类:{type(e).__name__}。跳过购买")
            #     if stop_channel.qsize() > 0:
            #         break
            if self.daily_enabled:
                try:
                    if self.daily_settings[0]:
                        self.daily_man.daily_sign()
                    if self.daily_settings[1]:
                        self.daily_man.vip_reward_acquire()
                    if self.daily_settings[2]:
                        self.daily_man.daily_accumulated_reward_acquire()
                    if self.daily_settings[3]:
                        self.daily_man.arena_reward_acquire(self.lib)
                    self.logger.log("每日日常完成")
                except Exception as e:
                    self.logger.log(f"每日日常失败，异常种类:{type(e).__name__}。跳过每日日常")
                if stop_channel.qsize() > 0:
                    break
            if self.task_enabled:
                try:
                    self.task.refresh_task()
                    for i, enable in enumerate(self.enable_list):
                        if not enable:
                            continue
                        tasks = self.task.task_list[i]
                        for task in tasks:
                            if task.state == 1:
                                result = self.task.claim_reward(task, self.lib)
                                self.logger.log(result['result'])
                except Exception as e:
                    self.logger.log(f"领取任务奖励失败，异常种类:{type(e).__name__}。跳过领取任务奖励")
                if stop_channel.qsize() > 0:
                    break
            if self.garden_enabled:
                self.garden_man.check_data(False)
                try:
                    if self.garden_man.auto_challenge(stop_channel):
                        need_continue = True
                except Exception as e:
                    self.logger.log(f"自动花园挑战失败，异常种类:{type(e).__name__}。跳过自动花园挑战")
                if stop_channel.qsize() > 0:
                    break
            if self.arena_enabled:
                try:
                    if self.arena_challenge_mode == 0:
                        self.arena_man.auto_challenge(stop_channel)
                    elif self.arena_challenge_mode == 1:
                        while stop_channel.qsize() == 0:
                            result = self.arena_man.challenge_first()
                            self.logger.log(result['result'])
                            if not result['success']:
                                break
                except Exception as e:
                    self.logger.log(f"竞技场挑战失败，异常种类:{type(e).__name__}。跳过竞技场挑战")
                if stop_channel.qsize() > 0:
                    break
            if self.command_enabled:
                try:
                    self.command_man.start(stop_channel)
                except Exception as e:
                    self.logger.log(f"自动指令执行失败，异常种类:{type(e).__name__}。跳过自动指令")
                if stop_channel.qsize() > 0:
                    break
            if self.territory_enabled:
                try:
                    if self.territory_man.can_challenge():
                        self.territory_man.check_data(False)
                        result = self.territory_man.upload_team()
                        self.logger.log(result['result'])
                        self.territory_man.auto_challenge(stop_channel)
                        result = self.territory_man.release_plant(self.user.id)
                        self.logger.log(result['result'])
                except Exception as e:
                    self.logger.log(f"领地挑战失败，异常种类:{type(e).__name__}。跳过领地挑战")
                if stop_channel.qsize() > 0:
                    break
            if self.serverbattle_enabled:
                try:
                    self.serverbattle_man.auto_challenge(stop_channel)
                except Exception as e:
                    self.logger.log(f"跨服挑战失败，异常种类:{type(e).__name__}。跳过跨服挑战")
                if stop_channel.qsize() > 0:
                    break
            if self.fuben_enabled:
                try:
                    while True:
                        if not self.fuben_man.auto_challenge(stop_channel):
                            break
                except Exception as e:
                    self.logger.log(f"自动副本挑战失败，异常种类:{type(e).__name__}。跳过自动副本挑战")
                if stop_channel.qsize() > 0:
                    break
            if self.challenge4Level_enabled:
                try:
                    while True:
                        self.challenge4Level.has_challenged = False
                        if not self.challenge4Level.auto_challenge(stop_channel):
                            finish_signal.emit()
                            return
                        if (
                            not self.challenge4Level.has_challenged
                            or stop_channel.qsize() > 0
                        ):
                            break
                except Exception as e:
                    self.logger.log(f"自动挑战失败，异常种类:{type(e).__name__}。跳过自动挑战")
            if self.exit_if_nothing_todo and not need_continue:
                self.logger.log("没有可以做的事情了，退出用户")
                if close_signal is not None:
                    close_signal.emit()
                if finish_signal is not None:
                    finish_signal.emit()
                return
            self.logger.log("工作完成，等待{}".format(second2str(self.rest_time)))
            if self.rest_time == 0:
                sleep_time = max(0.3 - (perf_counter() - enter_time), 0)
                time.sleep(sleep_time)
            for _ in range(self.rest_time):
                if stop_channel.qsize() > 0:
                    break
                time.sleep(1)
        self.logger.log("停止工作")
        if finish_signal is not None:
            finish_signal.emit()

    def start(self, close_signal, finish_signal):
        if self.start_thread is None or not self.start_thread.is_alive():
            self.start_thread = threading.Thread(
                target=self._start,
                args=(self.stop_channel, close_signal, finish_signal),
            )
            self.start_thread.start()

    def save(self):
        if self.save_dir is None:
            return
        self.challenge4Level.save(self.save_dir)
        save_path = os.path.join(self.save_dir, "usersettings_state")
        with open(save_path, "wb") as f:
            pickle.dump(
                {
                    "challenge4Level_enabled": self.challenge4Level_enabled,
                    "shop_enabled": self.shop_enabled,
                    "shop_auto_buy_dict": self.shop_auto_buy_dict,
                    "garden_cave_list": self.garden_cave_list,
                    "enable_list": self.enable_list,
                    "rest_time": self.rest_time,
                    "arena_enabled": self.arena_enabled,
                    "task_enabled": self.task_enabled,
                    "timeout": self.cfg.timeout,
                    "millsecond_delay": self.cfg.millsecond_delay,
                    "serverbattle_enabled": self.serverbattle_enabled,
                    "record_repository_tool_dict": self.record_repository_tool_dict,
                    "record_ignore_tool_id_set": self.record_ignore_tool_id_set,
                    "fuben_enabled": self.fuben_enabled,
                    "territory_enabled": self.territory_enabled,
                    "daily_enabled": self.daily_enabled,
                    "garden_enabled": self.garden_enabled,
                    "exit_if_nothing_todo": self.exit_if_nothing_todo,
                    "arena_challenge_mode": self.arena_challenge_mode,
                    "daily_settings": self.daily_settings,
                    "command_enabled": self.command_enabled,
                },
                f,
            )
        self.challenge4Level.save(self.save_dir)
        self.plant_evolution.save(self.save_dir)
        self.auto_synthesis_man.save(self.save_dir)
        self.heritage_man.save(self.save_dir)
        self.auto_compound_man.save(self.save_dir)
        self.fuben_man.save(self.save_dir)
        self.territory_man.save(self.save_dir)
        self.garden_man.save(self.save_dir)
        self.pipeline_man.save(self.save_dir)
        self.serverbattle_man.save(self.save_dir)
        self.command_man.save(self.save_dir)
        self.open_fuben_man.save(self.save_dir)

    def export_data(self, save_path=None):
        data = {
            "attrs": {
                "challenge4Level_enabled": self.challenge4Level_enabled,
                "shop_enabled": self.shop_enabled,
                "shop_auto_buy_dict": self.shop_auto_buy_dict,
                "garden_cave_list": self.garden_cave_list,
                "enable_list": self.enable_list,
                "rest_time": self.rest_time,
                "arena_enabled": self.arena_enabled,
                "task_enabled": self.task_enabled,
                "serverbattle_enabled": self.serverbattle_enabled,
                "record_repository_tool_dict": self.record_repository_tool_dict,
                "record_ignore_tool_id_set": self.record_ignore_tool_id_set,
                "fuben_enabled": self.fuben_enabled,
                "territory_enabled": self.territory_enabled,
                "daily_enabled": self.daily_enabled,
                "garden_enabled": self.garden_enabled,
                "exit_if_nothing_todo": self.exit_if_nothing_todo,
                "arena_challenge_mode": self.arena_challenge_mode,
                "daily_settings": self.daily_settings,
                "command_enabled": self.command_enabled,
            },
            "mans": {
                "cfg": self.cfg.save(),
                "challenge4Level": self.challenge4Level.save(),
                "fuben_man": self.fuben_man.save(),
                "territory_man": self.territory_man.save(),
                "garden_man": self.garden_man.save(),
                "serverbattle_man": self.serverbattle_man.save(),
                "command_man": self.command_man.save(),
            },
        }
        data_bin = pickle.dumps(data)
        data_bin = pickle.dumps(
            {
                "data": data_bin,
                "config": self.cfg.config,
            }
        )
        if save_path is not None:
            with open(save_path, "wb") as f:
                f.write(data_bin)
        return data_bin

    def import_data(self, data_bin):
        data = pickle.loads(data_bin)
        if "config" in data:
            data = pickle.loads(data["data"])
        for k, v in data['attrs'].items():
            if hasattr(self, k):
                setattr(self, k, v)
        for k, v in data['mans'].items():
            if hasattr(self, k):
                getattr(self, k).load(v)

    def load(self):
        if self.save_dir is None:
            return
        load_path = os.path.join(self.save_dir, "usersettings_state")
        if os.path.exists(load_path):
            with open(load_path, "rb") as f:
                d = pickle.load(f)
            for k, v in d.items():
                if hasattr(self, k):
                    setattr(self, k, v)
            if "timeout" in d:
                self.cfg.timeout = d["timeout"]
            if "millsecond_delay" in d:
                self.cfg.millsecond_delay = d["millsecond_delay"]
        self.challenge4Level.load(self.save_dir)
        self.plant_evolution.load(self.save_dir)
        self.auto_synthesis_man.load(self.save_dir)
        self.heritage_man.load(self.save_dir)
        self.auto_compound_man.load(self.save_dir)
        self.fuben_man.load(self.save_dir)
        self.territory_man.load(self.save_dir)
        self.garden_man.load(self.save_dir)
        self.pipeline_man.load(self.save_dir)
        self.serverbattle_man.load(self.save_dir)
        self.command_man.load(self.save_dir)
        self.open_fuben_man.load(self.save_dir)


# class GetUsersettings(threading.Thread):
#     def __init__(self, cfg: Config, root_dir, finish_trigger):
#         super().__init__()
#         self.cfg = cfg
#         self.root_dir = root_dir
#         self.finish_trigger = finish_trigger

#     def run(self):
#         usersettings = get_usersettings(self.cfg, self.root_dir)
#         self.finish_trigger.emit(usersettings)


def get_usersettings(cfg, user_dir, extra_logger=None, need_logs=True) -> UserSettings:
    config = Config(cfg)
    if need_logs:
        assert isinstance(user_dir, str)
        # data_dir = os.path.join(
        #     root_dir,
        #     f"data/user/{config.username}/{config.region}/{config.host}",
        # )
        log_dir = os.path.join(user_dir, "logs")
        os.makedirs(log_dir, exist_ok=True)
        logger = IOLogger(log_dir, extra_logger=extra_logger)
    else:
        logger = IOLogger(user_dir, extra_logger=extra_logger)

    with concurrent.futures.ThreadPoolExecutor(max_workers=3) as executor:
        futures = []
        futures.append(executor.submit(User, config))
        futures.append(executor.submit(Library, config))
        futures.append(executor.submit(Repository, config))

        concurrent.futures.wait(futures, return_when=concurrent.futures.ALL_COMPLETED)

        user: User = futures[0].result()
        lib: Library = futures[1].result()
        repo: Repository = futures[2].result()

    usersettings = UserSettings(
        config,
        repo,
        lib,
        user,
        logger.get_logger(),
        save_dir=None,
    )
    return usersettings
