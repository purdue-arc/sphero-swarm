from spherov2.types import Color

class Instruction:
    """
    type:
      -1 = kill all spheros
      0 = reset LED color
      1 = roll
      2 = turn
      3 = wait
    """

    spheroID = 0
    type = -2
    color = 0
    degrees = 0
    speed = 0
    duration = 0

    def __init__(self, *args):
        self.spheroID = args[0]
        self.type = args[1]
        match (args[1]):
            case -1:
                # valid case, but this will just make a terminate command
                pass
            case 0:
                self.color = args[2]
            case 1:
                self.speed = args[2]
                self.duration = args[3]
            case 2:
                self.degrees = args[2]
                self.duration = args[3]
            case 3:
                self.duration = args[2]
            case _:
                raise ValueError("Don't enter values that aren't -1 through 4 please")
