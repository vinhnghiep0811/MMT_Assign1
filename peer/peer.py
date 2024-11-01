import socket
import hashlib
import os

class Peer:
    def __init__(self, peer_id, peer_port, tracker_ip, tracker_port):
        self.peer_id = peer_id
        self.peer_port = peer_port
        self.tracker_ip = tracker_ip
        self.tracker_port = tracker_port
        self.connected_peers = [] 

    def generate_file_hash(self, file_path):
        hasher = hashlib.sha256()
        try:
            with open(file_path, "rb") as f:
                while chunk := f.read(8192):
                    hasher.update(chunk)
            return hasher.hexdigest()
        except FileNotFoundError:
            print(f"File {file_path} not found.")
            return None
    def upload_file(self, file_name):
        file_path = os.path.join(os.path.dirname(__file__), "repo", file_name)
        file_hash = self.generate_file_hash(file_path)
        if not file_hash:
            print("Unable to upload: file not found.")
            return
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.connect((self.tracker_ip, self.tracker_port))
            message = f"UPLOAD:{self.peer_id}:{self.peer_port}:{file_hash}:{file_name}"
            s.send(message.encode())
            response = s.recv(1024).decode()
            if response == "UPLOAD_SUCCESS":
                print("Tracker response:", response)
            elif response == "UPLOAD_ALREADY_EXISTS":
                print("This file has already been uploaded by this peer.")
            else:
                print("Upload failed or an unexpected response was received.")

    def register_with_tracker(self):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.connect((self.tracker_ip, self.tracker_port))
            message = f"REGISTER:{self.peer_id}:{self.peer_port}"
            s.send(message.encode())
            response = s.recv(1024).decode()
            print("Tracker response:", response)
            self.update_connected_peers()

    def update_connected_peers(self):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.connect((self.tracker_ip, self.tracker_port))
            message = f"UPDATE"
            s.send(message.encode())
            response = s.recv(1024).decode()
            self.connected_peers = response.split(', ') if response else []
            print("Updated connected peers:", self.connected_peers)

    def request_file(self, hash_code):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.connect((self.tracker_ip, self.tracker_port))
            message = f"REQUEST:{hash_code}"
            s.send(message.encode())
            response = s.recv(1024).decode()
            if response == "NO_PEERS_FOUND":
                print("No peers found with the requested file.")
            else:
                print(f"Peers with file {hash_code}: {response}")
                return response.split(", ") if response else []

    def show_files(self):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.connect((self.tracker_ip, self.tracker_port))
            message = "SHOW_FILES"
            s.send(message.encode())
            response = s.recv(4096).decode().strip()
            print("Files on tracker:\n", response)

    def show_peers(self):
        if not self.connected_peers:
            print("No connected peers.")
        else:
            print("Connected peers:")
            for peer in self.connected_peers:
                print(peer)

def main():
    peer = Peer(peer_id='peer1', peer_port = 5001, tracker_ip='127.0.0.1', tracker_port=8000)
    
    print("Please type your command:")
    
    while True:
        command = input("Command: ").strip().lower()
        
        if command == "register":
            peer.register_with_tracker()
        elif command == "show":
            peer.show_peers()
        elif command.startswith("upload"):
            _, file_name = command.split()
            peer.upload_file(file_name)
        elif command == "request":
            hash_code = input("Enter file hash to request: ").strip()
            peer.request_file(hash_code)
        elif command == "show_files":
            peer.show_files()
        elif command == "exit":
            print("Exiting...")
            break
        else:
            print("Invalid command.")

if __name__ == "__main__":
    main()
