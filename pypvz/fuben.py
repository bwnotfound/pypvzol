import logging

from .web import WebRequest
from .config import Config
from .library import Library


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

    def reward_info(self, lib: Library):
        if self.reward is None:
            return ""
        tool = lib.get_tool_by_id(self.reward)
        return tool.name

    def format_info(self, lib: Library = None, show_reward=False):
        result = self.name
        if show_reward:
            assert lib is not None and isinstance(lib, Library)
            if self.reward is not None:
                result += " (掉落：{})".format(self.reward_info(lib))
        return result


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

    def switch_layer(self, target_layer, logger=None):
        '''target_layer: [1,2]'''
        layer_chinese_list = ["一", "二"]
        while True:
            body = [float(1), float(1), float(0), []]
            response = self.wr.amf_post_retry(
                body,
                "api.garden.challenge",
                "/pvz/amf/",
                "切换副本层数",
                logger=logger,
                except_retry=True,
            )
            if response.status != 1:
                raise RuntimeError("切换副本层数失败，异常信息：" + str(response.body))
            text = response.body.description
            current_layer = layer_chinese_list.index(text[-2]) + 1
            if logger is not None:
                logger.log(text)
            else:
                logging.info(text)
            if current_layer == target_layer:
                break
