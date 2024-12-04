import socket
import hashlib
import os
import json
import time
from queue import PriorityQueue
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
                self.queues.update({ file_id : PriorityQueue(response.get("number_of_pieces"))})
                print(self.files)
                print("Get peer info succeed. Start downloading.")
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

    def add_file(self, file_name, file_id):
        if self.peer_id == -1:
            print("Please join a torrent first!")
            pass
        path = os.path.abspath(file_name)
        if os.path.exists(path):
            piece_size = 128
            size = os.path.getsize(path)
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

    def connect_to_peer(self):
        pass
    
    def start_server(self):
        self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.server_socket.bind((socket.gethostbyname(socket.gethostname()), self.peer_port))
        self.server_socket.listen(5) 
        print(f"Listening for incoming connections...")

node_list = []

def main():
    
    while True:
        command = input("Command: ").strip().lower()
        
        if command.startswith("register"):
            tracker_ip = command.split(" ")[1]
            tracker_port = command.split(" ")[2]
            torrent_id = command.split(" ")[3]
            peer = Peer(5001)
            node_list.append(peer)
            peer.register_to_torrent(tracker_ip, tracker_port, torrent_id)
        elif command.startswith("request"):
            file_name = command.split(" ", 1)[1]
            peer.request_peer_list(file_name)
        elif command.startswith("add"):
            file_name = command.split(" ")[1]
            file_id = command.split(" ")[2]
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


if __name__ == "__main__":
    main() 
