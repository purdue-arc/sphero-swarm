# 3V is probably low?

from spherov2.sphero_edu import SpheroEduAPI
from spherov2.scanner import find_toy
from spherov2.commands.power import Power 

toy = find_toy(toy_name="SB-B11D")

with SpheroEduAPI(toy) as api:
    print(Power.get_battery_voltage(api._SpheroEduAPI__toy))