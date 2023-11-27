import re
import logging
from typing import Literal

from . import Config, WebRequest, Library


class TaskItem:
    def __init__(self, root, choice: Literal[1, 2, 3, 4]):
        self.id = int(root['id'])
        self.title = root['title']
        self.discription = root['dis']
        self.choice = choice
        # self.max_count = int(root['maxCount'])
        # self.cur_count = int(root['curCount'])
        self.state = int(root['state'])
        rewards = {}
        for k, v in root['reward'].items():
            if k == "tools":
                continue
            if v == "" or v is None:
                rewards[k] = None
            else:
                rewards[k] = int(v)
        self.reward_money = rewards['money']
        self.reward_exp = rewards['exp']
        self.reward_honor = rewards['honor']
        self.reward_tools = None
        if "tools" in root['reward']:
            self.reward_tools = [
                {"id": int(tool["id"]), "amount": int(tool["num"])}
                for tool in root['reward']['tools']
            ]

    def brief_description(self):
        groups = re.findall(r"(.*)<font.*>(.*)</font>(.*)", self.discription)
        if len(groups) == 0:
            return self.discription
        result = "".join(groups[0])
        return result

    def brief_title(self):
        groups = re.findall(r"(.*)<font.*>(.*)</font>(.*)", self.title)
        if len(groups) == 0:
            return self.title
        result = "".join(groups[0])
        return result


class Task:
    def __init__(self, cfg: Config):
        self.cfg = cfg
        self.wr = WebRequest(cfg)

    def refresh_task(self):
        body = []
        response = self.wr.amf_post_retry(body, "api.duty.getAll", "/pvz/amf/", "刷新任务")
        body = response.body
        self.main_task = [TaskItem(r, 1) for r in body['mainTask']]
        self.side_task = [TaskItem(r, 2) for r in body['sideTask']]
        self.daily_task = [TaskItem(r, 3) for r in body['dailyTask']]
        self.active_task = [TaskItem(r, 4) for r in body['activeTask']]
        self.task_list = [
            self.main_task,
            self.side_task,
            self.daily_task,
            self.active_task,
        ]

    def claim_reward(self, task_item: TaskItem, lib: Library):
        body = [float(task_item.id), float(task_item.choice)]
        response = self.wr.amf_post_retry(body, "api.duty.reward", "/pvz/amf/", "领取任务奖励")
        if response.status != 0:
            msg = "领取任务奖励失败。错误原因:{}".format(response.body.description)
            logging.error(msg)
            raise NotImplementedError(msg)
        result = "{}:{}领取成功。获得：".format(
            task_item.brief_title(), task_item.brief_description()
        )
        if task_item.reward_money is not None:
            result += "金币{},".format(task_item.reward_money)
        if task_item.reward_exp is not None:
            result += "经验{},".format(task_item.reward_exp)
        if task_item.reward_honor is not None:
            result += "荣誉{},".format(task_item.reward_honor)
        if task_item.reward_tools is not None:
            reward_str_list = []
            for reward in task_item.reward_tools:
                tool = lib.get_tool_by_id(reward['id'])
                if tool is None:
                    logging.warning("未知的奖励物品id:{}".format(reward['id']))
                    continue
                reward_str_list.append("{}({})".format(tool.name, reward['amount']))
            result = result + ",".join(reward_str_list)
        return {
            "success": True,
            "result": result,
        }
