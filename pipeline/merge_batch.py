#!/usr/bin/env python3
"""Merge a Slack / Claude DM run's batch branch into the default branch, so the next run sees its batch number, ads and hooks.

The GitHub Action .github/workflows/merge-batches.yml runs this at every push of a claude/* branch; by hand:

  python3 pipeline/merge_batch.py claude/bf-3piece-4v-10s-2026-10-25 [--push] [--dry-run]

Only a branch whose changes are batch output is merged by itself: specs under pipeline/recipes/, the ledger, docs/BATCHES.md,
the novelty log, product files, clip_index.json / clip_bank.json. A branch that changes anything else (code, docs) is left for a
person (exit 0 with a warning). The data files both sides changed are merged entry by entry against the merge base: the ledger
by batch, the novelty log by product and batch (the branch's version wins where both changed one entry); docs/BATCHES.md is
rebuilt from the merged ledger. Any other conflict stops the merge and nothing is pushed (exit 1).
"""
import argparse
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
DEFAULT = "claude/loving-meitner-4amjii"
LEDGER, NOVELTY, BATCHES_MD = "pipeline/data/batch_ledger.json", "pipeline/data/novelty_log.json", "docs/BATCHES.md"
ALLOWED = re.compile(r"^(pipeline/recipes/|pipeline/data/(batch_ledger|novelty_log|clip_index|clip_bank)\.json$"
                     r"|pipeline/data/products/[^/]+\.json$|docs/BATCHES\.md$)")


class Stop(Exception):
    pass


def git(cwd, *a, check=True):
    r = subprocess.run(["git", *a], cwd=cwd, capture_output=True, text=True)
    if check and r.returncode:
        raise Stop(f"git {' '.join(a)}: {r.stderr.strip() or r.stdout.strip()}")
    return r.stdout


def show_json(cwd, rev, path, empty):
    r = subprocess.run(["git", "show", f"{rev}:{path}"], cwd=cwd, capture_output=True, text=True)
    return json.loads(r.stdout) if r.returncode == 0 and r.stdout.strip() else empty


def pick(b, o, t):
    """3-way value: the side that changed it; both changed: the branch's (t). An entry only one side has is kept."""
    if o == t or t is None:
        return o
    if o is None or o == b:
        return t
    return o if t == b else t


def merge_ledger(base, ours, theirs):
    key = lambda x: (x["n"], x.get("rev", 1))          # noqa: E731
    B, O, T = ({key(x): x for x in d.get("batches") or []} for d in (base, ours, theirs))
    batches = [pick(B.get(k), O.get(k), T.get(k)) for k in sorted(set(O) | set(T))]
    nxt = max([ours.get("next") or 0, theirs.get("next") or 0] + [b["n"] + 1 for b in batches])
    return dict(ours, batches=batches, next=nxt)


def merge_novelty(base, ours, theirs):
    out = {k: v for k, v in ours.items() if k != "products"}
    out.update({k: v for k, v in theirs.items() if k not in out and k != "products"})
    prods = {}
    bp, op, tp = (d.get("products") or {} for d in (base, ours, theirs))
    for slug in list(op) + [s for s in tp if s not in op]:
        o, t, b = op.get(slug) or {}, tp.get(slug) or {}, bp.get(slug) or {}
        B, O, T = ({x.get("name"): x for x in d.get("batches") or []} for d in (b, o, t))
        names = [x.get("name") for x in o.get("batches") or []] + [x.get("name") for x in t.get("batches") or [] if x.get("name") not in O]
        prods[slug] = dict(o or t, batches=[pick(B.get(n), O.get(n), T.get(n)) for n in names])
    out["products"] = prods
    return out


def batches_md(work, ledger_d):
    sys.path.insert(0, os.path.join(work, "pipeline"))
    import importlib
    import ledger
    importlib.reload(ledger)
    path = os.path.join(work, BATCHES_MD)
    old = open(path, encoding="utf-8").read() if os.path.exists(path) else ""
    if old.startswith("<<<<<<<") or "| Batch |" not in old:
        old = git(work, "show", f"HEAD:{BATCHES_MD}", check=False)
    pre = old[:old.index("| Batch |")] if "| Batch |" in old else "# Batches (B-numbers)\n\n"
    return pre + ledger.table(ledger_d)


def dump(path, d):
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(d, fh, indent=1, ensure_ascii=False)
        fh.write("\n")


def merge(branch, repo=ROOT, default=DEFAULT, remote="origin", push=False, dry=False, fetch=True, say=print):
    """-> {status: merged | already | skipped (changes outside batch output), commit}; raises Stop on a conflict it can't settle."""
    if fetch:
        git(repo, "fetch", "-q", remote, default, branch.removeprefix(f"{remote}/"))
    pre = f"{remote}/" if remote else ""
    ref = branch if not remote or branch.startswith(pre) else pre + branch
    dref = pre + default
    if subprocess.run(["git", "merge-base", "--is-ancestor", ref, dref], cwd=repo).returncode == 0:
        say(f"{branch}: already in {default}")
        return dict(status="already")
    base = git(repo, "merge-base", ref, dref).strip()
    changed = [p for p in git(repo, "diff", "--name-only", base, ref).splitlines() if p]
    outside = [p for p in changed if not ALLOWED.match(p)]
    if outside:
        say(f"::warning::{branch}: not merged by itself, it changes more than batch output: {', '.join(outside[:8])}"
            f"{' …' if len(outside) > 8 else ''}")
        return dict(status="skipped", outside=outside)
    work = tempfile.mkdtemp(prefix="merge_batch_")
    try:
        git(repo, "worktree", "add", "-q", "--detach", work, dref)
        r = subprocess.run(["git", "merge", "--no-ff", "--no-commit", ref], cwd=work, capture_output=True, text=True)
        conflicts = [p for p in git(work, "diff", "--name-only", "--diff-filter=U").splitlines() if p]
        if r.returncode and not conflicts:
            raise Stop(f"git merge failed: {r.stderr.strip() or r.stdout.strip()}")
        bad = [p for p in conflicts if p not in (LEDGER, NOVELTY, BATCHES_MD)]
        if bad:
            raise Stop(f"conflicts outside the ledger / novelty log: {', '.join(bad)}")
        led = None
        if LEDGER in changed or LEDGER in conflicts:
            led = merge_ledger(show_json(repo, base, LEDGER, {}), show_json(repo, dref, LEDGER, {}), show_json(repo, ref, LEDGER, {}))
            dump(os.path.join(work, LEDGER), led)
        if NOVELTY in conflicts:
            dump(os.path.join(work, NOVELTY), merge_novelty(show_json(repo, base, NOVELTY, {}), show_json(repo, dref, NOVELTY, {}),
                                                            show_json(repo, ref, NOVELTY, {})))
        if led is not None or BATCHES_MD in conflicts:
            led = led or json.load(open(os.path.join(work, LEDGER), encoding="utf-8"))
            open(os.path.join(work, BATCHES_MD), "w", encoding="utf-8").write(batches_md(work, led))
        for p in (LEDGER, NOVELTY):
            if os.path.exists(os.path.join(work, p)):
                json.load(open(os.path.join(work, p), encoding="utf-8"))            # valid JSON, or stop
        git(work, "add", "-A")
        ids = sorted(set(re.findall(r"_(B\d{3}(?:r\d+)?)_", " ".join(changed))))
        msg = (f"Merge {branch.removeprefix(pre)} into {default}" + (f" ({', '.join(ids)})" if ids else "")
               + "\n\nBatch output only (specs, ledger, novelty log); merged by pipeline/merge_batch.py.")
        git(work, "commit", "-q", "-m", msg)
        sha = git(work, "rev-parse", "HEAD").strip()
        if dry:
            say(f"{branch}: would merge {len(changed)} file(s) {ids} (dry run)")
            return dict(status="merged", commit=sha, batches=ids, dry_run=True)
        if push:
            git(work, "push", "-q", remote, f"HEAD:{default}")
        else:
            say(f"(merged in a scratch worktree only: --push sends it to {default})")
        say(f"{branch}: merged into {default} {ids}")
        return dict(status="merged", commit=sha, batches=ids)
    finally:
        subprocess.run(["git", "merge", "--abort"], cwd=work, capture_output=True)
        subprocess.run(["git", "worktree", "remove", "--force", work], cwd=repo, capture_output=True)
        shutil.rmtree(work, ignore_errors=True)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("branch")
    ap.add_argument("--push", action="store_true")
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--default", default=DEFAULT)
    a = ap.parse_args()
    if a.branch.removeprefix("origin/") == a.default:
        print("the default branch itself: nothing to merge")
        return 0
    for attempt in range(3):            # the default branch moved while merging: fetch and merge again
        try:
            merge(a.branch, default=a.default, push=a.push, dry=a.dry_run)
            return 0
        except Stop as e:
            if "rejected" in str(e) or "fetch first" in str(e) or "non-fast-forward" in str(e):
                continue
            print(f"::error::{a.branch}: not merged: {e}")
            return 1
    print(f"::error::{a.branch}: not merged: the default branch kept moving")
    return 1


if __name__ == "__main__":
    sys.exit(main())
