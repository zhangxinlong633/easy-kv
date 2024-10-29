import hashlib  # 导入 hashlib 用于哈希函数
import socket  # 导入 socket 用于网络通信
import threading  # 导入 threading 用于并发执行
import json  # 导入 json 处理 JSON 数据
import time  # 导入 time 用于睡眠和计时功能
import logging  # 导入 logging 用于日志记录
import os  # 导入 os 进行操作系统相关功能
import plyvel  # 导入 plyvel 用于 LevelDB 操作
from flask import Flask, request, jsonify  # 导入 Flask 用于 HTTP 服务器
import sys  # 导入 sys 处理命令行参数

m = 16  # Chord 环的大小，决定哈希值的范围

def sha256_hash(key):
    # 使用 SHA-256 对 key 进行哈希并将其适配到 Chord 环的大小
    return int(hashlib.sha256(key.encode()).hexdigest(), 16) % (2**m)

# 用于选择合适的结点，进行存储
class FingerTable:
    # 管理 Chord 网络中节点列表的类
    def __init__(self):
        self.nodes = []  # 初始化一个空的节点列表

    def add_node(self, node):
        # 添加新节点并按 node_id 排序
        self.nodes.append(node)
        self.nodes.sort(key=lambda n: n.node_id)

    def get_successor(self, key):
        # 找到给定 key 的后继节点
        for node in self.nodes:
            if node.node_id >= key:
                return node
        return self.nodes[0] if self.nodes else None

    def propagate(self, sender):
        # 将节点列表更新传播给其他节点
        for node in self.nodes:
            if node.node_id != sender.node_id:
                sender.send_request(node.ip, node.port, {
                    "operation": "update_nodes",
                    "nodes": [(n.node_id, n.ip, n.port) for n in self.nodes]
                })

# 用于存储k-v数据的数据库
class LocalStore:
    # 使用 LevelDB 处理键值存储的类
    def __init__(self, db_directory, port):
        self.db_path = os.path.join(db_directory, f"leveldb_{port}")
        if not os.path.exists(db_directory):
            os.makedirs(db_directory)
        self.db = plyvel.DB(self.db_path, create_if_missing=True)

    def put(self, key, value):
        # 在数据库中存储键值对
        self.db.put(key.encode('utf-8'), value.encode('utf-8'))

    def get(self, key):
        # 获取给定 key 的值
        value = self.db.get(key.encode('utf-8'))
        return value.decode('utf-8') if value else None

    def delete(self, key):
        # 从数据库中删除键值对
        self.db.delete(key.encode('utf-8'))

    def close(self):
        # 关闭数据库连接
        self.db.close()

# Chord DHT的控制逻辑
class ChordNode:
    # 表示 Chord 节点的类
    def __init__(self, ip, port, registry, listen=False, db_directory='./leveldb'):
        # 使用 IP、端口和注册表初始化节点
        self.node_id = sha256_hash(f"node_{ip}:{port}")
        self.ip = ip
        self.port = port
        self.registry = registry
        self.logger = logging.getLogger(f"ChordNode {self.node_id}")
        logging.basicConfig(level=logging.INFO)

        if listen:
            # 如果启用监听，设置键值存储和服务器线程
            self.store = LocalStore(db_directory, port)
            self.server_thread = threading.Thread(target=self.start_server)
            self.server_thread.start()
            time.sleep(1)

    def start_server(self):
        # 启动服务器以监听传入连接
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as server_socket:
            server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            server_socket.bind((self.ip, self.port))
            server_socket.listen()
            self.logger.info(f"Listening on {self.ip}:{self.port}")

            while True:
                client_socket, _ = server_socket.accept()
                threading.Thread(target=self.handle_client, args=(client_socket,)).start()

    def handle_client(self, client_socket):
        # 处理传入的客户端请求
        try:
            data = client_socket.recv(1024)
            if not data:
                return
            request = json.loads(data.decode('utf-8'))
            operation = request.get("operation")

            if operation == "store_key":
                # 存储键值对操作
                key = request.get("key")
                value = request.get("value")
                self.store_key_value(key, value)
                client_socket.sendall(json.dumps({"status": "stored", "key": key}).encode('utf-8'))

            elif operation == "find_key":
                # 查找键操作
                key = request.get("key")
                value = self.find_key_value(key)
                response = {
                    "status": "success",
                    "key": key,
                    "value": value
                } if value else {"status": "error", "message": "Key not found"}
                client_socket.sendall(json.dumps(response).encode('utf-8'))

            elif operation == "delete_key":
                # 删除键操作
                key = request.get("key")
                self.delete_key_value(key)
                client_socket.sendall(json.dumps({"status": "deleted", "key": key}).encode('utf-8'))

            elif operation == "register_node":
                # 注册新节点到网络
                node_info = request.get("node")
                self.register_node(node_info)
                client_socket.sendall(json.dumps({"status": "registered"}).encode('utf-8'))

            elif operation == "update_nodes":
                # 更新节点列表
                nodes_info = request.get("nodes")
                self.update_nodes(nodes_info)

            else:
                # 未知操作
                client_socket.sendall(json.dumps({"status": "error", "message": "unknown operation"}).encode('utf-8'))

        except Exception as e:
            self.logger.error(f"Error handling client: {e}")
            client_socket.sendall(json.dumps({"status": "error", "message": "exception occurred"}).encode('utf-8'))
        finally:
            client_socket.close()

    def find_successor(self, key):
        # 找到给定 key 的后继节点
        return self.registry.get_successor(key)

    def join(self, seed_node):
        # 使用种子节点加入 Chord 网络
        seed_ip, seed_port = seed_node
        seed_port = int(seed_port)

        response = self.send_request(seed_ip, seed_port, {
            "operation": "register_node",
            "node": {"node_id": self.node_id, "ip": self.ip, "port": self.port}
        })

        if response.get("status") == "registered":
            self.logger.info(f"Joined Chord network with seed node: {seed_node}")
        else:
            self.logger.error("Failed to join the Chord network.")

    def register_node(self, node_info):
        # 注册新节点并更新网络
        new_node = ChordNode(node_info['ip'], node_info['port'], self.registry, listen=False)
        self.registry.add_node(new_node)
        self.registry.propagate(self) 
        print("*** Find new node: " + str(node_info['ip']) + ":" + str(node_info['port']) + "...")

    def update_nodes(self, nodes_info):
        # 更新注册表中的节点列表
        self.registry.nodes = [ChordNode(ip, port, self.registry, listen=False) for _, ip, port in nodes_info]

    def store_key_value(self, key, value):
        # 存储键值对，或转发给正确的节点
        key_hash = sha256_hash(key)
        successor = self.find_successor(key_hash)
        if successor.node_id != self.node_id:
            response = successor.send_request(successor.ip, successor.port, {
                "operation": "store_key",
                "key": key,
                "value": value
            })
            return
        self.logger.info(f"Storing key '{key}' with value '{value}' at node {self.node_id}")
        self.store.put(key, value)

    def find_key_value(self, key):
        # 查找键的值，或将请求转发给正确的节点
        key_hash = sha256_hash(key)
        successor = self.find_successor(key_hash)
        if successor.node_id == self.node_id:
            self.logger.info(f"Finding key '{key}' at node {self.node_id}")
            return self.store.get(key)
        else:
            response = successor.send_request(successor.ip, successor.port, {
                "operation": "find_key",
                "key": key
            })
            if response.get("status") == "success":
                return response.get("value")
            return None

    def delete_key_value(self, key):
        # 删除键值对，或转发请求
        key_hash = sha256_hash(key)
        successor = self.find_successor(key_hash)
        if successor.node_id == self.node_id:
            self.logger.info(f"Deleting key '{key}' at node {self.node_id}")
            self.store.delete(key)
        else:
            response = successor.send_request(successor.ip, successor.port, {
                "operation": "delete_key",
                "key": key
            })

    def send_request(self, ip, port, message, retries=3, timeout=5):
        # 向另一个节点发送网络请求，带有重试逻辑
        for _ in range(retries):
            try:
                with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                    s.settimeout(timeout)
                    s.connect((ip, port))
                    s.sendall(json.dumps(message).encode('utf-8'))
                    response = s.recv(1024)
                    if response:
                        return json.loads(response.decode('utf-8'))
                    else:
                        return {}
            except Exception as e:
                self.logger.error(f"Error sending request to {ip}:{port}, retrying... Error: {e}")
                time.sleep(1)
        self.logger.error(f"Failed to send request to {ip}:{port} after {retries} retries.")
        return {}

# 用于提供用户一个HTTP Rest API, 并且提供后端存储的访问
class HttpServer:
    # 运行 Chord 网络和 HTTP 接口的主应用类
    def __init__(self, ip, chord_port, http_port, seed_node=None):
        self.registry = FingerTable()  # 初始化节点注册表
        self.current_node = ChordNode(ip, chord_port, self.registry, listen=True)  # 创建当前 Chord 节点

        if seed_node is not None:
            # 如果提供了种子节点，加入网络
            self.current_node.join(seed_node)
        else:
            # 否则，作为独立节点启动
            self.current_node.registry.add_node(self.current_node)
            self.current_node.seed_node = True

        self.app = Flask(__name__)  # 初始化 Flask 应用
        self.setup_routes()  # 设置 HTTP 路由
        self.app.run(host='0.0.0.0', port=http_port)  # 运行 Flask 应用

    def setup_routes(self):
        # 定义键值操作的 HTTP 路由
        @self.app.route('/put', methods=['POST'])
        def put():
            try:
                data = request.get_json()
                key = data['key']
                value = data['value']
                self.current_node.store_key_value(key, value)
                return jsonify({'status': 'success', 'key': key})
            except Exception as e:
                return jsonify({'status': 'error', 'message': str(e)}), 400

        @self.app.route('/get/<key>', methods=['GET'])
        def get(key):
            try:
                value = self.current_node.find_key_value(key)
                if value is not None:
                    return jsonify({'status': 'success', 'key': key, 'value': value})
                else:
                    return jsonify({'status': 'error', 'message': 'Key not found'}), 404
            except Exception as e:
                return jsonify({'status': 'error', 'message': str(e)}), 400

        @self.app.route('/delete/<key>', methods=['DELETE'])
        def delete(key):
            try:
                self.current_node.delete_key_value(key)
                return jsonify({'status': 'deleted', 'key': key})
            except Exception as e:
                return jsonify({'status': 'error', 'message': str(e)}), 400

if __name__ == '__main__':
    chord_port = 0
    if len(sys.argv) > 1:
        # 解析命令行参数以获取种子节点和端口
        seed_node = tuple(sys.argv[1].split(':')) # seed端口
        chord_port = int(sys.argv[2]) # chord 通信端口
        http_port = int(sys.argv[3]) # http通信端口
    else:
        seed_node = None  # 默认是seed,所以不需要seed_node通信信息
        chord_port = 6000 # 默认的chord node的端口
        http_port = 5000  # 默认http 通信端口

    ip = "0.0.0.0"
    HttpServer(ip, chord_port, http_port, seed_node)  # 启动应用


