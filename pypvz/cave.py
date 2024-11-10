from xml.etree.ElementTree import Element, fromstring
from typing import Union
import logging
import time

from .web import WebRequest
from .library import Library
from .config import Config
from .ui.message import Logger


class Cave:
    '''
    id: int  # 洞口的唯一标识，非所有人的
    cave_id: int  # 服务器中每个人洞口的唯一标识
    '''

    def __init__(
        self,
        root: Union[Element, dict],
        type,
        layer,
        number,
    ):
        self.type = type
        self.layer = layer
        self.number = number
        if type <= 3:
            assert isinstance(root, Element)
            self.id = int(root.get("id"))
            self.cave_id = root.find("oi").text
            self.cave_id = int(self.cave_id) if self.cave_id is not None else None
            self.name = root.find("na").text
            orgs = root.find("orgs")
            # 判断orgs是否含有子节点
            if orgs is not None and len(orgs) > 0:
                self.grade = int(root.find("orgs").find("org").find("gd").text)
            else:
                self.grade = None
            self.rest_time = int(root.find("lt").text)
            self.open_grade = int(root.find("og").text)
        elif type == 4:
            assert isinstance(root, dict)
            self.id = int(root["id"])
            self.name = root['name']
            self.grade = int(root['monsters']['star_1'][0]['gd'])
        else:
            raise NotImplementedError

    def quick_cave_id(self, user_id=None, garden_layer=None):
        if self.type <= 3:
            assert user_id is not None and garden_layer is not None
            if self.type == 1:
                garden_layer_offset = 9 * 3
                layer_offset = 9
            else:
                garden_layer_offset = 12 * 4
                layer_offset = 12
            return (
                user_id * 1000
                + [1, 6, 3][self.type - 1] * 100
                + (garden_layer - 1) * garden_layer_offset
                + (self.layer - 1) * layer_offset
                + self.number
            )
        elif self.type == 4:
            return self.id
        else:
            raise NotImplementedError

    def format_name(self, difficulty=None):
        if self.type <= 3:
            type_name_list = ["暗洞", "公洞", "个洞"]
            difficulty_name_list = ["简单", "普通", "困难"]
            name = "{}-{}-{}{}: {}".format(
                type_name_list[self.type - 1],
                self.layer,
                self.number,
                (
                    "({})".format(difficulty_name_list[difficulty - 1])
                    if (difficulty is not None)
                    else ""
                ),
                self.name,
            )
        elif self.type == 4:
            name = "{}{}".format(
                self.name,
                "-{}星".format(difficulty) if (difficulty is not None) else "",
            )
        else:
            raise NotImplementedError
        return name

    @property
    def is_ready(self):
        # rest_time包括了保护时间，所以rest_time小于等于0时，表示已经可以挑战
        if self.type <= 3:
            return self.grade is not None and self.rest_time <= 0
        elif self.type == 4:
            return True
        else:
            raise NotImplementedError


class CaveMan:
    def __init__(self, cfg: Config, lib: Library):
        self.cfg = cfg
        self.lib = lib
        self.wr = WebRequest(cfg)

    def get_caves(self, user_id, type, layer: int = None, logger: Logger = None):
        """
        Args:
            id (int): user's id. not platform id
            type (int): 1:暗洞 2:公洞 3:个洞 4:宝石
            layer (int): 洞口层数: 1~3/4

        Returns:
            list[Cave]

        Raises:
            ValueError: type must be 1, 2, 3, 4
            RuntimeError: web request failed.
        """
        if type <= 3:
            type_name = "public" if type == 2 else "private"
            if type == 1:
                type_name = type_name + "_" + str(layer * 2)
            elif type == 2:
                type_name = type_name + (f"_{layer}" if layer > 1 else "")
            elif type == 3:
                type_name = type_name + (f"_{layer * 2 - 1}" if layer > 1 else "")
            else:
                raise ValueError("type must be 1, 2 or 3")
            url = f"/pvz/index.php/cave/index/id/{user_id}/type/{type_name}/sig/0"
            try:
                resp = self.wr.get_retry(
                    url, "获取矿洞信息", logger=logger, except_retry=True
                )
                resp_text = resp.decode("utf-8")
            except Exception as e:
                if logger is not None:
                    logger.log("获取矿洞信息失败")
                raise RuntimeError("获取矿洞信息失败")
            root = fromstring(resp_text)
            caves = [
                Cave(cave, type, layer, i + 1)
                for i, cave in enumerate(root.find("hunting").findall("h"))
            ]
        elif type == 4:
            body = [float(user_id)]
            response = self.wr.amf_post_retry(
                body,
                'api.stone.getCaveInfo',
                '/pvz/amf/',
                '获取宝石副本信息',
                except_retry=True,
            )
            caves = [
                Cave(cave, type, user_id, i + 1)
                for i, cave in enumerate(response.body['caves'])
            ]

        return caves

    def challenge(self, cave_id, plant_list: list[int], difficulty, type):
        """
        Challenge a cave.

        Args:
            cave_id (int): cave id which is unique in server scope.
            plant_list (list[int]): plant id list
            difficulty (int): 1: easy 2: normal 3: hard

        Returns:
            bool: if success

        Raises:
            ValueError: type must be 1, 2, 3, 4
            RuntimeError: web request failed.
        """
        if type <= 3:
            target_amf = "api.cave.challenge"
        elif type == 4:
            target_amf = 'api.stone.challenge'
        else:
            raise NotImplementedError
        body = [
            float(cave_id),
            [int(i) for i in plant_list],
            float(difficulty),
        ]
        response = self.wr.amf_post_retry(
            body, target_amf, '/pvz/amf/', '洞口挑战', allow_empty=True
        )
        if response is None:
            return {
                "success": False,
                "result": "可能是植物没血了",
            }
        if response.status == 0:
            return {"success": True, "result": response.body}
        else:
            return {"success": False, "result": response.body.description}

    def get_lottery(self, challenge_resp_body):
        lottery_key = challenge_resp_body['awards_key']
        body = [lottery_key]
        response = self.wr.amf_post_retry(
            body, "api.reward.lottery", '/pvz/amf/', '获取战利品信息'
        )
        if response.status == 0:
            result = [
                {"id": int(item["id"]), "amount": int(item["amount"])}
                for item in response.body['tools']
            ]
            return {"success": True, "result": result}
        else:
            return {
                "success": False,
                "result": "获取战力品信息失败。原因：{}".format(
                    response.body.description
                ),
            }

    def get_garden_cave(self, id):
        url = f"/pvz/index.php/garden/index/id/{id}/sig/0"
        resp = self.wr.get_retry(url, "获取花园信息")
        root = fromstring(resp.decode("utf-8"))
        garden_cave_item = root.find("garden").find("monster").find("mon")
        if garden_cave_item is None:
            return None
        return GardenCave(garden_cave_item, self.lib)

    def use_sand(self, cave_id):
        body = [float(cave_id)]
        response = self.wr.amf_post_retry(
            body, "api.cave.useTimesands", '/pvz/amf/', '使用时之沙', except_retry=True
        )
        if response.status == 0:
            return {
                "success": True,
            }
        else:
            return {
                "success": False,
                "result": response.body.description,
            }

    def switch_garden_layer(self, target_layer, logger):
        '''
        target_layer in [1,2,3,4,5,6]

        洞口已切换到第{}层
        '''
        target_char = "一二三四五六七八九"[target_layer - 1]
        body = [float(1), float(0), float(0), []]
        while True:
            response = self.wr.amf_post_retry(
                body,
                "api.garden.challenge",
                '/pvz/amf/',
                '切换花园层',
                except_retry=True,
            )
            resp_text = response.body.description
            if "洞口已切换" not in resp_text:
                return {
                    "success": False,
                    "result": resp_text,
                }
            if target_char in resp_text:
                return {
                    "success": True,
                    "result": resp_text,
                }
            logger.log(resp_text)


class GardenCave:
    def __init__(self, root, lib: Library):
        self.id = int(root['id'])
        self.monster_id = int(root['monid'])
        self.plant_id = int(root['pid'])
        self.name = root['name']
        self.owner_id = int(root['owid'])
        self.reward = [
            lib.get_tool_by_id(int(tool_id)) for tool_id in root['reward'].split(",")
        ]
        # monster = root.find("read").find("org")
