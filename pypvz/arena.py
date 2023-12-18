from . import Config, WebRequest


class ArenaOpponent:
    def __init__(self, root):
        self.name = root['nickname']
        self.rank = int(root['rank'])
        self.user_id = int(root['userid'])  # 不是platform_id


class Arena:
    def __init__(self, cfg: Config):
        self.cfg = cfg
        self.wr = WebRequest(cfg)

    def refresh_arena(self):
        response = self.wr.amf_post_retry(
            [], "api.arena.getArenaList", "/pvz/amf/", "获取竞技场列表", except_retry=True
        )
        self.opponent_list = [ArenaOpponent(root) for root in response.body['opponent']]
        self.challenge_num = int(response.body['owner']["num"])

    def challenge_first(self):
        response = self.wr.amf_post_retry(
            [float(self.opponent_list[0].user_id)],
            "api.arena.challenge",
            "/pvz/amf/",
            "挑战竞技场",
            allow_empty=True,
            except_retry=True
        )
        if response == None:
            return {
                "success": False,
                "result": "挑战竞技场，但服务器返回为空。可能是竞技场次数不够或挑战对手不存在导致的。",
            }

        if response.status == 1:
            return {
                "success": False,
                "result": "挑战竞技场出现异常。原因：{}".format(response.body.description),
            }
        return {
            "success": True,
            "result": "挑战竞技场成功。挑战{}，挑战结果：{}".format(
                self.opponent_list[0].name,
                "成功" if response.body["is_winning"] else "失败",
            ),
        }
    
    def batch_challenge(self, num):
        body = [f"/arena {num}"]
        response = self.wr.amf_post_retry(
            body,
            "api.gift.get",
            "/pvz/amf/",
            "批量挑战竞技场",
        )
        if response.body['msg'] == "使用成功":
            return {
                "success": True,
            }
        elif response.body['msg'] == "道具异常":
            return {
                "success": False,
                "error_type": 1,
                "result": "挑战竞技场出现异常。原因：{}".format(response.body['msg']),
            }
        elif "指令有误" in response.body['msg'] :
            return {
                "success": False,
                "error_type": 2,
                "result": "挑战竞技场出现异常。原因：{}".format(response.body['msg']),
            }
