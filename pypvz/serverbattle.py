from . import Config, WebRequest


class ServerbattleMan:
    def __init__(self, cfg: Config):
        self.cfg = cfg
        self.wr = WebRequest(cfg)

    def challenge(self):
        body = []
        try:
            response = self.wr.amf_post(
                body, 'api.serverbattle.challenge', "/pvz/amf/", "跨服挑战"
            )
            if response.status != 0:
                return {
                    "success": False,
                    "result": f"跨服挑战失败。错误原因：{response.body.description}",
                }
            return {
                "success": True,
                "result": f"跨服挑战成功。挑战结果：{response.body['is_winning']}",
            }
        except Exception as e:
            return {"success": False, "result": f"跨服挑战失败。异常类型：{type(e).__name__}"}
