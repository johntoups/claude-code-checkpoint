#!/usr/bin/env python3
"""Checkpoint bookkeeping, so the model only writes content.

  checkpoint.py new <name> "<one-line topic>"   create <name>.md from the template, add the register row
  checkpoint.py finish <name> --out DIR [--no-git] [--force]
        apply markers and caps (moving items to <name>.archive.md), stamp the time, update the
        register row, render to DIR/<name>.html, commit only this session's files, push.
        Prints PUBLISH=no and does nothing when the files are unchanged since the last commit.
  checkpoint.py set-url <name> <url> --out DIR [--no-git]   record the artifact URL after the first publish

Markers, written at the start of a list item's text:
  [done]        Up next or Waiting on item finished     -> archive "Done", dated
  [superseded]  Decision replaced by a later decision   -> archive "Decisions"
  [obsolete]    Trap no longer applies                  -> archive "Traps"
  [resolved]    Unverified item settled                 -> archive "Unverified"
  [pinned]      Fact kept in view regardless of the cap
Caps: Facts in view 15 (oldest unpinned move first); Recent sessions 5.
"""
import datetime, os, re, subprocess, sys

HERE = os.path.dirname(os.path.realpath(__file__))
REG = os.path.dirname(HERE)
README = os.path.join(REG, "README.md")
FACTS_CAP, RECENT_CAP = 15, 5
ARCH_ORDER = ["Done", "Facts", "Decisions", "Traps", "Unverified", "Recent sessions"]
now = datetime.datetime.now()
TODAY, STAMP = now.strftime("%Y-%m-%d"), now.strftime("%Y-%m-%d %H:%M")

def die(msg): print("ERROR: " + msg); sys.exit(1)
def safe(name):
    if not name or re.search(r"[/:\\]", name) or name.startswith("."): die(f"session name {name!r} is not filename-safe; /rename first")
def git(*a, check=True):
    return subprocess.run(["git", "-C", REG, *a], capture_output=True, text=True, check=check).stdout

def parse(text):
    """-> (preamble_lines, [(heading, [lines])], trailer_lines). Trailer starts at the final '---'."""
    lines = text.split("\n")
    trailer = []
    for i in range(len(lines) - 1, -1, -1):
        if lines[i].strip() == "---": trailer, lines = lines[i:], lines[:i]; break
    pre, secs, cur = [], [], None
    for ln in lines:
        if ln.startswith("## "): cur = (ln[3:].strip(), []); secs.append(cur)
        elif cur is None: pre.append(ln)
        else: cur[1].append(ln)
    return pre, secs, trailer
def unparse(pre, secs, trailer):
    out = pre[:]
    for h, body in secs: out += [f"## {h}"] + body
    return "\n".join(out + trailer)
ITEM = re.compile(r"^(\s*)(\d+\.|-)\s+(.*)$")
def get(secs, name):
    for h, b in secs:
        if h.lower() == name.lower(): return b
    return None

def register_rows():
    return open(README, encoding="utf-8").read().split("\n")
def find_row(lines, name):
    for i, ln in enumerate(lines):
        cells = [c.strip() for c in ln.strip().strip("|").split("|")]
        if ln.startswith("|") and len(cells) >= 5 and cells[0].lower() == name.lower(): return i, cells
    return None, None
def set_row(name, **kw):
    lines = register_rows(); i, cells = find_row(lines, name)
    if i is None: die(f"{name} is not in the register; run new first")
    for k, v in kw.items(): cells[{"topic": 1, "url": 3, "date": 4}[k]] = v
    lines[i] = "| " + " | ".join(cells) + " |"
    open(README, "w", encoding="utf-8").write("\n".join(lines))

def cmd_new(name, topic):
    safe(name)
    lines = register_rows()
    if find_row(lines, name)[0] is not None: die(f"{name} is already registered (case-insensitive); rejoin it instead")
    path = os.path.join(REG, name + ".md")
    if os.path.exists(path): die(f"{path} already exists")
    t = open(os.path.join(HERE, "TEMPLATE.md"), encoding="utf-8").read()
    owner = os.environ.get("CHECKPOINT_OWNER") or (git("config", "user.name", check=False).split() or ["Me"])[0]
    t = (t.replace("{{OWNER}}", owner).replace("{{SESSION}}", name).replace("{{ONE_LINE_TOPIC}}", topic).replace("{{DATE}} {{TIME}}", STAMP)
          .replace("{{DATE}}", TODAY).replace("{{ARTIFACT_URL}}", "not yet published"))
    open(path, "w", encoding="utf-8").write(t)
    lines.append(f"| {name} | {topic} | {name}.md | — | {TODAY} |")
    open(README, "w", encoding="utf-8").write("\n".join(lines).rstrip("\n") + "\n")
    print(f"CREATED={path}\nNEXT=fill the sections, then: checkpoint.py finish {name} --out <scratchpad>/checkpoint-render")

def apply_rules(name):
    path = os.path.join(REG, name + ".md")
    pre, secs, trailer = parse(open(path, encoding="utf-8").read())
    apath = os.path.join(REG, name + ".archive.md")
    if os.path.exists(apath): apre, asecs, atr = parse(open(apath, encoding="utf-8").read())
    else:
        apre = [f"# {name} archive", "", f"Items moved out of view from `{name}.md`. Append only. Rendered collapsed at the bottom of the checkpoint page.", ""]
        asecs, atr = [], []
    moved = {}
    def arch_add(sec, line, top=False):
        b = get(asecs, sec)
        if b is None: b = []; asecs.append((sec, b))
        items = [l for l in b if l.strip()]
        items = [line] + items if top else items + [line]
        b[:] = items + [""]
        moved[sec] = moved.get(sec, 0) + 1
    def take(secname, marker, dest, fmt):
        b = get(secs, secname)
        if b is None: return
        keep = []
        for ln in b:
            m = ITEM.match(ln)
            if m and m.group(3).lower().startswith(marker):
                arch_add(dest, "- " + fmt(m.group(3)[len(marker):].strip()))
            else: keep.append(ln)
        b[:] = keep
    take("Up next", "[done]", "Done", lambda t: f"{TODAY}: {t}")
    take("Waiting on", "[done]", "Done", lambda t: f"{TODAY}: {t}")
    take("Decisions", "[superseded]", "Decisions", lambda t: f"{t} (superseded {TODAY})")
    take("Traps", "[obsolete]", "Traps", lambda t: f"{t} (obsolete {TODAY})")
    take("Unverified", "[resolved]", "Unverified", lambda t: f"{t} (resolved {TODAY})")
    b = get(secs, "Facts")
    if b is not None:
        idx = [i for i, ln in enumerate(b) if ITEM.match(ln)]
        excess = len(idx) - FACTS_CAP
        drop = [i for i in idx if "[pinned]" not in b[i]][:max(0, excess)]
        for i in drop: arch_add("Facts", b[i].strip())
        b[:] = [ln for i, ln in enumerate(b) if i not in drop]
    b = get(secs, "Recent sessions")
    if b is not None:
        idx = [i for i, ln in enumerate(b) if ITEM.match(ln)]
        over = idx[RECENT_CAP:]
        for i in reversed(over): arch_add("Recent sessions", b[i].strip(), top=True)
        b[:] = [ln for i, ln in enumerate(b) if i not in over]
    open(path, "w", encoding="utf-8").write(unparse(pre, secs, trailer))
    if moved:
        asecs.sort(key=lambda s: ARCH_ORDER.index(s[0]) if s[0] in ARCH_ORDER else 99)
        open(apath, "w", encoding="utf-8").write(unparse(apre, asecs, atr).rstrip("\n") + "\n")
    return path, apath, moved

def stamp(path):
    s = open(path, encoding="utf-8").read()
    s = re.sub(r"(\*\*Checkpoint:\*\*\s*)[^·\n]*?(\s*·|\s*$)", lambda m: m.group(1) + STAMP + m.group(2), s, count=1, flags=re.M)
    open(path, "w", encoding="utf-8").write(s)

def render(name, out):
    os.makedirs(out, exist_ok=True)
    dst = os.path.join(out, name + ".html")
    subprocess.run([sys.executable, os.path.join(HERE, "render.py"), os.path.join(REG, name + ".md"), dst], check=True, capture_output=True)
    return dst

def files(name):
    return [f for f in (name + ".md", name + ".archive.md", "README.md") if os.path.exists(os.path.join(REG, f))]

def commit(name, msg, nogit):
    if nogit: return "skipped (--no-git)"
    fs = files(name)
    git("add", "--", *fs)
    if not git("diff", "--cached", "--name-only", "--", *fs).strip(): return "nothing to commit"
    git("commit", "-q", "-m", msg, "--", *fs)
    sha = git("log", "-1", "--format=%h").strip()
    # Push only if every unpushed commit stays inside the register folder. Anything else ahead
    # belongs to other work; pushing it is the user's call, so hold and name it.
    subprocess.run(["git", "-C", REG, "fetch", "-q"], capture_output=True)
    upstream = git("rev-parse", "--abbrev-ref", "--symbolic-full-name", "@{u}", check=False).strip()
    if not upstream: return f"{sha} committed, PUSH FAILED: the register branch has no upstream (git push -u origin <branch> once)"
    prefix = git("rev-parse", "--show-prefix").strip()   # "" when the register is the repo root
    ahead = [c for c in git("rev-list", f"{upstream}..HEAD", check=False).split() if c]
    foreign = []
    for c in ahead:
        touched = git("show", "--name-only", "--format=", c).split()
        if any(not t.startswith(prefix) for t in touched):
            foreign.append(git("log", "-1", "--format=%h %s", c).strip())
    if foreign:
        return f"{sha} committed, PUSH HELD: {len(foreign)} unpushed commit(s) outside the register would go with it: " + "; ".join(foreign)
    r = subprocess.run(["git", "-C", REG, "push", "-q", "origin", "HEAD"], capture_output=True, text=True)
    return f"{sha} pushed ({len(ahead)} checkpoint commit(s))" if r.returncode == 0 else f"{sha} committed, PUSH FAILED: {r.stderr.strip()}"

def url_of(name):
    _, cells = find_row(register_rows(), name)
    return cells[3] if cells and cells[3].startswith("http") else ""

def cmd_finish(name, out, nogit, force):
    safe(name)
    if find_row(register_rows(), name)[0] is None: die(f"{name} is not in the register; run new first")
    path, apath, moved = apply_rules(name)
    rel = [os.path.relpath(p, REG) for p in (path, apath) if os.path.exists(p)]
    changed = force or nogit or bool(git("status", "--porcelain", "--", *rel).strip())
    if not changed:
        print(f"PUBLISH=no\nREASON=no changes since the last committed checkpoint\nURL={url_of(name)}"); return
    stamp(path); set_row(name, date=TODAY)
    html_path = render(name, out)
    res = commit(name, f"checkpoint: {name} {STAMP}", nogit)
    url = url_of(name)
    print(f"PUBLISH=yes\nHTML={html_path}\nURL={url or 'none yet: first publish, pass an icon, then run set-url'}\nMOVED={moved or 'nothing'}\nGIT={res}")

def cmd_set_url(name, url, out, nogit):
    path = os.path.join(REG, name + ".md")
    s = open(path, encoding="utf-8").read()
    s = re.sub(r"(\*\*Artifact:\*\*\s*)\S.*?$", lambda m: m.group(1) + url, s, count=1, flags=re.M)
    open(path, "w", encoding="utf-8").write(s); set_row(name, url=url)
    html_path = render(name, out)
    print(f"PUBLISH=yes\nHTML={html_path}\nURL={url}\nGIT={commit(name, f'checkpoint: {name} artifact url', nogit)}")

if __name__ == "__main__":
    a = sys.argv[1:]
    opt = lambda f: (a.pop(a.index(f) + 1), a.remove(f))[0] if f in a else None
    flag = lambda f: (a.remove(f), True)[1] if f in a else False
    out, nogit, force = opt("--out"), flag("--no-git"), flag("--force")
    if not a: print(__doc__); sys.exit(1)
    if a[0] == "new" and len(a) == 3: cmd_new(a[1], a[2])
    elif a[0] == "finish" and len(a) == 2 and out: cmd_finish(a[1], out, nogit, force)
    elif a[0] == "set-url" and len(a) == 3 and out: cmd_set_url(a[1], a[2], out, nogit)
    else: print(__doc__); sys.exit(1)
