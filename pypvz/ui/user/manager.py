import pickle
from queue import Queue
import logging
import os
from threading import Event
from ... import (
    Config,
    Repository,
    Library,
    SynthesisMan,
    WebRequest,
)
from ..message import Logger
from ... import FubenRequest, Serverbattle
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
                plant, self.attribute2plant_attribute[self.chosen_attribute]
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
            if isinstance(e, RuntimeError):
                logger.log("合成异常。异常信息：{}".format(str(e)))
            else:
                logger.log("合成异常。异常种类：{}".format(type(e).__name__))
            if refresh_signal is not None:
                self.check_data()
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

    def can_challenge(self):
        body = []
        response = self.wr.amf_post_retry(
            body,
            "api.territory.init",
            "/pvz/amf/",
            "查询领地剩余次数",
            logger=self.logger,
            except_retry=True,
        )
        if response.status != 0:
            self.logger.log("查询领地剩余次数失败，原因：{}".format(response.body.description))
            return False
        rest_num = int(response.body["challengecount"])
        if rest_num < self.difficulty_choice:
            self.logger.log("剩余次数不足，剩余次数：{}".format(rest_num))
            return False
        return True

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


class ServerBattleMan:
    def __init__(self, cfg: Config, logger: Logger):
        self.cfg = cfg
        self.logger = logger
        self.serverbattle = Serverbattle(cfg)
        self.rest_challenge_num_limit = 60

    def auto_challenge(self, stop_channel: Queue):
        current_challenge_num = self.rest_challenge_num()
        if current_challenge_num is None:
            self.logger.log("获取跨服信息失败")
            return

        while True:
            if current_challenge_num <= self.rest_challenge_num_limit:
                self.logger.log(
                    "跨服挑战次数剩余量已达限定值：{}/{}".format(
                        current_challenge_num, self.rest_challenge_num_limit
                    )
                )
                return
            result = self.serverbattle.challenge()
            self.logger.log(result["result"])
            if not result["success"]:
                break
            if stop_channel.qsize() > 0:
                break
            current_challenge_num -= 1

    def rest_challenge_num(self):
        result = self.serverbattle.get_info()
        if not result["success"]:
            self.logger.log(result["result"])
            return None
        return int(result["result"]["remaining_challenges"])

    def save(self, save_dir):
        save_path = os.path.join(save_dir, "serverbattle_man")
        with open(save_path, "wb") as f:
            pickle.dump(
                {
                    "rest_challenge_num_limit": self.rest_challenge_num_limit,
                },
                f,
            )

    def load(self, load_dir):
        load_path = os.path.join(load_dir, "serverbattle_man")
        if os.path.exists(load_path):
            with open(load_path, "rb") as f:
                d = pickle.load(f)
            for k, v in d.items():
                if hasattr(self, k):
                    setattr(self, k, v)
