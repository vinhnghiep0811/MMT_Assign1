import socket
import threading
import hashlib
import sys
registered_peers = {} 
running = True 
file_registry = {}
peer_list = {}
file_peers = {}
metainfo_file = "metainfo.txt"

def stop_tracker_server():
    global running
    running = False
    print("Stopping tracker server...")

def handle_peer_connection(client_socket, client_address):
    try:
        data = client_socket.recv(1024).decode()
        if data.startswith("REGISTER"):
            _, peer_id, peer_port = data.split(":")
            if peer_id not in registered_peers:
                registered_peers[peer_id] = [peer_port]
            print(f"Peer {peer_id} registered on port {peer_port}")
            client_socket.send("REGISTERED".encode())

        elif data.startswith("UPLOAD"):
            _, peer_id, peer_port, file_hash, file_name = data.split(":")
            peer_port = int(peer_port)
            if file_hash in file_registry and peer_id in [peer[0] for peer in file_registry[file_hash]]:
                print("File already uploaded by this peer.")
                client_socket.send("UPLOAD_ALREADY_EXISTS".encode())
                return
            if file_hash not in file_registry:
                file_registry[file_hash] = []
            file_registry[file_hash].append((file_name, peer_id, peer_port))
            print(f"File {file_name} with hash {file_hash} registered by peer {peer_id}:{peer_port}")
            with open(metainfo_file, 'a') as f:
                f.write(f"{file_name} - {file_hash} - {peer_id}:{peer_port}\n")
            client_socket.send("UPLOAD_SUCCESS".encode())

        elif data.startswith("SHOW_FILES"):
            if file_registry:
                files_info = "\n".join([f"{entries[0][0]} - {file_hash}" for file_hash, entries in file_registry.items()])
            else:
                files_info = "No files currently registered."
            client_socket.send(files_info.encode())

        elif data.startswith("REQUEST"):
            _, hash_code = data.split(":")
            if hash_code in file_registry:
                peer_list = ', '.join([f"{ip}:{port}" for ip, port in file_registry[hash_code]])
                client_socket.send(peer_list.encode())
            else:
                client_socket.send("NO_PEERS_FOUND".encode())

        elif data.startswith("UPDATE"):
            if registered_peers:
                peer_list = ', '.join(registered_peers.keys())
            else:
                peer_list = "No connected peers."
            client_socket.send(peer_list.encode())

    except Exception as e:
        print(f"Error handling peer {client_address}: {e}")
    finally:
        client_socket.close()

def save_metainfo(self, file_name, file_hash):
        with open(self.metainfo_file, 'a') as f:
            f.write(f"{file_name} - {file_hash}\n")

def start_tracker_server(host="0.0.0.0", port=8000):
    global running
    server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server_socket.bind((host, port))
    server_socket.listen()
    print(f"Tracker server started on {host}:{port}")

    while running:
        try:
            server_socket.settimeout(1.0)  
            client_socket, client_address = server_socket.accept()
            print(f"Accepted connection from {client_address}")
            client_thread = threading.Thread(target=handle_peer_connection, args=(client_socket, client_address))
            client_thread.start()
        except socket.timeout:
            continue

if __name__ == "__main__":
    tracker_thread = threading.Thread(target=start_tracker_server)
    tracker_thread.start()

    while True:
        command = input("Type 'stop' to stop the tracker: ").strip().lower()
        if command == "stop":
            stop_tracker_server()
            break

    tracker_thread.join() 
    print("Tracker server has been stopped.")