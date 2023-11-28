import pickle
import os
import time
from queue import Queue
import threading

from ...shop import Shop

from ... import (
    Config,
    Repository,
    Library,
    User,
    Task,
    ArenaMan,
    HeritageMan,
    ServerbattleMan,
)
from ..message import IOLogger
from ...utils.evolution import PlantEvolution
from ...utils.common import second2str
from .auto_challenge import Challenge4Level
from .manager import (
    AutoSynthesisMan,
    FubenMan,
    TerritoryMan,
    DailyMan,
    GardenMan,
)
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
        logger: IOLogger,
        save_dir=None,
    ):
        self.cfg = cfg
        self.friendMan = user.friendMan
        self.repo = repo
        self.lib = lib
        self.user = user
        self.save_dir = save_dir
        self.io_logger = logger
        self.logger = logger.new_logger()
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
        self.auto_use_item_enabled = False
        self.auto_use_item_list = []
        self.garden_cave_list = []
        self.rest_time = 0
        self.arena_enabled = False
        self.arena_man = ArenaMan(cfg)
        self.auto_synthesis_man = AutoSynthesisMan(cfg, lib, repo)
        self.heritage_man = HeritageMan(self.cfg, self.lib)
        self.serverbattle_man = ServerbattleMan(self.cfg)
        self.serverbattle_enabled = False
        self.auto_compound_man = AutoCompoundMan(cfg, lib, repo, self.logger)
        self.fuben_man = FubenMan(cfg, repo, self.logger)
        self.fuben_enabled = False
        self.territory_man = TerritoryMan(cfg, repo, self.logger)
        self.territory_enabled = False
        self.record_repository_tool_dict = {}
        self.record_ignore_tool_id_set = set()
        self.daily_enabled = False
        self.daily_man = DailyMan(cfg, self.logger)
        self.garden_man = GardenMan(cfg, repo, lib, self.logger)
        self.garden_enabled = False
        
        self.pipeline_man = PipelineMan(cfg, lib, repo, user, self.logger)

    def _start(self, stop_channel: Queue):
        self.repo.refresh_repository(self.logger)
        while stop_channel.qsize() == 0:
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
            if self.auto_use_item_enabled:
                try:
                    self.auto_use_item(stop_channel)
                except Exception as e:
                    self.logger.log(f"自动使用道具失败，异常种类:{type(e).__name__}。跳过自动使用道具")
                if stop_channel.qsize() > 0:
                    break
            if self.daily_enabled:
                try:
                    self.daily_man.daily_sign()
                    self.daily_man.vip_reward_acquire()
                    self.logger.log("每日签到完成")
                except Exception as e:
                    self.logger.log(f"每日签到失败，异常种类:{type(e).__name__}。跳过每日签到")
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
                    self.garden_man.auto_challenge(stop_channel)
                except Exception as e:
                    self.logger.log(f"自动花园挑战失败，异常种类:{type(e).__name__}。跳过自动花园挑战")
                if stop_channel.qsize() > 0:
                    break
            if self.territory_enabled:
                self.territory_man.check_data(False)
                try:
                    result = self.territory_man.upload_team()
                    self.logger.log(result['result'])
                except Exception as e:
                    self.logger.log(f"上领地植物失败，异常种类:{type(e).__name__}。跳过领地挑战")
                else:
                    try:
                        self.territory_man.auto_challenge(stop_channel)
                    except Exception as e:
                        self.logger.log(f"自动领地挑战失败，异常种类:{type(e).__name__}。跳过自动领地挑战")
                try:
                    result = self.territory_man.release_plant(self.user.id)
                    self.logger.log(result['result'])
                except Exception as e:
                    self.logger.log(f"领地释放植物失败，异常种类:{type(e).__name__}。")
                if stop_channel.qsize() > 0:
                    break
            if self.serverbattle_enabled:
                try:
                    while True:
                        result = self.serverbattle_man.challenge()
                        self.logger.log(result["result"])
                        if not result["success"]:
                            break
                        if stop_channel.qsize() > 0:
                            break
                except Exception as e:
                    self.logger.log(f"跨服挑战失败，异常种类:{type(e).__name__}。跳过跨服挑战")
                    break
                if stop_channel.qsize() > 0:
                    break
            if self.fuben_enabled:
                try:
                    self.fuben_man.auto_challenge(stop_channel)
                except Exception as e:
                    self.logger.log(f"自动副本挑战失败，异常种类:{type(e).__name__}。跳过自动副本挑战")
                if stop_channel.qsize() > 0:
                    break
            if self.arena_enabled:
                try:
                    self.arena_man.refresh_arena()
                    while self.arena_man.challenge_num > 0:
                        result = self.arena_man.challenge_first()
                        if result['success']:
                            result['result'] += ".还剩{}次挑战机会".format(
                                self.arena_man.challenge_num - 1
                            )
                        self.logger.log(result['result'])
                        if not result['success']:
                            break
                        self.arena_man.refresh_arena()
                        if stop_channel.qsize() > 0:
                            break
                except Exception as e:
                    self.logger.log(f"竞技场挑战失败，异常种类:{type(e).__name__}。跳过竞技场挑战")
                if stop_channel.qsize() > 0:
                    break
            if self.challenge4Level_enabled:
                try:
                    self.challenge4Level.auto_challenge(stop_channel)
                except Exception as e:
                    self.logger.log(f"自动挑战失败，异常种类:{type(e).__name__}。跳过自动挑战")
            self.logger.log("工作完成，等待{}".format(second2str(self.rest_time)))
            if self.rest_time == 0:
                time.sleep(0.1)
            for _ in range(self.rest_time):
                if stop_channel.qsize() > 0:
                    break
                time.sleep(1)

    def start(self):
        if self.start_thread is None or not self.start_thread.is_alive():
            self.start_thread = threading.Thread(
                target=self._start,
                args=(self.stop_channel, ),
            )
            self.start_thread.start()

    def auto_use_item(self, stop_channel: Queue):
        self.repo.refresh_repository(logger=self.logger)
        for tool_id in self.auto_use_item_list:
            if stop_channel.qsize() > 0:
                break
            repo_tool = self.repo.get_tool(tool_id)
            if repo_tool is None:
                continue
            tool_type = self.lib.get_tool_by_id(tool_id).type
            amount = repo_tool['amount']
            if tool_type == 3:
                while amount > 0:
                    result = self.repo.open_box(tool_id, amount, self.lib)
                    self.logger.log(result['result'])
                    if not result["success"]:
                        break
                    amount -= result["open_amount"]
            else:
                result = self.repo.use_item(tool_id, amount, self.lib)
                self.logger.log(result['result'])

    def save(self):
        self.challenge4Level.save(self.save_dir)
        save_path = os.path.join(self.save_dir, "usersettings_state")
        with open(save_path, "wb") as f:
            pickle.dump(
                {
                    "challenge4Level_enabled": self.challenge4Level_enabled,
                    "shop_enabled": self.shop_enabled,
                    "shop_auto_buy_dict": self.shop_auto_buy_dict,
                    "auto_use_item_list": self.auto_use_item_list,
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
                },
                f,
            )
        self.plant_evolution.save(self.save_dir)
        self.auto_synthesis_man.save(self.save_dir)
        self.heritage_man.save(self.save_dir)
        self.auto_compound_man.save(self.save_dir)
        self.fuben_man.save(self.save_dir)
        self.territory_man.save(self.save_dir)
        self.garden_man.save(self.save_dir)
        self.pipeline_man.save(self.save_dir)

    def load(self):
        self.challenge4Level.load(self.save_dir)
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
        self.plant_evolution.load(self.save_dir)
        self.auto_synthesis_man.load(self.save_dir)
        self.heritage_man.load(self.save_dir)
        self.auto_compound_man.load(self.save_dir)
        self.fuben_man.load(self.save_dir)
        self.territory_man.load(self.save_dir)
        self.garden_man.load(self.save_dir)
        self.pipeline_man.load(self.save_dir)
