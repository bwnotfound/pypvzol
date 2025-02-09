import time
import logging
from concurrent.futures import ThreadPoolExecutor, as_completed

from pyamf import remoting, AMF0, DecodeError

from .. import Config, WebRequest, Repository

# from ..config import Config
# from ..web import WebRequest
# from ..repository import Repository


class RecoverMan:
    def __init__(self, cfg: Config):
        self.wr = WebRequest(cfg)
        self.cfg = cfg
        self.heal_dict = {
            "低级血瓶": 13,
            "中级血瓶": 14,
            "高级血瓶": 15,
        }

    def recover(self, target_id, choice='中级血瓶'):
        body = [float(target_id), float(self.heal_dict[choice])]
        response = self.wr.amf_post_retry(
            body, "api.apiorganism.refreshHp", "/pvz/amf/", "回复植物血量"
        )
        if response.status == 0:
            return {"success": True, "result": int(response.body)}
        else:
            description = response.body.description
            if "该生物不存在" in description:
                return {"success": False, "result": "该生物不存在"}
            if "该植物血量已满" in description:
                return {"success": False, "result": "该植物血量已满"}
            return {"success": False, "result": response.body.description}

    def recover_list(self, target_id_list, choice='中级血瓶', pool_size=3):
        success_num = 0
        fail_num = 0
        if len(target_id_list) == 0:
            return success_num, fail_num
        with ThreadPoolExecutor(max_workers=pool_size) as executor:
            futures = [
                executor.submit(self.recover, id, choice) for id in target_id_list
            ]

        for future in as_completed(futures):
            try:
                result = future.result()
                if result["success"] or "该植物血量已满" in result["result"]:
                    success_num += 1
                elif "该生物不存在" in result["result"]:
                    raise RuntimeError("该生物不存在")
                else:
                    logging.warning("回复植物血量失败: {}".format(result["result"]))
                    fail_num += 1
            except Exception as e:
                logging.warning(
                    "回复植物血量异常，异常信息：{}:{}".format(type(e).__name__, str(e))
                )
                fail_num += 1
        return success_num, fail_num

    def recover_list_stable(
        self,
        plant_id_list,
        repo: Repository,
        recover_threshold,
        logger,
        choice='高级血瓶',
        pool_size=3,
        refresh_repo_first=True,
    ):
        if len(plant_id_list) == 0 or recover_threshold >= 1:
            return True
        if refresh_repo_first:
            repo.refresh_repository()
        cnt, max_retry = 0, 20
        success_num_all = 0
        while cnt < max_retry:
            recover_list = []
            for plant_id in plant_id_list:
                plant = repo.get_plant(plant_id)
                if plant is None:
                    continue
                if plant.hp_now / plant.hp_max <= recover_threshold:
                    recover_list.append(plant_id)
            if len(recover_list) == 0:
                return True
            success_num, fail_num = self.recover_list(
                recover_list, choice=choice, pool_size=pool_size
            )
            success_num_all += success_num
            if fail_num == 0:
                break
            logger.log("尝试恢复植物血量。成功{}，失败{}".format(success_num, fail_num))
            repo.refresh_repository(logger=logger)
            cnt += 1
        else:
            logger.log("尝试恢复植物血量失败，退出运行")
            return False
        repo.refresh_repository()
        if success_num_all > 0:
            logger.log("成功给{}个植物回复血量".format(success_num_all))
        return True

    def recover_zero(self, repo: Repository, need_refresh=True, choice='中级血瓶'):
        if need_refresh:
            repo.refresh_repository()
        hp_zeros = repo.hp_below(0, id_only=True)
        return self.recover_list(hp_zeros, choice)

    # def recover_zero_loop(self, time_gap=2, log=False):
    #     step = 1
    #     while True:
    #         now = time.perf_counter()
    #         success_num, fail_num = self.recover_zero()
    #         time.sleep(time_gap - (time.perf_counter() - now))
    #         if log:
    #             result = "loop{} over: 处理了{}个植物".format(step, success_num + fail_num)
    #             if fail_num > 0:
    #                 result = result + "，其中{}个失败".format(fail_num)
    #             print(result)
    #         step += 1
