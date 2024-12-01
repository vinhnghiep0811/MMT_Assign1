import json
import sys
import socket
from threading import Thread

torrent_table = {"1" : ["fileid1"],"2" : {}}
peer_list = {}
tracker_id = 1

def save_tracker_config(ip, port):
    config = {
        "tracker": {
            "ip": ip,
            "port": port,
            "id":tracker_id
        }
    }
    with open('config.json', 'w') as config_file:
        json.dump(config, config_file)

############MULTI TRACKER###############

def find_file_info():
    #TODO
    pass

def find_torrent_info():
    #TODO
    pass

def check_for_file():
    pass

def check_for_torrent():
    pass

#########PEER REQUEST HANDLING##########

def register_peer(message):
    peer_ip = message.get("peer_ip")
    peer_port = message.get("peer_port")
    torrent = message.get("torrent")
    if torrent not in torrent_table:
        response = find_torrent_info()
        return response
    else:
        file_name = "tracker/torrent" + torrent + ".json"
        torrent_file = {}
        with open(file_name, "r") as file:
            torrent_file = json.load(file)
        id = -1
        for peer in torrent_file["peer_list"]:
            if peer["peer_ip"] == peer_ip and peer["peer_port"] == peer_port:
                id = peer["peer_id"]
        if id == -1: #not registered
            torrent_file["peer_list"].append({"peer_id": torrent_file["peer_number"]+1,
                                              "peer_ip": peer_ip,
                                              "peer_port":peer_port})
            peer_id=torrent_file["peer_number"]+1
            torrent_file["peer_number"] = peer_id
            with open(file_name, "w") as file:
                json.dump(torrent_file, file)
            return {"status": "yes", "message": "Registration succeed", "peer_id" : peer_id}
        else: 
            return {"status": "already", "message": "Peer already registered", "peer_id" : id}

def get_peers(message):
    file_id = message.get("file_id")
    torrent = str(message.get("torrent_id"))
    peer_id = message.get("peer_id")
    if file_id not in torrent_table[torrent]:
        return find_file_info(file_id)
    else:
        peer_list = []
        torrent_file = {}
        with open("tracker/torrent" + torrent + ".json", "r") as file:
            torrent_file = json.load(file)
        pieces_number = torrent_file["file_list"][file_id]["number_of_pieces"]
        piece_size = torrent_file["file_list"][file_id]["piece_size"]
        if peer_id not in torrent_file["file_list"][file_id]["peers"]:
            torrent_file["file_list"][file_id]["peers"].append(peer_id)
        peer_list_id = torrent_file["file_list"][file_id]["peers"]
        for peer in torrent_file["peer_list"]:
            if peer["peer_id"] in peer_list_id:
                peer_to_add = {}
                peer_to_add.update(peer)
                peer_to_add.update({"pieces_list" : {}})
                peer_list.append(peer_to_add)
        with open("tracker/torrent" + torrent + ".json", "w") as file:
            json.dump(torrent_file, file)
        return {"status" : "yes", "peer_list" : peer_list, "number_of_pieces" : pieces_number, "piece_size" : piece_size}



def remove_peer(msg):
    #TODO
    pass 

def tracker_thread(conn):
    try:
        message = json.loads(conn.recv(4096).decode())
        action = message.get("action")
        
        if action == "register":
            response = register_peer(message)
            conn.sendall(json.dumps(response).encode())
        elif action== "request":
            response = get_peers(message)
            conn.sendall(json.dumps(response).encode())
        elif action == "quit":
            response = remove_peer(message)
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
    
    while True:  # Keep the server running to accept multiple connections
        conn, addr = serversocket.accept()  # Correctly unpack conn and addr
        print(f"Connection from {addr}")
        nconn = Thread(target=tracker_thread, args=(conn,))  # Start a new thread for each connection
        nconn.start()

  

if __name__ == "__main__":
    #hostname = socket.gethostname()
    hostip = get_host_default_interface_ip()
    port = 22236
    tracker_id = 1
    save_tracker_config(hostip, port)
    print("Listening on: {}:{}".format(hostip,port))
    server_program(hostip, port)