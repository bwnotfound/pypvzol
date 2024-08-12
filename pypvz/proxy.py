import re
import requests
import logging
import time
from threading import Thread, Event
from socket import socket, AF_INET, SOCK_STREAM
from io import BytesIO
from http.server import BaseHTTPRequestHandler
import os


class Request(BaseHTTPRequestHandler):
    def __init__(self, data):
        self.rfile = BytesIO(data)
        self.raw_requestline = self.rfile.readline()
        self.error_code = self.error_message = None
        self.parse_request()
        self.path = self.path
        self.headers = self.headers
        self.command = self.command


def getAddr(d):
    a = re.search("Host: (.*)\r\n", d)
    if a == None:
        a = re.search("Host: (.*)", d)
    host = a.group(1)
    a = host.split(":")
    if len(a) == 1:
        return (a[0], 80)
    else:
        return (a[0], int(a[1]))


def SendAndRecv(Stream, BuffList, i, j):
    while True:
        BuffList[i] = Stream[i].recv(1024)
        # print(i, "接收到:", BuffList[i])
        if BuffList[i] == b'':
            break
        Stream[j].send(BuffList[i])


def interBoth(tmp, client):
    Stream = [tmp, client]
    BufferList = [b'', b'']
    Thread(target=SendAndRecv, args=(Stream, BufferList, 0, 1)).start()
    Thread(target=SendAndRecv, args=(Stream, BufferList, 1, 0)).start()
    while BufferList[0] == b'' and BufferList[1] == b'':
        time.sleep(0.001)
    while BufferList[0] != b'' or BufferList[1] != b'':
        time.sleep(0.001)
    client.close()
    tmp.close()


def receive_full_data(client, data=None, timeout=0.03, buff_size=10240):
    client.setblocking(False)
    now = time.perf_counter()
    if data is None:
        data = b""
    if isinstance(data, str):
        data = data.encode()
    cnt, max_retry = 0, 10
    while cnt < max_retry:
        try:
            buff = client.recv(buff_size)
        except Exception as e:
            buff = b""
        if not buff:
            if len(data) == 0:
                time.sleep(0.1)
                cnt += 1
                continue
            if time.perf_counter() - now > timeout:
                break
            continue
        now = time.perf_counter()
        data += buff
        if len(buff) < buff_size:
            if len(data) == 0:
                time.sleep(0.1)
            try:
                buff = client.recv(buff_size)
            except Exception as e:
                buff = b""
            if len(buff) == 0:
                break
            data += buff
    client.setblocking(True)
    return data


def route_request(data: str, client, self):
    self.handle_request(data, client)


def process(request_data, client, self):
    try:
        header_line = request_data.split("\r\n")[0]
        method = header_line.split(' ')[0]
        if method == "CONNECT":
            # response_start_line = "HTTP/1.1 200 Connection Established\r\n\r\n"
            # # response = "HTTP/1.1 407 Unauthorized\r\n"
            # client.send(response_start_line.encode())
            Addr = getAddr(request_data)
            server = socket(AF_INET, SOCK_STREAM)
            try:
                server.connect(Addr)
            except:
                server.close()
                return
            server.send(request_data.encode())
            # server.sendall(request_data.encode())
            interBoth(client, server)
            return
        if header_line.find("http://") != -1 and method in ['GET', 'POST', 'HEAD']:
            # 此处为GET、POST请求方式实现
            Thread(
                target=self.handle_request,
                args=(request_data.encode(), client),
            ).start()
            return
        elif header_line.find("http://") != -1:
            Thread(
                target=self.handle_other_request,
                args=(request_data.encode(), client),
            ).start()
        else:
            raise NotImplementedError
    except Exception as identifier:
        logging.error(identifier)


def local(serverIP, serverPort, stop_event: Event, self):
    tcpSocket = socket(AF_INET, SOCK_STREAM)
    tcpSocket.bind((serverIP, serverPort))
    tcpSocket.listen(5)
    while not stop_event.is_set():
        tmp, addr = tcpSocket.accept()
        try:
            data = receive_full_data(tmp, timeout=2)
            if len(data) == 0:
                tmp.close()
                continue
            data = data.decode()
        except Exception as e:
            try:
                tmp.close()
            except:
                pass
            continue
        Thread(
            target=process,
            args=(
                data,
                tmp,
                self,
            ),
        ).start()


class GameWindowProxyServer:
    def __init__(self, cache_dir, port, proxy=None):
        self.cache_dir = cache_dir
        self.port = port
        self.proxy = proxy
        self.stop_event = Event()
        self.thread = None

    def start(self):
        self.stop_event.clear()
        serverIP = '127.0.0.1'
        serverPort = self.port
        self.thread = Thread(target=local, args=(serverIP, serverPort, self.stop_event, self))
        self.thread.start()
        # local(serverIP, serverPort, self.stop_event, self)

    def send(self, response, client):
        response_line = f"HTTP/1.1 {response.status_code} {response.reason}\r\n"
        if "Content-Length" not in response.headers:
            response.headers["Content-Length"] = len(response.content)
        if "Content-Encoding" in response.headers:
            response.headers.pop("Content-Encoding")
        if "Transfer-Encoding" in response.headers:
            response.headers.pop("Transfer-Encoding")
        response_headers = ''
        for header, value in response.headers.items():
            response_headers += f"{header}: {value}\r\n"
        content = response.content
        response_data = (
            response_line.encode() + response_headers.encode() + b"\r\n" + content
        )
        client.sendall(response_data)
        client.close()

    def send_data(self, data, client, is_head=False):
        response_line = "HTTP/1.1 200 OK\r\n"
        response_headers = {
            "Content-Type": "application/octet-stream",
            "Content-Length": len(data),
        }
        if is_head:
            data = b""
        response_data = (
            response_line.encode()
            + "\r\n".join([f"{k}: {v}" for k, v in response_headers.items()]).encode()
            + b"\r\n\r\n"
            + data
        )
        client.sendall(response_data)
        client.close()

    def handle_request(self, data, client):
        # 从二进制data解析request
        request = Request(data)
        url, header = request.path, request.headers
        if request.command == "POST":
            try:
                post_data = data.split(b"\r\n\r\n")[1]
            except:
                post_data = b""
        cache_path = self._get_cache_file_path(url)
        if os.path.exists(cache_path):
            with open(cache_path, "rb") as f:
                data = f.read()
            self.send_data(data, client, is_head=request.command == "HEAD")
            return
        if request.command == "GET":
            response = requests.get(url, headers=header, proxies=self.proxy)
        elif request.command == "POST":
            response = requests.post(url, headers=header, proxies=self.proxy, data=post_data)
        else:
            raise NotImplementedError
        self.send(response, client)
    
    def handle_other_request(self, data, client):
        request = Request(data)
        url, header = request.path, request.headers
        response = requests.request(request.command, url, headers=header, proxies=self.proxy)
        self.send(response, client)
        
    def _get_cache_file_path(self, url):
        """Generate a path for the cache file based on the URL"""
        url_path = url.replace('http://', '').replace('https://', '').split("?")[0]
        url_path = "/".join((url_path.split("/"))[1:])  # Remove the protocol part
        return os.path.join(self.cache_dir, url_path)


if __name__ == "__main__":
    cache_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data/cache")
    GameWindowProxyServer(cache_dir, 20413).start()
