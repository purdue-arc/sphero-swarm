import numpy as np

# Returns necessary change in angle to point in new direction
def nextVectorDirection(sphero):
    actualv = np.array([sphero.x, sphero.y], dtype=float) # Current position
    nextv = np.array([sphero.target_x, sphero.target_y], dtype=float) # Next position
    prev_angle = sphero.previous_int_angle # Current angle

    # Direction vector
    direction = nextv - actualv # Desired vector

    if np.linalg.norm(direction) == 0:
        return 0  # no movement → no turn

    # Angle of movement (in degrees)
    target_angle = np.degrees(np.arctan2(direction[1], direction[0]))
    sphero.previous_int_angle = target_angle

    # Compute smallest angle difference
    theta = target_angle - prev_angle

    # Normalize to [-180, 180]
    theta = (theta + 180) % 360 - 180

    return int(round(theta))

# x = input("act x")
# y = input("act y")
# nx = input("next x")
# ny = input("next y")
# nextVectorDirection((x,y), (nx,ny))