import socket
import hashlib
import os
import json
import time
import threading
import base64
from queue import Queue
from threading import Thread
from collections import Counter
from math import ceil

class Peer:
    def __init__(self, peer_port):
        self.peer_id=-1
        self.peer_port = peer_port 
        self.tracker_ip = None
        self.tracker_port = None
        self.torrent = None
        self.queues = {} #manage queues of unacquired pieces
        self.files = {}
        self.pieces = {}
        self.file_mapping = {}
        #self.peer_list = None
        """ {file_id : 
                {"peer_list" : 
                    [{"peer_id": 1, 
                    "peer_ip": "192.168.56.1",
                    "peer_port": 5001,
                    "piece_list": {} }
                    ],
                "retrieved_pieces" : {}
                }
            } """
        #Queues, piece_list, retrieved_list lưu sao tùy bạn nha

    # Lưu file_id cùng với file_name, chủ yếu để đặt tên cho file được ghép lại
    def add_file_mapping(self, file_id, file_name):
        if file_id not in self.file_mapping:
            self.file_mapping[file_id] = file_name
        else:
            print(f"File ID {file_id} already exists with file_name = {self.file_mapping[file_id]}")
    
    # Hàm tạo mảnh pieces
    def create_pieces(self, file_name, file_id):
        """Divide the file into pieces and create a hash for each piece."""
        file_path = os.path.join(os.path.dirname(__file__), file_name)
        piece_size = 20*1024  # 512KB
        if file_id not in self.pieces:
            self.pieces[file_id] = []
        with open(file_path, 'rb') as f:
            piece_index = 0
            while True:
                piece = f.read(piece_size)
                if not piece:
                    break
                piece_hash = hashlib.sha1(piece).hexdigest()  # Use SHA-1 for the piece hash
                self.pieces[file_id].append({
                    "id": piece_index,
                    "data": piece,
                    "hash": piece_hash,
                    "status": "owned",
                })
                piece_index += 1
        return self.pieces

    # Hàm tạo file json lưu metainfo
    def create_metainfo(self, file_name, file_id):
        size = os.path.getsize(file_name)
        if file_id not in self.pieces:
            self.pieces[file_id] = []
        if not self.pieces[file_id]:
            pieces = self.create_pieces(file_name, file_id)
        metainfo = {
            "file_name": file_name,
            "size": size,
            "pieces": [{"id": piece["id"], "hash": piece["hash"], "status": piece["status"]} for piece in self.pieces[file_id]]
        }
        metainfo_filename = "file_status.json"
        if not os.path.exists(metainfo_filename):
        # Khởi tạo file JSON trống
            metainfo_table = {}
            with open(metainfo_filename, 'w') as json_file:
                json.dump(metainfo_table, json_file)
        else:
            # Đọc nội dung JSON hiện tại nếu file tồn tại
            with open(metainfo_filename, 'r') as json_file:
                try:
                    metainfo_table = json.load(json_file)
                except json.JSONDecodeError:
                    print("Warning: JSON file is not valid. Reinitializing metainfo.")
                    metainfo_table = {}

        metainfo_table[file_id] = metainfo

        with open(metainfo_filename, 'w') as json_file:
            json.dump(metainfo_table, json_file, indent=4)  # Write metainfo to JSON file with pretty printing
        
        print(f"Metainfo saved to {metainfo_filename}")
        return metainfo_table

    # Hàm đăng ký peer với tracker
    def register_to_torrent(self, tracker_ip, tracker_port, torrent):
        #send message to torrent
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            # Connect to the tracker
            s.connect((str(tracker_ip), int(tracker_port)))
            message = {
                "action": "register",
                "peer_ip": socket.gethostbyname(socket.gethostname()),
                "peer_port": self.peer_port,
                "torrent": torrent
            }
            s.sendall(json.dumps(message).encode())
            response = json.loads(s.recv(1024).decode())
            if response.get("status") == "yes":
                message = response.get("message")
                self.peer_id = response.get("peer_id")
                self.tracker_ip = tracker_ip
                self.tracker_port = int(tracker_port)
                self.torrent = torrent
                print(message)
            elif response.get("status") == "already":
                self.tracker_ip = tracker_ip
                self.tracker_port = int(tracker_port)
                self.peer_id = response.get("peer_id")
                self.torrent = torrent
                message = response.get("message")
                print(message)
            elif response.get("status") == "torrent_found":
                new_tracker_ip = response.get("tracker_ip")
                new_tracker_port = response.get("tracker_port")
                res = input(f"Torrent found at tracker {new_tracker_ip} : {new_tracker_port}, change tracker? [y/n]")
                if res == "y":
                    print("Registering to new tracker...")
                    self.register_to_torrent(new_tracker_ip, new_tracker_port, torrent)
                else:
                    print("No torrent was selected.")
            else: #cannot find torrent
                print("No such torrent was found. No torrent was selected.")
        except ConnectionResetError as e:
            print("Connection was reset by the tracker:", e)
        except Exception as e:
            print("An error occurred while registering with the tracker:", e)

    def handle_request(self, file_id):
        peer_list = self.request_peer_list(file_id)
        #print(f"[{threading.current_thread().name}] Peer list for {file_name}: {peer_list}")
        self.connect(file_id, peer_list)

    def request_peer_list(self, file_id):
        if self.peer_id == -1:
            print("Please join a torrent first!")
            pass
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            s.connect((self.tracker_ip, self.tracker_port))
            message = {
                "action" : "request",
                "file_id" : file_id,
                "torrent_id" : self.torrent,
                "peer_id" : self.peer_id,
            }
            s.sendall(json.dumps(message).encode())
            response = json.loads(s.recv(1024).decode())
            if response.get("status") == "yes":
                #TODO load pre-downloaded pieces if needed
                self.files.update({file_id : {"peer_list" : response.get("peer_list"), "retrieved_pieces": {}, "number_of_pieces" : response.get("number_of_pieces"), "piece_size" : response.get("piece_size")}})
                self.queues.update({ file_id : Queue(response.get("number_of_pieces"))})
                peer_list = self.files[file_id]["peer_list"]
                print("Get peer info succeed. Start downloading.")
                return peer_list
            elif response.get("status") == "found_in_tracker":
                res = input(f"File infomation found at torrent {response.get("torrent")} instead, switch torrent? [y/n]")
                if res == "y":
                    self.register_to_torrent(self.tracker_ip, self.tracker_port, response.get("torrent"))
                    self.request_peer_list(file_id)
                else:
                    print("No file information was retrieved.")
            elif response.get("status") == "found_in_different_tracker":
                res = input(f"File infomation found at torrent {response.get("torrent")} of tracker {response.get("tracker_ip")} : {response.get("tracker_port")} instead, switch torrent? [y/n]")
                if res == "y":
                    self.register_to_torrent(response.get("tracker_ip"), response.get("tracker_port"), response.get("torrent"))
                    self.request_peer_list(file_id)
                else:
                    print("No file information was retrieved.")
            else:
                print("No such file was found.")
        except ConnectionResetError as e:
            print("Connection was reset by the tracker:", e)
        except Exception as e:
            print("An error occurred while requesting list:", e)

    # Hàm tạo luồng để kết nối đến các peer trong peer_list
    def connect(self, file_id, peer_list):
        threads = []
        print(f"[{threading.current_thread().name}] Connecting to peers...")
        for peer in peer_list:
            if peer["peer_id"] == self.peer_id: pass
            else:
                thread = threading.Thread(target=self.connect_to_peer, args=(file_id, peer, peer_list))
                threads.append(thread)
                thread.start()
        for thread in threads:
            thread.join()

    # Hàm này để lấy về piece_list từ peer, lưu info vào self.pieces và đưa vào queue để chuẩn bị tải
    def connect_to_peer(self, file_id, peer, peer_list): 
        p_ip = peer["peer_ip"]
        p_port = peer["peer_port"]
        piece_list = self.connect_to_peers(p_ip, p_port, file_id)
        if file_id not in self.pieces:
            self.pieces[file_id] = []
        for piece in piece_list:
            if not any(p['hash'] == piece['hash'] for p in self.pieces[file_id]):
                piece['status'] = "downloading"
                self.pieces[file_id].append(piece)
                self.queues[file_id].put(piece)
        self.download_pieces_from_queue(file_id, peer_list)

    # Hàm kết nối đến peer để lấy list_piece
    def connect_to_peers(self, ip, port, file_id):
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            s.connect((ip, port))
            print(f"Connected to peer {ip}:{port}")
            request = {"action": "request_piece_list", "file_id": file_id}
            s.sendall(json.dumps(request).encode())
            size_data = b""
            while b"\n" not in size_data: 
                size_data += s.recv(1)
            total_size = int(size_data.decode().strip())
            received_data = b""
            while len(received_data) < total_size:
                chunk = s.recv(4096)
                if not chunk:
                    break
                received_data += chunk
            response = json.loads(received_data.decode())
            piece_list = response.get("pieces", [])
            s.close()
            print(f"Received piece list from peer: {ip} : {port}")
            return piece_list

        except Exception as e:
            print(f"Error connecting to peer {ip}:{port}: {e}")
            return []

    # Hàm dẫn vào hàm download piece, lấy từng piece trong queue ra và tạo luồng riêng để tải đồng thời, sau đó ghép lại
    def download_pieces_from_queue(self, file_id, peer_list):
        peer_piece_map = {}
        for peer in peer_list:
            ip = peer["peer_ip"]
            port = peer["peer_port"]
            if peer["peer_id"] == self.peer_id: pass
            else: 
                piece_list = self.connect_to_peers(ip, port, file_id)
                if piece_list:
                    peer_piece_map[(ip, port)] = piece_list
        threads = []
        while not self.queues[file_id].empty():
            piece = self.queues[file_id].get()
            piece_id = piece["id"]
            print(f"Downloading piece: ID = {piece_id}")
            thread = Thread(target=self.download_piece, args=(piece_id, peer_piece_map, file_id))
            threads.append(thread)
            thread.start()
        for thread in threads:
            thread.join()
        if self.queues[file_id].empty():  # Kiểm tra nếu queue rỗng
            self.reassemble_file(file_id)

    # Khi có được piece_id cần tải từ queue, lấy peer_piece_map ở trên ra để xem peer nào đang có
    def download_piece(self, piece_id, peer_piece_map, file_id):
        for peer, piece_list in peer_piece_map.items():
            peer_ip, peer_port = peer
            peer_has_piece = any(piece["id"] == piece_id and piece["status"] for piece in piece_list)

            if peer_has_piece:
                piece_data = self.request_piece_from_peer(peer_ip, peer_port, piece_id, file_id)
                if piece_data:
                    for piece in self.pieces[file_id]:
                        if piece["id"] == piece_data["id"] and piece["hash"] == piece_data["hash"]:
                            piece["data"] = piece_data["data"]
                            piece["status"] = piece_data["status"]
                            break
                    print(f"Successfully downloaded piece {piece_id} and added to pieces.")
                    break
                else:
                    print(f"Failed to download piece {piece_id} from peer {peer_ip}:{peer_port}.")
            else:
                print(f"Piece {piece_id} not available from any peers.")

    # Hàm tải data của piece từ peer
    def request_piece_from_peer(self, peer_ip, peer_port, piece_id, file_id):
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            s.connect((peer_ip, peer_port))
            print(f"Requesting piece {piece_id} from peer {peer_ip}:{peer_port}")
            request = {"action": "download_piece", "piece_id": piece_id, "file_id": file_id}
            s.sendall(json.dumps(request).encode())
            # response = s.recv(4096)  # Receive the piece data    
            size_data = b""
            while b"\n" not in size_data:  # Đọc đến khi nhận được ký tự xuống dòng
                size_data += s.recv(1)
            total_size = int(size_data.decode().strip())
            # print(f"Expecting data of size: {total_size} bytes")
            response = b""  # Dữ liệu nhận được (dưới dạng bytes)
            while len(response) < total_size:
                chunk = s.recv(4096)  # Nhận từng phần dữ liệu
                if not chunk:
                    break
                response += chunk     
            if not response:
                print(f"No data received from peer {peer_ip}:{peer_port}")
                s.close()
                return None   
            piece_data = json.loads(response.decode())
            if "data" in piece_data:
                data_base64 = piece_data["data"]
                # Giải mã base64 thành dữ liệu byte
                data = base64.b64decode(data_base64)
                piece_data["data"] = data 
                file_name = piece_data["file_name"]

                # Lưu thông tin file_name với file_id
                self.add_file_mapping(file_id, file_name)
                print(f"Received piece {piece_id} data from peer {peer_ip}:{peer_port}, size: {len(data)} bytes")
                
                s.close()  # Đóng kết nối sau khi nhận xong
                return piece_data
            else:
                print(f"Error: No 'data' field in response from peer {peer_ip}:{peer_port}")
                s.close()
                return None
        except Exception as e:
            print(f"Error requesting piece {piece_id} from peer {peer_ip}:{peer_port}: {e}")
            return None

    # Hàm ghép
    def reassemble_file(self, file_id):
        file_name = self.file_mapping.get(file_id)
        if file_name:
            file_path = os.path.join(file_name)
            with open(file_path, "wb") as f:
                for piece in sorted(self.pieces[file_id], key=lambda x: x['id']):
                    piece_data = piece['data']
                    if isinstance(piece_data, str):
                        piece_data = piece_data.encode('utf-8')  # Chuyển thành bytes với mã hóa utf-8
                    f.write(piece_data)
            self.create_metainfo(file_name, file_id)
            print("File reassembled successfully.")

    def add_file(self, file_name, file_id):
        if self.peer_id == -1:
            print("Please join a torrent first!")
            pass
        if os.path.exists(file_name):
            piece_size = 20*1024
            size = os.path.getsize(file_name)
            number_of_pieces = ceil(size/piece_size)
        else:
            print("File not found.")
            return
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            s.connect((self.tracker_ip, self.tracker_port))
            message = {
                "action" : "add",
                "file_id" : file_id,
                "torrent" : self.torrent,
                "peer_id" : self.peer_id,
                "number_of_pieces" : number_of_pieces,
                "piece_size" : piece_size
            }
            s.sendall(json.dumps(message).encode())
            response = json.loads(s.recv(1024).decode())
            if response.get("message") == "File added.":
                self.files.update({file_id : {"peer_list" : [], "retrieved_pieces" : {}}})
                #TODO add pieces to retrieved pieces
            print(response.get("message"))
        except ConnectionResetError as e:
            print("Connection was reset by the tracker:", e)
        except Exception as e:
            print("An error occurred while requesting list:", e)

    def stop_file(self, file_id):
        if self.peer_id == -1:
            print("Please join a torrent first!")
            pass
        if file_id not in self.files:
            print("Currently not sharing/receiving such file.")
            pass
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            s.connect((self.tracker_ip, self.tracker_port))
            message = {
                "action" : "stop",
                "file_id" : file_id,
                "torrent" : self.torrent,
                "peer_id" : self.peer_id,
            }
            s.sendall(json.dumps(message).encode())
            response = json.loads(s.recv(1024).decode())
            if response.get("message") == "Stop sharing/receiving file succeed.":
                #TODO store retrieved pieces down to temp file 
                self.files.pop(file_id)
                self.queues.pop(file_id)
            print(response.get("message"))
        except ConnectionResetError as e:
            print("Connection was reset by the tracker:", e)
        except Exception as e:
            print("An error occurred while requesting list:", e)

    def quit_torrent(self):
        if self.peer_id == -1:
            print("Please join a torrent first!")
            pass
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            s.connect((self.tracker_ip, self.tracker_port))
            message = {
                "action" : "quit",
                "torrent" : self.torrent,
                "peer_id" : self.peer_id,
            }
            s.sendall(json.dumps(message).encode())
            response = json.loads(s.recv(1024).decode())
            print(response.get("message"))
        except ConnectionResetError as e:
            print("Connection was reset by the tracker:", e)
        except Exception as e:
            print("An error occurred while requesting list:", e)

    # def connect_to_peer(self):
    #     pass
    
    def start_server(self):
        self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.server_socket.bind((socket.gethostbyname(socket.gethostname()), self.peer_port))
        self.server_socket.listen(5) 
        print(f"Listening for incoming connections...")
        while True:
            conn, addr = self.server_socket.accept()
            print(f"Connection accepted from {addr}")
            thread = Thread(target=self.handle_peer_connection, args=(conn,))
            thread.start()
            time.sleep(0.5)


    def handle_peer_connection(self, conn):
        try:
            while True:
                data = conn.recv(1024)
                if not data:
                    break
                request = json.loads(data.decode())
                if request["action"] == "request_piece_list":
                    file_id = request.get("file_id")
                    if file_id not in self.pieces:
                        self.pieces[file_id] = []
                    file_data = self.pieces[file_id]
                    encoded_pieces = [
                        {
                            "id": piece["id"],
                            "hash": piece["hash"],
                            "status": piece["status"]
                        }
                        for piece in file_data
                    ]
                    if isinstance(file_data, list):
                        response = {"action": "response_piece_list", "pieces": encoded_pieces}
                    else:
                        response = {"action": "error", "message": f"Invalid data structure for file_id {file_id}"}
                    response_json = json.dumps(response)
                    total_size = len(response_json.encode())
                    conn.sendall(f"{total_size}\n".encode())
                    conn.sendall(response_json.encode())
                elif request["action"] == "download_piece":
                    file_id = request.get("file_id")
                    file_name = self.file_mapping.get(file_id)
                    piece_id = request.get("piece_id")
                    piece = next((p for p in self.pieces[file_id] if p["id"] == piece_id), None)
                    if piece and piece["status"] == "owned":
                        piece_data = base64.b64encode(piece["data"]).decode('utf-8')
                        response = {
                            "action": "piece_data",
                            "file_name": file_name,
                            "id": piece_id,
                            "data": piece_data,
                            "hash": piece["hash"], 
                            "status": piece["status"]
                        }
                    else:
                        response = {
                            "action": "error",
                            "message": "Piece not found or not available"
                        }
                    response_json = json.dumps(response)
                    total_size = len(response_json.encode())
                    conn.sendall(f"{total_size}\n".encode())
                    conn.sendall(response_json.encode())
                    print("Received data:", data.decode())
        except Exception as e:
            print("Error handling peer connection:", e)
        finally:
            conn.close()

    def start(self):
        server_thread = Thread(target=self.start_server)
        server_thread.daemon = True
        server_thread.start()
node_list = []

def main():
    peer = Peer(5002)
    peer.start()
    time.sleep(0.5)

    threads = []

    while True:
        command = input("Command: ").strip().lower()
        
        if command.startswith("register"):
            tracker_ip = command.split(" ")[1]
            tracker_port = command.split(" ")[2]
            torrent_id = command.split(" ")[3]
            node_list.append(peer)
            peer.register_to_torrent(tracker_ip, tracker_port, torrent_id)
        elif command.startswith("request"):
            file_id = command.split(" ", 1)[1]
            thread = threading.Thread(target=peer.handle_request, args=(file_id,))
            threads.append(thread)
            thread.start()
        elif command.startswith("add"):
            file_name = command.split(" ")[1]
            file_id = command.split(" ")[2]
            peer.add_file_mapping(file_id, file_name)
            peer.create_metainfo(file_name, file_id)
            peer.add_file(file_name, file_id)
        elif command.startswith("stop"):
            file_id = command.split(" ", 1)[1]
            peer.stop_file(file_id)
        elif command == "exit":
            peer.quit_torrent()
            print("Exiting...")
            break
        else:
            print("Invalid command.")
    for thread in threads:
        thread.join()

if __name__ == "__main__":
    main() 
