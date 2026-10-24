# Merge detection and splitting for the brightness-threshold tracker.
#
# Two spheros that roll together fuse into a single bright blob, so the contour
# pass returns one detection where there should be two and one track dies. The
# helpers here take that blob apart again: a distance transform inside the
# blob's own ROI usually still shows one peak per sphero, and those peaks seed a
# watershed that cuts the blob in two. When the cut fails the caller falls back
# to each track's predicted position and hands out the pixels by nearest
# prediction instead.
#
# Everything in this module is a plain function over (mask, tuples, numbers) so
# it can be exercised without a camera - see test_blob_merge.py.

from collections import deque

import cv2
import numpy as np

# A blob this much bigger than one sphero is a merge candidate. The lower bound
# is tunable (slider / --merge-area-ratio); the upper bound guards against
# glare and reflections, which come in far larger than 2 spheros.
MERGE_AREA_MAX_RATIO = 2.4

# A split is only believed if both halves land in this range of one sphero.
SPLIT_PIECE_MIN_RATIO = 0.45
SPLIT_PIECE_MAX_RATIO = 1.70

# Peaks shorter than this fraction of the tallest one are noise, not a sphero.
# Deliberately low so a smaller sphero next to a bigger one still registers.
PEAK_MIN_HEIGHT_FRAC = 0.35

ROI_MARGIN = 6          # padding around the merged blob's bounding box
SEED_RADIUS = 2         # watershed marker disc drawn at each peak
VELOCITY_SMOOTHING = 0.6  # weight kept from the previous velocity estimate


class SingleAreaEstimator:
    """Running median area of blobs that are unambiguously one sphero.

    Median rather than mean so the odd bad frame (a half-occluded sphero, a
    sliver of glare) doesn't drag the estimate around.
    """

    def __init__(self, history=45):
        self.areas = deque(maxlen=history)

    def update(self, area):
        if area > 0:
            self.areas.append(float(area))

    @property
    def estimate(self):
        if not self.areas:
            return None
        return float(np.median(self.areas))


def predict(pos, vel):
    """Where a track should be next frame, from its last position and velocity."""
    return (pos[0] + vel[0], pos[1] + vel[1])


def update_velocity(old_vel, old_pos, new_pos, smoothing=VELOCITY_SMOOTHING):
    """Exponentially smoothed per-frame displacement."""
    mx = new_pos[0] - old_pos[0]
    my = new_pos[1] - old_pos[1]
    return (smoothing * old_vel[0] + (1.0 - smoothing) * mx,
            smoothing * old_vel[1] + (1.0 - smoothing) * my)


def clamp_to_box(point, bbox, margin=4):
    """Keep a dead-reckoned position inside the blob it is being tracked in."""
    x1, y1, x2, y2 = bbox
    return (min(max(point[0], x1 - margin), x2 + margin),
            min(max(point[1], y1 - margin), y2 + margin))


def is_merged(area, single_area, ratio, tracks_near=0):
    """True when this blob looks like two spheros stuck together."""
    # More tracks than blobs in this spot: something merged regardless of area.
    if tracks_near >= 2:
        return True
    if not single_area or single_area <= 0:
        return False
    return ratio <= (area / single_area) <= MERGE_AREA_MAX_RATIO


def find_peaks(dist, min_separation, max_peaks=3):
    """Local maxima of a distance transform, at least min_separation apart.

    Returns [(x, y, height), ...] tallest first. A plain global cutoff would
    drop the smaller sphero whenever the two differ in size, so this keeps
    every local maximum and only enforces spacing between them.
    """
    if dist is None or dist.size == 0:
        return []
    peak = float(dist.max())
    if peak <= 0:
        return []

    sep = max(1, int(round(min_separation)))
    k = 2 * sep + 1
    dilated = cv2.dilate(dist, np.ones((k, k), np.uint8))
    candidates = (dist >= dilated - 1e-6) & (dist >= PEAK_MIN_HEIGHT_FRAC * peak)

    ys, xs = np.nonzero(candidates)
    if len(xs) == 0:
        return []
    order = np.argsort(dist[ys, xs])[::-1]

    peaks = []
    for i in order:
        x, y, h = int(xs[i]), int(ys[i]), float(dist[ys[i], xs[i]])
        if all((x - px) ** 2 + (y - py) ** 2 >= sep * sep for px, py, _ in peaks):
            peaks.append((x, y, h))
            if len(peaks) >= max_peaks:
                break
    return peaks


def _roi_bounds(mask, bbox, margin):
    h, w = mask.shape[:2]
    x1, y1, x2, y2 = bbox
    x1 = max(0, int(x1) - margin)
    y1 = max(0, int(y1) - margin)
    x2 = min(w, int(x2) + margin)
    y2 = min(h, int(y2) + margin)
    return x1, y1, x2, y2


def _region_stats(ys, xs, ox, oy):
    """Blob tuple (area, cx, cy, x1, y1, x2, y2) for a set of ROI pixels."""
    if len(xs) == 0:
        return None
    return (float(len(xs)),
            float(xs.mean()) + ox, float(ys.mean()) + oy,
            float(xs.min()) + ox, float(ys.min()) + oy,
            float(xs.max()) + ox + 1.0, float(ys.max()) + oy + 1.0)


def split_blob(mask, bbox, min_peak_sep, margin=ROI_MARGIN):
    """Cut a merged blob in two with a distance transform + watershed.

    Works only on the blob's own ROI, so the rest of the mask is untouched.
    Returns (pieces, peak_count); pieces is two blob tuples in image
    coordinates, or None when the blob didn't show exactly two peaks.
    """
    x1, y1, x2, y2 = _roi_bounds(mask, bbox, margin)
    if x2 - x1 < 3 or y2 - y1 < 3:
        return None, 0

    roi = (mask[y1:y2, x1:x2] > 0).astype(np.uint8)
    dist = cv2.distanceTransform(roi, cv2.DIST_L2, 5)
    peaks = find_peaks(dist, min_peak_sep)
    if len(peaks) != 2:
        return None, len(peaks)

    # 1 = background seed, 2/3 = one seed per peak, 0 = let watershed decide.
    markers = np.zeros(roi.shape, np.int32)
    markers[roi == 0] = 1
    for i, (px, py, _h) in enumerate(peaks):
        cv2.circle(markers, (px, py), SEED_RADIUS, i + 2, -1)

    cv2.watershed(cv2.cvtColor(roi * 255, cv2.COLOR_GRAY2BGR), markers)

    pieces = []
    for label in (2, 3):
        ys, xs = np.nonzero(markers == label)
        stats = _region_stats(ys, xs, x1, y1)
        if stats is None:
            return None, 2
        pieces.append(stats)
    return pieces, 2


def split_by_prediction(mask, bbox, predictions, margin=ROI_MARGIN):
    """Fallback split: give each blob pixel to the nearest predicted position."""
    if len(predictions) != 2:
        return None
    x1, y1, x2, y2 = _roi_bounds(mask, bbox, margin)
    roi = mask[y1:y2, x1:x2]
    ys, xs = np.nonzero(roi > 0)
    if len(xs) == 0:
        return None

    gx = xs.astype(np.float32) + x1
    gy = ys.astype(np.float32) + y1
    d0 = (gx - predictions[0][0]) ** 2 + (gy - predictions[0][1]) ** 2
    d1 = (gx - predictions[1][0]) ** 2 + (gy - predictions[1][1]) ** 2
    nearest = d1 < d0

    if not nearest.any() or nearest.all():
        # The predictions coincide, or both sit off the same side of the blob,
        # so nearest-prediction puts every pixel in one pile. Halve the blob
        # along its longer axis instead: which track gets which half is
        # arbitrary while they are this close, and the held velocities pull
        # them apart again over the next frames.
        axis = xs if (x2 - x1) >= (y2 - y1) else ys
        nearest = axis > np.median(axis)
        if not nearest.any() or nearest.all():
            return None

    pieces = []
    for take in (~nearest, nearest):
        stats = _region_stats(ys[take], xs[take], x1, y1)
        if stats is None:
            return None
        pieces.append(stats)
    return pieces


def pieces_plausible(pieces, single_area):
    """Both halves have to look like one sphero each for a split to be trusted."""
    if pieces is None or len(pieces) != 2:
        return False
    if not single_area or single_area <= 0:
        return True   # nothing to compare against yet - take the split
    return all(SPLIT_PIECE_MIN_RATIO <= (p[0] / single_area) <= SPLIT_PIECE_MAX_RATIO
               for p in pieces)


def assign_pieces(pieces, predictions):
    """Order pieces against predictions by minimum total distance.

    Greedy nearest-neighbour swaps identities when two spheros pass close, so
    both pairings are scored and the cheaper one wins.
    """
    def cost(a, b):
        return ((pieces[a][1] - predictions[0][0]) ** 2 + (pieces[a][2] - predictions[0][1]) ** 2) ** 0.5 + \
               ((pieces[b][1] - predictions[1][0]) ** 2 + (pieces[b][2] - predictions[1][1]) ** 2) ** 0.5

    return [0, 1] if cost(0, 1) <= cost(1, 0) else [1, 0]
