<<<<<<< HEAD
import json
import sys
import socket
from threading import Thread

torrent_table = {}
peer_list = {}
=======
import socket
from threading import Thread
import json


# def add_file_to_torrent():
#     pass
>>>>>>> 0475fe2ed6b4123f8a78f0175903bdb4664af754

def send_list(peer_list, conn):
    with open(peer_list, "r") as file:
        data = file.read(1024)
        while data:
            conn.send(data.encode())
            data = file.read(1024)

<<<<<<< HEAD
def save_tracker_config(ip, port):
    config = {
        "tracker": {
            "ip": ip,
            "port": port
        }
    }
    with open('config.json', 'w') as config_file:
        json.dump(config, config_file)

def register_peer(message):
    """Registers a peer and associates it with a torrent."""
    peer_id = message.get("peer_id")
    peer_ip = message.get("peer_ip")
    peer_port = message.get("peer_port")
    metainfo = message.get("metainfo")
    file_name = message.get("file_name")
    torrent_hash = metainfo["hash"]
    if not file_name or not metainfo:
        print("Error: Missing file_name or 'metainfo' in the registration message.")
        return "Registration failed"
    # Add peer to the registry for the given torrent
    if torrent_hash not in torrent_table:
        torrent_table[torrent_hash] = {
            "file_name": file_name,
            "peers": []
        }
        
    peer_info = {
        "peer_id": peer_id,
        "peer_ip": peer_ip,
        "peer_port": peer_port,
        "pieces": metainfo["pieces"]
    }
    torrent_table[torrent_hash]["peers"].append(peer_info)
    try:
        with open("torrent.json", "w") as f:
            json.dump(torrent_table, f, indent=4)
        print("Updated torrent table saved to torrent.json.")
    except IOError as e:
        print(f"Error saving torrent table: {e}")
    print(f"Registered peer {peer_id} for torrent {torrent_hash}")
    return "Registration successful"

def get_peers(file_name):
    for torrent_hash, torrent_info in torrent_table.items():
        if torrent_info["file_name"] == file_name:
            peers = [{"peer_id": peer["peer_id"], "peer_ip": peer["peer_ip"], "peer_port": peer["peer_port"]}
                     for peer in torrent_info["peers"]]
            response = {
                "file_name": file_name,
                "peers": peers
            }
            return json.dumps(response)
    return json.dumps({"error": "File not found"})


def remove_peer(peer_ip, peer_port, torrent):
    pass 

def tracker_thread(conn):
    #TODO DECODE MESSAGE
    try:
        data = conn.recv(4096).decode()
        message = json.loads(data)
        action = message.get("action")
        
        if action == "register":
            response = register_peer(message)
            conn.sendall(response.encode())
        elif action == "get_all_files":
            file_names = [info["file_name"] for info in torrent_table.values()]
            conn.sendall(json.dumps(file_names).encode())
        elif action== "request":
            file_name = message.get("file_name")
            response = get_peers(file_name)
            conn.sendall(response.encode())
        else:
            conn.sendall("Error: Unknown action".encode())
    except json.JSONDecodeError:
        conn.sendall("Error: Invalid JSON format".encode())
    except Exception as e:
        print(f"Error handling message: {e}")
        conn.sendall(f"Error: {e}".encode())
    finally:
        conn.close()

    
=======
def add_peer(peer_ip, peer_port, pieces, torrent):
    peer = {'peer_ip': peer_ip, 'peer_port' : peer_port, 'number_of_pieces' : pieces}
    #TODO find file name depend on torrent
    list_file_name = "sample_list"
    try: 
        with open(list_file_name, "r") as file:
            peer_list = json.load(file)
    except FileExistsError:
        return 1, list_file_name
    peer_list.append(peer)
    with open(list_file_name, "w") as file:
        json.dump(peer_list, file, indent=4)
    return 0, list_file_name

def remove_peer(peer_ip, peer_port, torrent):
    #TODO find file name depend on torrent
    list_file_name = "sample_list" #tạm
    try:
        with open(list_file_name, "r") as file:
            peer_list = json.load(file)
        peer_list = [d for d in peer_list if d.get('peer_ip') != peer_ip]
    except FileExistsError:
        return 1
    with open(list_file_name, "w") as file:
        json.dump(peer_list, file, indent=4)
    return 0

def tracker_thread(ip, port, conn, msg):
    #TODO decode msg to action, pieces and torrent
    action = ''
    pieces = ''
    torrent = ''
    if action == 'start':
        torrent_exist, list_file_name = add_peer(ip, port, pieces, torrent)
        if torrent_exist == 0: send_list(list_file_name, conn)
        else:
            conn.send("ERROR: NO SUCH TORRENT WAS FOUND".encode())
    elif action == 'stop':
        remove_peer(ip, port, torrent)
    elif action == 'done':
        pass
    

>>>>>>> 0475fe2ed6b4123f8a78f0175903bdb4664af754
#######TRACKER INTIALIZATION########

def get_host_default_interface_ip():
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
       s.connect(('8.8.8.8',1))
       ip = s.getsockname()[0]
    except Exception:
       ip = '127.0.0.1'
    finally:
       s.close()
    return ip


def server_program(host, port):
    serversocket = socket.socket()
    serversocket.bind((host, port))
    serversocket.listen(10)
<<<<<<< HEAD
    
    while True:  # Keep the server running to accept multiple connections
        conn, addr = serversocket.accept()  # Correctly unpack conn and addr
        print(f"Connection from {addr}")
        nconn = Thread(target=tracker_thread, args=(conn,))  # Start a new thread for each connection
        nconn.start()

  
=======
    while True:
        addr, conn = serversocket.accept()
        pip, pport = addr
        msg = serversocket.recv()
        nconn = Thread(target=tracker_thread, args=(pip, pport, conn, msg))
        nconn.start()

>>>>>>> 0475fe2ed6b4123f8a78f0175903bdb4664af754

if __name__ == "__main__":
    #hostname = socket.gethostname()
    hostip = get_host_default_interface_ip()
    port = 22236
<<<<<<< HEAD
    save_tracker_config(hostip, port)
=======
>>>>>>> 0475fe2ed6b4123f8a78f0175903bdb4664af754
    print("Listening on: {}:{}".format(hostip,port))
    server_program(hostip, port)