# Synthetic tests for color_id.py - coloured discs with a white core on a dark
# background, which is roughly what a lit sphero looks like on camera. Run from
# perception/:  PYTHONPATH=. python tests/test_color_id.py
# (also collects under pytest if you have it).

import cv2
import numpy as np

import color_id

GATE = 0.35

# BGR, matching the first few entries of _LED_PALETTE in Controls_Test_Server.py
RED = (0, 0, 255)
GREEN = (0, 255, 0)
BLUE = (255, 0, 0)
YELLOW = (0, 255, 255)


def sphero_frame(spheros, size=(300, 300)):
    """Frame with one lit sphero per (centre, bgr): coloured glow, white core."""
    frame = np.zeros(size + (3,), np.uint8)
    for (cx, cy), bgr in spheros:
        cv2.circle(frame, (cx, cy), 14, bgr, -1)
        cv2.circle(frame, (cx, cy), 8, (255, 255, 255), -1)
    return frame


def blob_contours(frame, thresh=200):
    """Contours of the white cores, as the brightness threshold would see them."""
    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    _, mask = cv2.threshold(gray, thresh, 255, cv2.THRESH_BINARY)
    contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    return sorted(contours, key=lambda c: cv2.boundingRect(c)[0])   # left to right


def sig_of(bgr, ring=color_id.RING_PX):
    frame = sphero_frame([((150, 150), bgr)])
    (c,) = blob_contours(frame)
    return color_id.colour_signature(frame, c, ring)


def learnt(sig, n=10):
    prof = color_id.ColourProfile()
    for _ in range(n):
        prof.update(sig, GATE)
    return prof.estimate


def test_signature_reads_the_glow_not_the_core():
    red = sig_of(RED)
    assert red is not None
    # With no ring the sample is only the saturated white core: no colour
    assert sig_of(RED, ring=0) is None
    print(f"  red            -> {red[0]:.2f}, {red[1]:.2f}")


def test_white_glare_has_no_signature():
    assert sig_of((255, 255, 255)) is None


def test_palette_colours_are_separable():
    sigs = {name: sig_of(bgr) for name, bgr in
            (("red", RED), ("green", GREEN), ("blue", BLUE), ("yellow", YELLOW))}
    names = list(sigs)
    for i, a in enumerate(names):
        for b in names[i + 1:]:
            d = color_id.colour_distance(sigs[a], sigs[b])
            assert d > GATE, f"{a}/{b} only {d:.2f} apart"
    print("  min pair dist  ->", round(min(color_id.colour_distance(sigs[a], sigs[b])
                                          for i, a in enumerate(names) for b in names[i + 1:]), 2))


def test_profile_needs_samples_and_rejects_outliers():
    prof = color_id.ColourProfile()
    red, green = sig_of(RED), sig_of(GREEN)
    prof.update(red, GATE)
    assert prof.estimate is None, "one sample is not a profile yet"
    for _ in range(color_id.PROFILE_WARMUP):
        prof.update(red, GATE)
    assert not prof.update(green, GATE), "a swapped-in green sample must be dropped"
    assert prof.update(None, GATE) is False
    assert color_id.colour_distance(prof.estimate, red) < 0.01


def test_lost_id_goes_to_matching_colour_not_nearest():
    # ID 0 was red, lost at the left. A green blob appears right next to that
    # spot and the red one reappears far away: red must still get ID 0.
    lost = {0: ((50, 50), learnt(sig_of(RED)))}
    cands = [("green", (55, 50), sig_of(GREEN)), ("red", (250, 250), sig_of(RED))]
    out = color_id.match_lost(cands, lost, GATE)
    assert set(out) == {"red"} and out["red"][0] == 0, out


def test_crossing_pair_resolved_jointly():
    # Two lost spheros reappear at each other's last spots: nearest-position
    # would swap them, colour must not.
    lost = {0: ((50, 150), learnt(sig_of(RED))), 1: ((250, 150), learnt(sig_of(BLUE)))}
    cands = [("a", (245, 150), sig_of(RED)), ("b", (55, 150), sig_of(BLUE))]
    out = color_id.match_lost(cands, lost, GATE)
    assert out["a"][0] == 0 and out["b"][0] == 1, out


def test_uncoloured_blob_waits_when_colour_known():
    lost = {0: ((50, 50), learnt(sig_of(RED)))}
    assert color_id.match_lost([("glare", (52, 50), None)], lost, GATE) == {}


def test_falls_back_to_position_without_profile():
    lost = {0: ((50, 50), None), 1: ((250, 250), None)}
    cands = [("x", (240, 245), None), ("y", (60, 55), sig_of(GREEN))]
    out = color_id.match_lost(cands, lost, GATE)
    assert out["x"] == (1, None) and out["y"] == (0, None), out


def test_colour_match_beats_position_only_match():
    # ID 0 has no colour learnt yet, ID 1 is known green: a green blob sitting
    # on ID 0's last spot is still ID 1.
    lost = {0: ((50, 50), None), 1: ((250, 250), learnt(sig_of(GREEN)))}
    out = color_id.match_lost([("g", (50, 50), sig_of(GREEN))], lost, GATE)
    assert out["g"][0] == 1, out


def test_first_assignment_order_is_left_to_right():
    # The spotter hands out IDs left to right; colours then attach to those IDs.
    frame = sphero_frame([((250, 100), BLUE), ((50, 200), RED), ((150, 50), GREEN)])
    sigs = [color_id.colour_signature(frame, c) for c in blob_contours(frame)]
    for sig, bgr in zip(sigs, (RED, GREEN, BLUE)):
        assert color_id.colour_distance(sig, sig_of(bgr)) < 0.05


if __name__ == "__main__":
    tests = [v for k, v in sorted(globals().items()) if k.startswith("test_")]
    for t in tests:
        print(f"{t.__name__}:")
        t()
    print(f"\n{len(tests)} tests passed")
