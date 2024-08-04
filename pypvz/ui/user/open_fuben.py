import pickle
import concurrent.futures
from queue import Queue
import os
from threading import Event
import time
from ... import (
    Config,
    Repository,
    Library,
    WebRequest,
)
from ..message import Logger
from ...shop import Shop
from ...fuben import FubenCave
from ...utils.recover import RecoverMan
from ...utils.common import signal_block_emit


class OpenFubenMan:
    def __init__(self, cfg: Config, repo: Repository, lib: Library, logger: Logger):
        self.cfg = cfg
        self.repo = repo
        self.lib = lib
        self.logger = logger
        self.team = []
        self.ignored_cave_list = []
        self.wr = WebRequest(cfg)
        self.shop_req = Shop(cfg)
        self.recover_man = RecoverMan(cfg)
        self.fuben_layer_info_list: list[list[FubenCave]] = [None for _ in range(5)]
        self.max_pool_size = 3
        self.min_challenge_amount = 5
        self.need_recover = True
        self.recover_threshold = 0.01
        self.recover_choice = "高级血瓶"
        self.watch_id = 613  # 时之怀表id
        self.fuben_book_id = 612  # 副本挑战书id
        # self.shop_req.refresh_shop()

    def watch_repo_tool(self, tool_id):
        tool = self.repo.get_tool(tool_id)
        if tool is None:
            return 0
        return tool['amount']

    def get_world_fuben_caves(self, layer):
        body = [float(layer)]
        response = self.wr.amf_post_retry(
            body,
            "api.fuben.display",
            '/pvz/amf/',
            '副本洞口信息',
            logger=self.logger,
            except_retry=True,
        )
        caves = [FubenCave(root) for root in response.body['_caves']]
        self.world_fuben_challenge_amount = int(response.body['_lcc'])
        return caves

    def recover(self):
        cnt, max_retry = 0, 20
        success_num_all = 0
        while cnt < max_retry:
            recover_list = []
            for plant_id in self.team:
                plant = self.repo.get_plant(plant_id)
                if plant is None:
                    continue
                if plant.hp_now / plant.hp_max <= self.recover_threshold:
                    recover_list.append(plant_id)
            if len(recover_list) == 0:
                return True
            success_num, fail_num = self.recover_man.recover_list(
                recover_list, choice=self.recover_choice
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
        self.repo.refresh_repository()
        if success_num_all > 0:
            self.logger.log("成功给{}个植物回复血量".format(success_num_all))
        return True

    def get_cave_open_tools(self, target_cave: FubenCave, interrupt_event: Event):
        for open_tool in target_cave.open_tools:
            if interrupt_event.is_set():
                return False
            repo_tool = self.repo.get_tool(open_tool['id'])
            if repo_tool is not None and repo_tool['amount'] >= open_tool['amount']:
                continue

            good = self.shop_req.tool_id2good.get(open_tool['id'], None)
            if good is not None:
                buy_amount = max(
                    0,
                    open_tool['amount']
                    - (repo_tool['amount'] if repo_tool is not None else 0),
                )
                assert buy_amount > 0
                buy_result = self.shop_req.buy(
                    good.id,
                    buy_amount,
                )
                if not buy_result['success']:
                    self.logger.log(
                        "购买开启世界副本{}的道具失败，原因：{}".format(
                            target_cave.name, buy_result['result']
                        )
                    )
                    return False
                assert buy_result['tool_id'] == good.p_id
                if repo_tool is None:
                    self.repo.add_tool(
                        good.p_id,
                        0,
                    )
                    repo_tool = self.repo.get_tool(good.p_id)
                repo_tool['amount'] = buy_result['amount']
                continue

            source_cave = None
            for caves in self.fuben_layer_info_list:
                for cave in caves:
                    if cave.reward is None:
                        continue
                    if cave.reward == open_tool['id']:
                        source_cave = cave
                        break
                if source_cave is not None:
                    break
            if source_cave is not None:
                while True:
                    if interrupt_event.is_set():
                        return False
                    need_amount = open_tool['amount'] - (
                        repo_tool['amount'] if repo_tool is not None else 0
                    )
                    if need_amount <= 0:
                        break
                    if not self.challenge_world_cave(
                        source_cave, max(need_amount, self.min_challenge_amount)
                    ):
                        return False
                    self.repo.refresh_repository()
                    repo_tool = self.repo.get_tool(open_tool['id'])
                continue
            return False
        return True

    def add_cave_rest_count(self, target_cave: FubenCave, amount):
        body = [float(target_cave.cave_id), float(amount)]
        watch_amount = self.repo.get_tool(self.watch_id, return_amount=True)
        cnt, max_retry = 0, 20
        while cnt < max_retry:
            try:
                response = self.wr.amf_post_retry(
                    body,
                    "api.fuben.addCaveChallengeCount",
                    '/pvz/amf/',
                    '增加世界副本{}的挑战次数'.format(target_cave.name),
                    logger=self.logger,
                    allow_empty=True,
                )
                if response is None:
                    self.logger.log(
                        "增加世界副本{}的挑战次数返回值为空，判定为增加挑战次数失败".format(
                            target_cave.name
                        )
                    )
                    return False
                target_cave.rest_count = int(response.body)
                break
            except Exception as e:
                self.logger.log(
                    "增加世界副本{}的挑战次数出现异常，异常种类：{}。".format(
                        target_cave.name, e
                    )
                )
                self.repo.refresh_repository()
                now_amount = self.repo.get_tool(self.watch_id, return_amount=True)
                if now_amount != watch_amount:
                    self.logger.log("仓库怀表量发生变化，判定使用怀表成功")
                    self.repo.remove_tool(self.watch_id, amount)
                    return True
                if now_amount == 0:
                    self.logger.log("仓库怀表量为0，判定使用怀表失败")
                    return False
                cnt += 1
                self.logger.log(
                    "仓库怀表量未发生变化，暂停1s继续，最多再尝试{}次".format(
                        max_retry - cnt
                    )
                )
                time.sleep(1)
                continue
        self.repo.remove_tool(self.watch_id, amount)
        return True

    def challenge_world_cave(self, target_cave: FubenCave, amount):
        watch_tool = self.repo.get_tool(self.watch_id)
        fuben_book_tool = self.repo.get_tool(self.fuben_book_id)
        watch_tool_amount = watch_tool['amount'] if watch_tool is not None else 0
        fuben_book_tool_amount = (
            fuben_book_tool['amount'] if fuben_book_tool is not None else 0
        )
        if self.world_fuben_challenge_amount < amount:
            use_amount = min(
                amount - self.world_fuben_challenge_amount, fuben_book_tool_amount
            )
            if use_amount < amount - self.world_fuben_challenge_amount:
                self.logger.log(
                    "挑战世界副本{}失败，原因：副本挑战书数量不足".format(
                        target_cave.name
                    )
                )
                return False
            repo_tool = self.repo.get_tool(self.fuben_book_id)
            cnt, max_retry = 0, 20
            while cnt < max_retry:
                try:
                    use_result = self.repo.use_tool(
                        self.fuben_book_id, use_amount, self.lib
                    )
                    if not use_result["success"]:
                        self.logger.log(
                            "使用副本挑战书({})失败，原因：{}".format(
                                use_amount, use_result['result']
                            )
                        )
                        return False
                    break
                except Exception as e:
                    self.logger.log(
                        "使用副本挑战书({})出现异常，异常种类：{}，尝试刷新仓库".format(
                            use_amount, type(e).__name__
                        )
                    )
                    self.repo.refresh_repository()
                    if (
                        self.repo.get_tool(self.fuben_book_id, return_amount=True)
                        != repo_tool['amount']
                    ):
                        self.logger.log(
                            "仓库副本挑战书数量发生变化，判定使用副本挑战书成功"
                        )
                        break
                    cnt += 1
                    self.logger.log(
                        "仓库副本挑战书数量未发生变化，暂停1s继续，最多再尝试{}次".format(
                            max_retry - cnt
                        )
                    )
                    time.sleep(1)
                    continue
            self.world_fuben_challenge_amount += use_amount
            self.repo.remove_tool(self.fuben_book_id, use_amount)
        if target_cave.rest_count >= 0 and target_cave.rest_count < amount:
            use_amount = min(amount - target_cave.rest_count, watch_tool_amount)
            if use_amount < amount - target_cave.rest_count:
                self.logger.log(
                    "挑战世界副本{}失败，原因：时之怀表数量不足".format(
                        target_cave.name
                    )
                )
                return False
            self.add_cave_rest_count(target_cave, use_amount)

        def run():
            body = [
                float(target_cave.cave_id),
                [int(plant_id) for plant_id in self.team],
            ]
            response = self.wr.amf_post_retry(
                body,
                "api.fuben.challenge",
                '/pvz/amf/',
                '挑战副本洞口',
                logger=self.logger,
                allow_empty=True,
            )
            if response is None:
                return None
            if response.status != 0:
                return {
                    "success": False,
                    "result": response.body.description,
                }
            return {
                "success": True,
                "result": response.body,
            }

        futures = self._async_request([run for _ in range(amount)], return_future=True)
        for future in futures:
            try:
                result = future.result()
            except Exception as e:
                self.logger.log(
                    "挑战世界副本{}出现异常，异常种类：{}。判断为实际挑战了".format(
                        target_cave.name, e
                    )
                )
                continue
            if result is None:
                self.logger.log(
                    "挑战世界副本{}返回值为空，判定没有实际挑战".format(
                        target_cave.name
                    )
                )
                return False
            if not result['success']:
                self.logger.log(
                    "挑战世界副本{}失败，原因：{}".format(
                        target_cave.name, result['result']
                    )
                )
                return False
        if target_cave.rest_count >= 0:
            target_cave.rest_count = max(0, target_cave.rest_count - amount)
        self.logger.log(
            "成功挑战世界副本{}，挑战了{}次".format(target_cave.name, amount)
        )
        self.world_fuben_challenge_amount -= amount
        return True

    def _async_request(self, func_list, return_future=False):
        with concurrent.futures.ThreadPoolExecutor(
            max_workers=min(self.max_pool_size, len(func_list))
        ) as executor:
            futures = []
            for func in func_list:
                futures.append(executor.submit(func))
        if not return_future:
            for future in futures:
                try:
                    future.result()
                except Exception as e:
                    return False
            return True
        return futures

    def refresh_fuben_info(self):
        with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
            futures = []
            for layer in range(1, 6):
                futures.append(executor.submit(self.get_world_fuben_caves, layer))
        for i, future in enumerate(futures):
            try:
                self.fuben_layer_info_list[i] = future.result()
            except Exception as e:
                self.logger.log(
                    "获取世界副本信息出现异常，异常种类：{}。退出世界副本自动开图".format(
                        e
                    )
                )
                return False
        return True

    def get_available_world_fuben(self):
        available_fuben_list = []
        for i, caves in enumerate(self.fuben_layer_info_list):
            for cave in caves:
                if cave.status == 3 or cave.status == 4:
                    available_fuben_list.append((i, cave))
        return available_fuben_list

    def open_cave(self, target_cave: FubenCave):
        # api.fuben.openCave
        body = [
            float(target_cave.cave_id),
        ]
        response = self.wr.amf_post_retry(
            body,
            "api.fuben.openCave",
            '/pvz/amf/',
            '开启副本洞口',
            logger=self.logger,
            allow_empty=True,
        )
        if response is None:
            self.logger.log(
                "开启世界副本{}返回值为空，判定为开启副本成功".format(target_cave.name)
            )
            return True
        if response.status == 1:
            return False
        for open_tool in target_cave.open_tools:
            self.repo.remove_tool(open_tool['id'], open_tool['amount'])
        return True

    def start_world_fuben(self, interrupt_event: Event):
        if not self._async_request(
            [
                self.refresh_fuben_info,
                self.shop_req.refresh_shop,
                self.repo.refresh_repository,
            ]
        ):
            self.logger.log("开副本多线程失败，退出世界副本自动开图")
            return
        while True:
            if interrupt_event.is_set():
                return
            self.recover()
            available_fuben_list = self.get_available_world_fuben()
            if len(available_fuben_list) == 0:
                self.logger.log("没有可开启的世界副本，退出世界副本自动开图")
                return
            skip_fuben_list = []
            skip_ignore_fuben_list = []
            challenged = False
            for i, cave in available_fuben_list:
                if interrupt_event.is_set():
                    return
                continue_flag = False
                for c in self.ignored_cave_list:
                    if c.cave_id == cave.cave_id:
                        skip_ignore_fuben_list.append(cave)
                        continue_flag = True
                        break
                if continue_flag:
                    continue
                if not self.get_cave_open_tools(cave, interrupt_event):
                    # self.logger.log("获取世界副本{}的开启道具失败，跳过该副本".format(cave.name))
                    skip_fuben_list.append(cave)
                    continue
                self.logger.log(
                    "成功获取世界副本{}的开启道具: {}({})".format(
                        cave.name,
                        self.lib.get_tool_by_id(cave.open_tools[0]['id']).name,
                        cave.open_tools[0]['amount'],
                    )
                )
                cnt, max_retry = 0, 20
                while cnt < max_retry:
                    try:
                        open_result = self.open_cave(cave)
                        if not open_result:
                            self.logger.log(
                                "开启世界副本{}失败，尝试刷新仓库跳过该副本".format(
                                    cave.name
                                )
                            )
                            self.repo.refresh_repository()
                        break
                    except Exception as e:
                        cnt += 1
                        self.logger.log(
                            "开启世界副本{}出现异常，异常种类：{}。暂停1s重试，最多尝试{}次".format(
                                cave.name, type(e).__name__, max_retry - cnt
                            )
                        )
                        time.sleep(1)
                        continue
                if not open_result:
                    skip_fuben_list.append(cave)
                    continue

                self.logger.log("成功开启世界副本{}".format(cave.name))
                if not self.challenge_world_cave(cave, 1):
                    self.logger.log(
                        "挑战世界副本{}失败，退出世界副本自动开图".format(cave.name)
                    )
                    return
                self.logger.log("成功挑战世界副本{}，完成本副本开启".format(cave.name))
                challenged = True
            if len(skip_fuben_list) > 0 or len(skip_ignore_fuben_list) > 0:
                msg_list = []
                if len(skip_fuben_list) > 0:
                    msg_list.append(
                        "因为没有相应道具获取途径而跳过以下副本：{}".format(
                            ", ".join([cave.name for cave in skip_fuben_list])
                        )
                    )
                if len(skip_ignore_fuben_list) > 0:
                    msg_list.append(
                        "因为忽略列表忽略以下副本：{}".format(
                            ", ".join([cave.name for cave in skip_ignore_fuben_list])
                        )
                    )
                self.logger.log("。".join(msg_list))
            self.refresh_fuben_info()
            self.repo.refresh_repository()
            if not challenged and len(skip_fuben_list) == 0:
                self.logger.log(
                    "没有挑战或跳过任何副本，视为世界副本开图完毕。退出世界副本自动开图"
                )
                return

    def save(self, save_dir):
        save_path = os.path.join(save_dir, "open_fuben_man")
        with open(save_path, "wb") as f:
            pickle.dump(
                {
                    "team": self.team,
                    "max_pool_size": self.max_pool_size,
                    "min_challenge_amount": self.min_challenge_amount,
                    "ignored_cave_list": self.ignored_cave_list,
                    "need_recover": self.need_recover,
                    "recover_threshold": self.recover_threshold,
                    "recover_choice": self.recover_choice,
                },
                f,
            )

    def load(self, load_dir):
        load_path = os.path.join(load_dir, "open_fuben_man")
        if os.path.exists(load_path):
            with open(load_path, "rb") as f:
                d = pickle.load(f)
            for k, v in d.items():
                if hasattr(self, k):
                    setattr(self, k, v)
