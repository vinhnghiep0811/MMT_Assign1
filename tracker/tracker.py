import socket
from threading import Thread


torrent_table = {'torrent: ': [{}]}

def add_torrent():
    pass

def send_list(peer_list, peer_ip, peer_port):
    pass

def add_peer(peer_ip, peer_port, status, torrent):
    peer = {'peer_ip': peer_ip, 'peer_port' : peer_port, 'status' : status}
    if torrent in torrent_table:
        torrent_table[torrent].append(peer)
        return 0, torrent_table[torrent]
    else: return 1, torrent_table[torrent]

def remove_peer(peer_ip, peer_port, torrent):
    pass 

def tracker_thread(addr, conn, msg):
    #TODO DECODE MESSAGE
    action = ''
    piece_acquired = 0
    if action == 'start':
        torrent_exist, peerlist = add_peer()
        if torrent_exist == 0: send_list(peerlist, addr, )
        elif piece_acquired > 0:
            add_torrent()
            send_list()
    elif action == 'stop':
        remove_peer()
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
        msg = serversocket.recv()
        nconn = Thread(target=tracker_thread, args=(addr, conn, msg))
        nconn.start()


if __name__ == "__main__":
    #hostname = socket.gethostname()
    hostip = get_host_default_interface_ip()
    port = 22236
    print("Listening on: {}:{}".format(hostip,port))
    server_program(hostip, port)