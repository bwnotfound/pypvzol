from xml.etree.ElementTree import Element, fromstring
import logging
from time import sleep, time

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
        self.friends: list[Friend] = []
        for friend in friends:
            try:
                self.friends.append(Friend(friend))
            except:
                try:
                    logging.info(f"解析好友{friend.get('name')} 失败，已跳过")
                except:
                    logging.info(f"一个好友解析失败，已跳过")
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
        cnt, max_retry = 0, 15
        while cnt < max_retry:
            try:
                resp = self.wr.get_retry(
                    "/pvz/index.php/default/user/sig/0", "刷新用户信息"
                )
                root = fromstring(resp.decode("utf-8"))
                assert root.find("response").find("status").text == "success"
                break
            except Exception as e:
                cnt += 1
                msg = "刷新用户信息出现异常，异常类型：{}。选择等待3秒后重试。最多再等待{}次".format(
                    type(e).__name__, max_retry - cnt
                )
                logging.info(msg)
                sleep(3)
        self.friendMan.refresh(root)

        user = root.find("user")
        self.id = int(user.get("id"))
        self.name = user.get("name")
        self.money = int(user.get("money"))
        self.rmb_coupon = int(user.get("rmb_money"))
        self.face_url = user.get("face")
        if not self.face_url.startswith("http://"):
            self.face_url = f"http://{self.cfg.host}" + self.face_url
        self.cave_amount = int(user.find("cave").get("amount"))
        self.cave_amount_max = int(user.find("cave").get("max_amount"))
        self.territory_amount = int(user.find("territory").get("amount"))
        self.territory_amount_max = int(user.find("territory").get("max_amount"))
        self.honor = int(user.find("territory").get("honor"))
        grade = user.find("grade")
        exp_min = int(grade.get("exp_min"))
        self.exp_now = int(grade.get("exp")) - exp_min
        self.exp_max = int(grade.get("exp_max")) - exp_min
        self.today_exp = int(grade.get("today_exp"))
        self.today_exp_max = int(grade.get("today_exp_max"))
        self.grade = int(grade.get("id"))
        self.vip_expire_time = int(user.get("vip_etime"))
        self.vip_level = int(user.get("vip_grade"))

    def switch_user_vip_level(self, level: int, logger=None):
        # level: [0,4]
        body = [float(1), float(3), float(1), []]
        while True:
            response = self.wr.amf_post_retry(
                body,
                "api.garden.challenge",
                '/pvz/amf/',
                '切换VIP外显',
                except_retry=True,
            )
            assert response.status == 1, "切换VIP外显失败，返回内容：{}".format(
                response.body
            )
            resp_text = response.body.description
            if logger is not None:
                logger.log(resp_text)
            else:
                logging.info(resp_text)
            if "关闭" in resp_text:
                cur_level = 0
            else:
                cur_level = int(resp_text[-1])
            self.vip_level = cur_level
            if cur_level == level:
                return {
                    "success": True,
                    "result": resp_text,
                }

    def get_vip_rest_time(self):
        if self.vip_level == 0:
            self.switch_user_vip_level(1)
            self.refresh()
        rest_day = max(0, int((self.vip_expire_time - time()) / 86400))
        return rest_day

    # def refresh_garden(self):
    #     resp = self.wr.get(
    #         f"/pvz/index.php/garden/index/id/{self.id}/sig/0",
    #     )
    #     root = fromstring(resp.content.decode("utf-8"))

    #     garden = root.find("garden")
    #     self.garden_challenge_amount = int(garden.get("cn"))
    #     self.garden_challenge_max_amount = 5
