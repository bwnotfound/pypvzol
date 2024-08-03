import pickle
from queue import Queue
import os
from threading import Event
from time import sleep
from ... import (
    Config,
    Repository,
    Library,
    User,
)
from ..message import Logger
from ... import UpgradeMan
from .auto_challenge import Challenge4Level
from ...shop import PurchaseItem
from .compound import AutoCompoundMan
from ...upgrade import quality_name_list
from ...repository import Plant
from ...utils.evolution import PlantEvolution


class Pipeline:
    def __init__(self, name):
        self.name = name

    def run(self):
        pass

    def has_setting_window(self):
        return False

    def has_setting_widget(self):
        return False

    def setting_window(self, parent=None):
        return None

    def setting_widget(self, parent=None):
        return None

    def check_requirements(self):
        return []

    def serialize(self):
        return {}

    def deserialize(self, d):
        for k, v in d.items():
            if hasattr(self, k):
                try:
                    setattr(self, k, v)
                except:
                    pass


class SkipPipeline(Pipeline):
    def __init__(self):
        super().__init__("跳过")

    def run(self, plant_list, stop_channel: Queue):
        return {"success": True, "info": "跳过成功", "result": plant_list}


class Purchase(Pipeline):
    def __init__(self, cfg: Config, lib: Library, repo: Repository, logger: Logger):
        super().__init__("购买植物")
        self.cfg = cfg
        self.lib = lib
        self.repo = repo
        self.logger = logger
        from ...shop import Shop

        self.shop = Shop(cfg)
        self.shop_auto_buy_dict: dict[int, PurchaseItem] = dict()

    def purchase(self, item: PurchaseItem):
        return self.shop.buy(item.good.id, item.amount)

    def run(self, stop_channel: Queue):
        pre_id2plant = self.repo.id2plant
        total_amount = sum([item.amount for item in self.shop_auto_buy_dict.values()])
        if total_amount > self.repo.organism_grid_rest_amount:
            return {
                "success": False,
                "info": "购买失败，原因：植物数量超过上限，需要购买{}个，但仓库只有{}个空位".format(
                    total_amount, self.repo.organism_grid_rest_amount
                ),
            }
        for purchase_item in self.shop_auto_buy_dict.values():
            if stop_channel.qsize() != 0:
                return {
                    "success": False,
                    "info": "用户终止",
                }
            result = self.purchase(purchase_item)

            if not result['success']:
                self.logger.log()
                return {
                    "success": False,
                    "info": "购买失败，原因：{}".format(result['result']),
                }
        self.repo.refresh_repository()
        purchased_plant_list = []
        for purchase_item in self.shop_auto_buy_dict.values():
            if stop_channel.qsize() != 0:
                return {
                    "success": False,
                    "info": "用户终止",
                }
            good = purchase_item.good
            if not good.is_plant:
                continue
            pre_len = len(purchased_plant_list)
            for plant in self.repo.plants:
                if plant.pid == good.p_id and plant.id not in pre_id2plant:
                    purchased_plant_list.append(plant)
            if purchase_item.amount != len(purchased_plant_list) - pre_len:
                return {
                    "success": False,
                    "info": "购买失败，原因：尝试购买{}，预计购买{}个，实际购买{}个".format(
                        self.lib.get_plant_by_id(good.p_id).name,
                        purchase_item.amount,
                        len(purchased_plant_list) - pre_len,
                    ),
                }
        return {
            "success": True,
            "info": "购买成功",
            "result": purchased_plant_list,
        }

    def setting_window(self, parent=None):
        from ..windows import ShopAutoBuySetting

        return ShopAutoBuySetting(
            self.cfg,
            self.lib,
            self.logger,
            self.shop_auto_buy_dict,
            False,
            parent=parent,
        )

    def has_setting_window(self):
        return True

    def serialize(self):
        return {"shop_auto_buy_dict": self.shop_auto_buy_dict}


class OpenBox(Pipeline):
    def __init__(self, cfg: Config, lib: Library, repo: Repository, logger: Logger):
        super().__init__("开魔神箱")
        self.cfg = cfg
        self.lib = lib
        self.repo = repo
        self.logger = logger

        self.amount = 0

        self.box_type_str_list = [
            "魔神箱",
            "幽冥植物包",
            "元老植物包",
            "寒冰植物包",
            "烈焰植物包",
            "HP植物包",
            "攻击植物包",
            "狂魔植物包",
            "无极幽冥龙宝箱",
        ]
        self.box_type_quality_str_list = [
            "魔神",
            "战神",
            "劣质",
            "战神",
            "战神",
            "极品",
            "极品",
            "战神",
            "无极",
        ]
        self.box_type_id_list = [756, 806, 818, 790, 791, 794, 796, 798, 3000]
        self.current_box_type_index = 0

    @property
    def box_id(self):
        return self.box_type_id_list[self.current_box_type_index]

    @property
    def box_quality(self):
        return self.box_type_quality_str_list[self.current_box_type_index]

    @property
    def box_name(self):
        return self.box_type_str_list[self.current_box_type_index]

    def check_requirements(self):
        result = []
        quality_dict = None
        if hasattr(self, "quality_dict_func"):
            quality_dict = self.quality_dict_func()
        if quality_dict is not None:
            moshen_index = quality_name_list.index("魔神")
            amount = 0
            for quality_index, plant_num in quality_dict.items():
                if quality_index < moshen_index:
                    result.append("智能升品方案中有低于魔神的品质，不符合要求")
                    return result
                amount += plant_num
            if amount != self.amount:
                result.append(
                    "复合总共需要{}个植物，但开箱设置的是{}个植物，请改成复合所需要的植物总数量".format(
                        amount, self.amount
                    )
                )
                return result
        tool = self.repo.get_tool(self.box_id)
        if tool is None or tool['amount'] < self.amount:
            result.append(
                "使用{}失败，原因：{}需要{}个，实际有{}个".format(
                    self.box_name,
                    self.box_name,
                    self.amount,
                    (tool['amount'] if tool is not None else 0),
                )
            )
        if len(self.repo.plants) + self.amount > self.repo.organism_grid_amount:
            result.append(
                "使用{}失败，原因：植物数量超过上限，需要开箱{}个，但仓库只有{}个空位".format(
                    self.box_name,
                    self.amount,
                    self.repo.organism_grid_amount - len(self.repo.plants),
                )
            )
        return result

    def register_auto_set_amount(self, func):
        self.auto_set_amount_func = func

    def register_quality_dict_func(self, func: AutoCompoundMan):
        self.quality_dict_func = func

    def auto_set_amount(self):
        msg = "一键设置开箱数不管用啦，自己手动设置吧"
        if hasattr(self, "auto_set_amount_func"):
            if not self.auto_set_amount_func():
                self.logger.log(msg)
        else:
            self.logger.log(msg)

    def run(self, stop_channel: Queue):
        tool = self.repo.get_tool(self.box_id)
        if tool is None:
            return {
                "success": False,
                "info": "使用{}失败，原因：{}不存在".format(
                    self.box_name, self.box_name
                ),
            }
        if tool['amount'] < self.amount:
            return {
                "success": False,
                "info": "使用{}失败，原因：{}需要{}个，实际有{}个".format(
                    self.box_name, self.box_name, self.amount, tool['amount']
                ),
            }
        if len(self.repo.plants) + self.amount > self.repo.organism_grid_amount:
            return {
                "success": False,
                "info": "使用{}失败，原因：植物数量超过上限".format(self.box_name),
            }
        pre_id2plant = self.repo.id2plant
        while True:
            try:
                result = self.repo.use_tool(self.box_id, self.amount, self.lib)
                break
            except Exception as e:
                pre_amount = tool['amount']
                self.repo.refresh_repository()
                current_tool = self.repo.get_tool(self.box_id)
                if current_tool is None:
                    current_amount = 0
                else:
                    current_amount = current_tool['amount']
                if current_amount == pre_amount:
                    self.logger.log(
                        "使用{}异常，异常原因: {}。检测到箱子数量没有变化，重新开箱".format(
                            self.box_name, type(e).__name__
                        )
                    )
                    continue
                else:
                    self.logger.log(
                        "使用{}异常，异常原因: {}。检测到箱子数量变化，判定为开箱成功".format(
                            self.box_name, type(e).__name__
                        )
                    )
                    result = {
                        "success": True,
                    }
                    break
        if not result['success']:
            return {
                "success": False,
                "info": "使用{}失败，原因：{}".format(self.box_name, result['result']),
            }
        self.repo.refresh_repository()
        plant_list = []
        for plant in self.repo.plants:
            if plant.id in pre_id2plant or plant.quality_str != self.box_quality:
                continue
            plant_list.append(plant)
        if self.amount != len(plant_list):
            return {
                "success": False,
                "info": "打开{}失败，原因：预计获得{}个{}，实际获得{}个{}".format(
                    self.box_name,
                    self.amount,
                    self.box_quality,
                    len(plant_list),
                    self.box_quality,
                ),
            }
        return {
            "success": True,
            "info": "使用{}成功".format(self.box_name),
            "result": plant_list,
        }

    def setting_widget(self, parent=None):
        from ..windows.auto_pipeline.setting_panel import OpenBoxWidget

        return OpenBoxWidget(self, parent=parent)

    def has_setting_widget(self):
        return True

    def serialize(self):
        return {
            "amount": self.amount,
            "current_box_type_index": self.current_box_type_index,
        }

    def deserialize(self, d):
        super().deserialize(d)
        if self.current_box_type_index >= len(self.box_type_id_list):
            self.current_box_type_index = 0


class AutoChallenge(Pipeline):
    def __init__(
        self, cfg: Config, lib: Library, repo: Repository, user: User, logger: Logger
    ):
        super().__init__("带级")
        self.cfg = cfg
        self.lib = lib
        self.repo = repo
        self.user = user
        self.logger = logger
        self.challenge4level = Challenge4Level(cfg, user, repo, lib, logger=logger)
        self.challenge4level.main_plant_recover = True
        self.challenge4level.disable_cave_info_fetch = True
        self.challenge4level.enable_sand = True
        self.challenge4level.exit_no_trash_plant = True
        self.challenge4level.stone_book_per_use = 40
        self.repeat_time = 1

    def run(self, plant_list, stop_channel: Queue):
        for i in range(self.repeat_time):
            if stop_channel.qsize() != 0:
                return {
                    "success": False,
                    "info": "用户终止",
                }
            self.challenge4level.trash_plant_list = [plant.id for plant in plant_list]
            try:
                self.challenge4level.auto_challenge(stop_channel)
            except Exception as e:
                return {
                    "success": False,
                    "info": "挑战失败，原因：{}".format(type(e).__name__),
                }
        return {"success": True, "info": "挑战成功", "result": plant_list}

    def setting_window(self, parent=None):
        from ..windows import Challenge4levelSettingWindow

        return Challenge4levelSettingWindow(
            self.cfg,
            self.lib,
            self.repo,
            self.user,
            self.logger,
            self.challenge4level,
            parent=parent,
        )

    def has_setting_window(self):
        return True

    def serialize(self):
        return {
            "repeat_time": self.repeat_time,
            "auto_challenge": self.challenge4level.save(None),
        }

    def deserialize(self, d):
        for k, v in d.items():
            if hasattr(self, k):
                setattr(self, k, v)
        if 'auto_challenge' in d:
            self.challenge4level.load(d['auto_challenge'])


class UpgradeQuality(Pipeline):
    def __init__(self, cfg: Config, lib: Library, repo: Repository, logger: Logger):
        super().__init__("刷品")
        self.cfg = cfg
        self.lib = lib
        self.repo = repo
        self.logger = logger
        from ...upgrade import quality_name_list

        self.target_quality_index = quality_name_list.index("魔神")
        self.need_show_all_info = False
        self.pool_size = 3
        self.upgrade_plant_amount = 1
        self.interrupt_event = Event()
        self.rest_event = Event()

    def check_requirements(self):
        from ...upgrade import quality_name_list

        if self.target_quality_index > quality_name_list.index("魔神"):

            def get_tool(book_name):
                for tool in self.lib.tools.values():
                    if tool.name == book_name:
                        return tool

            quality_book = [
                get_tool("耀世盛典"),
                get_tool("上古奇书"),
                get_tool("永恒天书"),
                get_tool("太上宝典"),
                get_tool("混沌宝鉴"),
                get_tool("无极玉碟"),
            ]
            result = []
            for i in range(self.target_quality_index - quality_name_list.index("魔神")):
                tool = self.repo.get_tool(quality_book[i].id)
                if tool is None or tool['amount'] < self.upgrade_plant_amount:
                    result.append(
                        "{}数量不足，需要{}个，实际{}个".format(
                            quality_book[i].name,
                            self.upgrade_plant_amount,
                            (tool['amount'] if tool is not None else 0),
                        )
                    )
            return result
        return []

    def run(self, plant_list, stop_channel: Queue):
        if len(plant_list) < self.upgrade_plant_amount:
            return {
                "success": False,
                "info": "升品植物数量不足。需要{}个，实际{}个".format(
                    self.upgrade_plant_amount, len(plant_list)
                ),
            }
        upgrade_plant_list = plant_list[: self.upgrade_plant_amount]
        self.rest_event.clear()
        from ..windows.quality import UpgradeQualityThread

        self.quality_thread = UpgradeQualityThread(
            self.repo,
            self.lib,
            self.logger,
            UpgradeMan(self.cfg),
            [plant.id for plant in upgrade_plant_list],
            self.target_quality_index,
            self.need_show_all_info,
            None,
            self.interrupt_event,
            None,
            self.rest_event,
            self.pool_size,
        )
        self.interrupt_event.clear()
        self.quality_thread.start()
        while stop_channel.qsize() == 0 and not self.rest_event.is_set():
            sleep(0.1)
        if stop_channel.qsize() > 0:
            self.interrupt_event.set()
            self.rest_event.wait()
            return {
                "success": False,
                "info": "用户终止",
            }
        self.repo.refresh_repository()
        for plant in upgrade_plant_list:
            repo_plant = self.repo.get_plant(plant.id)
            if repo_plant is None:
                return {
                    "success": False,
                    "info": "刷品失败，原因：植物{}不存在".format(plant.name(self.lib)),
                }
            if repo_plant.quality_index < self.target_quality_index:
                return {
                    "success": False,
                    "info": "刷品失败，原因：植物{}品质不达标".format(
                        plant.name(self.lib)
                    ),
                }
        return {
            "success": True,
            "info": "升品成功",
            "result": plant_list,
        }

    def setting_widget(self, parent=None):
        from ..windows.auto_pipeline.setting_panel import UpgradeQualityWidget

        return UpgradeQualityWidget(self, parent=parent)

    def has_setting_widget(self):
        return True

    def serialize(self):
        return {
            "target_quality_index": self.target_quality_index,
            "need_show_all_info": self.need_show_all_info,
            "pool_size": self.pool_size,
            "upgrade_plant_amount": self.upgrade_plant_amount,
        }


class AutoUpgradeQuality(Pipeline):  # 智能升品，仅适用于开魔神箱
    def __init__(self, cfg: Config, lib: Library, repo: Repository, logger: Logger):
        super().__init__("智能升品")
        self.cfg = cfg
        self.lib = lib
        self.repo = repo
        self.logger = logger
        self.need_show_all_info = False
        self.pool_size = 3
        self.interrupt_event = Event()
        self.rest_event = Event()

    def register_quality_dict_func(self, func):
        self.quality_dict_func = func

    def get_quality_dict(self) -> None | dict[int, int]:
        assert hasattr(self, "quality_dict_func")
        return self.quality_dict_func()

    def check_requirements(self):
        quality_dict = self.get_quality_dict()
        if quality_dict is None:
            return ["智能升品需设置流水线为自动开箱-练级-智能升品-复合"]

        def get_tool(book_name):
            for tool in self.lib.tools.values():
                if tool.name == book_name:
                    return tool

        quality_book = [
            get_tool("耀世盛典"),
            get_tool("上古奇书"),
            get_tool("永恒天书"),
            get_tool("太上宝典"),
            get_tool("混沌宝鉴"),
            get_tool("无极玉碟"),
        ]
        result = []
        acquired_book_num = {i: 0 for i in range(len(quality_book))}
        moshen_index = quality_name_list.index("魔神")
        for quality_index, plant_num in quality_dict.items():
            if quality_index < moshen_index:
                return ["智能升品检测到复合方案中有低于魔神的品质，不符合要求"]
            if quality_index == moshen_index:
                continue
            quality_index -= moshen_index + 1
            for i in range(quality_index + 1):
                acquired_book_num[i] += plant_num
        for index, book_num in acquired_book_num.items():
            if book_num == 0:
                continue
            book = quality_book[index]
            tool = self.repo.get_tool(book.id)
            if tool is None or tool['amount'] < book_num:
                result.append(
                    "{}数量不足，需要{}个，实际只有{}个".format(
                        book.name,
                        book_num,
                        (tool['amount'] if tool is not None else 0),
                    )
                )
        return result

    def run(self, plant_list: list[Plant], stop_channel: Queue):
        quality_dict = self.get_quality_dict()
        if quality_dict is None:
            return {
                "success": False,
                "info": "智能升品需设置流水线为自动开箱-练级-智能升品-复合",
            }

        plant_id_list = [plant.id for plant in plant_list]
        moshen_index = quality_name_list.index("魔神")

        for quality_index, plant_num in quality_dict.items():
            if quality_index <= moshen_index:
                continue
            upgrade_plant_id_list = plant_id_list[:plant_num]
            plant_id_list = plant_id_list[plant_num:]

            self.rest_event.clear()
            from ..windows.quality import UpgradeQualityThread

            self.quality_thread = UpgradeQualityThread(
                self.repo,
                self.lib,
                self.logger,
                UpgradeMan(self.cfg),
                upgrade_plant_id_list,
                quality_index,
                self.need_show_all_info,
                None,
                self.interrupt_event,
                None,
                self.rest_event,
                self.pool_size,
            )
            self.interrupt_event.clear()
            self.quality_thread.start()
            while stop_channel.qsize() == 0 and not self.rest_event.is_set():
                sleep(0.1)
            if stop_channel.qsize() > 0:
                self.interrupt_event.set()
                self.rest_event.wait()
                return {
                    "success": False,
                    "info": "用户终止",
                }
        self.repo.refresh_repository()

        in_plant_quality_dict = {}
        plant_id_list = [plant.id for plant in plant_list]
        for plant_id in plant_id_list:
            plant = self.repo.get_plant(plant_id)
            if plant is None:
                return {
                    "success": False,
                    "info": "智能升品失败，原因：本该存在的植物不存在了",
                }
            if plant.quality_index not in in_plant_quality_dict:
                in_plant_quality_dict[plant.quality_index] = 0
            in_plant_quality_dict[plant.quality_index] += 1
        for quality_index, plant_num in quality_dict.items():
            if in_plant_quality_dict.get(quality_index, 0) < plant_num:
                return {
                    "success": False,
                    "info": "智能升品失败，原因：{}品质植物预期升品{}个，实际升品{}个".format(
                        quality_name_list[quality_index],
                        plant_num,
                        in_plant_quality_dict.get(quality_index, 0),
                    ),
                }

        return {
            "success": True,
            "info": "升品成功",
            "result": plant_list,
        }

    def setting_widget(self, parent=None):
        from ..windows.auto_pipeline.setting_panel import AutoUpgradeQualityWidget

        return AutoUpgradeQualityWidget(self, parent=parent)

    def has_setting_widget(self):
        return True

    def serialize(self):
        return {
            "need_show_all_info": self.need_show_all_info,
            "pool_size": self.pool_size,
        }

    def deserialize(self, d):
        for k, v in d.items():
            if hasattr(self, k):
                setattr(self, k, v)


class AutoStoneTalent(Pipeline):
    def __init__(self, cfg: Config, lib: Library, repo: Repository, logger: Logger):
        super().__init__("升宝石")
        self.cfg = cfg
        self.lib = lib
        self.repo = repo
        self.logger = logger
        self.target_stone_level = [0 for _ in range(9)]

    def run(self, plant_list: list[Plant], stop_channel: Queue):
        pass

    def setting_window(self, parent=None):
        from ..windows.auto_pipeline.setting_panel import CustomProcessWidget

        return CustomProcessWidget(
            self,
            parent=parent,
        )

    def has_setting_window(self):
        return True

    def serialize(self):
        return {}


class AutoEvolution(Pipeline):
    def __init__(self, cfg: Config, lib: Library, repo: Repository, logger: Logger):
        super().__init__("进化")
        self.cfg = cfg
        self.lib = lib
        self.repo = repo
        self.logger = logger
        self.plant_evolution = PlantEvolution(cfg, repo, lib, only_one=True)
        self.pool_size = 3
        self.interrupt_event = Event()
        self.rest_event = Event()

    def check_requirements(self):
        if len(self.plant_evolution.saved_evolution_paths) == 0:
            return ["自定义方案中: 进化pipeline未设置进化方案"]
        if len(self.plant_evolution.saved_evolution_paths) > 1:
            return ["自定义方案中: 进化pipeline设置了多个进化方案"]
        if len(self.plant_evolution.saved_evolution_paths[0]) == 0:
            return ["自定义方案中: 进化pipeline设置的进化方案为空"]

    def run(self, plant_list: list[Plant], stop_channel: Queue):
        plant_id_list = [plant.id for plant in plant_list]
        self.rest_event.clear()
        self.interrupt_event.clear()
        from ..windows.evolution import EvolutionPanelThread

        self.run_thread = EvolutionPanelThread(
            0,
            plant_id_list,
            self.repo,
            self.lib,
            self.logger,
            self.plant_evolution,
            None,
            self.interrupt_event,
            None,
            self.rest_event,
            pool_size=self.pool_size,
        )
        self.run_thread.start()
        while stop_channel.qsize() == 0 and not self.rest_event.is_set():
            sleep(0.1)
        if stop_channel.qsize() > 0:
            self.interrupt_event.set()
            self.rest_event.wait()
            return {
                "success": False,
                "info": "用户终止",
            }
        self.repo.refresh_repository()
        return {
            "success": True,
            "info": "进化成功",
            "result": plant_list,
        }

    def setting_window(self, parent=None):
        from ..windows.evolution import EvolutionPanelWindow

        return EvolutionPanelWindow(
            self.repo,
            self.lib,
            self.logger,
            self.plant_evolution,
            parent=parent,
        )

    def has_setting_window(self):
        return True

    def setting_widget(self, parent=None):
        from ..windows.auto_pipeline.setting_panel import EvolutionWidget

        return EvolutionWidget(self, parent=parent)

    def has_setting_widget(self):
        return True

    def serialize(self):
        return {
            "plant_evolution": self.plant_evolution.save(),
            "pool_size": self.pool_size,
        }

    def deserialize(self, data):
        self.plant_evolution.load(data["plant_evolution"])
        if "pool_size" in data:
            self.pool_size = data["pool_size"]


class CustomProcessChain(Pipeline):
    def __init__(self, cfg: Config, lib: Library, repo: Repository, logger: Logger):
        super().__init__("自定义处理")
        self.cfg = cfg
        self.lib = lib
        self.repo = repo
        self.logger = logger

        self.chosen_pipelines: list[Pipeline] = []
        self.available_pipeline_names = ["刷品", "进化", "升宝石"]
        self.name2class = {
            "刷品": UpgradeQuality,
            "进化": AutoEvolution,
            "升宝石": AutoStoneTalent,
        }

    def add_pipeline(self, name):
        if name not in self.name2class:
            self.logger.log(f"未知的处理操作名称: {name}")
            return
        pipeline_class = self.name2class[name]
        self.chosen_pipelines.append(
            pipeline_class(self.cfg, self.lib, self.repo, self.logger)
        )

    def remove_pipeline(self, pipeline):
        try:
            self.chosen_pipelines.remove(pipeline)
        except ValueError:
            self.logger.log(f"无法移除{pipeline.name}, 请重试")

    def run(self, plant_list: list[Plant], stop_channel: Queue):
        for pipeline in self.chosen_pipelines:
            result = pipeline.run(plant_list, stop_channel)
            if not result['success']:
                result["info"] = "自定义处理第{}个pipeline({})失败，原因：{}".format(
                    self.chosen_pipelines.index(pipeline),
                    pipeline.name,
                    result['info'],
                )
                return result
            plant_list = result['result']
        return {
            "success": True,
            "info": "自定义处理成功",
            "result": plant_list,
        }

    def setting_window(self, parent=None):
        from ..windows.auto_pipeline.setting_panel import CustomProcessWidget

        return CustomProcessWidget(
            self,
            parent=parent,
        )

    def has_setting_window(self):
        return True

    def serialize(self):
        return {
            "chosen_pipelines": [
                (pipeline.serialize()) for pipeline in self.chosen_pipelines
            ]
        }

    def deserialize(self, data):
        for pipeline_data in data["chosen_pipelines"]:
            try:
                pipeline_class = self.name2class[pipeline_data["name"]]
            except ValueError:
                self.logger.log(f"无法解析的pipeline名称: {pipeline_data['name']}")
            if isinstance(pipeline_class, UpgradeQuality):
                pipeline = UpgradeQuality(self.cfg, self.lib, self.repo, self.logger)
            elif isinstance(pipeline_class, AutoEvolution):
                pipeline = AutoEvolution(self.cfg, self.lib, self.repo, self.logger)
            elif isinstance(pipeline_class, AutoStoneTalent):
                pipeline = AutoStoneTalent(self.cfg, self.lib, self.repo, self.logger)
            else:
                raise ValueError(f"未知pipeline类别: {pipeline_class.__name__}")
            pipeline.deserialize(pipeline_data)
            self.chosen_pipelines.append(pipeline)


class AutoComponent(Pipeline):
    def __init__(self, cfg: Config, lib: Library, repo: Repository, logger: Logger):
        super().__init__("自动复合")
        self.cfg = cfg
        self.lib = lib
        self.repo = repo
        self.logger = logger
        from .compound import AutoCompoundMan

        self.auto_component_man = AutoCompoundMan(cfg, lib, repo, logger)
        self.interrupt_event = Event()
        self.rest_event = Event()

    def check_requirements(self):
        self.auto_component_man.check_data(refresh_repo=False)
        result = self.auto_component_man.one_cycle_consume_check()
        result = [info for info in result if "品质的植物数量现" not in info]
        if not self.auto_component_man.need_compound():
            result.append("复合已经达成目标数值")
        return result

    def run(self, plant_list, stop_channel: Queue):
        self.auto_component_man.auto_compound_pool_id.clear()
        for scheme in self.auto_component_man.scheme_list:
            if not scheme.enabled:
                continue
            scheme.auto_compound_pool_id.clear()
            scheme.auto_synthesis_man.auto_synthesis_pool_id.clear()
        for plant in plant_list:
            self.auto_component_man.auto_compound_pool_id.add(plant.id)
        from ..windows.compound import CompoundThread

        reach_target_event = Event()
        self.rest_event.clear()
        self.component_theard = CompoundThread(
            self.auto_component_man,
            None,
            self.interrupt_event,
            None,
            self.rest_event,
            reach_target_event=reach_target_event,
        )
        self.interrupt_event.clear()
        self.component_theard.start()
        while stop_channel.qsize() == 0 and not self.rest_event.is_set():
            sleep(0.1)
        if stop_channel.qsize() > 0:
            self.interrupt_event.set()
            self.rest_event.wait()
            return {
                "success": False,
                "info": "用户终止",
            }
        self.repo.refresh_repository()
        rest_plant_list = []
        for plant in plant_list:
            if self.repo.get_plant(plant.id) is not None:
                rest_plant_list.append(plant)
        cnt = 0
        for scheme in self.auto_component_man.scheme_list:
            if scheme.enabled:
                cnt += 1

        if len(rest_plant_list) != cnt:
            result = {
                "success": False,
                "info": "复合失败，原因：本应被吃的植物仍然存在",
            }
        elif len(self.auto_component_man.auto_compound_pool_id) != 0:
            result = {
                "success": False,
                "info": "复合失败，原因：复合池中仍然有植物",
            }
        else:
            if reach_target_event.is_set():
                result = {
                    "success": False,
                    "info": "复合成功，达到目标",
                }
            else:
                result = {
                    "success": True,
                    "info": "复合成功",
                }
        self.auto_component_man.auto_compound_pool_id.clear()
        return result

    def has_setting_window(self):
        return True

    def setting_window(self, parent=None):
        from ..windows import AutoCompoundWindow

        return AutoCompoundWindow(
            self.cfg,
            self.lib,
            self.repo,
            self.logger,
            self.auto_component_man,
            parent=parent,
        )

    def serialize(self):
        return {
            "auto_compound": self.auto_component_man.save(None),
        }

    def deserialize(self, d):
        for k, v in d.items():
            if hasattr(self, k):
                setattr(self, k, v)
        if 'auto_compound' in d:
            self.auto_component_man.load(d['auto_compound'])


class PipelineScheme:
    def __init__(
        self,
        cfg: Config,
        lib: Library,
        repo: Repository,
        user: User,
        logger: Logger,
    ):
        self.cfg = cfg
        self.logger = logger
        self.repo = repo
        self.lib = lib
        self.user = user
        self.name = "新方案"
        self.pipeline1: list[Pipeline] = [
            Purchase(cfg, lib, repo, logger),
            OpenBox(cfg, lib, repo, logger),
        ]
        self.pipeline1_choice_index = 1

        self.pipeline2: list[Pipeline] = [
            AutoChallenge(cfg, lib, repo, user, logger),
            SkipPipeline(),
        ]
        self.pipeline2_choice_index = 1

        self.pipeline3: list[Pipeline] = [
            UpgradeQuality(cfg, lib, repo, logger),
            SkipPipeline(),
            AutoUpgradeQuality(cfg, lib, repo, logger),
            CustomProcessChain(cfg, lib, repo, logger),
        ]
        self.pipeline3_choice_index = 2

        self.pipeline4: list[Pipeline] = [AutoComponent(cfg, lib, repo, logger)]
        self.pipeline4_choice_index = 0

        self.register_openbox()
        self.register_auto_upgrade_quality()

    @property
    def p1(self):
        return self.pipeline1[self.pipeline1_choice_index]

    @property
    def p2(self):
        return self.pipeline2[self.pipeline2_choice_index]

    @property
    def p3(self):
        return self.pipeline3[self.pipeline3_choice_index]

    @property
    def p4(self):
        return self.pipeline4[self.pipeline4_choice_index]

    def check_requirements(self):
        self.repo.refresh_repository(self.logger)
        result = []
        result.extend(self.p1.check_requirements())
        result.extend(self.p2.check_requirements())
        result.extend(self.p3.check_requirements())
        result.extend(self.p4.check_requirements())
        if (
            isinstance(self.p1, OpenBox)
            and (
                isinstance(self.p3, UpgradeQuality)
                or isinstance(self.p3, SkipPipeline)
                or isinstance(self.p3, AutoUpgradeQuality)
            )
            and isinstance(self.p4, AutoComponent)
        ):
            (
                inherit_book_dict,
                synthesis_book_dict,
                quality_dict,
                inherit_reinforce_num_required,
                synthesis_reinforce_num_required,
            ) = self.p4.auto_component_man.one_cycle_comsume_calc()
            deputy_plant_num_required = 0
            for v in quality_dict.values():
                deputy_plant_num_required += v
            if self.p1.amount != deputy_plant_num_required:
                result.append(
                    "复合需要{}个植物，但开箱设置的是{}个植物，请改成复合所需要的植物数量".format(
                        deputy_plant_num_required, self.p1.amount
                    )
                )

        return result

    def register_auto_upgrade_quality(self):
        def run():
            if not (
                isinstance(self.p1, OpenBox)
                and (isinstance(self.p3, AutoUpgradeQuality))
                and isinstance(self.p4, AutoComponent)
            ):
                return None

            result = {}
            auto_compound = self.p4
            assert isinstance(auto_compound, AutoComponent)
            for scheme in auto_compound.auto_component_man.scheme_list:
                if not scheme.enabled:
                    continue
                scheme_quality_dict = scheme.plant_comsume_calc()
                for k, v in scheme_quality_dict.items():
                    if k not in result:
                        result[k] = 0
                    result[k] += v
            return result

        u = self.pipeline3[2]
        assert isinstance(u, AutoUpgradeQuality)
        u.register_quality_dict_func(run)

    def register_openbox(self):
        def run1():
            if (
                isinstance(self.p1, OpenBox)
                and (
                    isinstance(self.p3, UpgradeQuality)
                    or isinstance(self.p3, SkipPipeline)
                    or isinstance(self.p3, AutoUpgradeQuality)
                )
                and isinstance(self.p4, AutoComponent)
            ):
                (
                    inherit_book_dict,
                    synthesis_book_dict,
                    quality_dict,
                    inherit_reinforce_num_required,
                    synthesis_reinforce_num_required,
                ) = self.p4.auto_component_man.one_cycle_comsume_calc()
                deputy_plant_num_required = 0
                for v in quality_dict.values():
                    deputy_plant_num_required += v
                self.p1.amount = deputy_plant_num_required
                return True
            return False

        def run2():
            if isinstance(self.p1, OpenBox) and isinstance(self.p4, AutoComponent):
                (
                    inherit_book_dict,
                    synthesis_book_dict,
                    quality_dict,
                    inherit_reinforce_num_required,
                    synthesis_reinforce_num_required,
                ) = self.p4.auto_component_man.one_cycle_comsume_calc()
                return quality_dict
            return None

        o = self.pipeline1[1]
        assert isinstance(o, OpenBox)
        o.register_auto_set_amount(run1)
        o.register_quality_dict_func(run2)

    def run(self, stop_channel: Queue, stop_after_finish=True):
        cnt = 0
        if stop_after_finish:
            pre_stop_channel = stop_channel
            stop_channel = Queue()
        while True:
            cnt += 1
            if stop_after_finish:
                if pre_stop_channel.qsize() != 0:
                    self.logger.log("用户终止")
                    return
            if stop_channel.qsize() != 0:
                self.logger.log("用户终止")
                return
            self.repo.refresh_repository()
            result = self.check_requirements()
            if len(result) > 0:
                self.logger.log(
                    f"检测到第{cnt}次全自动缺失以下物品：\n" + '\n'.join(result)
                )
                return
            result = self.pipeline1[self.pipeline1_choice_index].run(stop_channel)
            if stop_channel.qsize() != 0:
                self.logger.log("用户终止")
                return
            if not result['success']:
                self.logger.log(result['info'])
                return
            result = self.pipeline2[self.pipeline2_choice_index].run(
                result['result'], stop_channel
            )
            if stop_channel.qsize() != 0:
                self.logger.log("用户终止")
                return
            if not result['success']:
                self.logger.log(result['info'])
                return
            result = self.pipeline3[self.pipeline3_choice_index].run(
                result['result'], stop_channel
            )
            if stop_channel.qsize() != 0:
                self.logger.log("用户终止")
                return
            if not result['success']:
                self.logger.log(result['info'])
                return
            result = self.pipeline4[self.pipeline4_choice_index].run(
                result['result'], stop_channel
            )
            if stop_channel.qsize() != 0:
                self.logger.log("用户终止")
                return
            if not result['success']:
                self.logger.log(result['info'])
                return
            self.logger.log("全自动流程第{}次完成".format(cnt))

    def serialize(self):
        return {
            "name": self.name,
            "pipeline1_choice_index": self.pipeline1_choice_index,
            "pipeline2_choice_index": self.pipeline2_choice_index,
            "pipeline3_choice_index": self.pipeline3_choice_index,
            "pipeline4_choice_index": self.pipeline4_choice_index,
            "pipeline1_serialized": {p.name: p.serialize() for p in self.pipeline1},
            "pipeline2_serialized": {p.name: p.serialize() for p in self.pipeline2},
            "pipeline3_serialized": {p.name: p.serialize() for p in self.pipeline3},
            "pipeline4_serialized": {p.name: p.serialize() for p in self.pipeline4},
        }

    def deserialize(self, d):
        for k, v in d.items():
            if hasattr(self, k):
                setattr(self, k, v)
        if 'pipeline1_serialized' in d:
            for p in self.pipeline1:
                if p.name in d['pipeline1_serialized']:
                    p.deserialize(d['pipeline1_serialized'][p.name])
        if 'pipeline2_serialized' in d:
            for p in self.pipeline2:
                if p.name in d['pipeline2_serialized']:
                    p.deserialize(d['pipeline2_serialized'][p.name])
        if 'pipeline3_serialized' in d:
            for p in self.pipeline3:
                if p.name in d['pipeline3_serialized']:
                    p.deserialize(d['pipeline3_serialized'][p.name])
        if 'pipeline4_serialized' in d:
            for p in self.pipeline4:
                if p.name in d['pipeline4_serialized']:
                    p.deserialize(d['pipeline4_serialized'][p.name])


class PipelineMan:
    def __init__(
        self, cfg: Config, lib: Library, repo: Repository, user: User, logger: Logger
    ):
        self.cfg = cfg
        self.lib = lib
        self.repo = repo
        self.user = user
        self.logger = logger
        self.scheme_list: list[PipelineScheme] = []
        self.current_scheme_index = 0
        self.stop_after_finish = True

    @property
    def current_scheme(self):
        return self.scheme_list[self.current_scheme_index]

    def new_scheme(self):
        self.scheme_list.append(
            PipelineScheme(self.cfg, self.lib, self.repo, self.user, self.logger)
        )

    def remove_scheme(self, scheme: PipelineScheme):
        if scheme in self.scheme_list:
            self.scheme_list.remove(scheme)

    def save(self, save_dir):
        save_path = os.path.join(save_dir, "auto_pipeline")
        with open(save_path, "wb") as f:
            pickle.dump(
                {
                    "scheme_list_serilized": [
                        scheme.serialize() for scheme in self.scheme_list
                    ],
                    "current_scheme_index": self.current_scheme_index,
                    "stop_after_finish": self.stop_after_finish,
                },
                f,
            )

    def load(self, load_dir):
        load_path = os.path.join(load_dir, "auto_pipeline")
        if os.path.exists(load_path):
            with open(load_path, "rb") as f:
                d = pickle.load(f)
            for k, v in d.items():
                if hasattr(self, k):
                    setattr(self, k, v)
            for scheme_serilized in d['scheme_list_serilized']:
                scheme = PipelineScheme(
                    self.cfg, self.lib, self.repo, self.user, self.logger
                )
                scheme.deserialize(scheme_serilized)
                self.scheme_list.append(scheme)
