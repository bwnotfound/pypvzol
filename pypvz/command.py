from .web import WebRequest


class Command:
    def __init__(self, cfg):
        self.cfg = cfg
        self.wr = WebRequest(cfg)

    def send(self, command: str, msg=None):
        if msg is None:
            msg = command
        body = [command]
        response = self.wr.amf_post_retry(
            body,
            "api.gift.get",
            "/pvz/amf/",
            msg,
        )
        if response.body['msg'] == "使用成功":
            return {
                "success": True,
            }
        elif response.body['msg'] == "道具异常":
            return {
                "success": False,
                "error_type": 1,
                "result": "{}出现异常。原因：{}".format(msg, response.body['msg']),
            }
        elif "指令有误" in response.body['msg']:
            return {
                "success": False,
                "error_type": 2,
                "result": "{}出现异常。原因：{}".format(msg, response.body['msg']),
            }
        elif "稳定" in response.body['msg']:
            return {
                "success": False,
                "error_type": 3,
                "result": "{}出现异常。原因：{}".format(msg, response.body['msg']),
            }
