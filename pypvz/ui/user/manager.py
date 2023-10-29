import pickle
import os
from threading import Event
from time import sleep
from ... import (
    Config,
    Repository,
    Library,
    SynthesisMan,
    HeritageMan,
)
from ..message import Logger
from ... import FubenRequest


class AutoSynthesisMan:
    def __init__(self, cfg: Config, lib: Library, repo: Repository):
        self.lib = lib
        self.cfg = cfg
        self.repo = repo
        self.synthesisMan = SynthesisMan(cfg, lib)
        self.main_plant_id = None
        self.chosen_attribute = "HP"
        self.reinforce_number = 10
        self.auto_synthesis_pool_id = set()
        self.attribute_list = ["HP", "攻击", "命中", "闪避", "穿透", "护甲", "HP特", "攻击特"]
        self.attribute_book_dict = {
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
        self.end_mantissa = 1.0
        self.end_exponent = 0
        self.force_synthesis = False

    def check_data(self, refresh_repo=True):
        if refresh_repo:
            self.repo.refresh_repository()
        if isinstance(self.main_plant_id, int):
            if self.repo.get_plant(self.main_plant_id) is None:
                self.main_plant_id = None
        else:
            self.main_plant_id = None
        auto_synthesis_pool_id = list(self.auto_synthesis_pool_id)
        for deputy_plant_id in auto_synthesis_pool_id:
            if self.repo.get_plant(deputy_plant_id) is None:
                self.auto_synthesis_pool_id.remove(deputy_plant_id)

    def get_max_attribute_plant_id(self):
        auto_synthesis_pool_id = list(self.auto_synthesis_pool_id)
        max_attribute_value = 0
        max_plant_id = None
        for deputy_plant_id in auto_synthesis_pool_id:
            plant = self.repo.get_plant(deputy_plant_id)
            if plant is None:
                continue
            attribute_value = getattr(
                plant, self.attribute2plant_attribute[self.chosen_attribute]
            )
            if attribute_value > max_attribute_value:
                max_attribute_value = attribute_value
                max_plant_id = deputy_plant_id
        return max_plant_id

    def _synthesis(self, id1, id2, attribute_name):
        result = {
            "success": False,
            "result": "合成出错，请在确定底座无误后重新尝试(注意部分情况下尽管出错但是仍然合成了，请注意)。以下为详细报错原因：",
        }
        try:
            response = self.synthesisMan.synthesis(
                id1,
                id2,
                self.attribute_book_dict[attribute_name],
                self.reinforce_number,
            )
        except RuntimeError as e:
            result['result'] += str(e)
            return result
        if response.status != 0:
            try:
                result['result'] += response.body.description
            except:
                result["result"] += str(response.body)
            return result
        result["success"] = True
        result['result'] = "合成成功"
        return result

    def synthesis(self, need_check=True):
        if need_check:
            self.check_data(need_check)
        if self.main_plant_id is None:
            return {"success": False, "result": "未设置底座"}
        if len(self.auto_synthesis_pool_id) == 0:
            return {"success": False, "result": "合成池为空"}
        book = self.repo.get_tool(self.attribute_book_dict[self.chosen_attribute])
        if book is None:
            return {
                "success": False,
                "result": "没有{}合成书了".format(self.chosen_attribute),
            }
        book_amount = book['amount']
        if not book_amount > 0:
            return {"success": False, "result": f"{self.chosen_attribute}合成书数量不足"}
        reinforce = self.repo.get_tool(self.lib.name2tool["增强卷轴"].id)
        if reinforce is None:
            return {"success": False, "result": "没有增强卷轴了"}
        reinforce_amount = reinforce['amount']
        if reinforce_amount < self.reinforce_number:
            return {"success": False, "result": f"增强卷轴数量不足10个(目前数量：{reinforce_amount})"}
        deputy_plant_id = list(self.auto_synthesis_pool_id)[0]
        result = self._synthesis(
            deputy_plant_id, self.main_plant_id, self.chosen_attribute
        )
        if result['success']:
            self.auto_synthesis_pool_id.remove(deputy_plant_id)
            self.main_plant_id = deputy_plant_id
            book['amount'] = max(book['amount'] - 1, 0)
            if book['amount'] == 0:
                for i, tool in enumerate(self.repo.tools):
                    if tool['id'] == book['id']:
                        self.repo.tools.pop(i)
                        break
        return result

    def synthesis_all(
        self,
        logger: Logger,
        interrupt_event: Event = None,
        need_synthesis=None,
        synthesis_number=None,
        refresh_all_signal=None,
    ):
        try:
            length = len(self.auto_synthesis_pool_id)
            if synthesis_number is not None:
                length = min(synthesis_number, length)
            if length == 0:
                logger.log("合成池为空")
                return
            elif length < 0:
                logger.log("合成次数不能为负数")
                return
            self.check_data()
            while not (len(self.auto_synthesis_pool_id) == 0) and length > 0:
                if interrupt_event is not None and interrupt_event.is_set():
                    interrupt_event.clear()
                    logger.log("中止合成")
                    return
                if need_synthesis is not None:
                    if not need_synthesis():
                        return
                result = self.synthesis(need_check=False)
                logger.log(result['result'])
                self.check_data()
                if refresh_all_signal is not None:
                    refresh_all_signal.emit()
                if not result["success"]:
                    logger.log("合成异常，已跳出合成")
                    return
                length -= 1
            logger.log("合成完成")
        except Exception as e:
            logger.log("合成异常。异常种类：{}".format(type(e).__name__))
            if self.force_synthesis:
                logger.log("重启合成")
                while True:
                    try:
                        if interrupt_event is not None and interrupt_event.is_set():
                            interrupt_event.clear()
                            logger.log("中止合成")
                            return
                        self.check_data()
                        break
                    except Exception as e:
                        logger.log(
                            "重启异常，暂停1秒，继续重启（一直异常请手动终止）。异常种类：{}".format(type(e).__name__)
                        )
                        sleep(1)
                if self.main_plant_id is None:
                    logger.log("重新设置底座为合成池中最大属性的植物")
                    plant_id = self.get_max_attribute_plant_id()
                    self.main_plant_id = plant_id
                    self.auto_synthesis_pool_id.remove(plant_id)
                self.synthesis()

    def save(self, save_dir):
        save_path = os.path.join(save_dir, "user_autosynthesisman")
        with open(save_path, "wb") as f:
            pickle.dump(
                {
                    "main_plant_id": self.main_plant_id,
                    "chosen_attribute": self.chosen_attribute,
                    "auto_synthesis_pool_id": self.auto_synthesis_pool_id,
                    "reinforce_number": self.reinforce_number,
                    "end_mantissa": self.end_mantissa,
                    "end_exponent": self.end_exponent,
                    "force_synthesis": self.force_synthesis,
                },
                f,
            )

    def load(self, load_dir):
        load_path = os.path.join(load_dir, "user_autosynthesisman")
        if os.path.exists(load_path):
            with open(load_path, "rb") as f:
                d = pickle.load(f)
            for k, v in d.items():
                if hasattr(self, k):
                    setattr(self, k, v)
        self.check_data()


class AutoCompoundMan:
    def __init__(self, cfg: Config, lib: Library, repo: Repository, logger: Logger):
        self.lib = lib
        self.cfg = cfg
        self.repo = repo
        self.logger = logger
        self.auto_synthesis_man = AutoSynthesisMan(cfg, lib, repo)
        self.heitage_man = HeritageMan(cfg, lib)
        self.liezhi_plant_id = None
        self.receiver_plant_id = None
        self.source_plant_id = None
        self.use_all_exchange = True
        self.auto_synthesis_pool_id = set()
        self.n1, self.n2, self.k, self.m = 2, 1, 5, 3
        self.chosen_attribute = "HP特"
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
        self.force_compound = True
        self.set_force_compound(True)
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

    def set_force_compound(self, force_compound):
        self.force_compound = force_compound
        self.auto_synthesis_man.force_synthesis = self.force_compound
        
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
        auto_synthesis_pool_id = list(self.auto_synthesis_pool_id)
        for deputy_plant_id in auto_synthesis_pool_id:
            if self.repo.get_plant(deputy_plant_id) is None:
                self.auto_synthesis_pool_id.remove(deputy_plant_id)

    def one_cycle_consume_check(self):
        result = []
        inherit_book_num_required = self.m + (0 if self.use_all_exchange else 1)
        inherit_reinforce_num_required = self.k * self.m + (
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
            if inherit_all_book is None or inherit_book['amount'] == 0:
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
        deputy_plant_num = len(self.auto_synthesis_pool_id)
        if deputy_plant_num < deputy_plant_num_required:
            result.append(
                "合成池数量现有{}个，需要{}个".format(
                    deputy_plant_num,
                    deputy_plant_num_required,
                )
            )
        return result

    def export_deputy_plant_to_synthesis(self, num):
        auto_synthesis_pool_id = list(self.auto_synthesis_pool_id)
        for plant_id in auto_synthesis_pool_id[:num]:
            self.auto_synthesis_pool_id.remove(plant_id)
            self.auto_synthesis_man.auto_synthesis_pool_id.add(plant_id)

    def get_deputy_plant(self):
        auto_synthesis_pool_id = list(self.auto_synthesis_pool_id)
        plant_id = auto_synthesis_pool_id[-1]
        auto_synthesis_pool_id.pop()
        self.auto_synthesis_pool_id.remove(plant_id)
        return plant_id

    def synthesis_plant(self, plant_id, num):
        self.export_deputy_plant_to_synthesis(num)
        self.auto_synthesis_man.main_plant_id = plant_id
        self.auto_synthesis_man.synthesis_all(
            self.logger,
        )
        plant_id = self.auto_synthesis_man.main_plant_id
        self.auto_synthesis_man.main_plant_id = None
        return plant_id

    def _exchange(self, id1, func):
        cnt, max_retry = 0, 5
        plant1 = self.repo.get_plant(id1)
        while cnt < max_retry:
            cnt += 1
            try:
                result = func()
                break
            except Exception as e:
                self.logger.log("在复制植物时出现传承异常，异常类型：{}".format(type(e).__name__))
                if not self.force_compound:
                    result = {
                        "success": False,
                    }
                    break
                self.repo.refresh_repository()
                after_plant1 = self.repo.get_plant(id1)
                attr_name = self.attribute2plant_attribute[self.chosen_attribute]
                if not getattr(after_plant1, attr_name) == getattr(plant1, attr_name):
                    self.logger.log(
                        "检测传出植物前后属性一致，判断为传承失败，尝试暂停1秒后重新传承，最多再尝试{}次".format(
                            max_retry - cnt
                        )
                    )
                    sleep(1)
                else:
                    self.logger.log("检测传出植物前后属性不一致，判断为传承成功，继续复合")
                    result = {
                        "success": True,
                    }
                    break
        else:
            self.logger.log(f"尝试{max_retry}次传承失败，中止复合")
            result = {
                "success": False,
            }
        return result["success"]

    def exchange_one(self, id1, id2, book_id, num):
        def run():
            return self.heitage_man.exchange_one(id1, id2, book_id, num)

        return self._exchange(id1, run)

    def exchange_all(self, id1, id2):
        def run():
            return self.heitage_man.exchange_all(id1, id2)

        return self._exchange(id1, run)

    def _synthesis(self, id1, id2, book_id, reinforce_num):
        cnt, max_retry = 0, 5
        while cnt < max_retry:
            cnt += 1
            try:
                response = self.auto_synthesis_man.synthesisMan.synthesis(
                    id1,
                    id2,
                    book_id,
                    reinforce_num,
                )
                if response.status != 0:
                    result = {
                        "success": False,
                        "result": response.body.description,
                    }
                else:
                    result = {
                        "success": True,
                        "result": "合成成功",
                    }
                break
            except Exception as e:
                self.logger.log("合成植物时出现异常，异常类型：{}".format(type(e).__name__))
                if not self.force_compound:
                    result = {
                        "success": False,
                        "result": "合成失败",
                    }
                    break
                self.repo.refresh_repository()
                if self.repo.get_plant(id2) is not None:
                    self.logger.log(
                        "检测被吃植物仍然存在，判断为合成失败，尝试暂停1秒后重新合成，最多再尝试{}次".format(
                            max_retry - cnt
                        )
                    )
                    sleep(1)
                else:
                    self.logger.log("检测被吃植物消失，判断为合成成功，继续复合")
                    result = {
                        "success": True,
                        "result": "合成成功",
                    }
                    break
        else:
            self.logger.log(f"尝试{max_retry}次合成失败，中止复合")
            result = {
                "success": False,
                "result": "合成失败",
            }
        return result

    def copy_source_plant(
        self,
    ):
        copy_plant_id = self.get_deputy_plant()
        success = self.exchange_one(
            self.source_plant_id,
            copy_plant_id,
            self.inherit_book['id'],
            10 - self.k,
        )
        if not success:
            self.logger.log("在复制植物时出现传承错误，中断复合")
            return None
        self.source_plant_id = self.synthesis_plant(self.source_plant_id, self.n1)
        copy_plant_id = self.synthesis_plant(copy_plant_id, self.n2)
        return copy_plant_id

    def compound_one_cycle(self):
        self.check_data()
        result = self.one_cycle_consume_check()
        if len(result) > 0:
            message = "统计复合一个循环所需要的材料时发现以下缺失：\n" + "\n".join(result) + "\n请补齐材料后开始复合"
            self.logger.log(message)
            return False
        if not self.need_compound():
            return False
        for i in range(self.m):
            copy_plant_id = self.copy_source_plant()
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

    def compound_loop(self, interrupt_event: Event, refresh_all_signal):
        is_first = True
        while True:
            if interrupt_event.is_set():
                self.logger.log("手动中止复合")
                return
            if not is_first:
                refresh_all_signal.emit()
            if is_first:
                is_first = False
            continue_loop = self.compound_one_cycle()
            if not continue_loop:
                break
        self.logger.log("复合完成")

    def save(self, save_dir):
        save_path = os.path.join(save_dir, "user_auto_compound_man")
        self.check_data(False)
        with open(save_path, "wb") as f:
            pickle.dump(
                {
                    "liezhi_plant_id": self.liezhi_plant_id,
                    "receiver_plant_id": self.receiver_plant_id,
                    "source_plant_id": self.source_plant_id,
                    "use_all_exchange": self.use_all_exchange,
                    "auto_synthesis_pool_id": self.auto_synthesis_pool_id,
                    "n1": self.n1,
                    "n2": self.n2,
                    "k": self.k,
                    "m": self.m,
                    "chosen_attribute": self.chosen_attribute,
                    "end_mantissa": self.end_mantissa,
                    "end_exponent": self.end_exponent,
                    "force_compound": self.force_compound,
                },
                f,
            )

    def load(self, load_dir):
        load_path = os.path.join(load_dir, "user_auto_compound_man")
        if os.path.exists(load_path):
            with open(load_path, "rb") as f:
                d = pickle.load(f)
            for k, v in d.items():
                if hasattr(self, k):
                    setattr(self, k, v)
            self.set_force_compound(self.force_compound)
            self.set_chosen_attribute(self.chosen_attribute)
        self.check_data(False)




class FubenMan:
    
    def __init__(self, cfg: Config):
        self.cfg = cfg
        self.fuben_request = FubenRequest(cfg)
        
    def get_caves(self, layer):
        return self.fuben_request.get_caves(layer)