from spherov2.types import Color

class Instruction:
    """
    type:
      -2 = kill immediate
      -1 = kill all spheros after commands run
      0 = reset LED color
      1 = roll
      2 = turn
      3 = wait
    """

    spheroID = 0
    type = -3
    color = 0
    degrees = 0
    speed = 0
    duration = 0

    def __init__(self, *args):
        self.spheroID = args[0]
        self.type = args[1]
        match (args[1]):
            case -2:
                # valid case - similar to case -1
                pass
            case -1:
                # valid case, but this will just make a terminate command
                pass
            case 0:
                self.color = Color(args[2], args[3], args[4])
            case 1:
                self.speed = args[2]
                self.duration = args[3]
            case 2:
                self.degrees = args[2]
                self.duration = args[3]
            case 3:
                self.duration = args[2]
            case _:
                raise ValueError("Don't enter values that aren't -2 through 4 please")
            
    # hopefully this will make debugging easier...
    def __str__(self):
        return("Instruction containing {}".format([self.SpheroID, self.type]))