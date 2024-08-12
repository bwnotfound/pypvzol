import mitmproxy.http
from mitmproxy import ctx, http
import os

# 导入 urlparse
from urllib.parse import urlparse


class CacheProxy:
    def __init__(self, cache_dir) -> None:
        self.cache_dir = cache_dir

    def get_cache_file_path(self, url):
        # 解析 url
        parse_result = urlparse(url)
        # 获取 url hostname后面的路径
        url_path = (
            parse_result.path[1:]
            if parse_result.path.startswith("/")
            else parse_result.path
        )
        file_path = os.path.join(self.cache_dir, url_path)
        # ctx.log.info(f"Cache Dir: {self.cache_dir}")
        # ctx.log.info(f"URL Path: {url_path}")
        # ctx.log.info(f"Cache File Path: {file_path}")
        if not os.path.exists(file_path) or os.path.isdir(file_path):
            return None
        return file_path

    def request(self, flow: mitmproxy.http.HTTPFlow):
        # ctx.log.info(f"请求: {flow.request.url} Method: {flow.request.method}")
        if flow.request.method not in ["GET", "POST"]:
            return
        parse_result = urlparse(flow.request.url)
        # ctx.log.info(f"Scheme: {parse_result.scheme} Host: {parse_result.hostname}")
        if parse_result.scheme != "http":
            return
        if "pvzol.org" not in parse_result.hostname:
            return
        cache_file_path = self.get_cache_file_path(flow.request.url)
        if cache_file_path is None:
            return
        # 读取缓存文件，直接用文件内容作为响应内容
        try:
            with open(cache_file_path, "rb") as f:
                content = f.read()
        except Exception as e:
            ctx.log.error(f"读取缓存文件失败: {e}")
            return
        # ctx.log.info(f"使用缓存文件: {cache_file_path}")
        flow.response = http.Response.make(
            200, content, {"Content-Type": "application/octet-stream"}
        )


file_path = __file__
while not file_path.endswith("game_window"):
    file_path = os.path.dirname(file_path)
CACHE_DIR = os.path.join(os.path.dirname(file_path), "data/cache")
addons = [CacheProxy(CACHE_DIR)]

# if __name__ == "__main__":
#     print("in main !!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!")
#     import multiprocessing
#     from mitmproxy.tools.main import mitmdump
#     import argparse

#     parser = argparse.ArgumentParser()
#     parser.add_argument("--port", type=int, required=True)
#     args = parser.parse_args()
#     GAME_PORT = args.port
#     proxy_file = __file__

#     game_window_proxy_process = multiprocessing.Process(
#         target=mitmdump, args=(["-s", proxy_file, "-p", str(GAME_PORT)],)
#     )
#     game_window_proxy_process.start()
#     game_window_proxy_process.join()
