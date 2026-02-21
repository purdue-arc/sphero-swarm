from .bonded_group import BondedGroup
from .algorithm import Algorithm
from .sphero import Sphero
from .constants import *

a = Sphero(0, x=1, y=1)
b = Sphero(1, x=1, y=1.1)
c = Sphero(2, x=2, y=3)
spheros = [a, b, c]
#group = BondedGroup(spheros, 0)
#print(str(group))

algorithm = Algorithm(10, 10, spheros)
#print(str(algorithm))

print(position_change.values())
