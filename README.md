Dear Diablo 2 fans!

I have been playing this game for years, and now that I have a Legion Go handheld console, i wanted to give it a try it and play my single player characters. Although I found that moving from my handlheld to my desktop i didn't have quick access to my characters unless i 
manualy transfer them.

So i started looking for a as seamless as possible solution to keep my single player characters updated on all my devices. 

I decided to ask Claude AI to help me build this vision I had and came up with D2RSPCP - Diablo 2 Resurrected Single Player Cross Progression tool!

Everything you read below this introductory text, was written by AI (I want to be as upfront as possible with this) as my coding skills would never be enough to write something like this.

I want to keep this free and open source, and let people who understand more about programming than me to feel free to update it as they wish. It serves my purpose and I hope it can somehow serve yours.

Make sure to backup your d2 files somewhere else just for good measure in case something breaks.

Now, stay a while, and listen! :)

## Disclaimer

D2RSPCP is an unofficial, fan-made, non-commercial tool. It is not affiliated
with, endorsed by, sponsored by, or approved by Blizzard Entertainment, Inc.,
Activision Blizzard, or Microsoft.

Diablo, Diablo II, Diablo II: Resurrected, Blizzard, and related names, logos,
and marks are trademarks or registered trademarks of Blizzard Entertainment,
Inc. They are used here only to describe what this software works with. This
project contains no Blizzard game files, code, or assets. It copies only the
save files that you own on your own devices, between machines that you control.

This project is intended for offline, single-player use only. Do not use it
with online or Battle.net characters. You are responsible for making sure your
use of this software complies with the Blizzard End User License Agreement,
Terms of Use, and any other terms that apply to you.

This software was written with the help of artificial intelligence and has had
only limited testing. It is provided "AS IS", without warranty of any kind,
express or implied, including but not limited to merchantability, fitness for
a particular purpose, and non-infringement. In no event shall the authors or
contributors be liable for any claim, damages, or other liability, including
loss, corruption, or overwriting of save files or characters, arising from the
use of this software. Always keep your own backups of your save files before
using it.

\\\\\\\\\\\\\\\\\\\\\\\ Below this line, everything was written by AI\\\\\\\\\\\\\\\\\\\\\\

D2RSPCP (Diablo 2 Resurrected Single Player Cross Progression) lets you carry your single-player D2R characters between devices, for example a Windows PC and a Steam OS handheld, without copying files by hand.

It has two parts. A small server runs in Docker on your own machine and keeps the current copy of your saves, plus older versions you can restore. A small client runs on each device you play on and keeps its local save folder in sync with the server. It syncs only the character files (.d2s, .ma0–.ma3, .map, .key, .ctl) and ignores everything else in the folder, such as online character data. When a file changes on one device, the others pick it up within seconds, as long as you quit the game before switching. The server also has a simple web page for adding, downloading and restoring files by hand.

Made with AI: everything in this project, including the code, Docker setup, web page and documentation, was written by an AI assistant in conversation with the project owner.

Tests have been made using a Windows PC and a Legion Go running SteamOS.

[SERVER-SETUP.md](https://github.com/user-attachments/files/33689112/SERVER-SETUP.md)
# D2RSPCP server setup (Docker)

The server is a small Docker container that stores the current copy of your saves, plus a history of older versions. Run it once, on a machine that is always on (a home server, NAS or mini PC). All your devices sync against it.

## Requirements

- A Linux machine (or any machine) with **Docker** and **Docker Compose v2** (`docker compose version` should work).
- The server must be reachable from your gaming devices. On a home network, give it a fixed IP (a DHCP reservation in your router).
- Port **8420** open to your local network (see Firewall below).

## 1. Get the files

Put these files in one folder on the server, for example `/home/YOURUSER/D2RSPCP/d2rspcp`:

```
d2rspcp.py[CLIENT-SETUP.md](https://github.com/user-attachments/files/33689113/CLIENT-SETUP.md)

Dockerfile
docker-compose.yml
README.md
.env.example
```

If you have the zip:
```
cd /home/YOURUSER/D2RSPCP
unzip -o d2rspcp.zip      # install with: sudo apt install unzip
cd d2rspcp
```

## 2. Create the .env file

The `.env` file holds your secret token. Create it next to `docker-compose.yml`:

```
cp .env.example .env
nano .env
```

Set a long random token. You can generate one with:
```
openssl rand -hex 32
```

The file should look like this (use your own value):
```
D2RSPCP_TOKEN=3f9a...your-long-random-string...
```

Keep this token. Every client needs the same one. The file name starts with a dot, so it is hidden in file managers; use `ls -a` to see it.

## 3. Build and start

```
docker compose --profile server up -d --build
```

- `--profile server` starts only the server. Do not use the client profile on this machine.
- `-d` runs it in the background. `restart: unless-stopped` brings it back after a reboot or crash.

## 4. Check it works

```
docker compose --profile server ps
docker compose --profile server logs --tail 30
curl http://localhost:8420/health
```

- `ps` should show the container as `Up` and `healthy`.
- `/health` should return `{"status":"ok"}`.
- From another device, open `http://SERVER-IP:8420/health` in a browser.

## 5. Use the web page

Open `http://SERVER-IP:8420/` in a browser and enter your token. You can:

- see every synced file with its size and last-changed time;
- **drag and drop** save files to add or replace them (the old version is kept);
- **download** any file;
- open **History** on a file to download or **restore** an older version.

Files added through the page count as the newest version, so your devices pick them up on their next sync.

## 6. Where your data lives

Everything is stored in `d2rspcp-data` next to `docker-compose.yml`:

```
d2rspcp-data/files/      the current copy of each synced file
d2rspcp-data/history/    older versions (last 20 of each file by default)
```

**Back this folder up** if your characters matter to you. Stopping or rebuilding the container does not delete it.

## 7. Settings you can change

Add these under `environment:` for `d2rspcp-server` in `docker-compose.yml`, then run the start command again.

| Variable | Default | Meaning |
|---|---|---|
| `D2RSPCP_TOKEN` | required | The shared secret, set in `.env` |
| `D2RSPCP_KEEP` | `20` | Older versions kept per file |
| `D2RSPCP_EXTENSIONS` | `.d2s,.ma0,.ma1,.ma2,.ma3,.map,.key,.ctl` | File types that are synced. Set the same value on the server **and every client** |
| `D2RSPCP_PORT` | `8420` | Port inside the container. To use a different port on the host, change the left side of `ports:` (for example `"9000:8420"`) |

Example for also syncing the shared stash:
```
      D2RSPCP_EXTENSIONS: ".d2s,.ma0,.ma1,.ma2,.ma3,.map,.key,.ctl,.d2i"
```

## 8. Firewall

If another device cannot reach the server, allow the port on the server machine.

Ubuntu / Debian with ufw:
```
sudo ufw allow from 192.168.1.0/24 to any port 8420 proto tcp
```
Change `192.168.1.0/24` to your own network range. This allows only your local network.

## 9. Everyday commands

Run these in the folder with `docker-compose.yml`.

```
docker compose --profile server logs -f        # watch the log (Ctrl+C to leave)
docker compose --profile server restart        # restart
docker compose --profile server down           # stop and remove the container (data is kept)
docker compose --profile server up -d --build  # start again, rebuilding from the current files
```

### Update to a new version

```
cd /home/YOURUSER/D2RSPCP
unzip -o d2rspcp.zip
cd d2rspcp
docker compose --profile server down
docker compose --profile server up -d --build
```

Your `.env` and `d2rspcp-data` are not overwritten, because the zip contains neither.

### Change the token

1. Edit `.env` with the new token.
2. Run `docker compose --profile server up -d --force-recreate`.
3. Update the token on every client (the `.bat` file on Windows, the systemd service on Linux/SteamOS) and restart them.

## 10. Security notes

- The server speaks plain HTTP. That is fine on a trusted home network.
- If you expose it to the internet, put it behind HTTPS (for example a reverse proxy such as Caddy or Nginx Proxy Manager), or use a VPN such as Tailscale or WireGuard. Do not forward port 8420 directly to the internet.
- The token is the only protection. Use a long random one and do not share it.

## Troubleshooting

| Problem | What to check |
|---|---|
| `required variable ... is missing a value` when starting | Use the latest `docker-compose.yml`, and make sure `.env` exists in the same folder and has `D2RSPCP_TOKEN` set |
| Container exits or restarts | `docker compose --profile server logs --tail 50` |
| `.env` seems missing | It is a hidden file; use `ls -a` |
| Web page asks for the token again | Wrong token; it must match `.env` exactly |
| Clients say "server unreachable" | Container running? Firewall? Correct IP and port in the client's `--server`? |
| Files are not listed on the page | Only the allowed extensions are shown and synced; check `D2RSPCP_EXTENSIONS` |
| Wrong character version is current | Open the web page, click **History** on the file, and **Restore** the version you want |
| Disk space grows | Lower `D2RSPCP_KEEP`, or delete old files in `d2rspcp-data/history/` |

# D2RSPCP client setup

The client keeps your local Diablo II Resurrected save folder in sync with your D2RSPCP server. Install it on every device you play on.

Replace these placeholders everywhere below:

| Placeholder | Meaning | Example |
|---|---|---|
| `SERVER-IP` | Address of the machine running the server | `192.168.1.50` |
| `YOURTOKEN` | The `D2RSPCP_TOKEN` from the server's `.env` | |
| `SAVE-PATH` | The folder where D2R keeps your saves on this device | see each section |

The server URL is `http://SERVER-IP:8420`. Before starting, open that address in a browser on the device. You should see the D2RSPCP page, and `http://SERVER-IP:8420/health` should show `{"status":"ok"}`.

**Files synced by default:** `.d2s .ma0 .ma1 .ma2 .ma3 .map .key .ctl`. Everything else in the folder is ignored.

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
scp YOURUSER@SERVER-IP:/home/YOURUSER/D2RSPCP/d2rspcp/d2rspcp.py .
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
scp YOURUSER@SERVER-IP:/home/YOURUSER/D2RSPCP/d2rspcp/d2rspcp.py .
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
