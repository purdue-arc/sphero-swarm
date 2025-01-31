from spherov2.types import Color


class Instruction:
    """
    type:
      0 = reset LED color
      1 = roll
      2 = turn
      3 = stop thread
    """

    spheroID = 0
    type = -1
    color = 0
    degrees = 0
    speed = 0
    duration = 0

    def __init__(self, *args):
        if (args[1] == 0):
            self.spheroID = args[0]
            self.type = args[1]
            self.color = args[2]
        
        elif (args[1] == 1):
            self.spheroID = args[0]
            self.type = args[1]
            self.speed = args[2]
            self.duration = args[3]

        elif (args[1] == 2):
            self.spheroID = args[0]
            self.type = args[1]
            self.degrees = args[2]
            self.duration = args[3]
