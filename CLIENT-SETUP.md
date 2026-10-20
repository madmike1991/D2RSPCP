# D2RSPCP client setup

The client keeps your local Diablo II Resurrected save folder in sync with your D2RSPCP server. Install it on every device you play on.

Replace these placeholders everywhere below:

| Placeholder | Meaning | Example |
|---|---|---|
| `SERVER-IP` | Address of the machine running the server | `192.168.1.50` |
| `YOURTOKEN` | The `D2RSPCP_TOKEN` from the server's `.env` | |
| `SAVE-PATH` | The folder where D2R keeps your saves on this device | see each section |

The server URL is `http://SERVER-IP:8420`. Before starting, open that address in a browser on the device. You should see the D2RSPCP page, and `http://SERVER-IP:8420/health` should show `{"status":"ok"}`.

**Files synced by default:** `.d2s .ma0 .ma1 .ma2 .ma3 .map .key .ctl .d2i`. Everything else in the folder is ignored.

**Golden rule:** quit D2R on one device, wait about 10 seconds for the sync, then start it on the other. If a device downloads a character while the game is open, the game may overwrite it with the version in memory.

---

## Part 1: Windows (using a .bat file)

### 1. Install Python
1. Download Python 3.10 or newer from https://www.python.org/downloads/.
2. In the installer, tick **"Add python.exe to PATH"**, then install.
3. Open PowerShell and check: `python --version`.

### 2. Create the client folder
1. Create `C:\D2RSPCP`.
2. Copy `d2rspcp.py` into it.
3. In PowerShell:
   ```
   cd C:\D2RSPCP
   python -m venv venv
   venv\Scripts\pip install requests
   ```
   If you upgrade Python later, delete the `venv` folder and run these two commands again.

### 3. Back up your saves
Copy your save folder somewhere safe before the first sync. It is normally:
```
C:\Users\YOURNAME\Saved Games\Diablo II Resurrected
```
On the first sync, if the same character exists on both sides, the newer file wins.

### 4. Test once
```
cd C:\D2RSPCP
venv\Scripts\python d2rspcp.py client --server http://SERVER-IP:8420 --token YOURTOKEN --saves "$env:USERPROFILE\Saved Games\Diablo II Resurrected" --config config --once
```
You should see lines such as `uploaded   Name.d2s` or `downloaded Name.d2s`. If you see "server unreachable", check the server address, the firewall, and that the server is running.

### 5. Create the .bat file
Create `C:\D2RSPCP\start-d2rspcp.bat` with this content:
```
@echo off
cd /d C:\D2RSPCP
start "" venv\Scripts\pythonw.exe d2rspcp.py client --server http://SERVER-IP:8420 --token YOURTOKEN --saves "%USERPROFILE%\Saved Games\Diablo II Resurrected" --config config --interval 5
exit
```
- `pythonw.exe` runs without a window. The command window closes right away.
- `--interval 5` checks the server every 5 seconds.

### 6. Start it at login
1. Press **Win+R**, type `shell:startup`, press Enter.
2. Put a **shortcut** to `start-d2rspcp.bat` in that folder.
3. Double-click the `.bat` to start it now without logging out.

### 7. Check it's running
In Task Manager, open the **Details** tab and look for `pythonw.exe`. You will see **two** entries for one running client; that is normal for a Python virtual environment. If you started the `.bat` twice you will see four, so end them all and start it once.

### 8. Stop or update
- **Stop:** end all `pythonw.exe` processes in Task Manager.
- **Update:** stop it, replace `d2rspcp.py`, run the `.bat` again.
- **See what it's doing:** temporarily run the test command from step 4 without `--once` in PowerShell. Logs print in the window; press Ctrl+C to stop.

---

## Part 2: Linux / SteamOS (systemd service)

These steps are for a Steam Deck or Legion Go running SteamOS, and work on most Linux distributions. Use Desktop Mode and open Konsole. The service lives in your home folder, so it survives SteamOS updates. Replace `/home/deck` with your home folder if it differs (check with `echo $HOME`).

### 1. Find your save folder
```
find ~ -type d -name "Diablo II Resurrected" 2>/dev/null
```
Under Proton the path usually looks like:
```
/home/deck/.local/share/Steam/steamapps/compatdata/<number>/pfx/drive_c/users/steamuser/Saved Games/Diablo II Resurrected
```
Copy the exact path it prints; that is your `SAVE-PATH`. If nothing is found, launch D2R once so it creates the folder.

### 2. Install the client
```
mkdir -p ~/d2rspcp && cd ~/d2rspcp
scp sysamdmin@SERVER-IP:/home/sysamdmin/D2RSPCP/d2rspcp/d2rspcp.py .
python3 -m venv venv
./venv/bin/pip install requests
```
The `scp` line copies the script from your server (change the user and path to match yours). You can instead copy `d2rspcp.py` from a USB stick or download it in the browser. Make sure it ends up in `~/d2rspcp`.

### 3. Back up your saves
```
cp -r "SAVE-PATH" ~/d2r-saves-backup
```

### 4. Test once
```
cd ~/d2rspcp
./venv/bin/python d2rspcp.py client --server http://SERVER-IP:8420 --token YOURTOKEN --saves "SAVE-PATH" --config ./config --once
```
You should see `uploaded` or `downloaded` lines. Replaced local files are backed up in `~/d2rspcp/config/backups`.

### 5. Create the systemd service
This creates a user service (no root needed). Fill in the placeholders first. Keep the quotes around `SAVE-PATH`.
```
mkdir -p ~/.config/systemd/user
cat > ~/.config/systemd/user/d2rspcp.service <<'EOF'
[Unit]
Description=D2RSPCP sync
After=network-online.target

[Service]
ExecStart=/home/deck/d2rspcp/venv/bin/python /home/deck/d2rspcp/d2rspcp.py client --server http://SERVER-IP:8420 --token YOURTOKEN --saves "SAVE-PATH" --config /home/deck/d2rspcp/config --interval 5
Restart=always
RestartSec=10

[Install]
WantedBy=default.target
EOF
systemctl --user daemon-reload
systemctl --user enable --now d2rspcp
```
`enable` starts it at every login, including Game Mode. `--now` starts it immediately.

### 6. Check it works
```
systemctl --user status d2rspcp
journalctl --user -u d2rspcp -f
```
Press Ctrl+C to leave the log view; the service keeps running.

What the log shows:
- The client is quiet when nothing has changed. It prints a line only when it uploads or downloads a file, so no new lines is normal.
- `uploaded` / `downloaded` lines mean a sync happened.
- `server unreachable` lines mean the connection to the server failed. If they appear only occasionally while syncing still works, it is harmless noise; if they never stop, check that the server is up and reachable (`curl -i http://SERVER-IP:8420/health`).

### 7. Everyday commands
```
systemctl --user restart d2rspcp          # after replacing d2rspcp.py or editing the service
systemctl --user stop d2rspcp             # stop syncing for now
systemctl --user disable --now d2rspcp    # stop and don't start at login
journalctl --user -u d2rspcp -n 50        # last 50 log lines
```
If you edit `d2rspcp.service`, run `systemctl --user daemon-reload` before restarting.

### 8. Update the client
```
cd ~/d2rspcp
scp sysamdmin@SERVER-IP:/home/sysamdmin/D2RSPCP/d2rspcp/d2rspcp.py .
systemctl --user restart d2rspcp
```

---

## Troubleshooting

| Problem | What to check |
|---|---|
| `server unreachable` on every cycle | Server running? Firewall allows port 8420? Correct IP in `--server`? |
| `401` / wrong token | The token must match the server's `.env` exactly |
| `save folder not found` | The `--saves` path is wrong; re-run the `find` command (Linux) or check the Windows path |
| Windows says `float | None` TypeError | Python is older than 3.10 or you have an old script; install a newer Python and recreate `venv`, and use the latest `d2rspcp.py` |
| A character did not update on the other device | Was the game closed on the first device? Wait ~10 seconds, then check the server page (`http://SERVER-IP:8420/`) for the file's time |
| Wrong version won | Open the server page, click **History** on the file and **Restore** the version you want |
| A file type is not syncing | Only the default extensions sync. To change them set `D2RSPCP_EXTENSIONS` on the server and every client |
