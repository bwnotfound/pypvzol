import pickle
import concurrent.futures
from queue import Queue
import logging
import os
from threading import Event
import time
from ... import (
    Config,
    Repository,
    Library,
    SynthesisMan,
    WebRequest,
)
from ..message import Logger
from ... import WorldFubenRequest, Serverbattle, Arena, Command
from ...fuben import FubenCave
from ...utils.recover import RecoverMan
from ..wrapped import signal_block_emit
from ...library import attribute2plant_attribute
from . import load_data, save_data
from ...utils.common import format_number


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
        self.end_mantissa = 1.0
        self.end_exponent = 0

    def check_data(self, refresh_repo=True):
        if refresh_repo:
            self.repo.refresh_repository()
        if self.main_plant_id is not None:
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
                plant, attribute2plant_attribute[self.chosen_attribute]
            )
            if attribute_value > max_attribute_value:
                max_attribute_value = attribute_value
                max_plant_id = deputy_plant_id
        return max_plant_id

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

        try:
            result = self.synthesisMan.synthesis(
                deputy_plant_id,
                self.main_plant_id,
                self.attribute_book_dict[self.chosen_attribute],
                self.reinforce_number,
            )
        except Exception as e:
            if "amf返回结果为空" in str(e):
                msg = "可能由以下原因引起：参与合成的植物不见了、增强卷轴不够、合成书不够"
                return {
                    "success": False,
                    "result": "合成异常，已跳出合成。{}".format(msg),
                }
            self.check_data()
            if deputy_plant_id not in self.auto_synthesis_pool_id:
                return {
                    "success": False,
                    "result": "合成异常。因为吃底座的植物不见了",
                }
            if self.main_plant_id is None:
                if deputy_plant_id in self.auto_synthesis_pool_id:
                    self.auto_synthesis_pool_id.remove(deputy_plant_id)
                self.main_plant_id = deputy_plant_id
                return {
                    "success": True,
                    "result": "合成异常，但是底座植物不存在，所以判定为合成成功",
                }
            else:
                logging.info("合成异常，检测到底座还在，尝试重新合成")
                return self.synthesis(need_check=False)

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
                return False
            elif length < 0:
                logger.log("合成次数不能为负数")
                return False
            self.check_data()
            signal_block_emit(refresh_signal)
            while not (len(self.auto_synthesis_pool_id) == 0) and length > 0:
                if interrupt_event is not None and interrupt_event.is_set():
                    logger.log("中止合成")
                    return False
                if need_synthesis is not None:
                    if not need_synthesis():
                        return False
                result = self.synthesis(need_check=False)
                logger.log(result['result'])
                self.check_data(False)
                signal_block_emit(refresh_signal)
                if not result["success"]:
                    logger.log("合成异常，已跳出合成")
                    return False
                length -= 1
            logger.log("合成完成")
        except Exception as e:
            if (
                isinstance(e, RuntimeError)
                or isinstance(e, ConnectionError)
                or isinstance(e, TimeoutError)
            ):
                logger.log("合成异常。异常信息：{}".format(type(e).__name__))
            else:
                logger.log("合成异常。异常种类：{}".format(type(e).__name__))
                logging.exception(e)
            if refresh_signal is not None:
                self.check_data()
                signal_block_emit(refresh_signal)
            logger.log("合成异常，已跳出合成")
            return False
        return True

    def save(self, save_dir=None):
        data = {
            "main_plant_id": self.main_plant_id,
            "chosen_attribute": self.chosen_attribute,
            "auto_synthesis_pool_id": self.auto_synthesis_pool_id,
            "reinforce_number": self.reinforce_number,
            "end_mantissa": self.end_mantissa,
            "end_exponent": self.end_exponent,
        }
        return save_data(data, save_dir, "user_autosynthesisman")

    def load(self, load_dir):
        load_path = os.path.join(load_dir, "user_autosynthesisman")
        if os.path.exists(load_path):
            with open(load_path, "rb") as f:
                d = pickle.load(f)
            for k, v in d.items():
                if hasattr(self, k):
                    setattr(self, k, v)
        self.check_data(False)


class SingleFubenCave:
    def __init__(
        self,
        cave: FubenCave,
        layer,
        number,
        use_sand=False,
        enabled=True,
        global_layer=1,
    ):
        self.cave = cave
        self.layer = layer
        self.number = number
        self.use_sand = use_sand
        self.enabled = enabled
        self.global_layer = global_layer

    @property
    def name(self):
        return self.cave.name

    @property
    def cave_id(self):
        return self.cave.cave_id

    @property
    def rest_count(self):
        return self.cave.rest_count


class FubenMan:
    def __init__(self, cfg: Config, repo: Repository, lib: Library, logger: Logger):
        self.cfg = cfg
        self.repo = repo
        self.lib = lib
        self.logger = logger
        self.fuben_request = WorldFubenRequest(cfg)
        self.recover_man = RecoverMan(cfg)
        self.caves: list[SingleFubenCave] = []
        self.team = []
        self.show_lottery = False
        self.need_recovery = False
        self.recover_hp_choice = "中级血瓶"
        self.pool_size = 3
        self.challenge_amount = 0
        self.current_fuben_layer = None
        self.has_challenged = False
        self.use_fuben_book_enabled = False
        self.infinit_cave_min_challenge_amount = 10

    def add_cave(
        self,
        cave: FubenCave,
        layer,
        number,
        use_sand=False,
        enabled=True,
        global_layer=1,
    ):
        for sc in self.caves:
            if cave.cave_id == sc.cave_id and global_layer == sc.global_layer:
                return
        sc = SingleFubenCave(cave, layer, number, use_sand, enabled, global_layer)
        self.caves.append(sc)

    def delete_cave(self, sc: SingleFubenCave):
        self.caves = list(
            filter(
                lambda x: not (
                    x.cave_id == sc.cave_id and x.global_layer == sc.global_layer
                ),
                self.caves,
            )
        )

    def get_caves(self, layer):
        return self.fuben_request.get_caves(layer, self.logger)

    def _recover(self):
        cnt, max_retry = 0, 20
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
            recover_list = [plant.id for plant in recover_list]
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

    def switch_fuben_layer(self, target_layer):
        if (
            self.current_fuben_layer is not None
            and target_layer == self.current_fuben_layer
        ):
            return True

        cnt, max_retry = 0, 20
        while cnt < max_retry:
            cnt += 1
            try:
                self.fuben_request.switch_layer(target_layer, self.logger)
                break
            except Exception as e:
                self.logger.log(
                    "切换到{}层失败，暂停1秒，最多再尝试{}次切换。异常种类:{}".format(
                        target_layer, max_retry - cnt, type(e).__name__
                    )
                )
                time.sleep(1)
                continue
        else:
            self.logger.log("切换到{}层失败，跳过该层".format(target_layer))
            return False
        self.current_fuben_layer = target_layer
        return True

    def use_fuben_book(self, amount, stop_channel: Queue):
        if amount == 0:
            self.logger.log("使用0本副本挑战书，跳过使用")
            return True
        repo_tool_amount = self.repo.get_tool(
            self.lib.fuben_book_id, return_amount=True
        )
        if repo_tool_amount < amount:
            self.logger.log("挑战世界副本失败，原因：副本挑战书数量不足，终止挑战")
            return False
        cnt, max_retry = 0, 20
        while cnt < max_retry:
            if stop_channel.qsize() > 0:
                return False
            try:
                use_result = self.repo.use_tool(
                    self.lib.fuben_book_id, amount, self.lib
                )
                if not use_result["success"]:
                    self.logger.log(
                        "使用{}本副本挑战书失败，原因：{}".format(amount, use_result['result'])
                    )
                    return False
                if use_result["effect"] != amount:
                    self.logger.log(
                        "使用副本挑战书失败，预计使用{}本，实际使用{}本，终止挑战".format(
                            amount, use_result["effect"]
                        )
                    )
                    return False
                self.logger.log(
                    "使用{}本副本挑战书成功，剩余{}本".format(amount, repo_tool_amount - amount)
                )
                self.repo.remove_tool(self.lib.fuben_book_id, amount)
                break
            except Exception as e:
                self.logger.log(
                    "使用{}本副本挑战书出现异常，异常种类：{}，尝试刷新仓库".format(amount, type(e).__name__)
                )
                self.repo.refresh_repository()
                if (
                    self.repo.get_tool(self.lib.fuben_book_id, return_amount=True)
                    == repo_tool_amount - amount
                ):
                    self.logger.log("仓库副本挑战书数量减少符合预期值，判定使用副本挑战书成功")
                    break
                cnt += 1
                self.logger.log(
                    "仓库副本挑战书数量不符合预期值{}，暂停1s继续，最多再尝试{}次".format(
                        repo_tool_amount - amount, max_retry - cnt
                    )
                )
                time.sleep(1)
                continue
        self.challenge_amount += amount
        return True

    def challenge(self, sc_list: list[SingleFubenCave], stop_channel: Queue):
        _cave_map = {}

        def get_fuben_cave(layer, number, use_cache=True) -> FubenCave:
            caves = _cave_map.get(layer, None)
            if caves is None or not use_cache:
                data = self.fuben_request.get_caves(
                    layer, self.logger, return_challenge_amount=True
                )
                _cave_map[layer] = caves = data[0]
                self.challenge_amount = data[1]
            assert number >= 1 and number <= len(caves)
            return caves[number - 1]

        for sc in sc_list:
            if stop_channel.qsize() > 0:
                return False
            if not sc.enabled:
                continue
            while True:
                cave = get_fuben_cave(sc.layer, sc.number)
                if cave.rest_count == 0:
                    break
                if not self.use_fuben_book_enabled:
                    if self.challenge_amount == 0:
                        return False
                else:
                    use_amount = (
                        cave.rest_count
                        if cave.rest_count >= 0
                        else self.infinit_cave_min_challenge_amount
                    )
                    use_amount -= self.challenge_amount
                    if use_amount > 0:
                        result = self.use_fuben_book(use_amount, stop_channel)
                        if not result:
                            return False

                def run():
                    if self.need_recovery:
                        if not self._recover():
                            return False
                    message = "挑战副本:{}".format(
                        cave.name,
                    )
                    result = self.fuben_request.challenge(
                        sc.cave_id, self.team, logger=self.logger
                    )
                    if result is None:
                        return False
                    if not result["success"]:
                        message = message + "失败. 原因: {}.".format(result["result"])
                        self.logger.log(message)
                        return False
                    else:
                        message = message + "成功. "
                    message = message + "挑战结果：{}".format(
                        "胜利" if result["result"]['is_winning'] else "失败"
                    )
                    self.logger.log(message)
                    if stop_channel.qsize() > 0:
                        return False
                    return True

                challenge_count = (
                    cave.rest_count
                    if cave.rest_count >= 0
                    else self.infinit_cave_min_challenge_amount
                )
                futures = []
                need_exit = False
                with concurrent.futures.ThreadPoolExecutor(
                    max_workers=self.pool_size
                ) as executor:
                    for _ in range(challenge_count):
                        futures.append(executor.submit(run))
                    has_failure = False
                    for future in concurrent.futures.as_completed(futures):
                        if stop_channel.qsize() > 0:
                            executor.shutdown(cancel_futures=True, wait=True)
                            return False
                        try:
                            if not future.result():
                                executor.shutdown(cancel_futures=True, wait=True)
                                need_exit = True
                                break
                            else:
                                self.challenge_amount -= 1
                                if cave.rest_count >= 0:
                                    cave.rest_count = max(cave.rest_count - 1, 0)
                                self.has_challenged = True
                        except Exception as e:
                            self.logger.log("挑战副本异常，异常类型：{}".format(type(e).__name__))
                            has_failure = True
                if self.challenge_amount == 0 and not self.use_fuben_book_enabled:
                    self.logger.log("副本挑战次数用完了")
                    return False
                if need_exit:
                    break
                if has_failure:
                    self.repo.refresh_repository()
                    get_fuben_cave(1, 1, use_cache=False)
                    continue
        return True

    def auto_challenge(self, stop_channel: Queue):
        self.has_challenged = False
        self.repo.refresh_repository()
        layer_sc_dict = {}
        for sc in self.caves:
            layer_sc_dict.setdefault(sc.global_layer, []).append(sc)

        for layer, sc_list in layer_sc_dict.items():
            if len(sc_list) == 0:
                continue
            if not self.switch_fuben_layer(layer):
                self.logger.log("切换到{}层失败，退出自动副本".format(layer))
                return False
            if not self.challenge(sc_list, stop_channel):
                self.logger.log("自动副本出现问题，退出自动副本")
                return False

        if self.has_challenged:
            return True
        else:
            return False

    def save(self, save_dir=None):
        data = {
            "caves": self.caves,
            "team": self.team,
            "show_lottery": self.show_lottery,
            "need_recovery": self.need_recovery,
            "recover_hp_choice": self.recover_hp_choice,
            "pool_size": self.pool_size,
            "use_fuben_book_enabled": self.use_fuben_book_enabled,
        }
        return save_data(data, save_dir, "auto_fuben")

    def load(self, load_dir):
        load_data(load_dir, "auto_fuben", self)
        if len(self.caves) > 0:
            sc = self.caves[0]
            if not hasattr(sc, "global_layer") or not hasattr(sc, "cave"):
                self.caves = []


class TerritoryMan:
    def __init__(self, cfg: Config, repo: Repository, logger: Logger):
        self.cfg = cfg
        self.repo = repo
        self.logger = logger
        self.wr = WebRequest(cfg)
        self.difficulty_choice = 3
        self.team = []
        self.smart_enabled = False
        self.max_fight_mantissa = 1.0
        self.max_fight_exponent = 0
        self.pool_size = 1

    @property
    def max_fight(self):
        return self.max_fight_mantissa * (10 ** (self.max_fight_exponent + 8))

    def check_data(self, refresh_repo=True):
        if refresh_repo:
            self.repo.refresh_repository()
        self.team = [
            plant_id
            for plant_id in self.team
            if self.repo.get_plant(plant_id) is not None
        ]

    def get_rest_num(self):
        body = []
        response = self.wr.amf_post_retry(
            body,
            "api.territory.init",
            "/pvz/amf/",
            "查询领地剩余次数",
            logger=self.logger,
            except_retry=True,
        )
        return int(response.body["challengecount"])

    def can_challenge(self):
        rest_num = self.get_rest_num()
        if rest_num < self.difficulty_choice:
            self.logger.log("领地剩余次数不足，剩余次数：{}".format(rest_num))
            return False
        return True

    def should_fight(self):
        if not self.smart_enabled or self.difficulty_choice != 4:
            return {"continue": True}
        body = [float(2004)]
        while True:
            response = self.wr.amf_post_retry(
                body,
                "api.territory.getTerritory",
                "/pvz/amf/",
                "查看领地信息",
                logger=self.logger,
                except_retry=True,
            )
            if response.status != 0:
                if "匹配对手中" in response.body.description:
                    continue
                raise RuntimeError(response.body.description)
            break
        for enemy in response.body["teritory"][1:]:
            if enemy["organisms"] is None or len(enemy["organisms"]) == 0:
                continue
            defender = enemy["organisms"][0]
            if int(defender['fighting']) > self.max_fight:
                return {
                    "continue": False,
                    "result": "对方战力{}超过最大战力限制".format(
                        format_number(int(defender['fighting']))
                    ),
                }
        return {"continue": True}

    def challenge(self, difficulty_choice=None):
        if difficulty_choice is None:
            difficulty_choice = self.difficulty_choice
        body = [float(2000 + difficulty_choice), [], float(1), float(0)]
        response = self.wr.amf_post_retry(
            body,
            "api.territory.challenge",
            "/pvz/amf/",
            "挑战领地",
            logger=self.logger,
            except_retry=True,
        )
        return response

    def auto_challenge_concurrent(self, stop_channel: Queue):
        def run():
            message = f"挑战领地难度{self.difficulty_choice}"
            response = self.challenge()
            if response.status == 1:
                message = message + "失败. 原因: {}.".format(response.body.description)
                if "匹配对手中" in response.body.description:
                    message = message + "继续运行"
                    self.logger.log(message)
                    return True
                else:
                    self.logger.log(message)
                    return False
            else:
                result = response.body
                message = message + "成功. "
                message = message + "挑战结果：{}".format(
                    "胜利" if result['fight']['is_winning'] else "失败"
                )
                message = message + ". 现在荣誉: {}".format(result['honor'])
                self.logger.log(message)
            if stop_channel.qsize() > 0:
                return False
            return True

        pool_size = self.pool_size
        future_list = []

        def pop_future():
            for future in concurrent.futures.as_completed(future_list):
                index = future_list.index(future)
                result = future.result()
                future_list.pop(index)
                return result

        with concurrent.futures.ThreadPoolExecutor(max_workers=pool_size) as executor:
            while stop_channel.qsize() == 0:
                while len(future_list) >= pool_size:
                    result = pop_future()
                    if not result:
                        return False
                future_list.append(executor.submit(run))
        if stop_channel.qsize() > 0:
            return False

    def auto_challenge(self, stop_channel: Queue):
        if not self.smart_enabled:
            return self.auto_challenge_concurrent(stop_channel)
        while stop_channel.qsize() == 0:
            message = f"挑战领地难度{self.difficulty_choice}"
            result = self.should_fight()
            if not result["continue"]:
                message += ", {}，选择挑战难度三，挑战结果：".format(result["result"])
                response = self.challenge(3)
            else:
                response = self.challenge()
            if response.status == 1:
                message = message + "失败. 原因: {}.".format(response.body.description)
                if "匹配对手中" in response.body.description:
                    message = message + "继续运行"
                    self.logger.log(message)
                    continue
                else:
                    self.logger.log(message)
                    return False
            else:
                result = response.body
                message = message + "成功. "
                message = message + "挑战结果：{}".format(
                    "胜利" if result['fight']['is_winning'] else "失败"
                )
                message = message + ". 现在荣誉: {}".format(result['honor'])
                self.logger.log(message)
            if stop_channel.qsize() > 0:
                return False
        if stop_channel.qsize() > 0:
            return False

    def release_plant(self, user_id):
        body = [float(user_id)]
        response = self.wr.amf_post_retry(
            body,
            "api.territory.quit",
            "/pvz/amf/",
            "释放领地",
            except_retry=True,
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

        def run(body):
            response = self.wr.amf_post_retry(
                body,
                "api.territory.challenge",
                "/pvz/amf/",
                "上领地植物",
                logger=self.logger,
                allow_empty=True,
                except_retry=True,
            )
            return response

        futures = []
        with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
            for i, plant_id in enumerate(self.team[:5]):
                body = [float(f"100{i+1}"), [int(plant_id)], float(1), float(0)]
                futures.append(executor.submit(run, body))
        concurrent.futures.wait(futures, return_when=concurrent.futures.ALL_COMPLETED)
        for f in futures:
            response = f.result()
            if response is None:
                return {"success": False, "result": "上领地植物时有的植物不存在"}
        return {"success": True, "result": "共上场{}个植物".format(len(self.team))}

    def save(self, save_dir=None):
        data = {
            "difficulty_choice": self.difficulty_choice,
            "team": self.team,
            "smart_enabled": self.smart_enabled,
            "max_fight_mantissa": self.max_fight_mantissa,
            "max_fight_exponent": self.max_fight_exponent,
            "pool_size": self.pool_size,
        }
        return save_data(data, save_dir, "auto_territory")

    def load(self, load_dir):
        load_data(load_dir, "auto_territory", self)
        self.team = self.team[:5]


class DailyMan:
    def __init__(self, cfg, logger: Logger):
        self.cfg = cfg
        self.wr = WebRequest(cfg)
        self.logger = logger

    def daily_accumulated_reward_acquire(self):
        self.wr.amf_post_retry(
            [float(5)],
            "api.active.rewardTimes",
            "/pvz/amf/",
            "累计每日奖励领取",
            logger=self.logger,
            except_retry=True,
        )

    def get_arena_reward_info(self):
        response = self.wr.amf_post_retry(
            [],
            "api.arena.getAwardWeekInfo",
            "/pvz/amf/",
            "竞技场奖励信息获取",
            logger=self.logger,
            except_retry=True,
        )
        body = response.body
        rank = int(body['rank']['rank'])
        award_info_list = []
        for item in body['award']:
            award_info_list.append(
                (
                    int(item['min_rank']),
                    int(item['max_rank']),
                    [
                        {"id": int(tool['id']), "amount": int(tool['amount'])}
                        for tool in item['tool']
                    ],
                )
            )
        return rank, award_info_list

    def arena_reward_acquire(self, lib: Library):
        rank, award_info_list = self.get_arena_reward_info()
        for item in award_info_list:
            if rank >= item[0] and rank <= item[1]:
                break
        else:
            self.logger.log("排名不够，无法领取竞技场奖励")
            return
        response = self.wr.amf_post_retry(
            [],
            "api.arena.awardWeek",
            "/pvz/amf/",
            "竞技场奖励领取",
            logger=self.logger,
            except_retry=True,
        )
        if response.status == 1:
            self.logger.log("竞技场" + response.body.description)
        else:
            msg = f"领取第{rank}名竞技场奖励成功。领取了"
            for reward_tool in item[2]:
                tool = lib.get_tool_by_id(reward_tool['id'])
                if tool is None:
                    continue
                msg += "{}个{},".format(reward_tool['amount'], tool.name)
            msg = msg[:-1]
            self.logger.log(msg)

    def vip_reward_acquire(self):
        response = self.wr.amf_post_retry(
            [],
            "api.vip.awards",
            "/pvz/amf/",
            "vip每日奖励",
            logger=self.logger,
            allow_empty=True,
            except_retry=True,
        )
        if response is None:
            return False
        return True

    def daily_sign(self):
        response = self.wr.amf_post_retry(
            [],
            "api.active.sign",
            "/pvz/amf/",
            "每日签到",
            logger=self.logger,
            except_retry=True,
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
        self.wr.amf_post_retry(
            [float(1), float(3), float(2), self.team],
            "api.garden.challenge",
            "/pvz/amf/",
            "挑战花园boss",
            logger=self.logger,
            exit_response=True,
        )

    def get_lottery(self):
        response = self.wr.amf_post_retry(
            [],
            "api.reward.lottery",
            "/pvz/amf/",
            "获取战利品",
            logger=self.logger,
        )
        if response.status != 0:
            return {"success": False, "result": response.body.description}
        else:
            return {"success": True, "result": response.body}

    def auto_challenge(self, stop_channel: Queue):
        if self.team is None or len(self.team) == 0:
            self.logger.log("未设置队伍")
            return False
        while True:
            failure = False
            message = "挑战花园boss"
            cnt, max_retry = 0, 15
            while cnt < max_retry:
                cnt += 1
                try:
                    self.challenge_boss()
                    break
                except Exception as e:
                    self.logger.log(
                        "挑战花园boss异常，尝试继续，还能尝试{}次。异常类型：{}".format(
                            max_retry - cnt, type(e).__name__
                        )
                    )
                    continue
            try:
                lottery_result = self.get_lottery()
            except Exception as e:
                self.logger.log("获取战利品异常，异常类型：{}".format(type(e).__name__))
                continue
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
                message = message + "失败。没有花园挑战次数了"
                failure = True
            self.logger.log(message)
            if stop_channel.qsize() > 0 or failure:
                return False

    def save(self, save_dir=None):
        data = {
            "team": self.team,
        }
        return save_data(data, save_dir, "auto_garden")

    def load(self, load_dir):
        load_data(load_dir, "auto_garden", self)


class ServerBattleMan:
    def __init__(self, cfg: Config, logger: Logger):
        self.cfg = cfg
        self.logger = logger
        self.serverbattle = Serverbattle(cfg)
        self.rest_challenge_num_limit = 60

    def auto_challenge(self, stop_channel: Queue):
        while True:
            if stop_channel.qsize() > 0:
                return
            current_challenge_num = self.rest_challenge_num()
            has_exception = False
            while True:
                if current_challenge_num <= self.rest_challenge_num_limit:
                    self.logger.log(
                        "跨服挑战次数剩余量已达限定值：{}/{}".format(
                            current_challenge_num, self.rest_challenge_num_limit
                        )
                    )
                    return
                cnt, max_retry = 0, 10
                empty_cnt, max_empty_retry = 0, 3
                while cnt < max_retry:
                    try:
                        result = self.serverbattle.challenge()
                        if result is None:
                            if empty_cnt >= max_empty_retry:
                                self.logger.log("跨服挑战异常，可能是次数用完了。退出跨服挑战。")
                                return
                            self.logger.log(
                                "跨服挑战异常，可能是次数用完了。重新尝试，最多尝试{}次".format(
                                    max_empty_retry - empty_cnt
                                )
                            )
                            empty_cnt += 1
                            continue
                        break
                    except Exception as e:
                        self.logger.log(
                            "跨服挑战异常，异常类型：{}".format(type(e).__name__, max_retry - cnt)
                        )
                        has_exception = True
                        break
                if has_exception:
                    self.logger.log("检测到跨服挑战出现异常，重新获取跨服挑战次数")
                    current_challenge_num = self.rest_challenge_num()
                    has_exception = False
                    continue

                if not result["success"]:
                    self.logger.log(result["result"])
                    if "匹配" not in result["result"]:
                        return
                current_challenge_num -= 1
                self.logger.log(
                    result["result"] + ". 还剩{}次挑战次数".format(current_challenge_num)
                )
                if stop_channel.qsize() > 0:
                    return

    def rest_challenge_num(self):
        response = self.serverbattle.get_info()
        return int(response.body["remaining_challenges"])

    def save(self, save_dir=None):
        data = {
            "rest_challenge_num_limit": self.rest_challenge_num_limit,
        }
        return save_data(data, save_dir, "serverbattle_man")

    def load(self, load_dir):
        load_data(load_dir, "serverbattle_man", self)


class ArenaMan:
    def __init__(self, cfg: Config, logger: Logger):
        self.cfg = cfg
        self.logger = logger
        self.arena = Arena(cfg)

    def get_challenge_num(self):
        self.arena.refresh_arena()
        return self.arena.challenge_num

    def auto_challenge(self, stop_channel: Queue):
        challenge_num = self.get_challenge_num()
        while challenge_num >= 100 and stop_channel.qsize() == 0:
            amount = None
            if challenge_num >= 10000:
                result = self.arena.batch_challenge(10000)
                amount = 10000
            elif challenge_num >= 1000:
                result = self.arena.batch_challenge(1000)
                amount = 1000
            elif challenge_num >= 100:
                result = self.arena.batch_challenge(100)
                amount = 100
            else:
                raise NotImplementedError("挑战次数{}异常".format(challenge_num))
            if not result["success"]:
                error_type = result["error_type"]
                if error_type == 1:
                    self.logger.log(
                        "挑战竞技场出现异常。原因：{}。判断为挑战次数不足，终止挑战".format(result["result"])
                    )
                    return
                elif error_type == 2:
                    self.logger.log("挑战竞技场出现异常。原因：{}。".format(result["result"]))
                    return
                self.logger.log(result["result"])
                return
            challenge_num -= amount
            self.logger.log("挑战竞技场成功。剩余挑战次数{}次".format(challenge_num))
        if stop_channel.qsize() > 0:
            return
        self.logger.log("挑战竞技场完成，剩余挑战次数：{}".format(challenge_num))
        return

    def challenge_first(self):
        self.arena.refresh_arena()
        result = self.arena.challenge_first()
        return result


class CommandMan:
    def __init__(self, cfg: Config, logger: Logger):
        self.cfg = cfg
        self.logger = logger
        self.command = Command(cfg)
        self.command_list = []

    def start(self, stop_queue: Queue):
        for command_str in self.command_list:
            while True:
                if stop_queue.qsize() > 0:
                    return
                result = self.command.send(command_str)
                if result['success']:
                    self.logger.log("{}执行成功".format(command_str))
                else:
                    if result['error_type'] == 2:
                        self.logger.log("指令{}有误，请重新设定该指令。".format(command_str))
                    elif result['error_type'] == 3:
                        self.logger.log("指令{}执行时发现未稳定通过，请先稳定通过".format(command_str))
                    elif result['error_type'] == 1:
                        self.logger.log("指令{}执行至道具异常，认定执行完毕".format(command_str))
                    break

    def save(self, save_dir=None):
        data = {
            "command_list": self.command_list,
        }
        return save_data(data, save_dir, "command_man")

    def load(self, load_dir):
        load_data(load_dir, "command_man", self)


class SkillStoneMan:
    def __init__(self, cfg: Config, lib: Library, logger: Logger):
        self.lib = lib
        self.cfg = cfg
        self.logger = logger
        self.wr = WebRequest(cfg)
        self.pool_size = 3

    def upgrade_skill(self, plant_id, skill_dict, is_spec):
        url = 'api.apiorganism.specSkillUp' if is_spec else 'api.apiorganism.skillUp'
        body = [
            float(plant_id),
            float(skill_dict["id"]),
        ]
        response = self.wr.amf_post_retry(
            body, url, "/pvz/amf/", "升级技能", allow_empty=True
        )
        if response is None:
            return response
        if response.status == 1:
            return {
                "success": False,
                "result": response.body.description,
            }
        now_id = int(response.body["now_id"])
        upgrade_success = skill_dict["id"] != now_id
        return {
            "success": True,
            "upgrade_success": upgrade_success,
        }

    def upgrade_stone(self, plant_id, stone_index):
        '''
        stone_index: [0,9)
        return: None代表升到10级了，道具异常表示没道具了
        '''
        body = [
            float(plant_id),
            "talent_" + str(stone_index + 1),
        ]
        response = self.wr.amf_post_retry(
            body, 'api.apiorganism.upgradeTalent', "/pvz/amf/", "升级宝石", allow_empty=True
        )
        if response is None:
            return response
        if response.status == 1:
            return {
                "success": False,
                "result": response.body.description,
            }
        return {"success": True, "result": response.body}

    def save(self, save_dir=None):
        data = {
            "pool_size": self.pool_size,
        }
        return save_data(data, save_dir, "skill_man")

    def load(self, load_dir):
        load_data(load_dir, "skill_man", self)
