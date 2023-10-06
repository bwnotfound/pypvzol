from xml.etree.ElementTree import Element, fromstring
import logging


from .web import WebRequest
from .config import Config


class Friend:
    def __init__(self, root: Element):
        self.id = int(root.get("id"))
        self.name = root.get("name")
        self.grade = int(root.get("grade"))
        self.platform_user_id = root.get("platform_user_id")
        self.face_url = root.get("face")

    @staticmethod
    def build(id, name, grade, platform_user_id, face_url):
        friend = Friend(
            Element(
                "friend",
                {
                    "id": id,
                    "name": name,
                    "grade": grade,
                    "platform_user_id": platform_user_id,
                    "face": face_url,
                },
            )
        )
        return friend


class FriendMan:
    def __init__(self, cfg: Config):
        self.cfg = cfg
        self.wr = WebRequest(cfg)

    def refresh(self, root: Element):
        user = root.find("user")
        friends = user.find("friends")
        self.friends = [Friend(friend) for friend in friends]
        self.friends.sort(key=lambda x: (x.grade, x.name), reverse=True)
        self.friends = [
            Friend.build(
                user.get("id"),
                user.get("name"),
                user.find("grade").get("id"),
                user.get("user_id"),
                user.get("face"),
            )
        ] + self.friends
        self.id2friend = {friend.id: friend for friend in self.friends}


class User:
    def __init__(self, cfg: Config):
        self.cfg = cfg
        self.wr = WebRequest(cfg)
        self.friendMan = FriendMan(cfg)
        self.refresh()

    def refresh(self):
        resp = self.wr.get(
            "http://s{}.youkia.pvz.youkia.com/pvz/index.php/default/user/sig/0"
        )
        root = fromstring(resp.decode("utf-8"))
        # try:
        #     root = fromstring(resp.decode("utf-8"))
        # except Exception as e:
        #     logging.error(
        #         "-----Refresh user failed: \n{}. \n-----Exception Stack: \n{}".format(
        #             resp.decode("utf-8"), str(e)
        #         )
        #     )
        #     raise e
        self.friendMan.refresh(root)

        user = root.find("user")
        self.user_id = int(user.get("user_id"))
        self.id = int(user.get("id"))
        self.name = user.get("name")
        self.money = int(user.get("money"))
        self.rmb_coupon = int(user.get("rmb_money"))
        self.face_url = user.get("face")
        self.cave_amount = int(user.find("cave").get("amount"))
        self.cave_amount_max = int(user.find("cave").get("max_amount"))
        self.territory_amount = int(user.find("territory").get("amount"))
        self.territory_amount_max = int(user.find("territory").get("max_amount"))
        grade = user.find("grade")
        exp_min = int(grade.get("exp_min"))
        self.exp_now = int(grade.get("exp")) - exp_min
        self.exp_max = int(grade.get("exp_max")) - exp_min
        self.today_exp = int(grade.get("today_exp"))
        self.today_exp_max = int(grade.get("today_exp_max"))
        self.grade = int(grade.get("id"))

    # def refresh_garden(self):
    #     resp = self.wr.get(
    #         f"http://s{self.cfg.region}.youkia.pvz.youkia.com/pvz/index.php/garden/index/id/{self.id}/sig/0",
    #         need_region=False,
    #     )
    #     root = fromstring(resp.content.decode("utf-8"))

    #     garden = root.find("garden")
    #     self.garden_challenge_amount = int(garden.get("cn"))
    #     self.garden_challenge_max_amount = 5
