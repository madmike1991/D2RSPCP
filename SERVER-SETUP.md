# D2RSPCP server setup (Docker)

The server is a small Docker container that stores the current copy of your saves, plus a history of older versions. Run it once, on a machine that is always on (a home server, NAS or mini PC). All your devices sync against it.

## Requirements

- A Linux machine (or any machine) with **Docker** and **Docker Compose v2** (`docker compose version` should work).
- The server must be reachable from your gaming devices. On a home network, give it a fixed IP (a DHCP reservation in your router).
- Port **8420** open to your local network (see Firewall below).

## 1. Get the files

Put these files in one folder on the server, for example `/home/YOURUSER/D2RSPCP/d2rspcp`:

```
d2rspcp.py
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
| `D2RSPCP_EXTENSIONS` | `.d2s,.ma0,.ma1,.ma2,.ma3,.map,.key,.ctl,.d2i` | File types that are synced. Set the same value on the server **and every client** |
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
