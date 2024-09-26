import pickle
import socket
from Instruction import Instruction

from spherov2 import scanner # turning works on relative direction, need to update code to match
from spherov2.sphero_edu import SpheroEduAPI
from spherov2.types import Color
import multiprocessing
import threading
import time
import sys

s = socket.socket()
port = 1234

s.connect(('localhost', port))

instruction = Instruction(0, 3, 0, 100, 10)

s.send(pickle.dumps(instruction))