import pickle
import os
import time
from queue import Queue
from concurrent.futures import ThreadPoolExecutor
import concurrent.futures
import threading

from ..shop import Shop

from ..cave import Cave
from .. import Config, Repository, Library, User, CaveMan, Task, SynthesisMan
from ..utils.recover import RecoverMan
from .message import IOLogger, Logger
from ..utils.evolution import PlantEvolution


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
        self.hp_choice = "中级血瓶"
        self.pop_after_100 = False
        self.pop_grade = 100
        self.auto_use_challenge_book = False

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
        else:
            raise NotImplementedError("cave type error: {}".format(cave.type))

        while True:
            result = self.caveMan.challenge(cave_id, team, difficulty, cave.type)
            success, result = result["success"], result["result"]
            if not success:
                if "狩猎场挑战次数已达上限" in result and self.auto_use_challenge_book:
                    use_result = self.repo.use_item(self.lib.name2tool["高级挑战书"].id, 1, self.lib)
                    if use_result["success"]:
                        logger.log(use_result["result"])
                        time.sleep(15)
                        continue
                    use_result = self.repo.use_item(self.lib.name2tool["挑战书"].id, 1, self.lib)
                    if use_result["success"]:
                        logger.log(use_result["result"])
                        time.sleep(15)
                        continue
                message = message + " 失败. 原因: {}.".format(
                    result,
                )
                logger.log(message)
                return False
            break

        plant_list = [
            self.repo.get_plant(int(plant_id['id']))
            for plant_id in result['assailants']
        ]
        plant_list = list(filter(lambda x: x is not None, plant_list))
        message = message + "\n\t出战植物: {}".format(
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
        plant_list = list(filter(lambda x: x is not None, plant_list))
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
            message = message + "\n\t升级植物: {}".format(' '.join(upgrade_list))
        # message = message + "\n\t掉落: {}".format(

        # )
        logger.log(message)
        if self.pop_after_100:
            trash_plant_list = [
                self.repo.get_plant(plant_id) for plant_id in self.trash_plant_list
            ]
            trash_plant_list = list(filter(lambda x: (x is not None) and x.grade < self.pop_grade, trash_plant_list))
            self.trash_plant_list = [x.id for x in trash_plant_list]
        return True

    def _assemble_team(self, cave: Cave):
        team = []
        team_grid_amount = 0
        for plant_id in self.main_plant_list:
            plant = self.repo.get_plant(plant_id)
            if plant is None:
                continue
            width = plant.width(self.lib)
            if team_grid_amount + width > self.grid_amount:
                break
            team.append(plant_id)
            team_grid_amount += width

        trash_plant_list = [
            self.repo.get_plant(plant_id) for plant_id in self.trash_plant_list
        ]
        trash_plant_list = list(filter(lambda x: x is not None, trash_plant_list))
        sorted_grade_trash_plant_list = sorted(
            trash_plant_list,
            key=lambda x: (x.grade, -x.width(self.lib)),
            reverse=True,
        )
        for plant in sorted_grade_trash_plant_list:
            width = plant.width(self.lib)
            if team_grid_amount + width > self.grid_amount:
                continue
            if cave.grade - plant.grade < 5:
                continue
            team.append(plant.id)
            team_grid_amount += width
        if team_grid_amount < self.grid_amount - self.free_max:
            return None
        return team

    def _recover(self, logger: Logger = None):
        max_attempts = 5
        rest_attempts = max_attempts
        while rest_attempts > 0:
            success_num, fail_num = self.recoverMan.recover_zero(
                need_refresh=False, choice=self.hp_choice
            )
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

                success = self._challenge(cave, team, difficulty, logger, friend=friend)
                if not success:
                    return

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
                    "hp_choice": self.hp_choice,
                    "pop_after_100": self.pop_after_100,
                    "auto_use_challenge_book": self.auto_use_challenge_book,
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
        main_plant_list = [self.repo.get_plant(x) for x in self.main_plant_list]
        main_plant_list.sort(
            key=lambda x: (x.grade, x.fight, x.name(self.lib)), reverse=True
        )
        self.main_plant_list = [x.id for x in main_plant_list]
        trash_plant_list = [self.repo.get_plant(x) for x in self.trash_plant_list]
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
        self.attribute_list = ["HP", "攻击", "命中", "闪避", "穿透", "护甲"]
        self.attribute_book_dict = {
            "HP": lib.name2tool["HP合成书"].id,
            "攻击": lib.name2tool["攻击合成书"].id,
            "命中": lib.name2tool["命中合成书"].id,
            "闪避": lib.name2tool["闪避合成书"].id,
            "穿透": lib.name2tool["穿透合成书"].id,
            "护甲": lib.name2tool["护甲合成书"].id,
        }

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
                id1, id2, self.attribute_book_dict[attribute_name], self.reinforce_number
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

    def synthesis(self):
        self.check_data()
        if self.main_plant_id is None:
            return {"success": False, "result": "未设置底座"}
        if len(self.auto_synthesis_pool_id) == 0:
            return {"success": False, "result": "合成池为空"}
        book_amount = self.repo.get_tool(
            self.attribute_book_dict[self.chosen_attribute]
        )['amount']
        if not book_amount > 0:
            return {"success": False, "result": f"{self.chosen_attribute}合成书数量不足"}
        reinforce_amount = self.repo.get_tool(self.lib.name2tool["增强卷轴"].id)['amount']
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
                },
                f,
            )

    def load(self, load_dir):
        load_path = os.path.join(load_dir, "user_autosynthesisman")
        if os.path.exists(load_path):
            with open(load_path, "rb") as f:
                d = pickle.load(f)
            for k, v in d.items():
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

        self.challenge4Level = Challenge4Level(cfg, user, repo, lib, caveMan)
        self.challenge4Level_enabled = True
        self.shop_enabled = False

        self.shop = Shop(cfg)
        self.shop_auto_buy_list = set()
        self.plant_evolution = PlantEvolution(cfg, repo, lib)
        self.task = Task(cfg)
        self.daily_task_enabled = False
        self.auto_use_item_enabled = False
        self.auto_use_item_list = []
        self.garden_cave_list = []

        self.auto_synthesis_man = AutoSynthesisMan(cfg, lib, repo)

    def _start(self, stop_channel: Queue, finished_trigger: Queue):
        logger = self.io_logger.new_logger()
        if self.shop_enabled:
            shop_info = self.shop.buy_list(list(self.shop_auto_buy_list), 1)
            for good_p_id, amount in shop_info:
                logger.log(f"购买了{amount}个{self.lib.get_tool_by_id(good_p_id).name}")
            logger.log("购买完成")
        if self.daily_task_enabled:
            self.task.refresh_task()
            for task in self.task.daily_task:
                if task.state == 1:
                    result = self.task.claim_reward(task)
                    logger.log(result['result'])
        if self.auto_use_item_enabled:
            self.auto_use_item(stop_channel, logger)
        if self.challenge4Level_enabled:
            self.challenge4Level.auto_challenge(stop_channel, logger=logger)
        finished_trigger.emit()

    def start(self, stop_channel: Queue, finished_trigger):
        finish_channel = Queue(maxsize=1)
        threading.Thread(
            target=self._start,
            args=(stop_channel, finished_trigger),
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

    def auto_use_item(self, stop_channel: Queue, logger):
        self.repo.refresh_repository()
        for tool_id in self.auto_use_item_list:
            if stop_channel.qsize() > 0:
                break
            repo_tool = self.repo.get_tool(tool_id)
            if repo_tool is None:
                continue
            tool_type = self.lib.get_tool_by_id(tool_id).type
            amount = repo_tool['amount']
            if tool_type == 3:
                while amount > 10:
                    result = self.repo.open_box(tool_id, 10, self.lib)
                    logger.log(result['result'])
                    amount -= 10
                result = self.repo.open_box(tool_id, amount, self.lib)
            else:
                raise RuntimeError("tool type not supported")
                # result = self.repo.use_item(tool_id, amount)
            logger.log(result['result'])
            for i in range(len(self.repo.tools)):
                if self.repo.tools[i]['id'] == tool_id:
                    break
            else:
                raise RuntimeError("tool not found")
            self.repo.tools.pop(i)

    def save(self):
        self.challenge4Level.save(self.save_dir)
        save_path = os.path.join(self.save_dir, "usersettings_state")
        with open(save_path, "wb") as f:
            pickle.dump(
                {
                    "challenge4Level_enabled": self.challenge4Level_enabled,
                    "shop_enabled": self.shop_enabled,
                    "daily_task_enabled": self.daily_task_enabled,
                    "shop_auto_buy_list": self.shop_auto_buy_list,
                    "auto_use_item_list": self.auto_use_item_list,
                    "garden_cave_list": self.garden_cave_list,
                },
                f,
            )
        self.plant_evolution.save(self.save_dir)
        self.auto_synthesis_man.save(self.save_dir)

    def load(self):
        self.challenge4Level.load(self.save_dir)
        load_path = os.path.join(self.save_dir, "usersettings_state")
        if os.path.exists(load_path):
            with open(load_path, "rb") as f:
                d = pickle.load(f)
            for k, v in d.items():
                setattr(self, k, v)
        self.plant_evolution.load(self.save_dir)
        self.auto_synthesis_man.load(self.save_dir)
