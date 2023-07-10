import json
import pathlib
import urllib.parse
import mimetypes
import socket
from datetime import datetime
from threading import Thread
import logging
from http.server import HTTPServer, BaseHTTPRequestHandler

BASE_DIR = pathlib.Path()
JSON_PATH = BASE_DIR.joinpath('storage/data.json')

SOCKET_SERVER_IP = '127.0.0.1'
SOCKET_SERVER_PORT = 5000
SOCKET_BUFFER_SIZE = 1024

HTTP_SERVER_IP = '0.0.0.0'
HTTP_SERVER_PORT = 3000


class HTTPHandler(BaseHTTPRequestHandler):
    def do_POST(self):
        body = self.rfile.read(int(self.headers['Content-Length']))
        send_data_to_socket(body)
        self.send_response(302)
        self.send_header('Location', 'index.html')
        self.end_headers()

    def do_GET(self):
        route = urllib.parse.urlparse(self.path)
        match route.path:
            case '/':
                self.send_html('index.html')
            case '/message':
                self.send_html('message.html')
            case _:
                file = BASE_DIR / route.path[1:]
                if file.exists():
                    self.send_static(file)
                else:
                    self.send_html('error.html', 404)

    def send_html(self, filename, status_code=200):
        self.send_response(status_code)
        self.send_header('Content-Type', 'text/html')
        self.end_headers()
        with open(filename, 'rb') as f:
            self.wfile.write(f.read())

    def send_static(self, filename):
        self.send_response(200)
        mime_type, *rest = mimetypes.guess_type(filename)
        if mime_type:
            self.send_header('Content-Type', mime_type)
        else:
            self.send_header('Content-Type', 'text/plain')
        self.end_headers()
        with open(filename, 'rb') as f:
            self.wfile.write(f.read())


def run_http_server(server=HTTPServer, handler=HTTPHandler):
    address = (HTTP_SERVER_IP, HTTP_SERVER_PORT)
    http_server = server(address, handler)
    logging.info('HTTP server started.')
    try:
        http_server.serve_forever()
    except KeyboardInterrupt:
        logging.info('HTTP server stopped.')
    finally:
        http_server.server_close()


def send_data_to_socket(data):
    client_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    client_socket.sendto(data, (SOCKET_SERVER_IP, SOCKET_SERVER_PORT))
    client_socket.close()


def save_data(data):
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")
    body = urllib.parse.unquote_plus(data.decode())
    try:
        payload = {key: value for key, value in [el.split('=') for el in body.split('&')]}
        if pathlib.Path.exists(pathlib.Path('storage/data.json')):
            with open('storage/data.json', 'r') as fd:
                existing_data = json.load(fd)
        else:
            existing_data = {}
        print(existing_data)
        entry = {timestamp: payload}
        existing_data.update(entry)
        print(existing_data)
        with open('storage/data.json', 'w', encoding='utf-8') as fd:
            json.dump(existing_data, fd, ensure_ascii=False)
    except ValueError as err:
        logging.error(f"Failed parse data {err}")
    except OSError as err:
        logging.error(f"Failed to save data {err}")


def run_socket_server(ip, port):
    server_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    server = ip, port
    server_socket.bind(server)
    logging.info('Socket started.')
    try:
        while True:
            data, address = server_socket.recvfrom(SOCKET_BUFFER_SIZE)
            save_data(data)
    except KeyboardInterrupt:
        logging.info('Socket server stopped.')
    finally:
        server_socket.close()


if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO, format="%(threadName)s: %(message)s")

    http_server_thread = Thread(target=run_http_server)
    http_server_thread.start()

    socket_server_thread = Thread(target=run_socket_server(SOCKET_SERVER_IP, SOCKET_SERVER_PORT))
    socket_server_thread.start()

    http_server_thread.join()
    socket_server_thread.join()
