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
            self.lib, self.shop, self.logger, self.shop_auto_buy_dict, parent=parent
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

        self.box_type_str_list = ["魔神箱", "无极幽冥龙箱"]
        self.box_type_quality_str_list = ["魔神", "无极"]
        self.box_type_id_list = [756, 3000]
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

    def run(self, stop_channel: Queue):
        tool = self.repo.get_tool(self.box_id)
        if tool is None:
            return {
                "success": False,
                "info": "使用{}失败，原因：{}不存在".format(self.box_name, self.box_name),
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
        super().__init__("升品")
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
                    "info": "刷品失败，原因：植物{}品质不达标".format(plant.name(self.lib)),
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

    def deserialize(self, d):
        for k, v in d.items():
            if hasattr(self, k):
                setattr(self, k, v)


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
        self.pipeline1_choice_index = 0

        self.pipeline2: list[Pipeline] = [AutoChallenge(cfg, lib, repo, user, logger)]
        self.pipeline2_choice_index = 0

        self.pipeline3: list[Pipeline] = [
            UpgradeQuality(cfg, lib, repo, logger),
            SkipPipeline(),
        ]
        self.pipeline3_choice_index = 0

        self.pipeline4: list[Pipeline] = [AutoComponent(cfg, lib, repo, logger)]
        self.pipeline4_choice_index = 0

    def check_requirements(self):
        self.repo.refresh_repository(self.logger)
        result = []
        result.extend(self.pipeline1[self.pipeline1_choice_index].check_requirements())
        result.extend(self.pipeline2[self.pipeline2_choice_index].check_requirements())
        result.extend(self.pipeline3[self.pipeline3_choice_index].check_requirements())
        result.extend(self.pipeline4[self.pipeline4_choice_index].check_requirements())
        return result

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
                self.logger.log(f"检测到第{cnt}次全自动缺失以下物品：\n" + '\n'.join(result))
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
