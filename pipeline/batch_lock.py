#!/usr/bin/env python3
"""Batch numbers claimed in Drive, so two runs started at the same time never take the same number.

Every Slack / Claude DM run works in its own copy of the repo, so its ledger (data/batch_ledger.json) does not know a batch another
run planned a minute ago: both took B026. Now `plan` claims its number in the Drive folder "_Batch numbers (pipeline, do not edit)"
(data/batch_lock.json) before anything is made: the next number after every number in the ledger, in the Outputs batch folders and
in the claim files; it writes a claim file "B026 – <product> – <date> – <id>", waits a moment and lists the folder again. The
earliest file of a number owns it; a run that lost the race renames its file "LOST ..." (nothing is deleted) and claims the next
number. A redo (--batch-id B045, names B045r2) keeps its number and claims nothing.

`running()` lists the claims of the last hours whose batch is not in Drive yet: plan warns when another batch of the same product is
being made right now (its hooks and statics are not in the novelty log yet, so the two batches may share some).

  python3 pipeline/batch_lock.py show        the claims, newest first, and the next free number
"""
import contextlib
import datetime
import io
import json
import os
import re
import socket
import sys
import time
import uuid

HERE = os.path.dirname(os.path.abspath(__file__))
CFG = os.path.join(HERE, "data", "batch_lock.json")
API = "https://www.googleapis.com/drive/v3/files"
NUM = re.compile(r"^(?:LOST\s+)?B(\d{3})\b")
SETTLE = 2.5            # seconds between writing a claim and reading the folder again (Drive lists catch up)
LAST = {}               # what the last claim() saw: {"n", "file", "lost": [...], "running": [...]}


def drive():
    sys.path.insert(0, HERE)
    import drive_upload
    with contextlib.redirect_stdout(io.StringIO()):
        return drive_upload, drive_upload.access_token()


def folder_id():
    return json.load(open(CFG, encoding="utf-8"))["folder"]


def claims(du, tok, fid):
    """The claim files, oldest first: [{id, name, createdTime, n, lost}]."""
    out = []
    for f in du.list_children(tok, fid):
        m = NUM.match(f.get("name") or "")
        if m:
            out.append(dict(f, n=int(m.group(1)), lost=f["name"].startswith("LOST")))
    return sorted(out, key=lambda f: (f.get("createdTime") or "", f["id"]))


def batch_folders(du, tok):
    """Numbers of the batch folders in Drive Outputs, Outputs/Winners and Outputs/New Products."""
    outputs = du.load_config()["drive"]["outputs_folder"]
    tops = du.list_children(tok, outputs)
    names = [f["name"] for f in tops]
    for f in tops:
        if f.get("mimeType", "").endswith("folder") and f["name"] in ("Winners", "New Products"):
            names += [g["name"] for g in du.list_children(tok, f["id"])]
    return {int(m.group(1)) for x in names for m in [re.match(r"^B(\d{3})", x)] if m}


def create(du, tok, fid, name, desc):
    body = json.dumps({"name": name, "parents": [fid], "mimeType": "text/plain", "description": desc}).encode()
    with du.api("POST", f"{API}?supportsAllDrives=true&fields=id,name,createdTime", tok, data=body,
                headers={"Content-Type": "application/json"}) as r:
        return json.loads(r.read())


def rename(du, tok, file_id, name):
    with du.api("PATCH", f"{API}/{file_id}?supportsAllDrives=true&fields=id,name", tok, data=json.dumps({"name": name}).encode(),
                headers={"Content-Type": "application/json"}) as r:
        return json.loads(r.read())


def running(du, tok, fid, done, hours=8, now=None):
    """Claims of the last `hours` whose batch is not in Drive yet (`done`: numbers with a folder): batches being made now."""
    now = now or datetime.datetime.now(datetime.timezone.utc)
    out = []
    for c in claims(du, tok, fid):
        try:
            t = datetime.datetime.fromisoformat(c["createdTime"].replace("Z", "+00:00"))
        except (KeyError, ValueError):
            continue
        if not c["lost"] and c["n"] not in done and (now - t).total_seconds() < hours * 3600:
            out.append(dict(n=c["n"], name=c["name"], created=c["createdTime"]))
    return out


def claim(local_next, product="", request="", theme="", pipeline="", du=None, tok=None, settle=None, tries=25):
    """The batch number this run owns: >= local_next, after every number Drive knows. Raises when Drive can't be used."""
    if du is None:
        du, tok = drive()
    fid = folder_id()
    settle = SETTLE if settle is None else settle
    lost = []
    done = batch_folders(du, tok)
    for _ in range(tries):
        cs = claims(du, tok, fid)
        n = max([local_next - 1] + sorted(done) + [c["n"] for c in cs]) + 1
        day = datetime.date.today().isoformat()
        name = f"B{n:03d} – {product or 'batch'} – {day} – {socket.gethostname()[:12]}-{uuid.uuid4().hex[:6]}"
        mine = create(du, tok, fid, name, json.dumps(dict(product=product, theme=theme, pipeline=pipeline, request=request[:500]),
                                                     ensure_ascii=False))
        time.sleep(settle)
        same = [c for c in claims(du, tok, fid) if c["n"] == n and not c["lost"]]
        owner = same[0] if same else None
        if owner and owner["id"] == mine["id"]:
            LAST.clear()
            LAST.update(n=n, file=name, lost=lost, running=[r for r in running(du, tok, fid, done) if r["n"] != n])
            return n
        rename(du, tok, mine["id"], "LOST " + name)
        lost.append(n)
    raise RuntimeError(f"could not claim a batch number after {tries} tries (lost {lost})")


def main():
    du, tok = drive()
    fid = folder_id()
    cs = claims(du, tok, fid)
    done = batch_folders(du, tok)
    for c in reversed(cs[-30:]):
        print(f"{c['createdTime'][:16]}  {c['name']}" + ("" if c["lost"] else "" if c["n"] in done else "   (not in Drive yet)"))
    print("next free number: B%03d" % (max([0] + sorted(done) + [c["n"] for c in cs]) + 1))
    return 0


if __name__ == "__main__":
    sys.exit(main())
