# D2RSPCP — Diablo 2 Resurrected Single Player Cross Progression

Keeps your D2R single-player characters, shared stash and related files in sync across PCs through a server you host yourself. One Docker image, two modes: `server` and `client`.

## 1. Run the server (once)

Create `.env`:

```
D2RSPCP_TOKEN=put-a-long-random-string-here
```

```
docker compose --profile server up -d
```

It listens on port 8420 and stores everything in `./d2rspcp-data` (current files plus the last 20 versions of each). Put it behind HTTPS (e.g. a reverse proxy) if it is reachable from the internet.

### Web UI

Open `http://your-server:8420/` in a browser and enter your token. You can drag and drop save files in to add or replace them, download any file, and browse each file's history to download or restore an older version. Other devices pick up manual changes on their next sync.

## 2. Run the client (each PC)

Add to `.env` on that PC:

```
D2RSPCP_TOKEN=same-token-as-server
D2RSPCP_SERVER=http://your-server:8420
D2R_SAVES_PATH=C:/Users/YOU/Saved Games/Diablo II Resurrected      # Windows
# D2R_SAVES_PATH=/home/YOU/.local/share/Steam/steamapps/compatdata/.../Saved Games/Diablo II Resurrected   # Linux / Proton
```

```
docker compose --profile client up -d
```

Default save folder on Windows: `%USERPROFILE%\Saved Games\Diablo II Resurrected`.

Without Docker: `pip install fastapi uvicorn requests`, then
`python d2rspcp.py client --server URL --token T --saves "PATH" --config ./config`.

## How syncing works

- Every 30s (`D2RSPCP_INTERVAL`) the client compares local files with the server by SHA-256.
- Only one side changed since the last sync → that side wins. Both changed → the newer file wins and the loser is backed up (server: `history/`, client: `/config/backups`).
- Files modified in the last 5 seconds are skipped, and files are written atomically.
- Nothing is ever deleted by the sync.
- Synced by default: `.d2s .ma0 .ma1 .ma2 .ma3 .map .key .ctl` (flat files only, other files in the folder, e.g. online character data, are ignored). Change the list with `D2RSPCP_EXTENSIONS` (comma separated), e.g. `.d2s,.ma0,.ma1,.ma2,.ma3,.map,.key,.ctl,.d2i` to also sync the shared stash. Set it the same on server and clients.

**Tip:** close the game before switching PCs. D2R writes on save/exit, and the client only picks up the changes once the file settles.
