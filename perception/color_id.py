# Colour identity for the brightness-threshold tracker.
#
# Every sphero runs its LED in its own colour (see _LED_PALETTE in
# controls/Controls_Test_Server.py), so colour is the one thing that tells two
# spheros apart once position alone can't. Frame-to-frame tracking stays
# positional; colour is only used to hand a lost display ID back to the right
# sphero when it reappears.
#
# A blob's colour is summarised as a point in the "chroma disc": the mean of
# saturation * (cos hue, sin hue) over its colourful pixels. Red, green and
# blue sit far apart on the rim, pastels sit nearer the centre, and white glare
# has no colourful pixels at all and gets no signature.
#
# Everything in this module is a plain function over (images, tuples, numbers)
# so it can be exercised without a camera - see tests/test_color_id.py.

from collections import deque

import cv2
import numpy as np
from scipy.optimize import linear_sum_assignment

# The LED core saturates to white on camera; the colour is in the glow around
# it, so the blob is grown by this many pixels before sampling.
RING_PX = 4

# A pixel counts as coloured when it is at least this saturated and this
# bright. The brightness floor keeps dark floor around the blob out of it.
SAT_MIN = 64
VAL_MIN = 100

# Fewer coloured pixels than this and the blob has no usable colour.
MIN_COLOUR_PX = 6

PROFILE_HISTORY = 30   # samples kept per display ID
PROFILE_WARMUP = 5     # samples taken unconditionally before gating kicks in
PROFILE_MIN = 3        # samples needed before a profile is trusted

# In lost -> found matching, colour decides and position only breaks ties:
# every 100 px between a blob and a lost sphero's last spot adds this much.
POS_WEIGHT = 0.05
# Cost of matching on position alone, when a lost ID has no colour learnt yet,
# so a colour match always beats it.
NO_PROFILE_COST = 1.0


def colour_signature(frame, contour, ring=RING_PX):
    """(a, b) chroma point for one blob, or None if it shows no clear colour."""
    x, y, w, h = cv2.boundingRect(contour)
    fh, fw = frame.shape[:2]
    x1, y1 = max(0, x - ring), max(0, y - ring)
    x2, y2 = min(fw, x + w + ring), min(fh, y + h + ring)
    if x2 <= x1 or y2 <= y1:
        return None

    region = np.zeros((y2 - y1, x2 - x1), np.uint8)
    cv2.drawContours(region, [contour], -1, 255, -1, offset=(-x1, -y1))
    if ring > 0:
        k = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (2 * ring + 1, 2 * ring + 1))
        region = cv2.dilate(region, k)

    hsv = cv2.cvtColor(frame[y1:y2, x1:x2], cv2.COLOR_BGR2HSV)
    px = hsv[region > 0]
    px = px[(px[:, 1] >= SAT_MIN) & (px[:, 2] >= VAL_MIN)]
    if len(px) < MIN_COLOUR_PX:
        return None

    angle = px[:, 0].astype(np.float32) * (np.pi / 90.0)   # OpenCV hue is 0-179
    sat = px[:, 1].astype(np.float32) / 255.0
    return (float(np.mean(sat * np.cos(angle))), float(np.mean(sat * np.sin(angle))))


def colour_distance(a, b):
    return ((a[0] - b[0]) ** 2 + (a[1] - b[1]) ** 2) ** 0.5


class ColourProfile:
    """What colour one display ID is, learnt while it is being tracked.

    Once warmed up, samples too far from the current estimate are dropped, so
    a track that briefly lands on the wrong sphero can't drag the profile over
    to that sphero's colour.
    """

    def __init__(self, history=PROFILE_HISTORY):
        self.samples = deque(maxlen=history)

    def update(self, sig, gate):
        if sig is None:
            return False
        est = self.estimate
        if len(self.samples) >= PROFILE_WARMUP and est is not None \
                and colour_distance(sig, est) > gate:
            return False
        self.samples.append(sig)
        return True

    @property
    def estimate(self):
        if len(self.samples) < PROFILE_MIN:
            return None
        arr = np.array(self.samples)
        return (float(np.median(arr[:, 0])), float(np.median(arr[:, 1])))


def match_lost(candidates, lost, gate):
    """Hand lost display IDs to unassigned blobs.

    candidates: [(key, (x, y), sig or None)] - blobs with no display ID
    lost:       {disp_id: ((x, y), profile_estimate or None)}
    gate:       largest colour distance still accepted as the same sphero

    Returns {key: (disp_id, colour_dist or None)}. Solved as one assignment
    over every pairing, not greedily, so the first blob can't take the ID a
    later one fits better. A lost ID with a known colour only goes to a blob
    that shows that colour; an uncoloured blob (glare, bad frame) is left for
    the next frame. A lost ID with no colour learnt falls back to position.
    """
    if not candidates or not lost:
        return {}

    ids = list(lost)
    infeasible = 1e6
    cost = np.full((len(candidates), len(ids)), infeasible)
    cdist = {}
    for i, (_key, (cx, cy), sig) in enumerate(candidates):
        for j, did in enumerate(ids):
            (lx, ly), prof = lost[did]
            pos = POS_WEIGHT * (((cx - lx) ** 2 + (cy - ly) ** 2) ** 0.5) / 100.0
            if prof is None:
                cost[i, j] = NO_PROFILE_COST + pos
            elif sig is not None:
                d = colour_distance(sig, prof)
                if d <= gate:
                    cost[i, j] = d + pos
                    cdist[(i, j)] = d

    rows, cols = linear_sum_assignment(cost)
    return {candidates[i][0]: (ids[j], cdist.get((i, j)))
            for i, j in zip(rows, cols) if cost[i, j] < infeasible}
