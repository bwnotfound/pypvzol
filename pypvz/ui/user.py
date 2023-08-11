import pickle
import os
from queue import Queue
from concurrent.futures import ThreadPoolExecutor
import concurrent.futures
import threading

from pyamf import DecodeError

from ..cave import Cave
from .. import Config, Repository, Library, User, CaveMan
from .message import IOLogger
from ..utils.recover import RecoverMan
from .message import Logger


class SingleCave:
    # main_plant_list: list[int] = None
    # trash_plant_list: list[int] = None

    def __init__(self, cave: Cave):
        self.difficulty = 1  # 1: easy, 2: normal, 3: hard
        self.enabled = True
        self.friend_id_list: list[int] = []
        self.cave = cave


class Challenge4Level:
    def __init__(
        self,
        cfg: Config,
        user: User,
        repo: Repository,
        lib: Library,
        caveMan: CaveMan,
        grid_amount=10,
        challenge_order=1,  # 1: 一个洞口挑战完所有好友或者不足以让战斗格填满后挑战下一个洞口 2: 一个好友挑战完所有洞口或者不足以让战斗格填满后挑战下一个好友
        free_max=10,
        stone_cave_challenge_max_attempts=25,
    ):
        self.cfg = cfg
        self.user = user
        self.friendman = user.friendMan
        self.repo = repo
        self.lib = lib
        self.caveMan = caveMan
        self.recoverMan = RecoverMan(cfg, repo)
        self.grid_amount = grid_amount

        self.caves: list[SingleCave] = []
        self.main_plant_list: list[int] = []
        self.trash_plant_list: list[int] = []
        self.challenge_order = challenge_order
        self.free_max = free_max
        self.friend_id2cave_id = {}
        self.stone_cave_challenge_max_attempts = stone_cave_challenge_max_attempts

    def add_cave(self, cave: Cave, friend_ids=None, difficulty=1, enabled=True):
        # 这里的cave需要的是cave的id属性，不是cave_id
        for c in self.caves:
            if cave.id == c.cave.id:
                print("cave already exists")
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
                raise ValueError("no friend can challenge this cave")
            sc = SingleCave(cave)
            sc.difficulty = difficulty
            sc.enabled = enabled
            for friend_id in friend_ids:
                sc.friend_id_list.append(friend_id)
                self.friend_id2cave_id.setdefault(friend_id, set()).add(cave.id)
            self.caves.append(sc)
        elif cave.type == 4:
            sc = SingleCave(cave)
            sc.difficulty = difficulty
            sc.enabled = enabled
            self.caves.append(sc)
        else:
            raise NotImplementedError

    def remove_cave(self, cave):
        if isinstance(cave, Cave):
            cave = cave.id
        assert isinstance(cave, int)

        sc = None
        for c in self.caves:
            if c.cave.id == cave:
                sc = c
                break
        assert sc is not None

        if sc.cave.type <= 3:
            pop_list = []
            for k, v in self.friend_id2cave_id.items():
                if cave in v:
                    v.remove(cave)
                if len(v) == 0:
                    pop_list.append(k)
            for k in pop_list:
                self.friend_id2cave_id.pop(k)
            for i, c in enumerate(self.caves):
                if c.cave.id == cave:
                    break
            self.caves.pop(i)
        elif sc.cave.type == 4:
            for i, c in enumerate(self.caves):
                if c.cave.id == cave:
                    break
            self.caves.pop(i)
        else:
            raise NotImplementedError

    def _challenge(self, cave: Cave, team, difficulty, logger: Logger, friend=None):
        if cave.type <= 3:
            cave_id = cave.cave_id
        elif cave.type == 4:
            assert friend is None
            cave_id = cave.id
        else:
            raise NotImplementedError

        try:
            result = self.caveMan.challenge(cave_id, team, difficulty, cave.type)
        except DecodeError:
            logger.log(
                "Amf DecodeError。 重定向的解析问题，暂时没有去解决，退出程序。不过可以继续重新运行，该bug发生频率约为每次挑战的1/10。"
            )
            return False
        success, result = result["success"], result["result"]

        if cave.type <= 3:
            message = "挑战{}({}) {}".format(
                friend.name,
                friend.grade,
                cave.format_name(difficulty),
            )
        elif cave.type == 4:
            message = "挑战{}".format(
                cave.format_name(difficulty),
            )
        if not success:
            message = message + " 失败. 原因: {}".format(
                result.description,
            )
            logger.log(message)
            return False

        message += "."
        plant_list = [
            self.repo.get_plant(int(plant_id['id']))
            for plant_id in result['assailants']
        ]
        message = message + "\n\t\t出战植物: {}".format(
            ' '.join(
                [
                    "{}({})".format(plant.name(self.lib), plant.grade)
                    for plant in plant_list
                ]
            )
        )
        grade_copy_list = [plant.grade for plant in plant_list]
        self.repo.refresh_repository()
        plant_list = [
            self.repo.get_plant(int(plant_id['id']))
            for plant_id in result['assailants']
        ]
        upgrade_list = [
            "{}({}->{})".format(
                plant.name(self.lib),
                grade_copy_list[i],
                plant.grade,
            )
            for i, plant in enumerate(plant_list)
            if plant.grade != grade_copy_list[i]
        ]
        if len(upgrade_list) > 0:
            message = message + "\n\t\t升级植物: {}".format(' '.join(upgrade_list))
        # message = message + "\n\t\t掉落: {}".format(

        # )
        logger.log(message)
        return True

    def _assemble_team(self, cave: Cave):
        team = []
        team_grid_amount = 0
        for plant_id in self.main_plant_list:
            plant = self.repo.get_plant(plant_id)
            assert plant is not None
            width = plant.width(self.lib)
            if team_grid_amount + width > self.grid_amount:
                break
            team.append(plant_id)
            team_grid_amount += width
        for plant_id in reversed(self.trash_plant_list):
            plant = self.repo.get_plant(plant_id)
            assert plant is not None
            width = plant.width(self.lib)
            if team_grid_amount + width > self.grid_amount:
                continue
            if cave.grade - plant.grade < 5:
                continue
            team.append(plant_id)
            team_grid_amount += width
        if team_grid_amount < self.grid_amount - self.free_max:
            return None
        return team
    
    def _recover(self, logger: Logger = None):
        max_attempts = 5
        rest_attempts = max_attempts
        while rest_attempts > 0:
            success_num, fail_num = self.recoverMan.recover_zero(need_refresh=False)
            if fail_num == 0:
                break
            self.repo.refresh_repository()
            rest_attempts -= 1
        if fail_num > 0:
            logger.log(f"尝试恢复植物血量，失败{max_attempts}。退出运行，你依旧可以重新运行。")
            return False
        return True

    def auto_challenge(self, stop_channel: Queue, logger: Logger = None):
        # TODO: 显示功能：将process显示，可加速版
        assert self.main_plant_list is not None and self.trash_plant_list is not None
        if self.challenge_order != 1:
            raise NotImplementedError

        _cave_map = {}

        def get_stone_cave(chapter_id, type, layer):
            uid = f"{type}_{layer}_{chapter_id}"
            caves = _cave_map.get(uid)
            if caves is None:
                _cave_map[uid] = caves = self.caveMan.get_caves(chapter_id, type)
            assert layer >= 1 and layer <= len(caves)
            return caves[layer - 1]

        break_flag = False
        while not break_flag:
            has_challenged = False
            for sc in self.caves:
                if sc.cave.type != 4 or not sc.enabled:
                    continue
                cave = get_stone_cave(sc.cave.chapter_id, sc.cave.type, sc.cave.layer)
                if not cave.is_ready:
                    continue
                team = self._assemble_team(cave)
                if team is None:
                    continue

                success = self._recover(logger=logger)
                if not success:
                    return

                difficulty = sc.difficulty

                success = self._challenge(cave, team, difficulty, logger)
                if not success:
                    break_flag = True
                    break
                has_challenged = True
                if stop_channel.qsize() > 0:
                    logger.log("stop auto challenge")
                    return
            if not has_challenged:
                break_flag = True

        def get_cave(friend_id, id, type, layer):
            uid = f"{friend_id}_{type}_{layer}"
            caves = _cave_map.get(uid)
            if caves is None:
                caves = self.caveMan.get_caves(friend_id, type, layer)
                _cave_map[uid] = caves
            find_flag = False
            for cave in caves:
                if cave.id == id:
                    find_flag = True
                    break
            if not find_flag:
                raise ValueError(f"can't find cave {id}")
            return cave

        tasks = []
        with ThreadPoolExecutor() as executor:
            for friend_id, cave_ids in self.friend_id2cave_id.items():
                for id in cave_ids:
                    for sc in self.caves:
                        if sc.cave.id == id:
                            break
                    if not sc.enabled:
                        continue
                    tasks.append(
                        executor.submit(
                            get_cave, friend_id, id, sc.cave.type, sc.cave.layer
                        )
                    )
        _, _ = concurrent.futures.wait(
            tasks, return_when=concurrent.futures.ALL_COMPLETED
        )
        # TODO: 这里的全部加载可能有点问题，等待进一步排查
        for friend_id, cave_ids in self.friend_id2cave_id.items():
            for id in cave_ids:
                for sc in self.caves:
                    if sc.cave.id == id:
                        break
                if not sc.enabled:
                    continue
                cave = get_cave(
                    friend_id,
                    id,
                    sc.cave.type,
                    sc.cave.layer if sc.cave.type <= 3 else None,
                )
                if not cave.is_ready:
                    continue

                team = self._assemble_team(cave)
                if team is None:
                    continue

                success = self._recover(logger=logger)
                if not success:
                    return

                difficulty = sc.difficulty

                friend = self.friendman.id2friend[friend_id]

                self._challenge(cave, team, difficulty, logger, friend=friend)

                if stop_channel.qsize() > 0:
                    logger.log("stop auto challenge")
                    return
        logger.log("挑战完成")

    def save(self, save_dir):
        save_path = os.path.join(save_dir, "user_challenge4level")
        with open(save_path, "wb") as f:
            pickle.dump(
                {
                    "caves": self.caves,
                    "main_plant_list": self.main_plant_list,
                    "trash_plant_list": self.trash_plant_list,
                    "challenge_order": self.challenge_order,
                    "free_max": self.free_max,
                    "friend_id2cave_id": self.friend_id2cave_id,
                    "stone_cave_challenge_max_attempts": self.stone_cave_challenge_max_attempts,
                },
                f,
            )

    def load(self, load_dir):
        load_path = os.path.join(load_dir, "user_challenge4level")
        if os.path.exists(load_path):
            with open(load_path, "rb") as f:
                d = pickle.load(f)
            for k, v in d.items():
                setattr(self, k, v)


class UserSettings:
    def __init__(
        self,
        cfg: Config,
        repo: Repository,
        lib: Library,
        user: User,
        caveMan: CaveMan,
        save_dir=None,
    ):
        self.cfg = cfg
        self.friendman = user.friendMan
        self.repo = repo
        self.lib = lib
        self.user = user
        self.caveMan = caveMan
        self.save_dir = save_dir

        self.challenge4Level = Challenge4Level(cfg, user, repo, lib, caveMan)
        self.challenge4Level_enabled = False

    def _start(self, stop_channel: Queue, finished_trigger:Queue, logger: Logger = None):
        # import time
        # for i in range(5):
        #     logger.log(i)
        #     time.sleep(1)
        if self.challenge4Level_enabled:
            self.challenge4Level.auto_challenge(stop_channel, logger=logger)
        finished_trigger.emit()

    def start(self, stop_channel: Queue, finished_trigger, logger: Logger = None):
        finish_channel = Queue(maxsize=1)
        threading.Thread(
            target=self._start, args=(stop_channel, finished_trigger), kwargs={'logger': logger}
        ).start()
        return finish_channel

    def add_cave_challenge4Level(
        self, cave: Cave, friend_ids=None, difficulty=1, enabled=True
    ):
        self.challenge4Level.add_cave(
            cave,
            friend_ids=friend_ids,
            difficulty=difficulty,
            enabled=enabled,
        )

    def remove_cave_challenge4Level(self, cave: Cave):
        self.challenge4Level.remove_cave(cave)

    def save(self):
        self.challenge4Level.save(self.save_dir)
        save_path = os.path.join(self.save_dir, "usersettings_state")
        with open(save_path, "wb") as f:
            pickle.dump(
                {
                    "challenge4Level_enabled": self.challenge4Level_enabled,
                },
                f,
            )

    def load(self):
        self.challenge4Level.load(self.save_dir)
        load_path = os.path.join(self.save_dir, "usersettings_state")
        if os.path.exists(load_path):
            with open(load_path, "rb") as f:
                d = pickle.load(f)
            for k, v in d.items():
                setattr(self, k, v)
