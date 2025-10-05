import numpy as np

'''
Given the current direction the sphero is facing (which can be calculated by subtracting perceptions'
coordinates from the sphero's previous coordinates) and the new position the sphero wants to get to,
return the angle that the sphero must turn
'''
def nextVectorDirection(actual, next):
    nextv = np.array([next[0], next[1]]).astype(float)
    actualv = np.array([actual[0], actual[1]]).astype(float)
    nextv[1] = -1 * nextv[1]
    actualv[1] = -1 * actualv[1]

    nextv = nextv - actualv # when this is 0 sphero is not moving to a new location
    d = np.dot(nextv, actualv)

    print(actualv)
    print(nextv)

    theta = np.arccos(d/ (np.linalg.norm(nextv) * np.linalg.norm(actualv))) # check for dividing dot product by 0
    # figure out what to do when actualv is 0?
    theta = np.round(theta * (180 / np.pi))
    degnext = np.arctan2(nextv[1], nextv[0]) + np.pi
    degact = np.arctan2(actualv[1], actualv[0]) + np.pi
    if (degact - degnext > 0):
        theta *= -1
    print(theta)

def nextVectorMagnitude(actual, next):
    nextv = np.array([next[0], next[1]]).astype(float)
    actualv = np.array([actual[0], actual[1]]).astype(float)
    differencev = np.array([nextv[0] - actualv[0], nextv[1] - actualv[1]])

    d = np.sqrt(np.square(differencev[0]) + np.square(differencev[1]))

    print(d)

x = input("act x")
y = input("act y")
nx = input("next x")
ny = input("next y")
nextVectorDirection((x,y), (nx,ny))
nextVectorMagnitude((x,y), (nx,ny))