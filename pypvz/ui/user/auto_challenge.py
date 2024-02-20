import pickle
import os
import time
from queue import Queue

from ...cave import Cave
from ... import (
    Config,
    Repository,
    Library,
    User,
    CaveMan,
)
from ...utils.recover import RecoverMan
from ..message import Logger
from . import load_data, save_data


class SingleCave:
    def __init__(self, cave: Cave, difficulty=3, garden_layer=None, use_sand=False):
        self.difficulty = difficulty  # 1: easy, 2: normal, 3: hard
        self.garden_layer = garden_layer
        self.use_sand = use_sand
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
        logger: Logger = None,
    ):
        self.cfg = cfg
        self.user = user
        self.friendMan = user.friendMan
        self.repo = repo
        self.lib = lib
        self.caveMan = CaveMan(cfg, lib)
        self.recoverMan = RecoverMan(cfg)
        self.logger = logger

        self.caves: list[SingleCave] = []
        self.main_plant_list: list[int] = []
        self.trash_plant_list: list[int] = []
        self.friend_id2cave = {}
        self.garden_layer_friend_id2cave = {} if cfg.server == "私服" else None
        self.garden_layer_caves = {} if cfg.server == "私服" else None
        self.hp_choice = "高级血瓶"
        self.pop_after_100 = True
        self.pop_grade = 100
        self.auto_use_challenge_book = False
        self.normal_challenge_book_amount = 1
        self.advanced_challenge_book_amount = 1
        self.enable_sand = False
        self.show_lottery = False
        self.enable_stone = True
        self.enable_large_plant_team = False
        self.exit_no_trash_plant = False
        self.show_series_success = False
        self.series_success_exit = False

        self.disable_cave_info_fetch = False
        self.need_recover = True
        self.accelerate_repository_in_challenge_cave = False

        self.current_garden_layer = None

        self.main_plant_recover = False
        self.main_plant_recover_rate = 0.01

        self.has_challenged = False
        self.cooldown_cave_id_set = set()
        self.stone_book_per_use = 0

    def add_cave(
        self,
        cave: Cave,
        friend_ids=None,
        difficulty=3,
        enabled=True,
        garden_layer=None,
        use_sand=False,
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
                for i, friend in enumerate(self.friendMan.friends):
                    if friend.grade < grade or (cave.type != 2 and i > 0):
                        break
                    friend_ids.append(friend.id)
            else:
                raise TypeError("friend_ids must be int or list[int]")
            if len(friend_ids) == 0:
                self.logger.log("你的等级不够，不能添加洞口{}".format(cave.name))
                return
            sc = SingleCave(
                cave,
                difficulty=difficulty,
                garden_layer=garden_layer,
                use_sand=use_sand,
            )
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
            sc = SingleCave(cave, use_sand=use_sand)
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

    def remove_cave_friend(self, sc, friend_ids, garden_layer=None):
        assert isinstance(sc, SingleCave)
        if self.cfg.server == "私服":
            self.friend_id2cave = self.garden_layer_friend_id2cave.get(garden_layer)

        if not sc.cave.type <= 3:
            return
        for friend_id in friend_ids:
            sc.friend_id_list.remove(friend_id)
            sc.friend_id2cave_id.pop(friend_id, None)
            self.friend_id2cave[friend_id].remove((sc.cave.id, sc.cave.name))

    def _assemble_team(self, grade):
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
        if team_grid_amount == team_limit or grade is None:
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
            if grade - plant.grade < 5:
                continue
            team.append(plant.id)
            team_grid_amount += width
        return team

    def _recover(self):
        cnt, max_retry = 0, 20
        success_num_all = 0
        while cnt < max_retry:
            recover_list = self.repo.hp_below(0, id_only=True)
            if self.main_plant_recover:
                for plant_id in self.main_plant_list:
                    plant = self.repo.get_plant(plant_id)
                    if plant is None:
                        continue
                    if plant_id in recover_list:
                        continue
                    if plant.hp_now / plant.hp_max < self.main_plant_recover_rate:
                        recover_list.append(plant_id)
            success_num, fail_num = self.recoverMan.recover_list(
                recover_list, choice=self.hp_choice
            )
            success_num_all += success_num
            if fail_num == 0:
                break
            self.logger.log(
                "尝试恢复植物血量。成功{}，失败{}".format(success_num, fail_num)
            )
            self.repo.refresh_repository(logger=self.logger)
            cnt += 1
        else:
            self.logger.log("尝试恢复植物血量失败，退出运行")
            return False
        if success_num_all > 0:
            self.logger.log("成功给{}个植物回复血量".format(success_num_all))
        return True

    def format_upgrade_message(self, team, response_body, cave_grade):
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

        if not self.accelerate_repository_in_challenge_cave:
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
                message = message + "\n\t升级植物: {}".format(
                    ' '.join(upgrade_msg_list)
                )
        else:
            plant_grade_list = []
            for plant in plant_list:
                if not hasattr(plant, "predict_grade"):
                    setattr(plant, "predict_grade", plant.grade)
                plant_grade_list.append((plant, plant.predict_grade))
            upgrade_data_list = []
            for plant, grade in plant_grade_list:
                if plant.predict_grade < cave_grade - 29:
                    plant.predict_grade = cave_grade - 29
                elif plant.predict_grade < cave_grade - 5:
                    plant.predict_grade = plant.predict_grade + 2.5
                upgrade_data_list.append((plant, grade, plant.predict_grade))
            upgrade_msg_list = [
                "{}({}->{})".format(
                    plant.name(self.lib),
                    int(grade1),
                    int(grade2),
                )
                for plant, grade1, grade2 in upgrade_data_list
            ]
            if len(upgrade_msg_list) > 0:
                message = message + "\n\t预测升级植物: {}".format(
                    ' '.join(upgrade_msg_list)
                )
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

    def pop_trash_plant(self):
        if not self.accelerate_repository_in_challenge_cave:
            trash_plant_list = [
                self.repo.get_plant(plant_id) for plant_id in self.trash_plant_list
            ]
            trash_plant_list = list(
                filter(
                    lambda x: (x is not None) and x.grade < self.pop_grade,
                    trash_plant_list,
                )
            )
            self.trash_plant_list = [x.id for x in trash_plant_list]
        else:
            trash_plant_list = [
                self.repo.get_plant(plant_id) for plant_id in self.trash_plant_list
            ]
            new_trash_plant_id_list = []
            for plant in trash_plant_list:
                if plant is None:
                    continue
                if not hasattr(plant, "predict_grade"):
                    if plant.grade < self.pop_grade:
                        new_trash_plant_id_list.append(plant.id)
                    continue
                if plant.predict_grade < self.pop_grade:
                    new_trash_plant_id_list.append(plant.id)
            self.trash_plant_list = new_trash_plant_id_list

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
                if self.exit_no_trash_plant and len(self.trash_plant_list) == 0:
                    return False
                for sc in self.caves:
                    if sc.cave.id == id and sc.cave.name == name:
                        break
                else:
                    continue
                if not sc.enabled or sc.cave.type not in [1, 2, 3]:
                    continue
                if self.disable_cave_info_fetch:
                    cave_id = sc.cave.quick_cave_id(friend_id, sc.garden_layer)
                    if cave_id in self.cooldown_cave_id_set:
                        continue

                    if self.enable_sand and sc.use_sand:
                        cnt, max_retry = 0, 20
                        while cnt < max_retry:
                            cnt += 1
                            try:
                                sand_result = self.caveMan.use_sand(cave_id)
                                break
                            except Exception as e:
                                self.logger.log(
                                    "使用时之沙异常，暂停1秒，最多再尝试{}次。异常种类:{}".format(
                                        max_retry - cnt, type(e).__name__
                                    )
                                )
                                continue
                        else:
                            self.logger.log(
                                "使用时之沙失败，终止刷洞。原因: 重试次数超过{}次.".format(
                                    max_retry
                                )
                            )
                            return False
                        if sand_result["success"]:
                            self.logger.log(
                                "成功对{}使用时之沙".format(
                                    sc.cave.format_name(sc.difficulty)
                                )
                            )
                        else:
                            self.logger.log(sand_result["result"])
                            continue
                else:
                    cave = get_cave(
                        friend_id,
                        sc,
                    )
                    cave_id = cave.cave_id
                    if not cave.is_ready:
                        if self.enable_sand and sc.use_sand:
                            cnt, max_retry = 0, 20
                            while cnt < max_retry:
                                cnt += 1
                                try:
                                    sand_result = self.caveMan.use_sand(cave_id)
                                    break
                                except Exception as e:
                                    self.logger.log(
                                        "使用时之沙异常，暂停1秒，最多再尝试{}次。异常种类:{}".format(
                                            max_retry - cnt, type(e).__name__
                                        )
                                    )
                                    continue
                            else:
                                self.logger.log(
                                    "使用时之沙失败，终止刷洞。原因: 重试次数超过{}次.".format(
                                        max_retry
                                    )
                                )
                                return False
                            if sand_result["success"]:
                                self.logger.log(
                                    "成功对{}使用时之沙".format(
                                        sc.cave.format_name(sc.difficulty)
                                    )
                                )
                            else:
                                self.logger.log(sand_result["result"])
                                continue
                        else:
                            continue

                team = self._assemble_team(sc.cave.grade)
                if team is None:
                    continue
                if (
                    self.need_recover
                    and not self.accelerate_repository_in_challenge_cave
                ):
                    success = self._recover()
                    if not success:
                        return True
                difficulty = sc.difficulty
                friend = self.friendMan.id2friend[friend_id]

                message = "挑战{}({}) {}".format(
                    friend.name,
                    friend.grade,
                    sc.cave.format_name(difficulty),
                )
                cnt, max_retry = 0, 20
                need_skip = False
                while cnt < max_retry:
                    cnt += 1
                    try:
                        result = self.caveMan.challenge(
                            cave_id, team, difficulty, sc.cave.type
                        )
                        success, result = result["success"], result["result"]
                        if not success:
                            if (
                                "狩猎场挑战次数已达上限" in result
                                or "挑战次数不足" in result
                            ) and self.auto_use_challenge_book:
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
                            if "冷却中" in result:
                                message = (
                                    message + "失败，已跳过该洞口。原因: 洞口冷却中."
                                )
                                self.logger.log(message)
                                need_skip = True
                                if self.disable_cave_info_fetch:
                                    self.cooldown_cave_id_set.add(cave_id)
                                break
                            message = message + "失败. 原因: {}.".format(result)
                            self.logger.log(message)
                            return False
                        else:
                            message = message + "成功. "
                            self.has_challenged = True
                            break
                    except Exception as e:
                        if isinstance(e, RuntimeError):
                            self.logger.log(
                                "刷洞出现异常，继续挑战，最多再挑战{}次。异常原因：{}".format(
                                    max_retry - cnt, str(e)
                                )
                            )
                        else:
                            self.logger.log(
                                "刷洞出现异常，继续挑战，最多再挑战{}次。异常类型：{}".format(
                                    max_retry - cnt, type(e).__name__
                                )
                            )
                        continue
                else:
                    message = message + "失败. 原因: 重试次数超过{}次.".format(
                        max_retry
                    )
                    self.logger.log(message)
                    return False

                if need_skip:
                    if stop_channel.qsize() > 0:
                        return False
                    continue

                message = message + "挑战结果：{}".format(
                    "胜利" if result['is_winning'] else "失败"
                )
                if self.show_series_success or self.series_success_exit:
                    if not hasattr(sc, 'series_success_count'):
                        sc.series_success_count = 0
                    if result['is_winning']:
                        sc.series_success_count += 1
                    else:
                        sc.series_success_count = 0
                    if self.show_series_success:
                        message = message + "，连胜次数：{}".format(
                            sc.series_success_count
                        )
                message = message + self.format_upgrade_message(
                    team, result, sc.cave.grade
                )
                self.logger.log(message)
                if self.pop_after_100:
                    self.pop_trash_plant()
                if stop_channel.qsize() > 0:
                    return False
                if self.series_success_exit and sc.series_success_count >= 20:
                    self.logger.log("连胜次数达到20，终止运行")
                    return False
        return True

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
                if self.exit_no_trash_plant and len(self.trash_plant_list) == 0:
                    return
                if sc.cave.type != 4 or not sc.enabled:
                    continue
                if not self.disable_cave_info_fetch:
                    cave = get_stone_cave(sc.cave.layer, sc.cave.number)
                    if not cave.is_ready:
                        continue
                team = self._assemble_team(sc.cave.grade)
                if team is None or len(team) == 0:
                    continue
                if (
                    self.need_recover
                    and not self.accelerate_repository_in_challenge_cave
                ):
                    success = self._recover()
                    if not success:
                        return
                difficulty = sc.difficulty

                message = "挑战{}".format(
                    sc.cave.format_name(difficulty),
                )
                if self.disable_cave_info_fetch:
                    cave_id = sc.cave.quick_cave_id()
                else:
                    cave_id = cave.id
                cnt, max_retry = 0, 20
                while cnt < max_retry:
                    cnt += 1
                    try:
                        result = self.caveMan.challenge(cave_id, team, difficulty, 4)
                        success, result = result["success"], result["result"]
                        if not success:
                            if "挑战次数不足" in result and self.stone_book_per_use > 0:
                                use_result = self.repo.use_item(
                                    self.lib.name2tool["宝石挑战书"].id,
                                    self.stone_book_per_use,
                                    self.lib,
                                )
                                if use_result["success"]:
                                    self.logger.log(use_result["result"])
                                    continue
                                else:
                                    self.logger.log(use_result["result"])
                                    return
                            message = message + "失败. 原因: {}.".format(result)
                            self.logger.log(message)
                            return
                            # if "挑战次数不足" in result:
                        else:
                            message = message + "成功. "
                            self.has_challenged = True
                            break
                    except Exception as e:
                        if isinstance(e, RuntimeError):
                            self.logger.log(
                                "刷洞出现异常，继续挑战，最多再挑战{}次。异常原因：{}".format(
                                    max_retry - cnt, str(e)
                                )
                            )
                        else:
                            self.logger.log(
                                "刷洞出现异常，继续挑战，最多再挑战{}次。异常类型：{}".format(
                                    max_retry - cnt, type(e).__name__
                                )
                            )
                        continue
                else:
                    message = message + "失败. 原因: 重试次数超过{}次.".format(
                        max_retry
                    )
                    self.logger.log(message)
                    return

                has_challenged = True
                message = message + "挑战结果：{}".format(
                    "胜利" if result['is_winning'] else "失败"
                )
                message = message + self.format_upgrade_message(
                    team, result, sc.cave.grade
                )
                self.logger.log(message)
                if self.pop_after_100:
                    self.pop_trash_plant()
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

        cnt, max_retry = 0, 20
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
        self.current_garden_layer = target_garden_layer
        return True

    def auto_challenge(self, stop_channel: Queue):
        # TODO: 显示功能：将process显示，可加速版
        assert self.main_plant_list is not None and self.trash_plant_list is not None
        if self.enable_stone:
            self.challenge_stone_fuben(stop_channel)
        if self.cfg.server == "官服":
            raise NotImplementedError("助手不支持官服")
        elif self.cfg.server != "私服":
            raise NotImplementedError("助手不支持服务器:{}".format(self.cfg.server))
        while True:
            enter_time = time.perf_counter()
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
                    if not self.challenge_cave(stop_channel):
                        return False
                except Exception as e:
                    self.logger.log(
                        "挑战第{}层洞口异常，异常种类:{}。跳过该层".format(
                            garden_layer, type(e).__name__
                        )
                    )
            time.sleep(max(0, 0.2 - (time.perf_counter() - enter_time)))
            if stop_channel.qsize() > 0:
                break
            if self.exit_no_trash_plant and len(self.trash_plant_list) != 0:
                continue
            break
        self.logger.log("挑战完成")
        return True

    def save(self, save_dir=None):
        data = {
            "caves": self.caves,
            "main_plant_list": self.main_plant_list,
            "trash_plant_list": self.trash_plant_list,
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
            "disable_cave_info_fetch": self.disable_cave_info_fetch,
            "need_recover": self.need_recover,
            "accelerate_repository_in_challenge_cave": self.accelerate_repository_in_challenge_cave,
            "main_plant_recover": self.main_plant_recover,
            "main_plant_recover_rate": self.main_plant_recover_rate,
            "exit_no_trash_plant": self.exit_no_trash_plant,
            "show_series_success": self.show_series_success,
            "series_success_exit": self.series_success_exit,
            "stone_book_per_use": self.stone_book_per_use,
        }
        return save_data(data, save_dir, "user_challenge4level")

    def load(self, load_dir):
        load_data(load_dir, "user_challenge4level", self)
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
