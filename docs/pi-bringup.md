# Raspberry Pi bring-up — new Pi checklist

Updated after actually doing this for Pi #1 — the earlier version of this
doc had a "Stage B/C" (network reachability, point the GUI at the Pi) that
we never actually needed; everything that mattered happened testing
directly on the Pi itself. All the connect/disconnect fixes below are
already merged into `main` — you're not re-doing any of that work, just
repeating the physical setup.

## 1. Flash and boot

Raspberry Pi Imager → 64-bit Raspberry Pi OS (Desktop if you have a monitor
handy for first boot, Lite if going fully headless). In advanced settings
before writing: set a **unique hostname** (`sphero-pi-02`, `-03`, etc. —
don't reuse `sphero-pi-01`), enable SSH, set Wi-Fi credentials.

**SSH auth: password is fine for now.** You can add a public key and
disable password auth later without re-flashing anything — see the note at
the bottom. Don't let key setup block getting the Pi usable today.

## 2. Connect Wi-Fi (if it didn't take during flashing)

Credentials set in Imager's advanced settings don't always stick. If SSH
won't connect or you're working directly at the Pi with no network, fix it
with `raspi-config` rather than hunting for a taskbar Wi-Fi icon — it works
regardless of whether the desktop's network applet is behaving:
```
sudo raspi-config
```
Navigate: **System Options → Wireless LAN** → enter SSID and password →
back out and select **Finish**. Confirm it worked:
```
ping -c 3 8.8.8.8
```

## 3. First boot + base packages

```
ssh <username>@sphero-pi-02.local
sudo apt update && sudo apt upgrade -y
sudo apt install -y git bluetooth bluez bluez-tools curl
sudo systemctl enable --now bluetooth
sudo systemctl status bluetooth   # must say "active (running)"
```

**Known gotcha:** `apt update`/`install` may say `Could not get lock
/var/lib/apt/lists/lock`. That's almost always `packagekitd` (the
background Software Updater) running automatically after a fresh boot —
check with `ps -p <pid> -o pid,cmd`, and if it's packagekit:
```
sudo systemctl stop packagekit
```
then retry. Not something you broke.

## 4. Verify Bluetooth sees your Spheros — before any of our code

```
bluetoothctl
power on
scan on
```
Confirm you see `SB-xxxx` names for the balls this Pi will own, then
`scan off`, `exit`. **Do not `pair`/`trust`/`connect`** — spherov2 does its
own BLE GATT connect via Bleak/BlueZ directly; manual pairing first can
leave the adapter in a state that fights with it.

## 5. Install `uv`

```
curl -LsSf https://astral.sh/uv/install.sh | sh
```
Close and reopen the terminal, then confirm: `uv --version`.

## 6. Clone the repo and set up a minimal environment

```
git clone https://github.com/purdue-arc/sphero-swarm.git ~/sphero-swarm
cd ~/sphero-swarm
git checkout main
uv venv
uv pip install spherov2 bleak websockets
```

**Use `main`, not `test`** — every fix from Pi #1's bring-up (scan
accumulation across attempts, the 30s Bleak connect timeout patch,
defensive disconnect, quieter error logging) is already merged there.
Skip `uv sync` on the full `pyproject.toml` — it also pulls
`depthai`/`ultralytics`/`pupil-apriltags`/`pygame`, which this Pi's
controls-only role doesn't need and may not build cleanly on ARM.

## 7. Set this Pi's ball list and run the real test

Edit the ball tag list at the bottom of `controls/Controls_Test_Server.py`
to the Spheros *this* Pi will own:
```
nano controls/Controls_Test_Server.py
```
Find `local_cli_test([...])` near the bottom, set it to this Pi's actual
`SB-` tags (double-check for duplicates — that one cost real debugging time
on Pi #1). Save (Ctrl+O, Enter, Ctrl+X), then run:
```
uv run python controls/Controls_Test_Server.py
```
This is the LED-only connection test (no movement) — scans, connects one
ball at a time (up to 30s each), sets LEDs, then idles. Ctrl+C to exit;
disconnects should now be clean and quiet thanks to the fixes already in
`main`.

## Switching from password to key-based SSH later

```
ssh-keygen -t ed25519            # once, on the mini-PC, if you don't have one
ssh-copy-id <username>@sphero-pi-02.local
```
Optionally disable password login afterward: edit `/etc/ssh/sshd_config` on
the Pi, set `PasswordAuthentication no`, `sudo systemctl restart ssh`.
