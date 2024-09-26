from spherov2.types import Color


class Instruction:
    """
    type:
      0 = reset yaw
      1 = reset locator
      2 = reset LED color
      3 = roll
    """

    def __init__(self, spheroID, type: int):
        self.spheroID = spheroID
        self.type = type

    def __init__(self, spheroID, type, color: Color):
        self.spheroID = spheroID
        self.type = type
        self.color = color

    def __init__(self, spheroID, type: int, heading: int, speed: int, duration: int):
        self.spheroID = spheroID
        self.type = type
        self.heading = heading
        self.speed = speed
        self.duration = duration