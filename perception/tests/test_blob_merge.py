# Synthetic tests for blob_merge.py - two touching circles on a black
# background, which is what two spheros rolling together look like to the
# brightness threshold. Run directly:  python test_blob_merge.py
# (also collects under pytest if you have it).

import cv2
import numpy as np

import blob_merge


def two_circles(c0, r0, c1, r1, size=(200, 200)):
    """Binary mask of two overlapping circles, plus the merged blob's bbox."""
    mask = np.zeros(size, np.uint8)
    cv2.circle(mask, c0, r0, 255, -1)
    cv2.circle(mask, c1, r1, 255, -1)
    contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    assert len(contours) == 1, "circles must actually touch for a merge test"
    x, y, w, h = cv2.boundingRect(contours[0])
    return mask, (x, y, x + w, y + h)


def near(pt, want, tol):
    return abs(pt[0] - want[0]) <= tol and abs(pt[1] - want[1]) <= tol


def test_split_equal_circles():
    mask, bbox = two_circles((90, 100), 12, (108, 100), 12)
    pieces, peaks = blob_merge.split_blob(mask, bbox, min_peak_sep=6)
    assert peaks == 2, f"expected 2 peaks, got {peaks}"
    assert pieces is not None
    centers = sorted((p[1], p[2]) for p in pieces)
    assert near(centers[0], (90, 100), 5), centers
    assert near(centers[1], (108, 100), 5), centers
    print("  equal circles  -> centers", [(round(c[0], 1), round(c[1], 1)) for c in centers])


def test_split_unequal_circles():
    # Different radii: a single global cutoff on the distance transform would
    # lose the smaller sphero's peak.
    mask, bbox = two_circles((90, 100), 13, (109, 100), 9)
    pieces, peaks = blob_merge.split_blob(mask, bbox, min_peak_sep=6)
    assert peaks == 2, f"expected 2 peaks, got {peaks}"
    centers = sorted((p[1], p[2]) for p in pieces)
    assert near(centers[0], (90, 100), 5), centers
    assert near(centers[1], (109, 100), 5), centers
    assert pieces[0][0] > 0 and pieces[1][0] > 0
    print("  unequal circles-> centers", [(round(c[0], 1), round(c[1], 1)) for c in centers])


def test_single_circle_is_not_split():
    mask = np.zeros((200, 200), np.uint8)
    cv2.circle(mask, (100, 100), 12, 255, -1)
    pieces, peaks = blob_merge.split_blob(mask, (88, 88, 112, 112), min_peak_sep=6)
    assert pieces is None and peaks == 1, f"peaks={peaks}"
    print("  single circle  -> not split (peaks=1)")


def test_heavy_overlap_falls_back_to_prediction():
    # Nearly concentric: one peak only, so the watershed path bails and the
    # caller's prediction fallback has to carry both tracks.
    mask, bbox = two_circles((100, 100), 12, (105, 100), 12)
    pieces, peaks = blob_merge.split_blob(mask, bbox, min_peak_sep=6)
    assert pieces is None, "a near-concentric pair should not pass the peak test"
    fallback = blob_merge.split_by_prediction(mask, bbox, [(97, 100), (108, 100)])
    assert fallback is not None and len(fallback) == 2
    assert fallback[0][1] < fallback[1][1], fallback
    print(f"  heavy overlap  -> peaks={peaks}, fallback centers "
          f"{round(fallback[0][1], 1)} / {round(fallback[1][1], 1)}")


def test_assignment_avoids_id_swap():
    mask, bbox = two_circles((90, 100), 12, (108, 100), 12)
    pieces, _ = blob_merge.split_blob(mask, bbox, min_peak_sep=6)
    pieces = sorted(pieces, key=lambda p: p[1])          # left, right
    # Track 0 is on the right, track 1 on the left: the order must flip.
    order = blob_merge.assign_pieces(pieces, [(110, 100), (88, 100)])
    assert order == [1, 0], order
    order = blob_merge.assign_pieces(pieces, [(88, 100), (110, 100)])
    assert order == [0, 1], order
    print("  assignment     -> respects predictions in both orders")


def test_velocity_carries_prediction_forward():
    vel = blob_merge.update_velocity((0.0, 0.0), (100, 100), (104, 100))
    assert vel[0] > 0 and abs(vel[1]) < 1e-6
    ahead = blob_merge.predict((104, 100), vel)
    assert ahead[0] > 104
    print(f"  velocity       -> vx={vel[0]:.2f}, next x={ahead[0]:.2f}")


def test_merge_flag_and_area_estimate():
    est = blob_merge.SingleAreaEstimator()
    for a in (440, 460, 450, 455, 1200):   # last one is a merged frame
        est.update(a)
    single = est.estimate
    assert 440 <= single <= 470, single     # median shrugs off the outlier

    assert blob_merge.is_merged(single * 1.8, single, 1.5)
    assert not blob_merge.is_merged(single * 1.05, single, 1.5)
    assert not blob_merge.is_merged(single * 6.0, single, 1.5)   # glare, not a merge
    assert blob_merge.is_merged(single * 1.05, single, 1.5, tracks_near=2)
    assert not blob_merge.is_merged(single * 1.8, None, 1.5)     # no estimate yet
    print(f"  merge flag     -> single area estimate {single:.0f}")


def test_pieces_plausible_rejects_lopsided_split():
    est = 450.0
    assert blob_merge.pieces_plausible([(430, 0, 0, 0, 0, 0, 0), (470, 0, 0, 0, 0, 0, 0)], est)
    assert not blob_merge.pieces_plausible([(60, 0, 0, 0, 0, 0, 0), (840, 0, 0, 0, 0, 0, 0)], est)
    assert not blob_merge.pieces_plausible(None, est)
    print("  sanity check   -> rejects lopsided pieces")


def test_clamp_keeps_dead_reckoning_in_the_blob():
    # A coasting track may not wander off the blob it is supposed to be inside.
    assert blob_merge.clamp_to_box((300, 100), (80, 90, 120, 110), margin=4) == (124, 100)
    assert blob_merge.clamp_to_box((100, 100), (80, 90, 120, 110), margin=4) == (100, 100)
    print("  clamp          -> dead reckoning stays on the blob")


def test_full_occlusion_crossing_keeps_ids():
    """Two spheros passing through each other while fully overlapped.

    At coincidence the pixels say nothing about which sphero is which, so the
    identities have to ride on dead reckoning: anchor += velocity each frame,
    with the split assigned by minimum total distance. The pair must come out
    swapped left-to-right, not bounced back the way they came.
    """
    mask = np.zeros((200, 200), np.uint8)
    cv2.circle(mask, (100, 100), 12, 255, -1)      # both spheros, one blob
    bbox = (88, 88, 112, 112)

    anchors = {0: (106.0, 100.0), 1: (94.0, 100.0)}   # 0 moving left, 1 right
    vels = {0: (-2.0, 0.0), 1: (2.0, 0.0)}
    for _ in range(6):
        preds = [blob_merge.predict(anchors[t], vels[t]) for t in (0, 1)]
        pieces = blob_merge.split_by_prediction(mask, bbox, preds)
        assert pieces is not None
        order = blob_merge.assign_pieces(pieces, preds)
        assert sorted(order) == [0, 1]
        for t, p in zip((0, 1), preds):
            anchors[t] = blob_merge.clamp_to_box(p, bbox)   # velocity held, not re-fit

    assert anchors[0][0] < anchors[1][0], anchors    # 0 came out on the left
    print(f"  occlusion      -> ids crossed over: 0 at x={anchors[0][0]:.0f}, "
          f"1 at x={anchors[1][0]:.0f}")


if __name__ == "__main__":
    tests = [v for k, v in sorted(globals().items()) if k.startswith("test_")]
    for t in tests:
        print(f"{t.__name__}:")
        t()
    print(f"\n{len(tests)} tests passed")
