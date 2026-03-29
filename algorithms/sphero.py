from .constants import constants

class Sphero:
    def __init__(self, id, x, y,
                 target_x=None, target_y=None,
                 previous_direction=0, direction=0, speed=constants.SIM_SPEED, color=constants.BLACK,
                 trait="tail",
                 bonding_directions=list(constants.position_change.values())[1:]):
        # attributes
        self.id = id
        self.speed = speed
        self.trait = trait  # "head" or "tail"
        self.color: tuple[int, int, int] = constants.RED if trait == "head" else constants.BLUE

        # position values
        self.x = x
        self.y = y
        self.true_x = x
        self.true_y = y
        self.target_x = target_x if target_x is not None else x
        self.target_y = target_y if target_y is not None else y
        self.previous_direction = previous_direction
        self.direction = direction

        # bonding rules. CHANGE THIS if you need to change the bonding rules
        self.bonding_directions = bonding_directions #the default: spheros can bond in all 8 directions.
        self.group_id = id # spheros are initialized as belonging to themselves

    def compute_target_position(self, direction): # -> (int, int)
        """
        Compute our sphero's target position given the direction

        Args:
            direction: (int) value between 0 to DIRECTIONS
        
        Returns:
            (int, int): sphero's target position
        """

        return (self.x + constants.position_change[direction][0], self.y + constants.position_change[direction][1])   

    def update_target(self):
        """
        Update our sphero's target position given our current direction

        Args:
            None
        
        Returns:
            None
        """

        self.target_x, self.target_y = self.compute_target_position(direction=self.direction)     

    def update_direction(self, direction):
        """
        Update our sphero's direction and previous direction given a direction

        Args:
            direction: (int) value between 0 and DIRECTIONS

        Returns:
            None
        """

        self.previous_direction = self.direction
        self.direction = direction

    def update_movement(self, direction):
        """
        Update a spheros direction and target position given a direction

        Args:
            direction: (int) value between 0 and DIRECTIONS

        Returns:
            None
        """
        self.update_direction(direction=direction)
        self.update_target()

    def get_direction_change(self):
        """
        Get the difference between our previous and current direction

        Args:
            None

        Returns:
           (int): Difference between previous and current direction
        """
        return self.previous_direction - self.direction

    def get_position_change(self):
        """
        Get the change in position given our sphero's direction.

        Parameters:
            None

        Returns:
            (int, int): Our sphero's change in position from moving in the direction it's chosen.
        """

        return constants.position_change[self.direction]

    def can_bond(self, adj_sphero):
        """
        Determines if our sphero and another sphero are close enough to bond

        Args:
            adj_sphero: (Sphero) another sphero

        Returns:
            (bool): Is our sphero and the adjacent sphero close enough to bond?
        """
        if (abs(self.x - adj_sphero.x) <= 1 and
            abs(self.y - adj_sphero.y) <= 1):
            return True
        return False

    def __str__(self):
        return f"pos: {self.x}, {self.y}, id: {self.id}, direction: {self.direction}, target pos: {self.target_x}, {self.target_y}"