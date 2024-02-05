from xml.etree.ElementTree import fromstring

import pyamf
from pyamf import remoting

from .config import Config
from .library import Library
from .user import FriendMan
from .web import WebRequest


class GardenMan:
    def __init__(self, cfg: Config, lib: Library, friendMan: FriendMan):
        self.cfg = cfg
        self.lib = lib
        self.friendMan = friendMan
        self.wr = WebRequest(cfg)

    def challenge(self, id, plant_list):
        """
        Challenge all caves of a garden .

        Args:
            id (int): friend id.
            plant_list (list[int]): plant id list

        Returns:
            bool: if success

        Raises:
            RuntimeError: web request failed.
        """
        if not isinstance(plant_list, (list, tuple)):
            plant_list = [plant_list]
        resp = self.wr.get(
            f"/pvz/index.php/garden/index/id/{id}/sig/0",
        )
        root = fromstring(resp.decode("utf-8"))
        garden = root.find("garden")
        monsters = garden.find("monster")
        for monster in monsters:
            position = monster.find("position")
            x, y = int(position.get("lx")), int(position.get("ly"))
            req = remoting.Request(
                target='api.garden.challenge',
                body=[float(id), float(x), float(y), [int(i) for i in plant_list]],
            )
            ev = remoting.Envelope(pyamf.AMF0)
            ev['/1'] = req
            bin_msg = remoting.encode(ev, strict=True)
            resp = self.wr.post("/pvz/amf/", data=bin_msg.getvalue())
            # TODO: check result

    def challenge_all(self, target_level_min, plant_list):
        for i, friend in enumerate(self.friendMan.friends):
            if friend.grade >= target_level_min:
                self.challenge(friend.id, plant_list)
            elif i != 0:
                break
