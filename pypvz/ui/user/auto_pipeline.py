import pickle
from queue import Queue
import logging
import os
from threading import Event
from time import sleep
from ... import (
    Config,
    Repository,
    Library,
    WebRequest,
    User,
)
from ..message import Logger
from ... import UpgradeMan
from .auto_challenge import Challenge4Level


class Pipeline:
    def __init__(self, name):
        self.name = name

    def run(self):
        pass


class _PurchaseItem:
    def __init__(self, root, amount):
        self.amount = amount
        self.id = root['id']
        if root['type'] == "organisms":
            self.pid = root['p_id']
            self.type = 0
        elif root['type'] == "tool":
            self.tool_id = root['tool_id']
            self.type = 1
        else:
            raise NotImplementedError


class Purchase(Pipeline):
    def __init__(self, cfg: Config, lib: Library, repo: Repository, logger: Logger):
        super().__init__("购买植物")
        self.cfg = cfg
        self.lib = lib
        self.repo = repo
        self.logger = logger
        self.wr = WebRequest(cfg)

        self.purchase_plant_list: list[_PurchaseItem] = []

    def purchase(self, item: _PurchaseItem):
        body = [float(item.id), float(item.amount)]
        response = self.wr.amf_post_retry(
            body,
            "api.shop.buy",
            "/pvz/amf/",
            "购买物品",
            logger=self.logger,
        )
        if response.status == 0 and response.body['status'] == 'success':
            return {
                "success": True,
                "result": str(response.body),
            }
        else:
            return {
                "success": False,
                "result": str(response.body),
            }

    def run(self, stop_channel: Queue):
        pre_id2plant = self.repo.id2plant
        for item in self.purchase_plant_list:
            if stop_channel.qsize() != 0:
                return {
                    "success": False,
                    "info": "用户终止",
                }
            result = self.purchase(item)

            if not result['success']:
                self.logger.log()
                return {
                    "success": False,
                    "info": "购买失败，原因：{}".format(result['result']),
                }
        self.repo.refresh_repository()
        purchased_plant_list = []
        for item in self.purchase_plant_list:
            if stop_channel.qsize() != 0:
                return {
                    "success": False,
                    "info": "用户终止",
                }
            if item.type != 0:
                continue
            pre_len = len(purchased_plant_list)
            for plant in self.repo.plants:
                if plant.pid == item.pid and plant.id not in pre_id2plant:
                    purchased_plant_list.append(plant)
            if item.amount != len(purchased_plant_list) - pre_len:
                return {
                    "success": False,
                    "info": "购买失败，原因：尝试购买{}，预计购买{}个，实际购买{}个".format(
                        self.lib.get_plant_by_id(item.pid).name,
                        item.amount,
                        len(purchased_plant_list) - pre_len,
                    ),
                }
        return {
            "success": True,
            "info": "购买成功",
            "result": [item for item in self.purchase_plant_list if item.type == 0],
        }


class OpenBox(Pipeline):
    def __init__(self, cfg: Config, lib: Library, repo: Repository, logger: Logger):
        super().__init__("开魔神箱")

        self.cfg = cfg
        self.lib = lib
        self.repo = repo
        self.logger = logger

        self.box_id = 0
        self.amount = 0

    def use_tool(self):
        return

    def run(self, stop_channel: Queue):
        pre_id2plant = self.repo.id2plant
        result = self.repo.use_tool(self.box_id, self.amount, self.lib)
        if not result['success']:
            return {
                "success": False,
                "info": "使用物品失败，原因：{}".format(result['result']),
            }
        self.repo.refresh_repository()
        plant_list = []
        for plant in self.repo.plants:
            if plant.id in pre_id2plant or plant.quality_str != "魔神":
                continue
            plant_list.append(plant)
        if self.amount != len(plant_list):
            return {
                "success": False,
                "info": "打开魔神箱失败，原因：预计获得{}个魔神，实际获得{}个魔神".format(
                    self.amount,
                    len(plant_list),
                ),
            }
        return {
            "success": True,
            "info": "使用物品成功",
            "result": plant_list,
        }


class AutoChallenge(Pipeline):
    def __init__(
        self, cfg: Config, lib: Library, repo: Repository, user: User, logger: Logger
    ):
        super().__init__("带级")
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
        self.force_upgrade = True
        self.pool_size = 3
        self.interrupt_event = Event()
        self.rest_event = Event()

    def run(self, plant_list, stop_channel: Queue):
        from ..windows.quality import UpgradeQualityThread

        self.quality_thread = UpgradeQualityThread(
            self.repo,
            self.lib,
            self.logger,
            UpgradeMan(self.cfg),
            plant_list,
            self.target_quality_index,
            self.need_show_all_info,
            None,
            self.interrupt_event,
            None,
            self.rest_event,
            self.force_upgrade,
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
        for plant in plant_list:
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


class AutoComponent(Pipeline):
    def __init__(self, cfg: Config, lib: Library, repo: Repository, logger: Logger):
        super().__init__("自动复合")
        self.cfg = cfg
        self.lib = lib
        self.repo = repo
        self.logger = logger
        from .manager import AutoCompoundMan

        self.auto_component_man = AutoCompoundMan(cfg, lib, repo, logger)
        self.interrupt_event = Event()
        self.rest_event = Event()

    def run(self, plant_list, stop_channel: Queue):
        for plant in plant_list:
            self.auto_component_man.auto_synthesis_pool_id.add(plant.id)
        from ..windows.compound import CompoundThread

        self.component_theard = CompoundThread(
            self.auto_component_man,
            None,
            self.interrupt_event,
            self.rest_event,
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
        for plant in plant_list:
            if self.repo.get_plant(plant.id) is not None:
                return {
                    "success": False,
                    "info": "复合失败，原因：植物{}本应被吃但仍然存在".format(plant.name(self.lib)),
                }
        return {
            "success": True,
            "info": "复合成功",
            "result": plant_list,
        }


class PipelineScheme:
    def __init__(
        self, cfg: Config, lib: Library, repo: Repository, user: User, logger: Logger
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

        self.pipeline3: list[Pipeline] = [UpgradeQuality(cfg, lib, repo, logger)]
        self.pipeline3_choice_index = 0

        self.pipeline4: list[Pipeline] = [AutoComponent(cfg, lib, repo, logger)]
        self.pipeline4_choice_index = 0

    def run(self, stop_channel: Queue):
        cnt = 0
        while True:
            cnt += 1
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
            # "pipeline1": self.pipeline1,
            "pipeline1_choice_index": self.pipeline1_choice_index,
            # "pipeline2": self.pipeline2,
            "pipeline2_choice_index": self.pipeline2_choice_index,
            # "pipeline3": self.pipeline3,
            "pipeline3_choice_index": self.pipeline3_choice_index,
            # "pipeline4": self.pipeline4,
            "pipeline4_choice_index": self.pipeline4_choice_index,
        }

    def deserialize(self, d):
        for k, v in d.items():
            if hasattr(self, k):
                setattr(self, k, v)


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
