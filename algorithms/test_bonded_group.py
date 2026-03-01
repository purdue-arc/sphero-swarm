from .bonded_group import BondedGroup
from .algorithm import Algorithm
from .sphero import Sphero
from .constants import *

a = Sphero(1, x=1, y=1)
b = Sphero(2, x=1, y=2)
c = Sphero(3, x=2, y=3)
spheros = [a, b, c]

algorithm = Algorithm(10, 10, spheros)
print(str(algorithm))
print('a', a.group_id)
print('b', b.group_id)
print('c', c.group_id)
#print(algorithm.current_grid)
#print(algorithm.next_grid)
algorithm.bond_all_groups()
print(str(algorithm))

#print(list(position_change.values())[1:])
