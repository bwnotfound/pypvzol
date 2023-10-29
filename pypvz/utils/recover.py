import time
import logging
from concurrent.futures import ThreadPoolExecutor, as_completed

from pyamf import remoting, AMF0, DecodeError

from .. import Config, WebRequest, Repository

# from ..config import Config
# from ..web import WebRequest
# from ..repository import Repository


class RecoverMan:
    def __init__(self, cfg: Config, repo: Repository):
        self.wr = WebRequest(cfg)
        self.cfg = cfg
        self.repo = repo
        self.heal_dict = {
            "低级血瓶": 13,
            "中级血瓶": 14,
            "高级血瓶": 15,
        }

    def recover(self, target_id, choice='中级血瓶'):
        body = [float(target_id), float(self.heal_dict[choice])]
        response = self.wr.amf_post(
            body, "api.apiorganism.refreshHp", "/pvz/amf/", "回复植物血量"
        )
        if response.status == 0:
            return {"success": True, "result": int(response.body)}
        elif response.status == 1:
            description = response.body.description
            if "该生物不存在" in description:
                return {"success": False, "result": "该生物不存在"}
            if "该植物血量已满" in description:
                return {"success": False, "result": "该植物血量已满"}
            return {"success": False, "result": response.body.description}
        else:
            raise NotImplementedError
        
    def recover_list(self, target_id_list, choice='中级血瓶'):
        success_num = 0
        fail_num = 0

        with ThreadPoolExecutor(max_workers=3) as executor:
            futures = [executor.submit(self.recover, id, choice) for id in target_id_list]

        for future in as_completed(futures):
            try:
                result = future.result()
                if result["success"]:
                    success_num += 1
                else:
                    logging.warning("回复植物血量失败: {}".format(result["result"]))
                    fail_num += 1
            except Exception as e:
                logging.warning("回复植物血量异常，异常类型：{}".format(type(e).__name__))
                fail_num += 1
        return success_num, fail_num

    def recover_zero(self, need_refresh=True, choice='中级血瓶'):
        if need_refresh:
            self.repo.refresh_repository()
        hp_zeros = self.repo.hp_below(0, id_only=True)
        success_num = 0
        fail_num = 0

        with ThreadPoolExecutor(max_workers=3) as executor:
            futures = [executor.submit(self.recover, id, choice) for id in hp_zeros]

        for future in as_completed(futures):
            result = future.result()
            if result["success"]:
                success_num += 1
            else:
                logging.warning("回复植物血量失败: {}".format(result["result"]))
                fail_num += 1
        return success_num, fail_num

    def recover_zero_loop(self, time_gap=2, log=False):
        step = 1
        while True:
            now = time.perf_counter()
            success_num, fail_num = self.recover_zero()
            time.sleep(time_gap - (time.perf_counter() - now))
            if log:
                result = "loop{} over: 处理了{}个植物".format(step, success_num + fail_num)
                if fail_num > 0:
                    result = result + "，其中{}个失败".format(fail_num)
                print(result)
            step += 1
