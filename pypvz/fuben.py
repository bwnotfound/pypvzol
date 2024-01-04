from time import sleep

from .web import WebRequest
from .config import Config


class FubenCave:
    def __init__(self, root):
        self.name = root['name']
        self.cave_id = int(root['cave_id'])
        self.rest_count = int(root['lcc'])  # 0~20，或者-1无限
        self.status = int(root['status'])  # 3: 能开启 4: 已开启未通关 5: 已通关。只要看3和5，4不管，自己判断
        self.open_tools = []
        for s in root['open_tools'].split(","):
            data = s.split("|")
            self.open_tools.append({"id": int(data[0]), "amount": int(data[1])})
        self.reward = (
            int(root['reward']) if root['reward'] != "" else None
        )  # 外显奖励的tool_id。None表示没有


class WorldFubenRequest:
    def __init__(self, cfg: Config):
        self.cfg = cfg
        self.wr = WebRequest(cfg)

    def get_caves(self, layer, logger, return_challenge_amount=False):
        body = [float(layer)]
        response = self.wr.amf_post_retry(
            body,
            "api.fuben.display",
            '/pvz/amf/',
            '副本洞口信息',
            logger=logger,
            except_retry=True,
        )
        caves = [FubenCave(root) for root in response.body['_caves']]
        if return_challenge_amount:
            return caves, int(response.body['_lcc'])
        else:
            return caves

    def challenge(self, cave_id, team, logger):
        body = [float(cave_id), [int(plant_id) for plant_id in team]]
        response = self.wr.amf_post_retry(
            body,
            "api.fuben.challenge",
            '/pvz/amf/',
            '挑战副本洞口',
            logger=logger,
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
