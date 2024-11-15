from spherov2.types import Color


class Instruction:
    """
    type:
      0 = reset yaw (not implemented)
      1 = reset locator (not implemented)
      2 = reset LED color
      3 = roll
      4 = reset aim
      5 = stop thread
    """

    spheroID = 0
    type = -1
    color = 0
    heading = 0
    speed = 0
    duration = 0

    def __init__(self, *args):
        if (args[1] == 0):
            self.spheroID = args[0]
            self.type = args[1]

        elif (args[1] == 1):
            self.spheroID = args[0]
            self.type = args[1]
        elif (args[1] == 2):
            self.spheroID = args[0]
            self.type = args[1]
            self.color = args[2]

        elif (args[1] == 3):
            self.spheroID = args[0]
            self.type = args[1]
            self.heading = args[2]
            self.speed = args[3]
            self.duration = args[4]
