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
    SynthesisMan,
    HeritageMan,
    WebRequest,
)
from ..message import Logger
from ... import FubenRequest
from ...fuben import FubenCave
from ...utils.recover import RecoverMan
from ..wrapped import signal_block_emit


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
        self.force_synthesis = True

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

    def check_data_retry(self, interrupt_event, logger, refresh_repo=True):
        while True:
            try:
                if interrupt_event is not None and interrupt_event.is_set():
                    logger.log("中止合成")
                    return
                self.check_data(refresh_repo=refresh_repo)
                break
            except Exception as e:
                logger.log("重启异常，暂停1秒，继续重启（一直异常请手动终止）。异常种类：{}".format(type(e).__name__))
                sleep(1)

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
        response = self.synthesisMan.synthesis(
            id1,
            id2,
            self.attribute_book_dict[attribute_name],
            self.reinforce_number,
        )
        if response.status != 0:
            result = {
                "success": False,
                "result": "合成出错。以下为详细报错原因：",
            }
            try:
                result['result'] += response.body.description
            except:
                result["result"] += str(response.body)
            return result
        if "fight" not in response.body:
            result = {
                "success": False,
                "result": "合成出错。以下为详细报错原因：",
            }
            result['result'] += str(response.body)
            return result
        return {
            "success": True,
            "result": "合成成功",
            "body": response.body,
        }

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
        cnt, max_retry = 0, 10
        while cnt < max_retry:
            cnt += 1
            try:
                result = self._synthesis(
                    deputy_plant_id, self.main_plant_id, self.chosen_attribute
                )
                if not result["success"] and "频繁" in result['result']:
                    raise RuntimeError(result['result'])
                break
            except RuntimeError as e:
                if "amf返回结果为空" in str(e):
                    return {
                        "success": False,
                        "result": "合成异常，已跳出合成。异常信息：{}".format(str(e)),
                    }
            except Exception as e:
                if not self.force_synthesis:
                    result = {
                        "success": False,
                        "result": "合成异常，已跳出合成。异常类型：{}".format(type(e).__name__),
                    }
                    break
                self.check_data()
                if self.main_plant_id is None:
                    result = {
                        "success": True,
                        "result": "合成异常，异常类型：{}。底座植物不存在，判定为合成成功".format(
                            type(e).__name__
                        ),
                    }
                    break
                logging.info(
                    "合成异常。异常种类：{}。底座植物存在，判定为合成失败，暂停1秒继续合成。还能最多尝试{}次".format(
                        type(e).__name__, max_retry - cnt
                    )
                )
                sleep(1)

        if result['success']:
            body = result['body']
            self.auto_synthesis_pool_id.remove(deputy_plant_id)
            deputy_plant = self.repo.get_plant(deputy_plant_id)
            deputy_plant.fight += int(body['fight'])
            deputy_plant.hp_max += int(body['hp'])
            deputy_plant.attack += int(body['attack'])
            deputy_plant.armor += int(body['miss'])
            deputy_plant.piercing += int(body['precision'])
            deputy_plant.miss += int(body['new_miss'])
            deputy_plant.precision += int(body['new_precision'])
            deputy_plant.speed += int(body['speed'])
            self.repo.remove_plant(self.main_plant_id)
            self.main_plant_id = deputy_plant_id
            reinforce['amount'] = max(reinforce['amount'] - self.reinforce_number, 0)
            if reinforce['amount'] == 0:
                self.repo.remove_tool(reinforce['id'])
            book['amount'] = max(book['amount'] - 1, 0)
            if book['amount'] == 0:
                self.repo.remove_tool(book['id'])
        return result

    def synthesis_all(
        self,
        logger: Logger,
        interrupt_event: Event = None,
        need_synthesis=None,
        synthesis_number=None,
        refresh_signal=None,
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
            signal_block_emit(refresh_signal)
            while not (len(self.auto_synthesis_pool_id) == 0) and length > 0:
                if interrupt_event is not None and interrupt_event.is_set():
                    logger.log("中止合成")
                    return
                if need_synthesis is not None:
                    if not need_synthesis():
                        return
                result = self.synthesis(need_check=False)
                logger.log(result['result'])
                self.check_data(False)
                signal_block_emit(refresh_signal)
                if not result["success"]:
                    logger.log("合成异常，已跳出合成")
                    return
                length -= 1
            logger.log("合成完成")
        except Exception as e:
            logger.log("合成异常。异常种类：{}".format(type(e).__name__))
            if self.force_synthesis:
                logger.log("重启合成")
                self.check_data_retry(interrupt_event, logger)
                if self.main_plant_id is None:
                    logger.log("重新设置底座为合成池中最大属性的植物")
                    plant_id = self.get_max_attribute_plant_id()
                    self.main_plant_id = plant_id
                    if plant_id in self.auto_synthesis_pool_id:
                        self.auto_synthesis_pool_id.remove(plant_id)
                self.synthesis_all(
                    logger,
                    interrupt_event=interrupt_event,
                    need_synthesis=need_synthesis,
                    synthesis_number=synthesis_number,
                    refresh_signal=refresh_signal,
                )
            else:
                if refresh_signal is not None:
                    self.check_data_retry(interrupt_event, logger)
                    signal_block_emit(refresh_signal)
                logger.log("合成异常，已跳出合成")

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
        self.check_data(False)


class AutoCompoundMan:
    def __init__(self, cfg: Config, lib: Library, repo: Repository, logger: Logger):
        self.lib = lib
        self.cfg = cfg
        self.repo = repo
        self.logger = logger
        self.auto_synthesis_man = AutoSynthesisMan(cfg, lib, repo)
        self.heritage_man = HeritageMan(cfg, lib)
        self.liezhi_plant_id = None
        self.receiver_plant_id = None
        self.source_plant_id = None
        self.use_all_exchange = True
        self.allow_inherite2target = True
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
            return self.heritage_man.exchange_one(id1, id2, book_id, num)

        return self._exchange(id1, run)

    def exchange_all(self, id1, id2):
        def run():
            return self.heritage_man.exchange_all(id1, id2)

        return self._exchange(id1, run)

    def _synthesis(self, id1, id2, book_id, reinforce_num):
        cnt, max_retry = 0, 10
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
                    if "频繁" in result['result']:
                        raise RuntimeError(result['result'])
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
                    "allow_inherite2target": self.allow_inherite2target,
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


class SingleFubenCave:
    def __init__(self, cave: FubenCave, layer, number, use_sand=False, enabled=True):
        self.name = cave.name
        self.cave_id = cave.cave_id
        self.rest_count = cave.rest_count
        self.layer = layer
        self.number = number
        self.use_sand = use_sand
        self.enabled = enabled


class FubenMan:
    def __init__(self, cfg: Config, repo: Repository, logger: Logger):
        self.cfg = cfg
        self.repo = repo
        self.logger = logger
        self.fuben_request = FubenRequest(cfg)
        self.recover_man = RecoverMan(cfg, repo)
        self.caves: list[SingleFubenCave] = []
        self.team = []
        self.show_lottery = False
        self.need_recovery = False
        self.recover_hp_choice = "中级血瓶"

    def add_cave(self, cave: FubenCave, layer, number, use_sand=False, enabled=True):
        for sc in self.caves:
            if cave.cave_id == sc.cave_id:
                return
        sc = SingleFubenCave(cave, layer, number, use_sand, enabled)
        self.caves.append(sc)

    def delete_cave(self, cave_id):
        self.caves = list(filter(lambda x: x.cave_id != cave_id, self.caves))

    def get_caves(self, layer):
        return self.fuben_request.get_caves(layer, self.logger)

    def _recover(self):
        cnt, max_retry = 0, 5
        success_num_all = 0
        while cnt < max_retry:
            recover_list = list(
                filter(
                    lambda x: x is not None and x.hp_now == 0,
                    [self.repo.get_plant(plant_id) for plant_id in self.team],
                )
            )
            if len(recover_list) == 0:
                return True
            success_num, fail_num = self.recover_man.recover_list(
                recover_list, choice=self.recover_hp_choice
            )
            success_num_all += success_num
            if fail_num == 0:
                break
            self.logger.log("尝试恢复植物血量。成功{}，失败{}".format(success_num, fail_num))
            self.repo.refresh_repository(logger=self.logger)
            cnt += 1
        else:
            self.logger.log("尝试恢复植物血量失败，退出运行")
            return False
        if success_num_all > 0:
            self.logger.log("成功给{}个植物回复血量".format(success_num_all))
        return True

    def auto_challenge(self, stop_channel: Queue):
        _cave_map = {}

        def get_fuben_cave(layer, number) -> FubenCave:
            caves = _cave_map.get(layer, None)
            if caves is None:
                _cave_map[layer] = caves = self.fuben_request.get_caves(
                    layer, self.logger
                )
            assert number >= 1 and number <= len(caves)
            return caves[number - 1]

        for sc in self.caves:
            if not sc.enabled:
                continue
            cave = get_fuben_cave(sc.layer, sc.number)
            if cave.rest_count == 0:
                continue
            challenge_count = cave.rest_count if cave.rest_count > 0 else 1
            for _ in range(challenge_count):
                if self.need_recovery:
                    if not self._recover():
                        return
                message = "挑战副本:{}".format(
                    cave.name,
                )
                try:
                    result = self.fuben_request.challenge(
                        sc.cave_id, self.team, logger=self.logger
                    )
                except Exception as e:
                    self.logger.log("副本挑战异常，异常类型：{}".format(type(e).__name__))
                    return
                success, result = result["success"], result["result"]
                if not success:
                    message = message + "失败. 原因: {}.".format(result)
                    self.logger.log(message)
                    return
                else:
                    message = message + "成功. "
                message = message + "挑战结果：{}".format(
                    "胜利" if result['is_winning'] else "失败"
                )
                self.logger.log(message)
                if stop_channel.qsize() > 0:
                    return

    def save(self, save_dir):
        save_path = os.path.join(save_dir, "auto_fuben")
        with open(save_path, "wb") as f:
            pickle.dump(
                {
                    "caves": self.caves,
                    "team": self.team,
                    "show_lottery": self.show_lottery,
                    "need_recovery": self.need_recovery,
                    "recover_hp_choice": self.recover_hp_choice,
                },
                f,
            )

    def load(self, load_dir):
        load_path = os.path.join(load_dir, "auto_fuben")
        if os.path.exists(load_path):
            with open(load_path, "rb") as f:
                d = pickle.load(f)
            for k, v in d.items():
                if hasattr(self, k):
                    setattr(self, k, v)


class TerritoryMan:
    def __init__(self, cfg: Config, repo: Repository, logger: Logger):
        self.cfg = cfg
        self.repo = repo
        self.logger = logger
        self.wr = WebRequest(cfg)
        self.difficulty_choice = 3
        self.team = []

    def check_data(self, refresh_repo=True):
        if refresh_repo:
            self.repo.refresh_repository()
        self.team = [
            plant_id
            for plant_id in self.team
            if self.repo.get_plant(plant_id) is not None
        ]

    def challenge(self):
        body = [float(2000 + self.difficulty_choice), [], float(1), float(0)]
        response = self.wr.amf_post_retry(
            body,
            "api.territory.challenge",
            "/pvz/amf/",
            "挑战领地",
            logger=self.logger,
        )
        if response.status != 0:
            return {"success": False, "result": response.body.description}
        else:
            return {"success": True, "result": response.body}

    def auto_challenge(self, stop_channel: Queue):
        while True:
            message = f"挑战领地难度{self.difficulty_choice}"
            try:
                result = self.challenge()
            except Exception as e:
                self.logger.log("挑战领地异常，异常类型：{}".format(type(e).__name__))
                return
            success, result = result["success"], result["result"]
            if not success:
                message = message + "失败. 原因: {}.".format(result)
                self.logger.log(message)
                return
            else:
                message = message + "成功. "
            message = message + "挑战结果：{}".format(
                "胜利" if result['fight']['is_winning'] else "失败"
            )
            message = message + ". 现在荣誉: {}".format(result['honor'])
            self.logger.log(message)
            if stop_channel.qsize() > 0:
                return

    def release_plant(self, user_id):
        body = [float(user_id)]
        response = self.wr.amf_post_retry(
            body,
            "api.territory.quit",
            "/pvz/amf/",
            "释放领地",
        )
        if response.status != 0:
            if response.body.description == "重置所有植物成功!":
                return {
                    "success": True,
                    "result": "释放领地所有植物成功",
                }
            return {"success": False, "result": response.body.description}
        return {"success": False, "result": str(response.body)}

    def upload_team(self):
        if len(self.team) > 5:
            logging.warning("上场植物数超过5，但上场植物数只能小于等于5")
        for i, plant_id in enumerate(self.team[:5]):
            body = [float(f"100{i+1}"), [int(plant_id)], float(1), float(0)]
            response = self.wr.amf_post_retry(
                body,
                "api.territory.challenge",
                "/pvz/amf/",
                "上领地植物",
                logger=self.logger,
            )
            if response.status != 0:
                return {"success": False, "result": response.body.description}
        return {"success": True, "result": "共上场{}个植物".format(len(self.team))}

    def save(self, save_dir):
        save_path = os.path.join(save_dir, "auto_territory")
        with open(save_path, "wb") as f:
            pickle.dump(
                {
                    "difficulty_choice": self.difficulty_choice,
                    "team": self.team,
                },
                f,
            )

    def load(self, load_dir):
        load_path = os.path.join(load_dir, "auto_territory")
        if os.path.exists(load_path):
            with open(load_path, "rb") as f:
                d = pickle.load(f)
            for k, v in d.items():
                if hasattr(self, k):
                    setattr(self, k, v)


class DailyMan:
    def __init__(self, cfg, logger: Logger):
        self.cfg = cfg
        self.wr = WebRequest(cfg)
        self.logger = logger

    def vip_reward_acquire(self):
        response = self.wr.amf_post_retry(
            [],
            "api.vip.awards",
            "/pvz/amf/",
            "vip每日奖励",
            logger=self.logger,
        )
        if response.status != 0:
            return {"success": False, "result": response.body.description}
        else:
            return {"success": True, "result": response.body}

    def daily_sign(self):
        response = self.wr.amf_post_retry(
            [],
            "api.active.sign",
            "/pvz/amf/",
            "每日签到",
            logger=self.logger,
        )
        if response.status != 0:
            return {"success": False, "result": response.body.description}
        else:
            return {"success": True, "result": response.body}


class GardenMan:
    def __init__(self, cfg: Config, repo: Repository, lib: Library, logger: Logger):
        self.cfg = cfg
        self.repo = repo
        self.lib = lib
        self.wr = WebRequest(cfg)
        self.logger = logger
        self.team = []

    def check_data(self, refresh_repo=True):
        if refresh_repo:
            self.repo.refresh_repository()
        self.team = [
            plant_id
            for plant_id in self.team
            if self.repo.get_plant(plant_id) is not None
        ]

    def challenge_boss(self):
        if self.team is None or len(self.team) == 0:
            self.logger.log("未设置队伍")
            return False
        try:
            self.wr.amf_post_retry(
                [float(1), float(3), float(2), self.team],
                "api.garden.challenge",
                "/pvz/amf/",
                "挑战花园boss",
                logger=self.logger,
                exit_response=True,
            )
        except Exception as e:
            self.logger.log("挑战花园boss异常，异常类型：{}".format(type(e).__name__))
            return False
        return True

    def get_lottery(self):
        response = self.wr.amf_post_retry(
            [],
            "api.reward.lottery",
            "/pvz/amf/",
            "获取战利品",
            logger=self.logger,
            exit_on_fail=True,
        )
        if response.status != 0:
            return {"success": False, "result": response.body.description}
        else:
            return {"success": True, "result": response.body}

    def auto_challenge(self, stop_channel: Queue):
        while True:
            failure = False
            message = "挑战花园boss"
            try:
                status = self.challenge_boss()
                if not status:
                    return
            except Exception as e:
                self.logger.log("挑战花园boss异常，异常类型：{}".format(type(e).__name__))
                return

            lottery_result = self.get_lottery()
            if lottery_result["success"] and len(lottery_result["result"]["tools"]) > 0:
                lottery_list = []
                for item in lottery_result["result"]["tools"]:
                    id, amount = int(item["id"]), int(item["amount"])
                    lib_tool = self.lib.get_tool_by_id(id)
                    if lib_tool is None:
                        continue
                    lottery_list.append("{}({})".format(lib_tool.name, amount))
                message = message + "成功.\n\t战利品: {}".format(" ".join(lottery_list))
            else:
                message = message + "失败. 失败原因：{}".format(lottery_result["result"])
                failure = True
            self.logger.log(message)
            if stop_channel.qsize() > 0 or failure:
                return

    def save(self, save_dir):
        save_path = os.path.join(save_dir, "auto_garden")
        with open(save_path, "wb") as f:
            pickle.dump(
                {
                    "team": self.team,
                },
                f,
            )

    def load(self, load_dir):
        load_path = os.path.join(load_dir, "auto_garden")
        if os.path.exists(load_path):
            with open(load_path, "rb") as f:
                d = pickle.load(f)
            for k, v in d.items():
                if hasattr(self, k):
                    setattr(self, k, v)
