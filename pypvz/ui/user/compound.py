import pickle
import os
from threading import Event
from time import sleep
from ... import (
    Config,
    Repository,
    Library,
    HeritageMan,
)
from ..message import Logger
from ..wrapped import signal_block_emit
from .manager import AutoSynthesisMan


class CompoundScheme:
    def __init__(self):
        self.source_plant_id = None
        self.n1, self.n2, self.k, self.m = 2, 1, 5, 3
        self.chosen_attribute = "HP特"


class AutoCompoundMan:
    def __init__(self, cfg: Config, lib: Library, repo: Repository, logger: Logger):
        self.lib = lib
        self.cfg = cfg
        self.repo = repo
        self.logger = logger
        self.attribute_list = ["HP特", "攻击特", "命中", "闪避", "穿透", "护甲", "HP", "攻击"]
        self.attribute_compose_book_dict = {
            "HP": lib.name2tool["HP合成书"].id,
            "攻击": lib.name2tool["攻击合成书"].id,
            "命中": lib.name2tool["命中合成书"].id,
            "闪避": lib.name2tool["闪避合成书"].id,
            "穿透": lib.name2tool["穿透合成书"].id,
            "护甲": lib.name2tool["护甲合成书"].id,
            "HP特": lib.name2tool["特效HP合成书"].id,
            "攻击特": lib.name2tool["特级攻击合成书"].id,
        }
        self.attribute2plant_attribute = {
            "HP": "hp_max",
            "攻击": "attack",
            "命中": "precision",
            "闪避": "miss",
            "穿透": "piercing",
            "护甲": "armor",
            "HP特": "hp_max",
            "攻击特": "attack",
        }
        self.attribute_inheritage_book_dict = {
            "HP": lib.name2tool["HP传承书"].id,
            "攻击": lib.name2tool["攻击传承书"].id,
            "命中": lib.name2tool["命中传承书"].id,
            "闪避": lib.name2tool["闪避传承书"].id,
            "穿透": lib.name2tool["穿透传承书"].id,
            "护甲": lib.name2tool["护甲传承书"].id,
            "HP特": lib.name2tool["HP传承书"].id,
            "攻击特": lib.name2tool["攻击传承书"].id,
            "全属性传承书": lib.name2tool["全属性传承书"].id,
            "传承增强卷轴": lib.name2tool["传承增强卷轴"].id,
        }
        self.auto_synthesis_man = AutoSynthesisMan(cfg, lib, repo)
        self.heritage_man = HeritageMan(cfg, lib)
        self.liezhi_plant_id = None
        self.receiver_plant_id = None
        self.source_plant_id = None
        self.use_all_exchange = True
        self.allow_inherite2target = True
        self.auto_compound_pool_id = set()
        self.n1, self.n2, self.k, self.m = 2, 1, 5, 3
        self.chosen_attribute = "HP特"
        self.set_chosen_attribute(self.chosen_attribute)
        self.end_mantissa = 1.0
        self.end_exponent = 1
        self.auto_synthesis_man.reinforce_number = 10

    @property
    def inherit_book(self):
        if self.chosen_attribute is None:
            return None
        return self.repo.get_tool(
            self.attribute_inheritage_book_dict[self.chosen_attribute]
        )

    @property
    def inherit_reinforce(self):
        return self.repo.get_tool(self.lib.name2tool["传承增强卷轴"].id)

    @property
    def synthesis_book(self):
        if self.chosen_attribute is None:
            return None
        return self.repo.get_tool(
            self.attribute_compose_book_dict[self.chosen_attribute]
        )

    @property
    def synthesis_reinforce(self):
        return self.repo.get_tool(self.lib.name2tool["增强卷轴"].id)

    def set_chosen_attribute(self, chosen_attribute):
        self.chosen_attribute = chosen_attribute
        self.auto_synthesis_man.chosen_attribute = self.chosen_attribute

    def need_compound(self):
        if self.receiver_plant_id is None:
            self.logger.log("未设置主力")
            return False
        plant = self.repo.get_plant(self.receiver_plant_id)
        if plant is None:
            self.logger.log("主力植物不存在")
            return False
        now_attr = getattr(
            plant,
            self.attribute2plant_attribute[self.chosen_attribute],
        )
        target_attr = self.end_mantissa * (10 ** (self.end_exponent + 8))
        if now_attr >= target_attr:
            self.logger.log("主力数值已达到设定值")
            return False
        else:
            return True

    def check_data(self, refresh_repo=True):
        if refresh_repo:
            self.repo.refresh_repository()
        self.auto_synthesis_man.check_data(False)
        if isinstance(self.liezhi_plant_id, int):
            if self.repo.get_plant(self.liezhi_plant_id) is None:
                self.liezhi_plant_id = None
        else:
            self.liezhi_plant_id = None
        if isinstance(self.receiver_plant_id, int):
            if self.repo.get_plant(self.receiver_plant_id) is None:
                self.receiver_plant_id = None
        else:
            self.receiver_plant_id = None
        if isinstance(self.source_plant_id, int):
            if self.repo.get_plant(self.source_plant_id) is None:
                self.source_plant_id = None
        else:
            self.source_plant_id = None
        auto_compound_pool_id = list(self.auto_compound_pool_id)
        for deputy_plant_id in auto_compound_pool_id:
            if self.repo.get_plant(deputy_plant_id) is None:
                self.auto_compound_pool_id.remove(deputy_plant_id)

    def one_cycle_consume_check(self):
        result = []
        inherit_book_num_required = self.m + (0 if self.use_all_exchange else 1)
        inherit_reinforce_num_required = (10 - self.k) * self.m + (
            0 if self.use_all_exchange else 10
        )
        synthesis_book_num_required = (self.n1 + self.n2 + 1) * self.m
        synthesis_reinforce_num_required = synthesis_book_num_required * 10
        deputy_plant_num_required = synthesis_book_num_required
        inherit_book = self.inherit_book
        if self.liezhi_plant_id is None:
            result.append("未设置劣质双格植物")
        if self.receiver_plant_id is None:
            result.append("未设置主力植物")
        if self.source_plant_id is None:
            result.append("未设置底座植物")
        if inherit_book is None:
            result.append("没有{}传承书了".format(self.chosen_attribute))
        elif inherit_book['amount'] < inherit_book_num_required:
            result.append(
                "{}传承书数量现有{}本，需要{}本".format(
                    self.chosen_attribute,
                    inherit_book['amount'],
                    inherit_book_num_required,
                )
            )
        if self.use_all_exchange:
            inherit_all_book = self.repo.get_tool(self.lib.name2tool["全属性传承书"].id)
            if inherit_all_book is None or inherit_all_book['amount'] == 0:
                result.append("没有全属性传承书了")
        inherit_reinforce = self.inherit_reinforce
        if inherit_reinforce is None:
            result.append("没有传承增强卷轴了")
        elif inherit_reinforce['amount'] < inherit_reinforce_num_required:
            result.append(
                "传承增强卷轴数量现有{}个，需要{}个".format(
                    inherit_reinforce['amount'],
                    inherit_reinforce_num_required,
                )
            )
        synthesis_book = self.synthesis_book
        if synthesis_book is None:
            result.append("没有{}合成书了".format(self.chosen_attribute))
        elif synthesis_book['amount'] < synthesis_book_num_required:
            result.append(
                "{}合成书数量现有{}本，需要{}本".format(
                    self.chosen_attribute,
                    synthesis_book['amount'],
                    synthesis_book_num_required,
                )
            )
        synthesis_reinforce = self.synthesis_reinforce
        if synthesis_reinforce is None:
            result.append("没有增强卷轴了")
        elif synthesis_reinforce['amount'] < synthesis_reinforce_num_required:
            result.append(
                "增强卷轴数量现有{}个，需要{}个".format(
                    synthesis_reinforce['amount'],
                    synthesis_reinforce_num_required,
                )
            )
        deputy_plant_num = len(self.auto_compound_pool_id)
        if deputy_plant_num < deputy_plant_num_required:
            result.append(
                "合成池数量现有{}个，需要{}个".format(
                    deputy_plant_num,
                    deputy_plant_num_required,
                )
            )
        return result

    def export_deputy_plant_to_synthesis(self, num):
        auto_compound_pool_id = list(self.auto_compound_pool_id)
        for plant_id in auto_compound_pool_id[:num]:
            self.auto_compound_pool_id.remove(plant_id)
            self.auto_synthesis_man.auto_synthesis_pool_id.add(plant_id)

    def get_deputy_plant(self):
        auto_compound_pool_id = list(self.auto_compound_pool_id)
        plant_id = auto_compound_pool_id[-1]
        auto_compound_pool_id.pop()
        self.auto_compound_pool_id.remove(plant_id)
        return plant_id

    def synthesis_plant(self, plant_id, num, refresh_signal):
        self.export_deputy_plant_to_synthesis(num)
        self.auto_synthesis_man.main_plant_id = plant_id
        self.auto_synthesis_man.synthesis_all(
            self.logger, refresh_signal=refresh_signal
        )
        plant_id = self.auto_synthesis_man.main_plant_id
        self.auto_synthesis_man.main_plant_id = None
        return plant_id

    def _exchange(self, id1, func):
        plant1 = self.repo.get_plant(id1)
        try:
            result = func()
        except Exception as e:
            if "amf返回结果为空" in str(e):
                msg = "可能由以下原因引起：参与复合的植物不见了、传承增强卷轴不够、传承书不够"
                self.logger.log("复合异常，已跳出复合。{}".format(msg))
                return False
            self.repo.refresh_repository()
            after_plant1 = self.repo.get_plant(id1)
            attr_name = self.attribute2plant_attribute[self.chosen_attribute]
            if not getattr(after_plant1, attr_name) == getattr(plant1, attr_name):
                self.logger.log("复合异常。检测传出植物前后属性一致，判断为传承失败。尝试重新传承")
                return self._exchange(id1, func)
            else:
                self.logger.log("复合异常。检测传出植物前后属性不一致，判断为传承成功。")
                return True
        return result["success"]

    def exchange_one(self, id1, id2, book_id, num):
        def run():
            return self.heritage_man.exchange_one(id1, id2, book_id, num)

        return self._exchange(id1, run)

    def exchange_all(self, id1, id2):
        def run():
            return self.heritage_man.exchange_all(id1, id2)

        return self._exchange(id1, run)

    def _synthesis(self, id1, id2, book_id, reinforce_num):
        try:
            result = self.auto_synthesis_man.synthesisMan.synthesis(
                id1,
                id2,
                book_id,
                reinforce_num,
            )
        except Exception as e:
            if "amf返回结果为空" in str(e):
                msg = "可能由以下原因引起：参与合成的植物不见了、增强卷轴不够、合成书不够"
                return {
                    "success": False,
                    "result": "合成异常，已跳出合成。{}".format(msg),
                }
            self.repo.refresh_repository()
            if self.repo.get_plant(id2) is None:
                return {
                    "success": True,
                    "result": "合成异常，但是底座植物不存在，所以判定为合成成功",
                }
            else:
                self.logger.log("合成异常，检测到底座还在，尝试重新合成")
                return self._synthesis(id1, id2, book_id, reinforce_num)
        return result

    def copy_source_plant(self, refresh_signal):
        copy_plant_id = self.get_deputy_plant()
        success = self.exchange_one(
            self.source_plant_id,
            copy_plant_id,
            self.inherit_book['id'],
            10 - self.k,
        )
        signal_block_emit(refresh_signal)
        if not success:
            self.logger.log("在复制植物时出现传承错误，中断复合")
            return None
        self.source_plant_id = self.synthesis_plant(
            self.source_plant_id, self.n1, refresh_signal
        )
        copy_plant_id = self.synthesis_plant(copy_plant_id, self.n2, refresh_signal)
        return copy_plant_id

    def compound_one_cycle(self, refresh_signal):
        self.check_data()
        if not self.need_compound():
            return False
        result = self.one_cycle_consume_check()
        if len(result) > 0:
            message = "统计复合一个循环所需要的材料时发现以下缺失：\n" + "\n".join(result) + "\n请补齐材料后开始复合"
            self.logger.log(message)
            return False
        for i in range(self.m):
            copy_plant_id = self.copy_source_plant(refresh_signal)
            if copy_plant_id is None:
                self.logger.log(f"复制第{i+1}个植物失败，中止复合")
            result = self._synthesis(
                self.liezhi_plant_id, copy_plant_id, self.synthesis_book['id'], 10
            )
            if not result["success"]:
                self.logger.log(result['result'])
                self.logger.log("合成异常，中止复合")
                return False
            self.logger.log("复制第{}个植物成功".format(i + 1))
        if self.allow_inherite2target:
            if not self.use_all_exchange:
                success = self.exchange_one(
                    self.liezhi_plant_id,
                    self.receiver_plant_id,
                    self.inherit_book['id'],
                    10,
                )
            else:
                success = self.exchange_all(
                    self.liezhi_plant_id,
                    self.receiver_plant_id,
                )
            if not success:
                self.logger.log("在将劣质双格满传给主力时出现传承错误，中断复合")
                return False
        return True

    def compound_loop(self, interrupt_event: Event, refresh_signal):
        is_first = True
        while True:
            if interrupt_event.is_set():
                self.logger.log("手动中止复合")
                return
            if not is_first:
                signal_block_emit(refresh_signal)
            if is_first:
                is_first = False
            continue_loop = self.compound_one_cycle(refresh_signal)
            if not continue_loop:
                break
        self.logger.log("复合完成")

    def save(self, save_dir):
        d = {
            "liezhi_plant_id": self.liezhi_plant_id,
            "receiver_plant_id": self.receiver_plant_id,
            "source_plant_id": self.source_plant_id,
            "use_all_exchange": self.use_all_exchange,
            "auto_compound_pool_id": self.auto_compound_pool_id,
            "n1": self.n1,
            "n2": self.n2,
            "k": self.k,
            "m": self.m,
            "chosen_attribute": self.chosen_attribute,
            "end_mantissa": self.end_mantissa,
            "end_exponent": self.end_exponent,
            "allow_inherite2target": self.allow_inherite2target,
        }
        if save_dir is not None:
            save_path = os.path.join(save_dir, "user_auto_compound_man")
            self.check_data(False)
            with open(save_path, "wb") as f:
                pickle.dump(
                    d,
                    f,
                )
        return d

    def load(self, load_dir):
        if isinstance(load_dir, dict):
            d = load_dir
        else:
            load_path = os.path.join(load_dir, "user_auto_compound_man")
            if os.path.exists(load_path):
                with open(load_path, "rb") as f:
                    d = pickle.load(f)

            else:
                d = {}
        for k, v in d.items():
            if hasattr(self, k):
                setattr(self, k, v)
        self.set_chosen_attribute(self.chosen_attribute)
        self.check_data(False)
