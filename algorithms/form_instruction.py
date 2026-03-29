import numpy as np

def nextVectorDirection(actual, next):
    nextv = np.array([next[0], next[1]]).astype(float)
    actualv = np.array([actual[0], actual[1]]).astype(float)
    d = np.dot(nextv, actualv)
    theta = np.arccos(d/ (np.linalg.norm(nextv) * np.linalg.norm(actualv)))
    theta = np.round(theta * (180 / np.pi))
    degnext = np.arctan2(nextv[1], nextv[0]) + np.pi
    degact = np.arctan2(actualv[1], actualv[0]) + np.pi
    if (degact - degnext > 0):
        theta *= -1
    print(theta)

x = input("act x")
y = input("act y")
nx = input("next x")
ny = input("next y")
nextVectorDirection((x,y), (nx,ny))