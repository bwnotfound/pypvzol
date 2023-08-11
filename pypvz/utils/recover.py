import time
from concurrent.futures import ThreadPoolExecutor, as_completed

import pyamf
from pyamf import remoting

from ..config import Config
from ..web import WebRequest
from ..repository import Repository
from ..ui.message import Logger


class RecoverMan:
    def __init__(self, cfg: Config, repo: Repository, logger: Logger = None):
        self.wr = WebRequest(cfg)
        self.cfg = cfg
        self.repo = repo
        self.logger = logger
        self.heal_dict = {
            "低级血瓶": 13,
            "中级血瓶": 14,
            "高级血瓶": 15,
        }

    def recover(self, target_id, choice='低级血瓶'):
        body = [float(target_id), float(self.heal_dict[choice])]
        req = remoting.Request(target='api.apiorganism.refreshHp', body=body)
        ev = remoting.Envelope(pyamf.AMF0)
        ev['/1'] = req
        bin_msg = remoting.encode(ev, strict=True)
        resp = self.wr.post(
            "http://s{}.youkia.pvz.youkia.com/pvz/amf/", data=bin_msg.getvalue()
        )
        resp_ev = remoting.decode(resp)
        response = resp_ev["/1"]
        if response.status == 0:
            return {"success": True, "result": int(response.body)} 
        elif response.status == 1:
            return {"success": False, "result": response.body.description}
        else:
            raise NotImplementedError

    def recover_zero(self, need_refresh=True):
        if need_refresh:
            self.repo.refresh_repository()
        hp_zeros = self.repo.hp_below(0, id_only=True)
        success_num = 0
        fail_num = 0
        success_list = [None] * len(hp_zeros)
        
        with ThreadPoolExecutor() as executor:
            futures = [executor.submit(self.recover, id) for id in hp_zeros]
        
        for i, future in enumerate(as_completed(futures)):
            result = future.result()
            if result["success"]:
                success_list[i] = result['result']
                success_num += 1
            else:
                fail_num += 1
        plant_list = [[self.repo.get_plant(id), success_list[i]] for i, id in enumerate(hp_zeros)]
        plant_list.sort(key=lambda x: (x[0].grade, -x[0].id), reverse=True)
        if self.logger is not None:
            message = "成功回复了{}个植物: ".format(success_num)
            for plant, _ in plant_list:
                message += f"{plant.name}({plant.grade}) "
            if fail_num > 0:
                message += f". 其中{fail_num}个失败"
            self.logger.log(message)
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
