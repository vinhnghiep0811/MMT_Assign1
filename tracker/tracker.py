import socket
from threading import Thread
import json


# def add_file_to_torrent():
#     pass

def send_list(peer_list, conn):
    with open(peer_list, "r") as file:
        data = file.read(1024)
        while data:
            conn.send(data.encode())
            data = file.read(1024)

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
    while True:
        addr, conn = serversocket.accept()
        pip, pport = addr
        msg = serversocket.recv()
        nconn = Thread(target=tracker_thread, args=(pip, pport, conn, msg))
        nconn.start()


if __name__ == "__main__":
    #hostname = socket.gethostname()
    hostip = get_host_default_interface_ip()
    port = 22236
    print("Listening on: {}:{}".format(hostip,port))
    server_program(hostip, port)