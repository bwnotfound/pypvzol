from time import sleep

from .web import WebRequest
from .config import Config


class FubenCave:
    def __init__(self, root):
        self.name = root['name']
        self.cave_id = int(root['cave_id'])
        self.rest_count = int(root['lcc'])  # 0~20，或者-1无限


class FubenRequest:
    def __init__(self, cfg: Config):
        self.cfg = cfg
        self.wr = WebRequest(cfg)

    def get_caves(self, layer, logger):
        body = [float(layer)]
        response = self.wr.amf_post_retry(body, "api.fuben.display", '/pvz/amf/', '副本洞口信息', logger=logger)
        caves = [FubenCave(root) for root in response.body['_caves']]
        return caves

    def challenge(self, cave_id, team, logger):
        body = [float(cave_id), [int(plant_id) for plant_id in team]]
        response = self.wr.amf_post_retry(
            body, "api.fuben.challenge", '/pvz/amf/', '挑战副本洞口', logger=logger
        )
        if response.status != 0:
            return {
                "success": False,
                "result": response.body.description,
            }
        return {
            "success": True,
            "result": response.body,
        }
