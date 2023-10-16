import pickle
import os
import time
from queue import Queue
import threading

from ..shop import Shop

from ..cave import Cave
from .. import Config, Repository, Library, User, CaveMan, Task, SynthesisMan, ArenaMan, HeritageMan
from ..utils.recover import RecoverMan
from .message import IOLogger, Logger
from ..utils.evolution import PlantEvolution
from ..utils.common import second2str


class SingleCave:
    def __init__(self, cave: Cave, difficulty=3, garden_layer=None):
        self.difficulty = difficulty  # 1: easy, 2: normal, 3: hard
        self.garden_layer = garden_layer
        self.use_sand = False
        self.enabled = True
        self.friend_id_list: list[int] = []
        self.cave = cave
        self.friend_id2cave_id = {}


class Challenge4Level:
    def __init__(
        self,
        cfg: Config,
        user: User,
        repo: Repository,
        lib: Library,
        caveMan: CaveMan,
        free_max=10,
        logger: Logger = None,
    ):
        self.cfg = cfg
        self.user = user
        self.friendman = user.friendMan
        self.repo = repo
        self.lib = lib
        self.caveMan = caveMan
        self.recoverMan = RecoverMan(cfg, repo)
        self.logger = logger

        self.caves: list[SingleCave] = []
        self.main_plant_list: list[int] = []
        self.trash_plant_list: list[int] = []
        self.free_max = free_max
        self.friend_id2cave = {}
        self.garden_layer_friend_id2cave = {} if cfg.server == "私服" else None
        self.garden_layer_caves = {} if cfg.server == "私服" else None
        self.hp_choice = "中级血瓶"
        self.pop_after_100 = False
        self.pop_grade = 100
        self.auto_use_challenge_book = False
        self.normal_challenge_book_amount = 1
        self.advanced_challenge_book_amount = 1
        self.enable_sand = False
        self.show_lottery = False
        self.enable_stone = True
        self.enable_large_plant_team = False

        self.disable_cave_info_fetch = False
        self.current_garden_layer = None

    def add_cave(
        self, cave: Cave, friend_ids=None, difficulty=3, enabled=True, garden_layer=None
    ):
        for c in self.caves:
            if (
                cave.id == c.cave.id and cave.name == c.cave.name
            ) and garden_layer == c.garden_layer:
                self.logger.log("洞口已经存在了")
                return
        if cave.type <= 3:
            if isinstance(friend_ids, int):
                friend_ids = [friend_ids]
            elif friend_ids is None:
                grade = cave.open_grade
                friend_ids = []
                for i, friend in enumerate(self.friendman.friends):
                    if friend.grade < grade or (cave.type != 2 and i > 0):
                        break
                    friend_ids.append(friend.id)
            else:
                raise TypeError("friend_ids must be int or list[int]")
            if len(friend_ids) == 0:
                self.logger.log("你的等级不够，不能添加洞口{}".format(cave.name))
                return
            sc = SingleCave(cave, difficulty=difficulty, garden_layer=garden_layer)
            sc.difficulty = difficulty
            if self.cfg.server == "私服":
                self.friend_id2cave = self.garden_layer_friend_id2cave.setdefault(
                    garden_layer, {}
                )
            for friend_id in friend_ids:
                sc.friend_id_list.append(friend_id)
                self.friend_id2cave.setdefault(friend_id, set()).add(
                    (cave.id, cave.name)
                )
            if self.cfg.server == "私服":
                self.garden_layer_caves.setdefault(garden_layer, []).append(sc)
            self.caves.append(sc)
        elif cave.type == 4:
            sc = SingleCave(cave)
            sc.difficulty = difficulty
            sc.enabled = enabled
            self.caves.append(sc)
        else:
            raise NotImplementedError

    def remove_cave(self, cave, garden_layer=None):
        assert isinstance(cave, Cave)

        for sc in self.caves:
            if sc.cave.id == cave.id and sc.cave.name == cave.name:
                break
        else:
            raise RuntimeError("cave not exists1")
        if self.cfg.server == "私服":
            self.friend_id2cave = self.garden_layer_friend_id2cave.get(garden_layer)

        if sc.cave.type <= 3:
            pop_list = []
            for k, v in self.friend_id2cave.items():
                if (cave.id, cave.name) in v:
                    v.remove((cave.id, cave.name))
                if len(v) == 0:
                    pop_list.append(k)
            for k in pop_list:
                self.friend_id2cave.pop(k)
            for i, c in enumerate(self.caves):
                if c.cave.id == cave.id and c.cave.name == cave.name:
                    break
            else:
                raise RuntimeError("cave not exists2")
            self.caves.pop(i)
            if sc.garden_layer not in self.garden_layer_caves:
                raise RuntimeError("garden layer not exists")
            for i, c in enumerate(self.garden_layer_caves[sc.garden_layer]):
                if c.cave.id == cave.id and c.cave.name == cave.name:
                    break
            else:
                raise RuntimeError("cave not exists3")
            self.garden_layer_caves[sc.garden_layer].pop(i)
        elif sc.cave.type == 4:
            for i, c in enumerate(self.caves):
                if c.cave.id == cave.id and c.cave.name == cave.name:
                    break
            else:
                raise RuntimeError("cave not exists4")
            self.caves.pop(i)
        else:
            raise NotImplementedError

    def _assemble_team(self, cave: Cave):
        team = []
        team_grid_amount = 0
        team_limit = 10 if not self.enable_large_plant_team else 16
        for plant_id in self.main_plant_list:
            plant = self.repo.get_plant(plant_id)
            if plant is None:
                continue
            width = plant.width(self.lib)
            if team_grid_amount + width > team_limit:
                break
            team.append(plant_id)
            team_grid_amount += width
        if team_grid_amount == team_limit:
            return team

        trash_plant_list = [
            self.repo.get_plant(plant_id) for plant_id in self.trash_plant_list
        ]
        trash_plant_list = list(filter(lambda x: x is not None, trash_plant_list))
        sorted_grade_trash_plant_list = sorted(
            trash_plant_list,
            key=lambda x: (-x.grade, x.width(self.lib)),
        )
        for plant in sorted_grade_trash_plant_list:
            width = plant.width(self.lib)
            if team_grid_amount + width > team_limit:
                continue
            if cave.grade - plant.grade < 5:
                continue
            team.append(plant.id)
            team_grid_amount += width
        if team_grid_amount < team_limit - self.free_max:
            return None
        return team

    def _recover(self):
        cnt, max_retry = 0, 3
        success_num_all = 0
        while cnt < max_retry:
            success_num, fail_num = self.recoverMan.recover_zero(
                need_refresh=False, choice=self.hp_choice
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

    def format_upgrade_message(self, team, response_body):
        message = ""
        plant_list = list(
            filter(
                lambda x: x is not None,
                [self.repo.get_plant(plant_id) for plant_id in team],
            )
        )
        message = message + "\n\t尝试出战植物: {}".format(
            ' '.join(
                [
                    "{}({})".format(plant.name(self.lib), plant.grade)
                    for plant in plant_list
                ]
            )
        )
        plant_grade_list = [(plant.id, plant.grade) for plant in plant_list]
        self.repo.refresh_repository(logger=self.logger)
        upgrade_data_list = []
        for plant_id, grade in plant_grade_list:
            after_plant = self.repo.get_plant(plant_id)
            if after_plant is None or after_plant.grade == grade:
                continue
            upgrade_data_list.append((after_plant, grade, after_plant.grade))
        upgrade_msg_list = [
            "{}({}->{})".format(
                plant.name(self.lib),
                grade1,
                grade2,
            )
            for plant, grade1, grade2 in upgrade_data_list
        ]
        if len(upgrade_msg_list) > 0:
            message = message + "\n\t升级植物: {}".format(' '.join(upgrade_msg_list))
        if self.show_lottery:
            lottery_result = self.caveMan.get_lottery(response_body)
            if lottery_result["success"]:
                lottery_list = []
                for item in lottery_result["result"]:
                    id, amount = item["id"], item["amount"]
                    lib_tool = self.lib.get_tool_by_id(id)
                    if lib_tool is None:
                        continue
                    lottery_list.append("{}({})".format(lib_tool.name, amount))
                message = message + "\n\t战利品: {}".format(" ".join(lottery_list))
            else:
                message = message + "\n\t{}".format(lottery_result["result"])
        return message

    def challenge_cave(self, stop_channel: Queue):
        _cave_map = {}

        def get_cave(friend_id, sc: SingleCave):
            uid = "{}_{}_{}".format(friend_id, sc.cave.type, sc.cave.layer)
            caves = _cave_map.get(uid, None)
            if caves is None:
                caves = self.caveMan.get_caves(
                    friend_id, sc.cave.type, sc.cave.layer, logger=self.logger
                )
                _cave_map[uid] = caves
            for cave in caves:
                if cave.id == id:
                    return cave
            else:
                raise ValueError(f"can't find cave {id}")

        for friend_id, caves in self.friend_id2cave.items():
            for id, name in caves:
                for sc in self.caves:
                    if sc.cave.id == id and sc.cave.name == name:
                        break
                else:
                    continue
                if not sc.enabled:
                    continue
                if self.disable_cave_info_fetch:
                    if not hasattr(sc, "friend_id2cave_id"):
                        sc.friend_id2cave_id = {}
                    cave_id = sc.friend_id2cave_id.get(friend_id, None)
                    if cave_id is None:
                        self.switch_garden_layer(sc.garden_layer)
                        cave = get_cave(friend_id, sc)
                cave = get_cave(
                    friend_id,
                    sc,
                )
                if cave is None:
                    return
                if not cave.is_ready:
                    if self.enable_sand and sc.use_sand:
                        sand_result = self.caveMan.use_sand(cave.cave_id)
                        if sand_result["success"]:
                            self.logger.log(
                                "成功对{}使用时之沙".format(cave.format_name(sc.difficulty))
                            )
                        else:
                            continue
                    else:
                        continue

                team = self._assemble_team(cave)
                if team is None:
                    continue

                success = self._recover()
                if not success:
                    return

                difficulty = sc.difficulty

                friend = self.friendman.id2friend[friend_id]

                message = "挑战{}({}) {}".format(
                    friend.name,
                    friend.grade,
                    cave.format_name(difficulty),
                )
                cnt, max_retry = 0, 20
                while cnt < max_retry:
                    result = self.caveMan.challenge(
                        cave.cave_id, team, difficulty, cave.type
                    )
                    success, result = result["success"], result["result"]
                    if not success:
                        if "狩猎场挑战次数已达上限" in result and self.auto_use_challenge_book:
                            use_result = self.repo.use_item(
                                self.lib.name2tool["高级挑战书"].id,
                                self.advanced_challenge_book_amount,
                                self.lib,
                            )
                            if use_result["success"]:
                                self.logger.log(use_result["result"])
                                continue
                            use_result = self.repo.use_item(
                                self.lib.name2tool["挑战书"].id,
                                self.normal_challenge_book_amount,
                                self.lib,
                            )
                            if use_result["success"]:
                                self.logger.log(use_result["result"])
                                continue
                        if "频繁" in result:
                            time.sleep(1)
                            cnt += 1
                            self.logger.log(
                                "挑战过于频繁，选择等待1秒后重试。最多再等待{}次".format(max_retry - cnt)
                            )
                            if stop_channel.qsize() > 0:
                                return
                            continue
                        if "冷却中" in result and (self.enable_sand and sc.use_sand):
                            sand_result = self.caveMan.use_sand(cave.cave_id)
                            if sand_result["success"]:
                                self.logger.log(
                                    "成功对{}使用时之沙".format(cave.format_name(difficulty))
                                )
                                message = message + "成功. "
                                break
                            else:
                                message = message + "失败. 原因: {}.".format(
                                    sand_result["result"]
                                )
                                self.logger.log(message)
                                return
                        message = message + "失败. 原因: {}.".format(result)
                        self.logger.log(message)
                        return
                    else:
                        message = message + "成功. "
                        break
                else:
                    message = message + "失败. 原因: 挑战过于频繁.".format(result)
                    self.logger.log(message)
                    return

                message = message + self.format_upgrade_message(team, result)
                self.logger.log(message)
                if self.pop_after_100:
                    trash_plant_list = [
                        self.repo.get_plant(plant_id)
                        for plant_id in self.trash_plant_list
                    ]
                    trash_plant_list = list(
                        filter(
                            lambda x: (x is not None) and x.grade < self.pop_grade,
                            trash_plant_list,
                        )
                    )
                    self.trash_plant_list = [x.id for x in trash_plant_list]
                if stop_channel.qsize() > 0:
                    return

    def challenge_stone_fuben(self, stop_channel: Queue):
        _cave_map = {}

        def get_stone_cave(layer, number) -> Cave:
            caves = _cave_map.get(layer, None)
            if caves is None:
                _cave_map[layer] = caves = self.caveMan.get_caves(
                    layer, 4, logger=self.logger
                )
            assert number >= 1 and number <= len(caves)
            return caves[number - 1]

        self.repo.refresh_repository(logger=self.logger)
        while self.enable_stone:
            has_challenged = False
            for sc in self.caves:
                if sc.cave.type != 4 or not sc.enabled:
                    continue
                cave = get_stone_cave(sc.cave.layer, sc.cave.number)
                if not cave.is_ready:
                    continue
                team = self._assemble_team(cave)
                if team is None:
                    continue
                success = self._recover()
                if not success:
                    return
                difficulty = sc.difficulty

                message = "挑战{}".format(
                    cave.format_name(difficulty),
                )
                cnt, max_retry = 0, 20
                while cnt < max_retry:
                    result = self.caveMan.challenge(cave.id, team, difficulty, 4)
                    success, result = result["success"], result["result"]
                    if not success:
                        if "频繁" in result:
                            time.sleep(1)
                            cnt += 1
                            self.logger.log(
                                "挑战过于频繁，选择等待1秒后重试。最多再等待{}次".format(max_retry - cnt)
                            )
                            if stop_channel.qsize() > 0:
                                return
                            continue
                        message = message + "失败. 原因: {}.".format(result)
                        self.logger.log(message)
                        return
                    else:
                        message = message + "成功. "
                        break
                else:
                    message = message + "失败. 原因: 挑战过于频繁.".format(result)
                    self.logger.log(message)
                    return
                has_challenged = True
                message = message + self.format_upgrade_message(team, result)
                self.logger.log(message)
                if self.pop_after_100:
                    trash_plant_list = [
                        self.repo.get_plant(plant_id)
                        for plant_id in self.trash_plant_list
                    ]
                    trash_plant_list = list(
                        filter(
                            lambda x: (x is not None) and x.grade < self.pop_grade,
                            trash_plant_list,
                        )
                    )
                    self.trash_plant_list = [x.id for x in trash_plant_list]
                if stop_channel.qsize() > 0:
                    return
            if not has_challenged:
                self.logger.log("没有可以挑战的宝石副本，跳出挑战宝石副本")
                break

    def switch_garden_layer(self, target_garden_layer):
        if (
            self.current_garden_layer is not None
            and target_garden_layer == self.current_garden_layer
        ):
            return True

        cnt, max_retry = 0, 3
        while cnt < max_retry:
            cnt += 1
            try:
                result = self.caveMan.switch_garden_layer(
                    target_garden_layer, self.logger
                )
            except Exception as e:
                self.logger.log(
                    "切换到{}层失败，暂停1秒，最多再尝试{}次切换。异常种类:{}".format(
                        target_garden_layer, max_retry - cnt, type(e).__name__
                    )
                )
                time.sleep(1)
                continue
            if not result["success"]:
                msg = "切换到{}层失败，暂停1秒，最多再尝试{}次切换。错误原因:{}".format(
                    target_garden_layer, max_retry - cnt, result["result"]
                )
                time.sleep(1)
            else:
                msg = result["result"]
            self.logger.log(msg)
            if not result["success"]:
                continue
            break
        else:
            self.logger.log("切换到{}层失败，跳过该层".format(target_garden_layer))
            return False
        return True

    def auto_challenge(self, stop_channel: Queue):
        # TODO: 显示功能：将process显示，可加速版
        assert self.main_plant_list is not None and self.trash_plant_list is not None

        self.challenge_stone_fuben(stop_channel)
        if self.cfg.server == "官服":
            try:
                self.challenge_cave(stop_channel)
            except Exception as e:
                self.logger.log("挑战宝石副本异常，异常种类:{}。跳过宝石副本".format(type(e).__name__))
        elif self.cfg.server != "私服":
            raise NotImplementedError
        else:
            for garden_layer in self.garden_layer_caves.keys():
                if stop_channel.qsize() > 0:
                    break
                if self.cfg.server == "私服":
                    self.friend_id2cave = self.garden_layer_friend_id2cave.get(
                        garden_layer, None
                    )
                    if self.friend_id2cave is None:
                        raise RuntimeError("garden layer is not added 2")
                    if not self.disable_cave_info_fetch:
                        if not self.switch_garden_layer(garden_layer):
                            continue
                try:
                    self.challenge_cave(stop_channel)
                except Exception as e:
                    self.logger.log(
                        "挑战第{}层洞口异常，异常种类:{}。跳过该层".format(garden_layer, type(e).__name__)
                    )
        self.logger.log("挑战完成")

    def save(self, save_dir):
        save_path = os.path.join(save_dir, "user_challenge4level")
        with open(save_path, "wb") as f:
            pickle.dump(
                {
                    "caves": self.caves,
                    "main_plant_list": self.main_plant_list,
                    "trash_plant_list": self.trash_plant_list,
                    "free_max": self.free_max,
                    "friend_id2cave": self.friend_id2cave,
                    "garden_layer_friend_id2cave": self.garden_layer_friend_id2cave,
                    "garden_layer_caves": self.garden_layer_caves,
                    "hp_choice": self.hp_choice,
                    "pop_after_100": self.pop_after_100,
                    "auto_use_challenge_book": self.auto_use_challenge_book,
                    "normal_challenge_book_amount": self.normal_challenge_book_amount,
                    "advanced_challenge_book_amount": self.advanced_challenge_book_amount,
                    "enable_sand": self.enable_sand,
                    "show_lottery": self.show_lottery,
                    "enable_stone": self.enable_stone,
                    "enable_large_plant_team": self.enable_large_plant_team,
                },
                f,
            )

    def load(self, load_dir):
        load_path = os.path.join(load_dir, "user_challenge4level")
        if os.path.exists(load_path):
            with open(load_path, "rb") as f:
                d = pickle.load(f)
            for k, v in d.items():
                if hasattr(self, k):
                    setattr(self, k, v)
        if self.advanced_challenge_book_amount > 5:
            self.advanced_challenge_book_amount = 5
        main_plant_list = list(
            filter(
                lambda x: x is not None,
                [self.repo.get_plant(x) for x in self.main_plant_list],
            )
        )
        main_plant_list.sort(
            key=lambda x: (x.grade, x.fight, x.name(self.lib)), reverse=True
        )
        self.main_plant_list = [x.id for x in main_plant_list]
        trash_plant_list = list(
            filter(
                lambda x: x is not None,
                [self.repo.get_plant(x) for x in self.trash_plant_list],
            )
        )
        trash_plant_list.sort(
            key=lambda x: (x.grade, x.fight, x.name(self.lib)), reverse=True
        )
        self.trash_plant_list = [x.id for x in trash_plant_list]


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
        if isinstance(self.main_plant_id, int):
            if self.repo.get_plant(self.main_plant_id) is None:
                self.main_plant_id = None
        else:
            self.main_plant_id = None
        auto_synthesis_pool_id = list(self.auto_synthesis_pool_id)
        for deputy_plant_id in auto_synthesis_pool_id:
            if self.repo.get_plant(deputy_plant_id) is None:
                self.auto_synthesis_pool_id.remove(deputy_plant_id)

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
        book_amount = self.repo.get_tool(
            self.attribute_book_dict[self.chosen_attribute]
        )['amount']
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
            book = self.repo.get_tool(self.attribute_book_dict[self.chosen_attribute])
            book['amount'] = max(book['amount'] - 1, 0)
        return result

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
        self.check_data()


class UserSettings:
    def __init__(
        self,
        cfg: Config,
        repo: Repository,
        lib: Library,
        user: User,
        caveMan: CaveMan,
        logger: IOLogger,
        save_dir=None,
    ):
        self.cfg = cfg
        self.friendman = user.friendMan
        self.repo = repo
        self.lib = lib
        self.user = user
        self.caveMan = caveMan
        self.save_dir = save_dir
        self.io_logger = logger
        self.logger = logger.new_logger()

        self.challenge4Level = Challenge4Level(
            cfg, user, repo, lib, caveMan, logger=self.logger
        )
        self.challenge4Level_enabled = True
        self.shop_enabled = False

        self.shop = Shop(cfg)
        self.shop_auto_buy_list = set()
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

    def _start(self, stop_channel: Queue, finished_trigger: Queue):
        while stop_channel.qsize() == 0:
            if self.shop_enabled:
                try:
                    shop_info = self.shop.buy_list(list(self.shop_auto_buy_list), 1)
                    for good_p_id, amount in shop_info:
                        self.logger.log(
                            f"购买了{amount}个{self.lib.get_tool_by_id(good_p_id).name}"
                        )
                    self.logger.log("购买完成")
                except Exception as e:
                    self.logger.log(f"购买失败，异常种类:{type(e).__name__}。跳过购买")
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
            if self.auto_use_item_enabled:
                try:
                    self.auto_use_item(stop_channel)
                except Exception as e:
                    self.logger.log(f"自动使用道具失败，异常种类:{type(e).__name__}。跳过自动使用道具")
                if stop_channel.qsize() > 0:
                    break
            if self.challenge4Level_enabled:
                try:
                    self.challenge4Level.auto_challenge(stop_channel)
                except Exception as e:
                    self.logger.log(f"自动挑战失败，异常种类:{type(e).__name__}。跳过自动挑战")
            self.logger.log("工作完成，等待{}".format(second2str(self.rest_time)))
            time.sleep(self.rest_time)
        finished_trigger.emit()

    def start(self, stop_channel: Queue, finished_trigger):
        finish_channel = Queue(maxsize=1)
        threading.Thread(
            target=self._start,
            args=(stop_channel, finished_trigger),
        ).start()
        return finish_channel

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
                    "shop_auto_buy_list": self.shop_auto_buy_list,
                    "auto_use_item_list": self.auto_use_item_list,
                    "garden_cave_list": self.garden_cave_list,
                    "enable_list": self.enable_list,
                    "rest_time": self.rest_time,
                    "arena_enabled": self.arena_enabled,
                    "task_enabled": self.task_enabled,
                },
                f,
            )
        self.plant_evolution.save(self.save_dir)
        self.auto_synthesis_man.save(self.save_dir)
        self.heritage_man.save(self.save_dir)

    def load(self):
        self.challenge4Level.load(self.save_dir)
        load_path = os.path.join(self.save_dir, "usersettings_state")
        if os.path.exists(load_path):
            with open(load_path, "rb") as f:
                d = pickle.load(f)
            for k, v in d.items():
                if hasattr(self, k):
                    setattr(self, k, v)
        self.plant_evolution.load(self.save_dir)
        self.auto_synthesis_man.load(self.save_dir)
        self.heritage_man.load(self.save_dir)
