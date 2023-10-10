from xml.etree.ElementTree import Element, fromstring
from typing import Union
import logging

from pyamf import remoting, AMF0, DecodeError

from .web import WebRequest
from .library import Library
from .config import Config


class Cave:
    '''
    id: int  # 洞口的唯一标识，非所有人的
    cave_id: int  # 服务器中每个人洞口的唯一标识
    '''

    def __init__(
        self,
        root: Union[Element, dict],
        user_id=None,
        type=None,
        layer=None,
        number=None,
        **kwargs,
    ):
        self.type = type
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
            self.user_id = user_id
            self.rest_time = int(root.find("lt").text)
            self.layer = layer
            self.number = number
            self.open_grade = int(root.find("og").text)
        elif type == 4:
            assert isinstance(root, dict), layer is not None
            self.id = int(root["id"])
            self.name = root['name']
            self.layer = layer
            self.chapter_id = int(kwargs['chapter_id'])
            self.grade = int(root['monsters']['star_1'][0]['gd'])
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
                "({})".format(difficulty_name_list[difficulty - 1])
                if (difficulty is not None)
                else "",
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
        # rest_time包括了保护时间，所以rest_time小于0时，表示已经可以挑战
        if self.type <= 3:
            return self.grade is not None and self.rest_time < 0
        elif self.type == 4:
            return True
        else:
            raise NotImplementedError


class CaveMan:
    def __init__(self, cfg: Config, lib: Library):
        self.cfg = cfg
        self.lib = lib
        self.wr = WebRequest(cfg)

    def get_caves(self, id, type, layer: int = None, retry=True):
        """
        Args:
            id (int): user's id. not platform id
            type (int): 1:暗洞 2:公洞 3:个洞
            layer (int): 洞口层数: 1~3

        Returns:
            list[Cave]

        Raises:
            ValueError: type must be 1, 2, 3, 4
            RuntimeError: web request failed.
        """
        if type <= 3:
            assert type in (1, 2, 3) and layer in (1, 2, 3)
            type_name = "public" if type == 2 else "private"
            if type == 1:
                type_name = type_name + "_" + str(layer * 2)
            elif type == 2:
                type_name = type_name + (f"_{layer}" if layer > 1 else "")
            elif type == 3:
                type_name = type_name + (f"_{layer * 2 - 1}" if layer > 1 else "")
            else:
                raise ValueError("type must be 1, 2 or 3")
            url = f"http://s{self.cfg.region}.youkia.pvz.youkia.com/pvz/index.php/cave/index/id/{id}/type/{type_name}/sig/0"
            resp = self.wr.get(url, need_region=False)
            root = fromstring(resp.decode("utf-8"))
            caves = [
                Cave(cave, id, type, layer, i + 1)
                for i, cave in enumerate(root.find("hunting").findall("h"))
            ]
            return caves
        elif type == 4:
            assert layer is None
            body = [float(id)]
            req = remoting.Request(target='api.stone.getCaveInfo', body=body)
            ev = remoting.Envelope(AMF0)
            ev['/1'] = req
            bin_msg = remoting.encode(ev, strict=True)
            while True:
                resp = self.wr.post(
                    "http://s{}.youkia.pvz.youkia.com/pvz/amf/", data=bin_msg.getvalue()
                )
                try:
                    resp_ev = remoting.decode(resp)
                    break
                except DecodeError:
                    if not retry:
                        break
                logging.info("重新尝试获取矿洞信息")
            response = resp_ev["/1"]
            body = response.body
            if response.status == 0:
                return [
                    Cave(cave, type=4, layer=i + 1, chapter_id=id)
                    for i, cave in enumerate(body['caves'])
                ]
            elif response.status == 1:
                raise NotImplementedError
            else:
                raise NotImplementedError

    def challenge(self, cave_id, plant_list: list[int], difficulty, type, retry=True):
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

        req = remoting.Request(
            target=target_amf,
            body=[
                float(cave_id),
                [int(i) for i in plant_list],
                float(difficulty),
            ],
        )
        ev = remoting.Envelope(AMF0)
        ev['/1'] = req
        bin_msg = remoting.encode(ev, strict=True)
        while True:
            resp = self.wr.post(
                "http://s{}.youkia.pvz.youkia.com/pvz/amf/", data=bin_msg.getvalue()
            )
            try:
                resp_ev = remoting.decode(resp)
                break
            except DecodeError:
                if not retry:
                    break
            logging.info("重新尝试请求洞口挑战")
        response = resp_ev["/1"]
        if response.status == 0:
            # onResult
            return {"success": True, "result": response.body}
        elif response.status == 1:
            # onStatus
            return {"success": False, "result": response.body.description}
        else:
            raise NotImplementedError
        
    def get_garden_cave(self, id):
        url = f"http://s{self.cfg.region}.youkia.pvz.youkia.com/pvz/index.php/garden/index/id/{id}/sig/0"
        resp = self.wr.get(url, need_region=False)
        root = fromstring(resp.decode("utf-8"))
        garden_cave_item = root.find("garden").find("monster").find("mon")
        if garden_cave_item is None:
            return None
        return GardenCave(garden_cave_item, self.lib)


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
