# Raspberry Pi bring-up — one Pi, one Sphero

First milestone from the distributed plan (see `distributed-plan-review.md`).
Three stages, in order — don't skip ahead. Repeat this whole doc for Pi #2–4
once Pi #1 is reliable.

## Stage A — Prove the Pi can talk to the Sphero at all (no network involved)

1. Flash Raspberry Pi Imager → 64-bit Raspberry Pi OS (Lite is fine). In
   advanced settings before writing: set hostname (`sphero-pi-01`), enable
   SSH, set Wi-Fi credentials (or plan Ethernet). Boots headless.
2. From the mini-PC: `ssh <user>@sphero-pi-01.local` (fall back to the Pi's
   IP from your router if `.local` doesn't resolve).
3. On the Pi:
   ```bash
   sudo apt update && sudo apt upgrade -y
   sudo apt install -y git bluetooth bluez bluez-tools curl
   sudo systemctl enable --now bluetooth
   sudo systemctl status bluetooth   # must say "active (running)"
   ```
4. Verify the adapter sees the Sphero — no pairing:
   ```bash
   bluetoothctl
   power on
   scan on
   ```
   Confirm the `SB-xxxx` name appears, then `scan off`, `exit`. **Do not
   `pair`/`trust`/`connect`** — spherov2's `BleakAdapter` does its own BLE
   GATT connect via BlueZ D-Bus and doesn't need OS-level pairing first;
   manual pairing can leave the adapter in a state that fights with it.
5. Install `uv` (this repo ships `install_uv.sh` for this):
   ```bash
   curl -LsSf https://astral.sh/uv/install.sh | sh
   ```
   Use `uv`, not system `pip` — Pi OS's default Python likely isn't the
   `3.12.10` this repo pins, and `uv` manages its own Python versions.
6. Get the code and run the safest possible smoke test:
   ```bash
   git clone <repo-url> ~/sphero-swarm && cd ~/sphero-swarm
   uv venv
   uv pip install spherov2 bleak websockets
   ```
   Skip `uv sync` on the full `pyproject.toml` for now — it also pulls
   `depthai`/`ultralytics`/`pupil-apriltags`/`pygame` (perception/ML deps
   this Pi's controls-only role doesn't need, some without ARM wheels).
   Edit the ball tag at the bottom of `controls/Controls_Test_Server.py` to
   your Sphero's tag, then:
   ```bash
   uv run python controls/Controls_Test_Server.py
   ```
   (default local mode, no `-s` — LED-only, no motion.) **Success** = the
   ball connects and lights up. This proves BLE-on-this-Pi-hardware works,
   the riskiest unknown, with zero network involved.

## Stage B — Prove the network can reach the Pi's service

Only start once Stage A works.

7. The one required code change — `Controls_Test_Server.py` binds to
   `'localhost'` (loopback only). On the Pi's copy, change:
   ```python
   host = "localhost"
   ```
   to:
   ```python
   host = "0.0.0.0"
   ```
8. Start it in server mode:
   ```bash
   uv run python controls/Controls_Test_Server.py -s
   ```
9. From the mini-PC — not through the GUI yet, keep this isolated:
   ```python
   import asyncio, websockets, json
   async def test():
       async with websockets.connect("ws://sphero-pi-01.local:6768") as ws:
           await ws.send(json.dumps({"type": "connect", "spheros": ["SB-XXXX"]}))
           print(await ws.recv())
   asyncio.run(test())
   ```
   **Success** = the mini-PC, over the real network, told the Pi to connect
   and got a response back.

## Stage C — Point the real GUI at the Pi

Only after A and B both work.

10. Temporarily hardcode `Controls.tsx`'s `ws://localhost:6768` to
    `ws://sphero-pi-01.local:6768` (making it configurable is follow-up
    work, not needed to prove the concept).
11. Don't let Electron's `start-controls` spawn `Controls_Server.py` locally
    for this test — start it manually on the Pi via SSH (step 8) first.
12. Open the app, Controls tab, hit connect. Ball lights up = full path
    validated end to end on real hardware across two machines.

## Explicitly not doing yet

The HTTP/JSON API and Coordinator service from the target-architecture
diagram are real follow-up work — not needed to answer "does one Pi
reliably control one Sphero over the network." Prove A–C first.
