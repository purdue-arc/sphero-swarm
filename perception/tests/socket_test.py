# terminal.py

import zmq

context = zmq.Context()

socket = context.socket(zmq.REQ)
socket.connect("tcp://127.0.0.1:5555")

print("Connected to ZeroMQ server")

while True:
    command = input("> ")

    socket.send_string(command)

    if command == "exit":
        break

    response = socket.recv()

    try:
        print(response.decode())
    except UnicodeDecodeError:
        print(response)