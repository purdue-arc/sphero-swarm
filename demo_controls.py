# socket_listener.py
import socket
import pickle

def start_server(host='localhost', port=1235):
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.bind((host, port))
    s.listen(1)
    print(f"Server listening on {host}:{port}...")

    conn, addr = s.accept()
    print(f"Connection established with {addr}")

    try:
        while True:
            data = conn.recv(4096)
            if not data:
                print("No data received. Closing connection.")
                break

            conn.send(b"Nothing")

    except KeyboardInterrupt:
        print("Server shutting down...")
    finally:
        conn.close()
        s.close()

if __name__ == "__main__":
    start_server()
