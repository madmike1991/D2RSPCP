#!/usr/bin/env python3
"""D2RSPCP - Diablo 2 Resurrected Single Player Cross Progression.

One program, two modes:
  server  Hosts the canonical copy of your saves (run it once, on your own box).
  client  Runs on each gaming PC; keeps a local save folder in sync with the server.

Config comes from CLI flags or environment variables (handy for Docker).
"""
import argparse
import hashlib
import hmac
import json
import logging
import os
import re
import shutil
import sys
import tempfile
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

log = logging.getLogger("d2rspcp")

# D2R single-player files live flat in "Saved Games/Diablo II Resurrected".
# Only these extensions are synced. Override with D2RSPCP_EXTENSIONS (comma separated),
# e.g. add ".d2i" to also sync the shared stash.
ALLOWED_EXT = {
    (e.strip() if e.strip().startswith(".") else "." + e.strip()).lower()
    for e in os.environ.get("D2RSPCP_EXTENSIONS", ".d2s,.ma0,.ma1,.ma2,.ma3,.map,.key,.ctl").split(",")
    if e.strip()
}
NAME_RE = re.compile(r"^[\w][\w .\-]{0,127}$")
MAX_FILE_BYTES = 10 * 1024 * 1024
SETTLE_SECONDS = 5  # ignore files touched this recently (game may be writing)


# --------------------------------------------------------------------------- helpers
def valid_name(name: str) -> bool:
    return bool(NAME_RE.match(name)) and Path(name).suffix.lower() in ALLOWED_EXT


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def stamp() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")


def atomic_write(path: Path, data: bytes, mtime: Optional[float] = None) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=path.parent, prefix=".d2rspcp-", suffix=".tmp")
    try:
        with os.fdopen(fd, "wb") as f:
            f.write(data)
        if mtime is not None:
            os.utime(tmp, (mtime, mtime))
        os.replace(tmp, path)
    finally:
        if os.path.exists(tmp):
            os.unlink(tmp)


def archive(path: Path, history_root: Path, keep: int) -> None:
    """Copy `path` into history_root/<name>/<timestamp> and prune old copies."""
    if not path.exists():
        return
    dest_dir = history_root / path.name
    dest_dir.mkdir(parents=True, exist_ok=True)
    shutil.copy2(path, dest_dir / stamp())
    for old in sorted(dest_dir.iterdir())[:-keep]:
        old.unlink(missing_ok=True)


# --------------------------------------------------------------------------- web UI
UI_HTML = r"""<!doctype html>
<html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>D2RSPCP</title>
<style>
:root{--bg:#f6f5f2;--card:#fff;--fg:#1d1b18;--mute:#77716a;--line:#e3dfd8;--acc:#9b2c1f;--accfg:#fff}
@media(prefers-color-scheme:dark){:root{--bg:#141210;--card:#1e1b18;--fg:#ece7df;--mute:#9a9187;--line:#33302b;--acc:#c0392b}}
*{box-sizing:border-box}
body{margin:0;background:var(--bg);color:var(--fg);font:15px/1.45 system-ui,sans-serif}
main{max-width:760px;margin:0 auto;padding:20px 16px 60px}
h1{font-size:20px;margin:0 0 2px}h1 span{color:var(--acc)}
.sub{color:var(--mute);margin:0 0 18px;font-size:13px}
.card{background:var(--card);border:1px solid var(--line);border-radius:10px;padding:14px;margin-bottom:16px}
button,.btn{font:inherit;border:1px solid var(--line);background:var(--card);color:var(--fg);border-radius:7px;padding:5px 11px;cursor:pointer}
button.pri{background:var(--acc);color:var(--accfg);border-color:var(--acc)}
button:hover{filter:brightness(.95)}
input[type=password]{font:inherit;padding:7px 10px;border-radius:7px;border:1px solid var(--line);background:var(--bg);color:var(--fg);width:100%;margin:8px 0}
#drop{border:2px dashed var(--line);border-radius:10px;padding:26px 12px;text-align:center;color:var(--mute);cursor:pointer}
#drop.over{border-color:var(--acc);color:var(--fg)}
.row{display:flex;gap:8px;align-items:center;padding:9px 0;border-top:1px solid var(--line);flex-wrap:wrap}
.row:first-child{border-top:0}
.name{flex:1 1 220px;font-weight:600;word-break:break-all}
.meta{color:var(--mute);font-size:12.5px}
.hist{width:100%;padding:4px 0 2px 14px}
.hrow{display:flex;gap:8px;align-items:center;padding:3px 0;font-size:13px;flex-wrap:wrap}
.hrow span.meta{flex:1 1 160px}
#msg{min-height:20px;font-size:13px;margin:0 0 10px}
.err{color:#c0392b}.ok{color:#2e8b57}
</style></head><body><main>
<h1>D2R<span>SPCP</span></h1>
<p class="sub">Diablo 2 Resurrected single player saves</p>
<div id="login" class="card" hidden>
  <b>Enter your server token</b>
  <input type="password" id="tok" placeholder="D2RSPCP_TOKEN" autocomplete="current-password">
  <button class="pri" id="go">Unlock</button> <span id="lerr" class="err"></span>
</div>
<div id="app" hidden>
  <div id="msg"></div>
  <div class="card">
    <div id="drop">Drop save files here, or click to choose<br>
      <small>Allowed: __EXT__ · an existing file is replaced (the old one is kept in history)</small></div>
    <input type="file" id="pick" multiple hidden>
  </div>
  <div class="card"><div id="list"></div></div>
  <button id="out">Forget token</button>
</div>
<script>
const $=s=>document.querySelector(s), enc=encodeURIComponent;
let token=''; try{token=localStorage.getItem('d2rspcp_token')||''}catch(e){}
function say(t,cls){const m=$('#msg');m.textContent=t;m.className=cls||''}
function showLogin(err){$('#app').hidden=true;$('#login').hidden=false;$('#lerr').textContent=err||''}
async function api(path,opts={}){
  opts.headers=Object.assign({Authorization:'Bearer '+token},opts.headers||{});
  const r=await fetch(path,opts);
  if(r.status===401){try{localStorage.removeItem('d2rspcp_token')}catch(e){};showLogin('Wrong token');throw new Error('Unauthorized')}
  if(!r.ok){let t='';try{t=(await r.json()).detail}catch(e){};throw new Error(t||('HTTP '+r.status))}
  return r}
const fmtSize=n=>n<1024?n+' B':(n/1024).toFixed(1)+' KB';
const fmtDate=s=>new Date(s*1000).toLocaleString();
function fmtVer(v){const m=/^(\d{4})(\d\d)(\d\d)T(\d\d)(\d\d)(\d\d)/.exec(v);
  return m?new Date(Date.UTC(+m[1],m[2]-1,+m[3],+m[4],+m[5],+m[6])).toLocaleString():v}
function save(blob,name){const a=document.createElement('a');a.href=URL.createObjectURL(blob);a.download=name;a.click();setTimeout(()=>URL.revokeObjectURL(a.href),5000)}
function btn(label,fn,cls){const b=document.createElement('button');b.textContent=label;if(cls)b.className=cls;b.onclick=fn;return b}
async function guard(fn){try{await fn()}catch(e){if(e.message!=='Unauthorized')say(e.message,'err')}}

async function load(){
  const files=await (await api('/api/files')).json();
  $('#login').hidden=true;$('#app').hidden=false;
  const list=$('#list');list.textContent='';
  const names=Object.keys(files).sort();
  if(!names.length){list.textContent='No files on the server yet.';return}
  for(const n of names){
    const f=files[n],row=document.createElement('div');row.className='row';
    const nm=document.createElement('div');nm.className='name';nm.textContent=n;
    const meta=document.createElement('div');meta.className='meta';meta.textContent=fmtSize(f.size)+' · '+fmtDate(f.mtime);
    const hist=document.createElement('div');hist.className='hist';hist.hidden=true;
    row.append(nm,meta,
      btn('Download',()=>guard(async()=>save(await (await api('/api/files/'+enc(n))).blob(),n))),
      btn('History',()=>guard(()=>toggleHist(n,hist))),hist);
    list.append(row)}}

async function toggleHist(n,box){
  if(!box.hidden){box.hidden=true;return}
  const vs=await (await api('/api/history/'+enc(n))).json();
  box.textContent='';
  if(!vs.length){box.textContent='No older versions yet.'}
  for(const v of vs){
    const r=document.createElement('div');r.className='hrow';
    const m=document.createElement('span');m.className='meta';m.textContent=fmtVer(v.version)+' · '+fmtSize(v.size);
    r.append(m,
      btn('Download',()=>guard(async()=>save(await (await api('/api/history/'+enc(n)+'/'+v.version)).blob(),n+'.'+v.version))),
      btn('Restore',()=>guard(async()=>{
        if(!confirm('Restore '+n+' from '+fmtVer(v.version)+'? The current file is kept in history.'))return;
        await api('/api/restore/'+enc(n)+'/'+v.version,{method:'POST'});
        say('Restored '+n,'ok');await load()})));
    box.append(r)}
  box.hidden=false}

async function upload(files){
  for(const f of files){
    await guard(async()=>{
      await api('/api/files/'+enc(f.name),{method:'PUT',body:f,headers:{'X-Mtime':String(Date.now()/1000)}});
      say('Uploaded '+f.name+'. Other devices will pick it up on their next sync.','ok')})}
  await guard(load)}

const drop=$('#drop'),pick=$('#pick');
drop.onclick=()=>pick.click();
pick.onchange=()=>{upload([...pick.files]);pick.value=''};
['dragover','dragenter'].forEach(e=>drop.addEventListener(e,ev=>{ev.preventDefault();drop.classList.add('over')}));
['dragleave','drop'].forEach(e=>drop.addEventListener(e,ev=>{ev.preventDefault();drop.classList.remove('over')}));
drop.addEventListener('drop',ev=>upload([...ev.dataTransfer.files]));
$('#go').onclick=()=>{token=$('#tok').value.trim();try{localStorage.setItem('d2rspcp_token',token)}catch(e){};guard(load)};
$('#tok').onkeydown=e=>{if(e.key==='Enter')$('#go').click()};
$('#out').onclick=()=>{try{localStorage.removeItem('d2rspcp_token')}catch(e){};token='';$('#tok').value='';showLogin('')};
if(token)guard(load).catch(()=>showLogin('')); else showLogin('');
</script></main></body></html>
"""


# --------------------------------------------------------------------------- server
def make_app(data_dir: Path, token: str, keep: int):
    from fastapi import Depends, FastAPI, HTTPException, Request, Response
    from fastapi.responses import HTMLResponse

    files_dir = data_dir / "files"
    history_dir = data_dir / "history"
    files_dir.mkdir(parents=True, exist_ok=True)
    app = FastAPI(title="D2RSPCP", docs_url=None, redoc_url=None)

    def auth(request: Request):
        supplied = request.headers.get("authorization", "")
        expected = f"Bearer {token}"
        if not hmac.compare_digest(supplied.encode(), expected.encode()):
            raise HTTPException(status_code=401, detail="bad token")

    def path_for(name: str) -> Path:
        if not valid_name(name):
            raise HTTPException(status_code=400, detail="invalid file name")
        return files_dir / name

    @app.get("/health")
    def health():
        return {"status": "ok"}

    @app.get("/api/files", dependencies=[Depends(auth)])
    def list_files():
        out = {}
        for p in files_dir.iterdir():
            if p.is_file() and valid_name(p.name):
                st = p.stat()
                out[p.name] = {"sha256": sha256_file(p), "mtime": st.st_mtime, "size": st.st_size}
        return out

    @app.get("/api/files/{name}", dependencies=[Depends(auth)])
    def get_file(name: str):
        p = path_for(name)
        if not p.is_file():
            raise HTTPException(status_code=404)
        return Response(p.read_bytes(), media_type="application/octet-stream",
                        headers={"X-Mtime": repr(p.stat().st_mtime)})

    @app.put("/api/files/{name}", dependencies=[Depends(auth)])
    async def put_file(name: str, request: Request):
        p = path_for(name)
        data = await request.body()
        if not data or len(data) > MAX_FILE_BYTES:
            raise HTTPException(status_code=413, detail="empty or too large")
        try:
            mtime = float(request.headers.get("x-mtime", time.time()))
        except ValueError:
            mtime = time.time()
        archive(p, history_dir, keep)
        atomic_write(p, data, mtime)
        log.info("stored %s (%d bytes)", name, len(data))
        return {"ok": True}

    def history_file(name: str, version: str) -> Path:
        path_for(name)
        if not re.fullmatch(r"\d{8}T\d{12}Z", version):
            raise HTTPException(status_code=400, detail="invalid version")
        h = history_dir / name / version
        if not h.is_file():
            raise HTTPException(status_code=404)
        return h

    @app.get("/", response_class=HTMLResponse)
    def ui():
        return UI_HTML.replace("__EXT__", " ".join(sorted(ALLOWED_EXT)))

    @app.get("/api/history/{name}", dependencies=[Depends(auth)])
    def list_history(name: str):
        path_for(name)
        d = history_dir / name
        if not d.is_dir():
            return []
        return [{"version": v.name, "size": v.stat().st_size} for v in sorted(d.iterdir(), reverse=True)]

    @app.get("/api/history/{name}/{version}", dependencies=[Depends(auth)])
    def get_history(name: str, version: str):
        return Response(history_file(name, version).read_bytes(), media_type="application/octet-stream")

    @app.post("/api/restore/{name}/{version}", dependencies=[Depends(auth)])
    def restore(name: str, version: str):
        h = history_file(name, version)
        p = path_for(name)
        data = h.read_bytes()  # read first: archive() may prune this very version
        archive(p, history_dir, keep)
        atomic_write(p, data, time.time())
        log.info("restored %s from %s", name, version)
        return {"ok": True}

    return app


def run_server(args):
    import uvicorn
    if not args.token:
        sys.exit("D2RSPCP_TOKEN is required for server mode")
    app = make_app(Path(args.data), args.token, args.keep)
    uvicorn.run(app, host="0.0.0.0", port=args.port, log_level="warning")


# --------------------------------------------------------------------------- client
def scan_local(saves: Path) -> dict:
    out, now = {}, time.time()
    for p in saves.iterdir():
        if not (p.is_file() and valid_name(p.name)):
            continue
        st = p.stat()
        if now - st.st_mtime < SETTLE_SECONDS:
            log.debug("skipping %s (modified just now)", p.name)
            continue
        try:
            out[p.name] = {"sha256": sha256_file(p), "mtime": st.st_mtime}
        except OSError as e:  # locked by the game: leave it out, retry next cycle
            log.debug("skipping %s (in use: %s)", p.name, e)
    return out


def sync_once(session, server: str, saves: Path, state: dict, backups: Path, keep: int) -> None:
    base = server.rstrip("/")
    r = session.get(f"{base}/api/files", timeout=30)
    r.raise_for_status()
    remote = r.json()
    local = scan_local(saves)
    # Files present locally but skipped as "just modified" must not be treated as missing.
    in_flux = {p.name for p in saves.iterdir() if p.is_file() and valid_name(p.name)} - set(local)

    def upload(name):
        p = saves / name
        data = p.read_bytes()
        resp = session.put(f"{base}/api/files/{name}", data=data,
                           headers={"X-Mtime": repr(local[name]["mtime"])}, timeout=60)
        resp.raise_for_status()
        state[name] = local[name]["sha256"]
        log.info("uploaded   %s", name)

    def download(name):
        resp = session.get(f"{base}/api/files/{name}", timeout=60)
        resp.raise_for_status()
        dest = saves / name
        archive(dest, backups, keep)
        atomic_write(dest, resp.content, float(resp.headers.get("X-Mtime", time.time())))
        state[name] = remote[name]["sha256"]
        log.info("downloaded %s", name)

    for name in sorted(set(local) | set(remote)):
        if name in in_flux:
            continue
        try:
            if name not in remote:
                upload(name)
            elif name not in local:
                download(name)
            else:
                l, r_ = local[name]["sha256"], remote[name]["sha256"]
                if l == r_:
                    state[name] = l
                    continue
                last = state.get(name)
                local_changed, remote_changed = l != last, r_ != last
                if local_changed and not remote_changed:
                    upload(name)
                elif remote_changed and not local_changed:
                    download(name)
                else:  # both changed (or never synced): newest wins, loser is backed up
                    if local[name]["mtime"] >= remote[name]["mtime"]:
                        log.warning("conflict on %s: keeping local (newer)", name)
                        upload(name)
                    else:
                        log.warning("conflict on %s: keeping server (newer); local copy backed up", name)
                        download(name)
        except OSError as e:  # e.g. file locked by the running game; retry next cycle
            log.warning("skipped %s: %s", name, e)


def run_client(args):
    import requests
    if not (args.server and args.token and args.saves):
        sys.exit("client mode needs --server, --token and --saves (or D2RSPCP_SERVER/TOKEN/SAVES)")
    saves = Path(args.saves)
    if not saves.is_dir():
        sys.exit(f"save folder not found: {saves}")
    config = Path(args.config)
    config.mkdir(parents=True, exist_ok=True)
    state_file = config / "state.json"
    state = json.loads(state_file.read_text()) if state_file.exists() else {}
    session = requests.Session()
    session.headers["Authorization"] = f"Bearer {args.token}"
    log.info("syncing %s <-> %s every %ss", saves, args.server, args.interval)
    while True:
        try:
            sync_once(session, args.server, saves, state, config / "backups", args.keep)
            state_file.write_text(json.dumps(state, indent=2))
        except requests.RequestException as e:
            log.warning("server unreachable: %s", e)
        if args.once:
            return
        time.sleep(args.interval)


# --------------------------------------------------------------------------- main
def main():
    env = os.environ.get
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("mode", nargs="?", choices=["server", "client"], default=env("D2RSPCP_MODE"))
    ap.add_argument("--token", default=env("D2RSPCP_TOKEN"), help="shared secret")
    ap.add_argument("--keep", type=int, default=int(env("D2RSPCP_KEEP", "20")), help="backup versions kept per file")
    ap.add_argument("--data", default=env("D2RSPCP_DATA", "/data"), help="[server] storage dir")
    ap.add_argument("--port", type=int, default=int(env("D2RSPCP_PORT", "8420")), help="[server] port")
    ap.add_argument("--server", default=env("D2RSPCP_SERVER"), help="[client] server URL")
    ap.add_argument("--saves", default=env("D2RSPCP_SAVES", "/saves"), help="[client] local D2R save folder")
    ap.add_argument("--config", default=env("D2RSPCP_CONFIG", "/config"), help="[client] state + backups dir")
    ap.add_argument("--interval", type=int, default=int(env("D2RSPCP_INTERVAL", "30")), help="[client] seconds between syncs")
    ap.add_argument("--once", action="store_true", help="[client] sync once and exit")
    ap.add_argument("-v", "--verbose", action="store_true")
    args = ap.parse_args()
    logging.basicConfig(level=logging.DEBUG if args.verbose else logging.INFO,
                        format="%(asctime)s %(levelname)s %(message)s")
    if not args.mode:
        ap.error("mode required (server|client) or set D2RSPCP_MODE")
    (run_server if args.mode == "server" else run_client)(args)


if __name__ == "__main__":
    main()
