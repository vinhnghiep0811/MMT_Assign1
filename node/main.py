import socket
import hashlib
import os
import json
import time
from queue import PriorityQueue
from threading import Thread
from collections import Counter
def load_tracker_config(file_path):
    """Tải cấu hình tracker từ file."""
    with open(file_path, 'r') as config_file:
        config = json.load(config_file)
        return config['tracker']['ip'], config['tracker']['port']

class Peer:

    def __init__(self, peer_id, peer_port, tracker_ip, tracker_port):
        self.peer_id = peer_id
        self.peer_port = peer_port
        self.tracker_ip = tracker_ip
        self.tracker_port = tracker_port
        self.pieces = []
        self.queue = PriorityQueue()
        self.peer_list = []
    
    def start_server(self):
        self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.server_socket.bind((socket.gethostbyname(socket.gethostname()), self.peer_port))
        self.server_socket.listen(5)  # Lắng nghe tối đa 5 kết nối
        print(f"Listening for incoming connections...")

        while True:
            conn, addr = self.server_socket.accept()
            print(f"Connection accepted from {addr}")
            thread = Thread(target=self.handle_peer_connection, args=(conn,))
            thread.start()
            time.sleep(0.5)

    def get_piece_info(self, piece_id):
        """Lấy thông tin về piece từ metainfo."""
        with open("file_status.json", "r") as f:
            metainfo_data = json.load(f)
        pieces = metainfo_data["pieces"]
        for piece in pieces:
            if piece["id"] == piece_id:
                return piece
        return None 

    def handle_peer_connection(self, conn):
        try:
            while True:
                data = conn.recv(1024)
                if not data:
                    break
                request = json.loads(data.decode())
                if request["action"] == "request_piece_list":
                    with open("file_status.json", "r") as f:
                        metainfo_data = json.load(f)
                    response = {"action": "response_piece_list", "pieces": metainfo_data["pieces"]}
                    conn.sendall(json.dumps(response).encode())
                elif request["action"] == "download_piece":
                    piece_id = request.get("piece_id")
                    piece = next((p for p in self.pieces if p["id"] == piece_id), None)
                    if piece and piece["status"]:
                        response = {
                            "action": "piece_data",
                            "id": piece_id,
                            "data": piece["data"].decode('utf-8'),
                            "hash": piece["hash"],  # Trả về thông tin của piece
                            "status": piece["status"]
                        }
                    else:
                        # Nếu chưa tải hoặc không tìm thấy piece, trả về thông báo lỗi
                        response = {
                            "action": "error",
                            "message": "Piece not found or not available"
                        }
                    conn.sendall(json.dumps(response).encode())
                    print("Received data:", data.decode())
        except Exception as e:
            print("Error handling peer connection:", e)
        finally:
            conn.close()

    def create_metainfo(self, file_name):
        file_path = os.path.join(os.path.dirname(__file__), "repo", file_name)
        file_size = os.path.getsize(file_path)
        pieces = self.create_pieces(file_name)
        torrent_hash = hashlib.sha1(json.dumps({
            "file_name": file_name,
            "size": file_size,
        }).encode()).hexdigest()
        
        metainfo = {
            "hash": torrent_hash,
            #"file_name": os.path.basename(file_path),
            "size": file_size,
            "pieces": [{"id": piece["id"], "hash": piece["hash"], "status": piece["status"]} for piece in pieces]
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

        metainfo_table[file_name] = metainfo

        with open(metainfo_filename, 'w') as json_file:
            json.dump(metainfo_table, json_file, indent=4)  # Write metainfo to JSON file with pretty printing
        
        print(f"Metainfo saved to {metainfo_filename}")
        return metainfo_table
    
    def create_pieces(self, file_name):
        """Divide the file into pieces and create a hash for each piece."""
        file_path = os.path.join(os.path.dirname(__file__), "repo", file_name)
        piece_size = 1  # 512KB
        with open(file_path, 'rb') as f:
            piece_index = 0
            while True:
                piece = f.read(piece_size)
                if not piece:
                    break
                piece_hash = hashlib.sha1(piece).hexdigest()  # Use SHA-1 for the piece hash
                if not any(p['hash'] == piece_hash for p in self.pieces):
                    self.pieces.append({
                        "id": piece_index,
                        "data": piece,
                        "hash": piece_hash,
                        "status": True,
                    })
                piece_index += 1
        return self.pieces

    def register_with_tracker(self, metainfo_table, file_name):
        metainfo = metainfo_table.get(file_name)
        if not metainfo:
            print(f"No metainfo found for {file_name}.")
            return
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            # Connect to the tracker
            s.connect((self.tracker_ip, self.tracker_port))
            message = {
                "action": "register",
                "peer_id": self.peer_id,
                "peer_ip": socket.gethostbyname(socket.gethostname()),
                "peer_port": self.peer_port,
                "file_name": file_name,
                "metainfo": metainfo
            }
            s.sendall(json.dumps(message).encode())
            response = s.recv(1024).decode()
            print("Tracker response:", response)
        except ConnectionResetError as e:
            print("Connection was reset by the tracker:", e)
        except Exception as e:
            print("An error occurred while registering with the tracker:", e)

    def get_all_files(self):
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            s.connect((self.tracker_ip, self.tracker_port))
            message = {"action": "get_all_files"}
            s.sendall(json.dumps(message).encode())
            response = s.recv(4096).decode()
            file_list = json.loads(response)
            print("Files available on the tracker:", file_list)
        except Exception as e:
            print("An error occurred while retrieving file list:", e)
    
    def request_peers(self, file_name):
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            s.connect((self.tracker_ip, self.tracker_port))
            message = {
                "action": "request",
                "file_name": file_name
            }
            s.sendall(json.dumps(message).encode())
            response = s.recv(4096).decode()
            self.peer_list = json.loads(response)
            if "error" in self.peer_list:
                print(f"Error: {self.peer_list['error']}")
            else:
                print(f"Peers holding '{file_name}':")
                for peer in self.peer_list["peers"]:
                    if peer["peer_id"] == self.peer_id: continue
                    print(f"Peer ID: {peer['peer_id']}, IP: {peer['peer_ip']}, Port: {peer['peer_port']}")
        except Exception as e:
            print("An error occurred while requesting file peers:", e)
        

    def connect_to_peer(self, peer):
        peer_id = peer["peer_id"]
        peer_ip = peer["peer_ip"]
        peer_port = peer["peer_port"]
        piece_list = self.connect(peer_ip, peer_port)
        
        if not self.pieces:
            piece_frequency = Counter(piece["id"] for piece in piece_list if piece["status"])
            for piece_id, frequency in piece_frequency.items():
                self.queue.put((frequency, piece_id))
        else:
            piece_frequency = Counter(piece["id"] for piece in piece_list if piece["status"])
            for piece_id, frequency in piece_frequency.items():
                if not any(piece["id"] == piece_id and piece["status"] for piece in self.pieces):
                    self.queue.put((frequency, piece_id))

    def connect_to_peers(self):
        threads = []
        for peer in self.peer_list["peers"]:
            if peer["peer_id"] == self.peer_id: continue
            thread = Thread(target=self.connect_to_peer, args=(peer, ))
            threads.append(thread)
            thread.start()

        for thread in threads:
            thread.join()

    def connect(self, ip, port):
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            s.connect((ip, port))
            print(f"Connected to peer {ip}:{port}")
            request = {"action": "request_piece_list"}
            s.sendall(json.dumps(request).encode())
            response = s.recv(4096).decode()
            piece_list = json.loads(response).get("pieces", [])
            piece_status_list = [piece.get("status", 0) for piece in piece_list]
            s.close()
            print("Received piece status list from peer:", piece_status_list)
            return piece_list

        except Exception as e:
            print(f"Error connecting to peer {ip}:{port}: {e}")
            return []

    def download_pieces_from_queue(self, file_name):
        peer_piece_map = {}
        for peer in self.peer_list["peers"]:
            peer_ip, peer_port = peer["peer_ip"], peer["peer_port"]
            piece_list = self.connect(peer_ip, peer_port)
            if piece_list:
                peer_piece_map[(peer_ip, peer_port)] = piece_list
        threads = []
        while not self.queue.empty():
            priority, piece_id = self.queue.get()
            print(f"Downloading piece: ID = {piece_id}, Priority (Frequency) = {priority}")
            thread = Thread(target=self.download_piece, args=(piece_id, peer_piece_map))
            threads.append(thread)
            thread.start()
        for thread in threads:
            thread.join()
        if self.queue.empty():  # Kiểm tra nếu queue rỗng
            self.reassemble_file(file_name)

    def request_piece_from_peer(self, peer_ip, peer_port, piece_id):
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            s.connect((peer_ip, peer_port))
            print(f"Requesting piece {piece_id} from peer {peer_ip}:{peer_port}")
            request = {"action": "download_piece", "piece_id": piece_id}
            s.sendall(json.dumps(request).encode())
            response = s.recv(4096).decode()  # Receive the piece data
            if not response:
                print(f"No data received from peer {peer_ip}:{peer_port}")
                return None
            piece_data = json.loads(response)
            data = piece_data["data"]
            s.close()  # Close connection after receiving piece
            print(f"Received piece {data} data from peer {peer_ip}:{peer_port}")
            return piece_data
        except Exception as e:
            print(f"Error requesting piece {piece_id} from peer {peer_ip}:{peer_port}: {e}")
            return None

    def download_piece(self, piece_id, peer_piece_map):
        # Attempt to download a specific piece from any peer that has it
        for peer, piece_list in peer_piece_map.items():
            peer_ip, peer_port = peer
            peer_has_piece = any(piece["id"] == piece_id and piece["status"] for piece in piece_list)
            if peer_has_piece:
                # Connect again specifically to download the piece
                piece_data = self.request_piece_from_peer(peer_ip, peer_port, piece_id)
                if piece_data:
                    # Save the piece data as needed (e.g., adding to self.pieces)
                    self.pieces.append(piece_data)
                    print(f"Successfully downloaded piece {piece_id} and added to pieces.")
                    break
                else:
                    print(f"Failed to download piece {piece_id} from peer {peer_ip}:{peer_port}.")
            else:
                print(f"Piece {piece_id} not available from any peers.")

    def reassemble_file(self, file_name):
        repo_path = os.path.join(os.path.dirname(__file__), "repo")
        file_path = os.path.join(repo_path, file_name)
        with open(file_path, "wb") as f:
            for piece in sorted(self.pieces, key=lambda x: x['id']):
                piece_data = piece['data']
            # Chuyển đổi `piece_data` từ `str` thành `bytes` nếu cần thiết
                if isinstance(piece_data, str):
                    piece_data = piece_data.encode('utf-8')  # Chuyển thành bytes với mã hóa utf-8
                f.write(piece_data)
        self.create_metainfo(file_name)
        print("File reassembled successfully.")

    def start(self):
        server_thread = Thread(target=self.start_server)
        server_thread.daemon = True
        server_thread.start()

def main():
    tracker_config_path = r'D:\Nam 3\MMT\BTL\P2P\CO3093\tracker\config.json'
    tracker_ip, tracker_port = load_tracker_config(tracker_config_path)  # Đọc IP và cổng từ file
    tracker_address = (tracker_ip, tracker_port)
    print(f"Connecting to tracker at {tracker_address}")
    peer = Peer(peer_id='peer2', peer_port = 5002, tracker_ip = tracker_ip, tracker_port = tracker_port)
    peer.start()
    time.sleep(0.5)
    print("Please type your command:")
    
    while True:
        command = input("Command: ").strip().lower()
        
        if command.startswith("start"):
            file_name = command.split(" ", 1)[1]
            metainfo_table = peer.create_metainfo(file_name)
            peer.register_with_tracker(metainfo_table, file_name)
        elif command == "get":
            peer.get_all_files()
        elif command.startswith("request"):
            file_name = command.split(" ", 1)[1]
            peer.request_peers(file_name)
        elif command == "connect":
            peer.connect_to_peers()
        elif command.startswith("download"):
            file_name = command.split(" ", 1)[1]
            peer.download_pieces_from_queue(file_name)
        elif command == "exit":
            print("Exiting...")
            break
        else:
            print("Invalid command.")


if __name__ == "__main__":
    main()