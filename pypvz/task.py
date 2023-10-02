import re
from typing import Literal

from pyamf import remoting, AMF0

from . import Config, WebRequest


class TaskItem:
    def __init__(self, root, choice: Literal[1, 2, 3, 4]):
        self.id = int(root['id'])
        self.title = root['title']
        self.discription = root['dis']
        self.choice = choice
        # self.max_count = int(root['maxCount'])
        # self.cur_count = int(root['curCount'])
        self.state = int(root['state'])
        self.reward = {
            "money": root['reward']['money'],
            "exp": root['reward']['exp'],
            "honor": root['reward']['honor'],
        }

    def brief_description(self):
        groups = re.findall(r"(.*)<font.*>(.*)</font>(.*)", self.discription)
        result = "".join(groups[0])
        return result


class Task:
    def __init__(self, cfg: Config):
        self.cfg = cfg
        self.wr = WebRequest(cfg)

    def refresh_task(self):
        body = []
        req = remoting.Request(target='api.duty.getAll', body=body)
        ev = remoting.Envelope(AMF0)
        ev['/1'] = req
        bin_msg = remoting.encode(ev, strict=True)
        resp = self.wr.post(
            "http://s{}.youkia.pvz.youkia.com/pvz/amf/", data=bin_msg.getvalue()
        )
        resp_ev = remoting.decode(resp)
        response = resp_ev["/1"]
        if response.status == 0:
            pass
        elif response.status == 1:
            raise NotImplementedError
        else:
            raise NotImplementedError
        body = response.body
        self.main_task = [TaskItem(r, 1) for r in body['mainTask']]
        self.side_task = [TaskItem(r, 2) for r in body['sideTask']]
        self.daily_task = [TaskItem(r, 3) for r in body['dailyTask']]
        self.active_task = [TaskItem(r, 4) for r in body['activeTask']]

    def claim_reward(self, task_item: TaskItem):
        body = [float(task_item.id), float(task_item.choice)]
        req = remoting.Request(target='api.duty.reward', body=body)
        ev = remoting.Envelope(AMF0)
        ev['/1'] = req
        bin_msg = remoting.encode(ev, strict=True)
        resp = self.wr.post(
            "http://s{}.youkia.pvz.youkia.com/pvz/amf/", data=bin_msg.getvalue()
        )
        resp_ev = remoting.decode(resp)
        response = resp_ev["/1"]
        if response.status == 0:
            pass
        elif response.status == 1:
            raise NotImplementedError
        else:
            raise NotImplementedError
        return {
            "success": True,
            "result": "任务[{}]领取成功，获得{}点荣誉值".format(
                task_item.brief_description(), task_item.reward['honor']
            ),
        }
