from . import Config, WebRequest


class Serverbattle:
    def __init__(self, cfg: Config):
        self.cfg = cfg
        self.wr = WebRequest(cfg)

    def challenge(self):
        body = []
        response = self.wr.amf_post_retry(
            body,
            'api.serverbattle.challenge',
            "/pvz/amf/",
            "跨服挑战",
            allow_empty=True,
        )
        if response is None:
            return None
        if response.status != 0:
            return {
                "success": False,
                "result": f"跨服挑战失败。错误原因：{response.body.description}",
            }
        return {
            "success": True,
            "result": f"跨服挑战成功。挑战结果：{response.body['is_winning']}",
        }

    def get_info(self):
        body = []
        response = self.wr.amf_post_retry(
            body,
            'api.serverbattle.qualifying',
            "/pvz/amf/",
            "获取跨服信息",
            except_retry=True,
        )
        return response
