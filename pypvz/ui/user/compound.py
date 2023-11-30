import pickle
import os
from threading import Event
import concurrent.futures

from ...upgrade import quality_name_list
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
        self.name = "新复合方案"
        self.enabled = True
        self.source_plant_id = None
        self.liezhi_plant_id = None
        self.n1, self.n2, self.k, self.m = 2, 1, 5, 3
        self.end_mantissa = 1.0
        self.end_exponent = 1
        self.chosen_attribute = "HP特"

        self.need_quality_index = quality_name_list.index("魔神")
        self.auto_synthesis_man = AutoSynthesisMan(cfg, lib, repo)
        self.heritage_man = HeritageMan(cfg, lib)
        self.set_chosen_attribute(self.chosen_attribute)
        self.auto_synthesis_man.reinforce_number = 10
        self.auto_compound_pool_id = set()

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

    @property
    def deputy_plant_num_required(self):
        return (self.n1 + self.n2 + 1) * self.m

    def set_chosen_attribute(self, chosen_attribute):
        self.chosen_attribute = chosen_attribute
        self.auto_synthesis_man.chosen_attribute = self.chosen_attribute

    def check_data(self, refresh_repo=True):
        if refresh_repo:
            self.repo.refresh_repository()
        self.auto_synthesis_man.check_data(False)
        if self.source_plant_id is not None:
            if self.repo.get_plant(self.source_plant_id) is None:
                self.source_plant_id = None
        else:
            self.source_plant_id = None

    def need_compound(self, plant):
        now_attr = getattr(
            plant,
            self.attribute2plant_attribute[self.chosen_attribute],
        )
        target_attr = self.end_mantissa * (10 ** (self.end_exponent + 8))
        if now_attr >= target_attr:
            self.logger.log(f'对于方案"{self.name}"而言，主力数值已达到设定值')
            return False
        else:
            return True

    def one_cycle_consume(self):
        inherit_book_num_required = self.m
        inherit_reinforce_num_required = (10 - self.k) * self.m
        synthesis_book_num_required = self.deputy_plant_num_required
        synthesis_reinforce_num_required = synthesis_book_num_required * 10
        deputy_plant_num_required = synthesis_book_num_required

        return (
            self.chosen_attribute,
            inherit_book_num_required,
            inherit_reinforce_num_required,
            synthesis_book_num_required,
            synthesis_reinforce_num_required,
            deputy_plant_num_required,
        )

    def import_deputy_plant(self, plant_id_list):
        for plant_id in plant_id_list:
            self.auto_compound_pool_id.add(plant_id)

    def export_deputy_plant_to_synthesis(self, num):
        auto_compound_pool_id = list(self.auto_compound_pool_id)
        for plant_id in auto_compound_pool_id[:num]:
            self.auto_compound_pool_id.remove(plant_id)
            self.auto_synthesis_man.auto_synthesis_pool_id.add(plant_id)

    def get_deputy_plant(self):
        auto_compound_pool_id = list(self.auto_compound_pool_id)
        plant_id = auto_compound_pool_id[-1]
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

    def exchange_one(self, id1, id2, book_id, num):
        plant1 = self.repo.get_plant(id1)
        try:
            result = self.heritage_man.exchange_one(id1, id2, book_id, num)
        except Exception as e:
            if "amf返回结果为空" in str(e):
                msg = "可能由以下原因引起：参与复合的植物不见了、传承增强卷轴不够、传承书不够"
                self.logger.log("复合异常，已跳出复合。{}".format(msg))
                return False
            self.repo.refresh_repository()
            after_plant1 = self.repo.get_plant(id1)
            attr_name = self.attribute2plant_attribute[self.chosen_attribute]
            if getattr(after_plant1, attr_name) == getattr(plant1, attr_name):
                self.logger.log("复合异常。检测传出植物前后属性一致，判断为传承失败。尝试重新传承")
                return self.exchange_one(id1, id2, book_id, num)
            else:
                self.logger.log("复合异常。检测传出植物前后属性不一致，判断为传承成功。")
                return True
        return result["success"]

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
            self.logger.log(f'方案"{self.name}"在复制植物时出现传承错误，中断复合')
            return None
        self.source_plant_id = self.synthesis_plant(
            self.source_plant_id, self.n1, refresh_signal
        )
        copy_plant_id = self.synthesis_plant(copy_plant_id, self.n2, refresh_signal)
        return copy_plant_id

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

    def compound_one_cycle(self, refresh_signal):
        for i in range(self.m):
            copy_plant_id = self.copy_source_plant(refresh_signal)
            if copy_plant_id is None:
                self.logger.log(f'方案"{self.name}"复制第{i+1}个植物失败，中止复合')
            result = self._synthesis(
                self.liezhi_plant_id, copy_plant_id, self.synthesis_book['id'], 10
            )
            if not result["success"]:
                self.logger.log(result['result'])
                self.logger.log("自动复合中把复制出来的植物给劣质双格吃时发生合成异常，中止复合")
                return False
            self.logger.log("复制第{}个植物成功".format(i + 1))
        return True

    def serialize(self):
        return {
            "name": self.name,
            "enabled": self.enabled,
            "source_plant_id": self.source_plant_id,
            "need_quality_index": self.need_quality_index,
            "n1": self.n1,
            "n2": self.n2,
            "k": self.k,
            "m": self.m,
            "chosen_attribute": self.chosen_attribute,
            "end_mantissa": self.end_mantissa,
            "end_exponent": self.end_exponent,
        }

    def deserialize(self, d):
        for k, v in d.items():
            if hasattr(self, k):
                setattr(self, k, v)
        self.set_chosen_attribute(self.chosen_attribute)
        self.check_data(False)


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
        self.scheme_list: list[CompoundScheme] = []
        self.heritage_man = HeritageMan(cfg, lib)
        self.liezhi_plant_id = None
        self.receiver_plant_id = None
        self.allow_inherite2target = True
        self.auto_compound_pool_id = set()

    def new_scheme(self):
        self.scheme_list.append(
            CompoundScheme(self.cfg, self.lib, self.repo, self.logger)
        )

    def remove_scheme(self, scheme: CompoundScheme):
        self.scheme_list.remove(scheme)

    def need_compound(self):
        if self.receiver_plant_id is None:
            self.logger.log("未设置主力")
            return False
        plant = self.repo.get_plant(self.receiver_plant_id)
        if plant is None:
            self.logger.log("主力植物不存在")
            return False
        for scheme in self.scheme_list:
            if not scheme.enabled:
                continue
            if not scheme.need_compound(plant):
                return False
        return True

    def check_data(self, refresh_repo=True):
        if refresh_repo:
            self.repo.refresh_repository()
        if self.liezhi_plant_id is not None:
            if self.repo.get_plant(self.liezhi_plant_id) is None:
                self.liezhi_plant_id = None
        else:
            self.liezhi_plant_id = None
        if self.receiver_plant_id is not None:
            if self.repo.get_plant(self.receiver_plant_id) is None:
                self.receiver_plant_id = None
        else:
            self.receiver_plant_id = None
        auto_compound_pool_id = list(self.auto_compound_pool_id)
        for deputy_plant_id in auto_compound_pool_id:
            if self.repo.get_plant(deputy_plant_id) is None:
                self.auto_compound_pool_id.remove(deputy_plant_id)
        for scheme in self.scheme_list:
            scheme.check_data(False)

    def one_cycle_consume_check(self):
        result = []
        if self.liezhi_plant_id is None:
            result.append("未设置劣质双格植物")
        if self.receiver_plant_id is None:
            result.append("未设置主力植物")
        for scheme in self.scheme_list:
            if not scheme.enabled:
                continue
            if scheme.source_plant_id is None:
                result.append(f'方案"{scheme.name}"未设置底座植物')
        inherit_book_dict = {}
        synthesis_book_dict = {}
        quality_dict = {}
        (
            inherit_reinforce_num_required,
            synthesis_reinforce_num_required,
        ) = (0, 0)
        for scheme in self.scheme_list:
            if not scheme.enabled:
                continue
            (
                chosen_attribute,
                inherit_book_num_required,
                scheme_inherit_reinforce_num_required,
                scheme_synthesis_book_num_required,
                scheme_synthesis_reinforce_num_required,
                scheme_deputy_plant_num_required,
            ) = scheme.one_cycle_consume()
            inherit_book_dict[chosen_attribute] = (
                inherit_book_dict.get(chosen_attribute, 0) + inherit_book_num_required
            )
            inherit_reinforce_num_required += scheme_inherit_reinforce_num_required
            synthesis_book_dict[chosen_attribute] = (
                synthesis_book_dict.get(chosen_attribute, 0)
                + scheme_synthesis_book_num_required
            )
            synthesis_reinforce_num_required += scheme_synthesis_reinforce_num_required
            quality_dict[scheme.need_quality_index] = (
                quality_dict.get(scheme.need_quality_index, 0)
                + scheme_deputy_plant_num_required
            )
        for chosen_attribute, inherit_book_num_required in inherit_book_dict.items():
            inherit_book = self.repo.get_tool(
                self.attribute_inheritage_book_dict[chosen_attribute]
            )
            if inherit_book is None:
                result.append("没有{}传承书了".format(chosen_attribute))
            elif inherit_book['amount'] < inherit_book_num_required:
                result.append(
                    "{}传承书数量现有{}本，需要{}本".format(
                        chosen_attribute,
                        inherit_book['amount'],
                        inherit_book_num_required,
                    )
                )
        for (
            chosen_attribute,
            synthesis_book_num_required,
        ) in synthesis_book_dict.items():
            synthesis_book = self.repo.get_tool(
                self.attribute_compose_book_dict[chosen_attribute]
            )
            if synthesis_book is None:
                result.append("没有{}合成书了".format(chosen_attribute))
            elif synthesis_book['amount'] < synthesis_book_num_required:
                result.append(
                    "{}合成书数量现有{}本，需要{}本".format(
                        chosen_attribute,
                        synthesis_book['amount'],
                        synthesis_book_num_required,
                    )
                )

        inherit_all_book_num_required = 1
        inherit_all_book = self.repo.get_tool(self.lib.name2tool["全属性传承书"].id)
        if inherit_all_book is None or inherit_all_book['amount'] == 0:
            result.append("没有全属性传承书了")
        elif inherit_all_book['amount'] < inherit_all_book_num_required:
            result.append(
                "全属性传承书数量现有{}本，需要{}本".format(
                    inherit_all_book['amount'],
                    inherit_all_book_num_required,
                )
            )

        inherit_reinforce = self.repo.get_tool(self.lib.name2tool["传承增强卷轴"].id)
        if inherit_reinforce is None:
            result.append("没有传承增强卷轴了")
        elif inherit_reinforce['amount'] < inherit_reinforce_num_required:
            result.append(
                "传承增强卷轴数量现有{}个，需要{}个".format(
                    inherit_reinforce['amount'],
                    inherit_reinforce_num_required,
                )
            )
        synthesis_reinforce = self.repo.get_tool(self.lib.name2tool["增强卷轴"].id)
        if synthesis_reinforce is None:
            result.append("没有增强卷轴了")
        elif synthesis_reinforce['amount'] < synthesis_reinforce_num_required:
            result.append(
                "增强卷轴数量现有{}个，需要{}个".format(
                    synthesis_reinforce['amount'],
                    synthesis_reinforce_num_required,
                )
            )
        pool_quality_dict = {}
        for plant_id in self.auto_compound_pool_id:
            plant = self.repo.get_plant(plant_id)
            if plant is None:
                continue
            pool_quality_dict[plant.quality_index] = (
                pool_quality_dict.get(plant.quality_index, 0) + 1
            )
        for quality_index, deputy_plant_num_required in quality_dict.items():
            if quality_index not in pool_quality_dict:
                result.append("没有{}品质的植物".format(quality_name_list[quality_index]))
            elif pool_quality_dict[quality_index] < deputy_plant_num_required:
                result.append(
                    "{}品质的植物数量现有{}个，需要{}个".format(
                        quality_name_list[quality_index],
                        pool_quality_dict[quality_index],
                        deputy_plant_num_required,
                    )
                )
        return result

    def get_plant_id_list(self, num, quality_index):
        auto_compound_pool_id = list(self.auto_compound_pool_id)
        result = []
        for plant_id in auto_compound_pool_id:
            plant = self.repo.get_plant(plant_id)
            if plant is None:
                continue
            if plant.quality_index == quality_index:
                result.append(plant_id)
            if len(result) == num:
                break
        if num > len(result):
            return None
        for plant_id in result:
            self.auto_compound_pool_id.remove(plant_id)
        return result

    def exchange_all(self, id1, id2):
        plant1 = self.repo.get_plant(id1)
        try:
            result = self.heritage_man.exchange_all(id1, id2)
        except Exception as e:
            if "amf返回结果为空" in str(e):
                msg = "可能由以下原因引起：参与全传的植物不见了、全传不够"
                self.logger.log("复合异常，已跳出复合。{}".format(msg))
                return False
            self.repo.refresh_repository()
            after_plant1 = self.repo.get_plant(id1)
            for attr_name in self.attribute2plant_attribute.values()[:6]:
                if getattr(after_plant1, attr_name) != getattr(plant1, attr_name):
                    self.logger.log("全传异常。检测传出植物前后属性不一致，判断为传承成功。")
                    return True
            self.logger.log("全传异常。检测传出植物前后属性一致，判断为传承失败。尝试重新传承")
            return self.exchange_all(id1, id2)
        return result["success"]

    def compound_one_cycle(self, refresh_signal):
        self.check_data()
        if not self.need_compound():
            return False
        result = self.one_cycle_consume_check()
        enabled_scheme_list = [scheme for scheme in self.scheme_list if scheme.enabled]
        if len(result) > 0:
            message = "统计复合一个循环所需要的材料时发现以下缺失：\n" + "\n".join(result) + "\n请补齐材料后开始复合"
            self.logger.log(message)
            return False
        for scheme in self.scheme_list:
            scheme.liezhi_plant_id = self.liezhi_plant_id

        for scheme in enabled_scheme_list:
            plant_list = self.get_plant_id_list(
                scheme.deputy_plant_num_required, scheme.need_quality_index
            )
            if plant_list is None:
                self.logger.log(
                    f'方案"{scheme.name}"复合所需的{quality_name_list[scheme.need_quality_index]}植物数量不足，中止复合'
                )
                return False
            scheme.import_deputy_plant(plant_list)

        # for scheme in enabled_scheme_list:
        #     scheme.compound_one_cycle(refresh_signal)

        futures = []
        with concurrent.futures.ThreadPoolExecutor(max_workers=6) as executor:
            for scheme in enabled_scheme_list:
                futures.append(
                    executor.submit(scheme.compound_one_cycle, refresh_signal)
                )
        concurrent.futures.wait(futures, return_when=concurrent.futures.ALL_COMPLETED)
        success_list = []
        for future, scheme in zip(futures, enabled_scheme_list):
            try:
                success_list.append(future.result())
            except Exception as e:
                if isinstance(e, RuntimeError):
                    self.logger.log(f'方案"{scheme.name}"自动复合异常。异常原因：{str(e)}')
                else:
                    self.logger.log(f'方案"{scheme.name}"自动复合异常。异常类型：{type(e).__name__}')
                return False
        flag = False
        for s, scheme in zip(success_list, enabled_scheme_list):
            if not s:
                flag = True
                self.logger.log(f'方案"{scheme.name}"自动复合失败')
        if flag:
            return False

        if self.allow_inherite2target:
            success = self.exchange_all(
                self.liezhi_plant_id,
                self.receiver_plant_id,
            )
            if not success:
                self.logger.log("在将劣质双格全传给主力时出现传承错误，中断复合")
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
            "auto_compound_pool_id": self.auto_compound_pool_id,
            "allow_inherite2target": self.allow_inherite2target,
            "auto_compound_scheme_serialized_list": [
                scheme.serialize() for scheme in self.scheme_list
            ],
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
        self.check_data(False)
        if "auto_compound_scheme_serialized_list" in d:
            auto_compound_scheme_serialized_list = d[
                'auto_compound_scheme_serialized_list'
            ]
            self.scheme_list = [
                CompoundScheme(self.cfg, self.lib, self.repo, self.logger)
                for _ in range(len(auto_compound_scheme_serialized_list))
            ]
            for scheme, serialized_scheme in zip(
                self.scheme_list, d["auto_compound_scheme_serialized_list"]
            ):
                scheme.deserialize(serialized_scheme)
