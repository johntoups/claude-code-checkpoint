#!/usr/bin/env python3
"""Checkpoint bookkeeping, so the model only writes content.

  checkpoint.py new <name> "<one-line topic>" [--kind game --system <id>]
        create <name>.md from the template, add the register row. With no --kind, the nearest
        .claude/checkpoint.json above the working directory may name one for this session
        (see kinds/README.md). Default kind: work (TEMPLATE.md).
  checkpoint.py finish <name> --out DIR [--no-git] [--force]
        apply markers and caps (moving items to <name>.archive.md), stamp the time, update the
        register row, render to DIR/<name>.html, commit only this session's files, push.
        Prints PUBLISH=no and does nothing when the files are unchanged since the last commit.
  checkpoint.py set-url <name> <url> --out DIR [--no-git]   record the artifact URL after the first publish
  checkpoint.py patch <name> <spec.json|-> [--finish --out DIR]
        apply one structured edit (JSON; see the skill) to <name>.md, all or nothing, then optionally finish.
        Keys: now, next, next_game, session, glance{Label: value|null}, add{Section:[...]}, mark[[Section, match, marker]],
        edit[[Section, match, new text]], section{Section: body}. A match must hit exactly one item.

Markers, written at the start of a list item's text:
  [done]        Up next or Waiting on item finished     -> archive "Done", dated
  [superseded]  Decision replaced by a later decision   -> archive "Decisions"
  [obsolete]    Trap no longer applies                  -> archive "Traps"
  [resolved]    Unverified item settled                 -> archive "Unverified"
                Threads item resolved (game kind)       -> archive "Resolved threads"
  [done]        Between games item finished (game kind) -> archive "Done"
  [superseded]  Table ruling replaced (game kind)       -> archive "Superseded rulings"
  [pinned]      Fact kept in view regardless of the cap
Caps: Facts in view 15 (oldest unpinned move first); Recent sessions 5 distinct days. The game Adventure log is never capped.\nfinish also prints WARN= lines for oversize items and sections; it never cuts content.
"""
import datetime, json, os, re, subprocess, sys

HERE = os.path.dirname(os.path.realpath(__file__))
REG = os.path.dirname(HERE)
README = os.path.join(REG, "README.md")
FACTS_CAP, RECENT_CAP = 15, 5
ARCH_ORDER = ["Done", "Resolved threads", "Facts", "Decisions", "Superseded rulings", "Traps", "Unverified", "Recent sessions"]
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
    return open(README, encoding="utf-8").read().rstrip("\n").split("\n")
def write_register(lines):
    """Write the README with the session table contiguous: a blank line inside a Markdown table ends it."""
    out = []
    for i, ln in enumerate(lines):
        nxt = next((l for l in lines[i + 1:] if l.strip()), "")
        if not ln.strip() and out and out[-1].startswith("|") and nxt.startswith("|"): continue
        out.append(ln)
    open(README, "w", encoding="utf-8").write("\n".join(out).rstrip("\n") + "\n")
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
    write_register(lines)

def project_kind(name):
    """Walk up from the working directory to the nearest .claude/checkpoint.json and return
    (kind, system) for this session name, or (None, None). Format in kinds/README.md."""
    d = os.getcwd()
    while True:
        f = os.path.join(d, ".claude", "checkpoint.json")
        if os.path.exists(f):
            cfg = json.load(open(f, encoding="utf-8"))
            s = {k.lower(): v for k, v in cfg.get("sessions", {}).items()}.get(name.lower(), {})
            return s.get("kind", cfg.get("kind")), s.get("system")
        if os.path.dirname(d) == d: return None, None
        d = os.path.dirname(d)

def cmd_new(name, topic, kind=None, system=None):
    safe(name)
    if not kind:
        kind, psys = project_kind(name); system = system or psys
    kind = kind or "work"
    tpl = os.path.join(HERE, "TEMPLATE.md") if kind == "work" else os.path.join(HERE, "kinds", kind, "TEMPLATE.md")
    if not os.path.exists(tpl): die(f"no template for kind {kind!r} ({tpl})")
    if kind != "work" and not system: die(f"kind {kind!r} needs --system <id>, or a system for {name!r} in .claude/checkpoint.json")
    lines = register_rows()
    if find_row(lines, name)[0] is not None: die(f"{name} is already registered (case-insensitive); rejoin it instead")
    path = os.path.join(REG, name + ".md")
    if os.path.exists(path): die(f"{path} already exists")
    t = open(tpl, encoding="utf-8").read()
    owner = os.environ.get("CHECKPOINT_OWNER") or (git("config", "user.name", check=False).split() or ["Me"])[0]
    t = (t.replace("{{OWNER}}", owner).replace("{{SESSION}}", name).replace("{{SYSTEM}}", system or "").replace("{{ONE_LINE_TOPIC}}", topic).replace("{{DATE}} {{TIME}}", STAMP)
          .replace("{{DATE}}", TODAY).replace("{{ARTIFACT_URL}}", "not yet published"))
    if kind == "game":
        sf = os.path.join(HERE, "kinds", "game", "systems", f"{system}.json")
        sd = json.load(open(sf, encoding="utf-8")) if os.path.exists(sf) else {}
        fields = sd.get("identity", ["Name"]) + sd.get("stats", []) + sd.get("tracks", []) + ["As of"]
        t = t.replace("{{SHEET}}", "\n".join(f"- **{f}:** " + ("Session 0" if f == "As of" else "?") for f in fields))
    open(path, "w", encoding="utf-8").write(t)
    lines.append(f"| {name} | {topic} | {name}.md | — | {TODAY} |")
    write_register(lines)
    print(f"CREATED={path}\nKIND={kind}" + (f"/{system}" if system else "") + f"\nNEXT=fill the sections, then: checkpoint.py finish {name} --out <scratchpad>/checkpoint-render")

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
    # game kind; absent sections are a no-op
    take("Between games", "[done]", "Done", lambda t: f"{TODAY}: {t}")
    take("Threads", "[resolved]", "Resolved threads", lambda t: f"{t} (resolved {TODAY})")
    take("Table rulings", "[superseded]", "Superseded rulings", lambda t: f"{t} (superseded {TODAY})")
    b = get(secs, "Facts")
    if b is not None:
        idx = [i for i, ln in enumerate(b) if ITEM.match(ln)]
        excess = len(idx) - FACTS_CAP
        drop = [i for i in idx if "[pinned]" not in b[i]][:max(0, excess)]
        for i in drop: arch_add("Facts", b[i].strip())
        b[:] = [ln for i, ln in enumerate(b) if i not in drop]
    b = get(secs, "Recent sessions")
    if b is not None:
        # keep the newest RECENT_CAP distinct days (several entries on one day count once); undated items count as their own day
        idx = [i for i, ln in enumerate(b) if ITEM.match(ln)]
        days, over = [], []
        for i in idx:
            d = re.match(r"(\d{4}-\d{2}-\d{2})", ITEM.match(b[i]).group(3))
            key = d.group(1) if d else f"#{i}"
            if key not in days: days.append(key)
            if len(days) > RECENT_CAP: over.append(i)
        for i in reversed(over): arch_add("Recent sessions", b[i].strip(), top=True)
        b[:] = [ln for i, ln in enumerate(b) if i not in over]
    for _, b in secs:
        # a blank line between two list items makes the Markdown list "loose"; drop it
        b[:] = [ln for i, ln in enumerate(b)
                if ln.strip() or not (any(ITEM.match(l) for l in b[i - 1:i] if i)
                                      and ITEM.match(next((l for l in b[i + 1:] if l.strip()), "")))]
    open(path, "w", encoding="utf-8").write(unparse(pre, secs, trailer))
    if moved:
        asecs.sort(key=lambda s: ARCH_ORDER.index(s[0]) if s[0] in ARCH_ORDER else 99)
        open(apath, "w", encoding="utf-8").write(unparse(apre, asecs, atr).rstrip("\n") + "\n")
    return path, apath, moved

ITEM_MAX, NOW_MAX, UPNEXT_MAX, FILE_MAX, REVIEW_AT = 500, 1200, 6000, 30000, 25
def size_report(path):
    """Warnings only; nothing is moved or cut. The writer decides what to tighten."""
    text = open(path, encoding="utf-8").read(); _, secs, _ = parse(text); warn = []; long = []
    for h, b in secs:
        n = sorted((len(ITEM.match(l).group(3)) for l in b if ITEM.match(l) and len(ITEM.match(l).group(3)) > ITEM_MAX), reverse=True)
        if n: long.append(f"{h} {len(n)} (max {n[0]})")
    if long: warn.append(f"items over {ITEM_MAX} chars: " + ", ".join(long) + "; one or two sentences each, detail in a linked doc")
    now = get(secs, "Now")
    if now is not None:
        state = "\n".join(l for l in now if not l.startswith("**Next"))
        if len(state.strip()) > NOW_MAX: warn.append(f"Now: {len(state.strip())} chars of state (budget {NOW_MAX}); two or three sentences")
    up = get(secs, "Up next")
    if up is not None and len("\n".join(up)) > UPNEXT_MAX: warn.append(f"Up next: {len(chr(10).join(up))} bytes (budget {UPNEXT_MAX})")
    for h in ("Traps", "Decisions"):
        b = get(secs, h)
        n = len([l for l in b if ITEM.match(l)]) if b else 0
        if n > REVIEW_AT: warn.append(f"{h}: {n} items; review for [obsolete] / [superseded] (never by age)")
    if len(text) > FILE_MAX: warn.append(f"file: {len(text)} bytes (budget {FILE_MAX}); a resume reads all of it")
    return warn

# ---- patch: one structured edit instead of many hand edits ----
MARKERS = {"done", "superseded", "obsolete", "resolved", "pinned"}
SEQ_STATES = {"done", "now", "gated", "blocked", "todo"}   # Sequence steps: "[state]" or "[state: note]", replaced in place, never archived
DATED_SECS = {"decisions", "table rulings"}
def spans(b):
    """[(start, end)] of list items in a section body; an item runs to the next item, blank line or heading."""
    out, i = [], 0
    while i < len(b):
        if ITEM.match(b[i]):
            j = i + 1
            while j < len(b) and b[j].strip() and not ITEM.match(b[j]) and not b[j].startswith("#") and b[j][:1] in (" ", "\t"): j += 1
            out.append((i, j)); i = j
        else: i += 1
    return out
def find_item(b, sec, needle):
    hits = [(s, e) for s, e in spans(b) if needle.lower() in " ".join(b[s:e]).lower()]
    if len(hits) != 1:
        shown = "; ".join(ITEM.match(b[s]).group(3)[:70] for s, _ in hits[:5])
        die(f"{sec}: {len(hits)} items match {needle!r}" + (f" ({shown})" if hits else "") + "; nothing was written")
    return hits[0]
def sec_body(secs, name):
    b = get(secs, name)
    if b is None: die(f"no section {name!r} in this checkpoint; nothing was written")
    return b
def append_item(b, line, before_parked=False):
    stop = next((i for i, l in enumerate(b) if l.strip().lower() == "### parked"), len(b)) if before_parked else len(b)
    last = max([e for s, e in spans(b[:stop])] or [0])
    if last == 0:  # no items yet: after any leading prose, else at top
        last = next((i for i in range(stop - 1, -1, -1) if b[i].strip()), -1) + 1
        if last and b[last - 1].strip(): b.insert(last, ""); last += 1
    b.insert(last, line)
    if last + 1 >= len(b) or b[last + 1].strip(): b.insert(last + 1, "")

def cmd_patch(name, spec_file):
    safe(name)
    path = os.path.join(REG, name + ".md")
    if not os.path.exists(path): die(f"{path} does not exist")
    spec = json.load(sys.stdin if spec_file == "-" else open(spec_file, encoding="utf-8"))
    if not isinstance(spec, dict): die("patch spec must be a JSON object; nothing was written")
    pre, secs, trailer = parse(open(path, encoding="utf-8").read()); done = []
    def one_line(t, what):
        t = " ".join(str(t).split())
        if not t: die(f"{what}: empty text; nothing was written")
        return t
    if "now" in spec or "next" in spec or "next_game" in spec:
        b = sec_body(secs, "Now")
        keep = {k: next((l for l in b if l.startswith(f"**{k}:**")), None) for k in ("Next game", "Next step")}
        state = [l for l in b if l.strip() and not l.startswith("**Next")]
        if "now" in spec: state = [one_line(p, "now") for p in (spec["now"] if isinstance(spec["now"], list) else [spec["now"]])]
        if "next_game" in spec: keep["Next game"] = f"**Next game:** {one_line(spec['next_game'], 'next_game')}"
        if "next" in spec: keep["Next step"] = f"**Next step:** {one_line(spec['next'], 'next')}"
        nb = [""]
        for p in state: nb += [p, ""]
        for k in ("Next game", "Next step"):
            if keep[k]: nb += [keep[k], ""]
        b[:] = nb; done.append("Now")
    if "session" in spec:
        b = sec_body(secs, "Recent sessions")
        line = f"- {TODAY}: {one_line(spec['session'], 'session')}"
        today = [s for s, e in spans(b) if ITEM.match(b[s]).group(3).startswith(TODAY)]
        if today:
            s = today[0]; e = dict(spans(b))[s]; b[s:e] = [line]  # other same-day entries stay; the cap counts the day once
        else:
            first = spans(b)[0][0] if spans(b) else None
            if first is None: append_item(b, line)
            else: b.insert(first, line)
        done.append("Recent sessions")
    for sec, items in (spec.get("add") or {}).items():
        items = items if isinstance(items, list) else [items]
        if sec.lower() == "parked":
            b = sec_body(secs, "Up next")
            if not any(l.strip().lower() == "### parked" for l in b):
                while b and not b[-1].strip(): b.pop()
                b += ["", "### Parked", ""]
            for t in items:
                pk = next(i for i, l in enumerate(b) if l.strip().lower() == "### parked")
                tail = b[pk + 1:]; append_item(tail, f"- {one_line(t, 'Parked')}"); b[pk + 1:] = tail
            done.append(f"Parked +{len(items)}"); continue
        b = sec_body(secs, sec)
        if sec.lower() == "adventure log":  # game kind: raw Markdown blocks, each starting with a ### heading
            while b and not b[-1].strip(): b.pop()
            for t in items: b += ["", str(t).strip()]
            b.append(""); done.append(f"{sec} +{len(items)}"); continue
        for t in items:
            t = one_line(t, sec)
            if sec.lower() in DATED_SECS and not re.match(r"\d{4}-\d{2}-\d{2}", t): t = f"{TODAY}: {t}"
            if sec.lower() == "up next":
                nums = [int(m.group(2)[:-1]) for l in b if (m := ITEM.match(l)) and m.group(2).endswith(".")]
                append_item(b, f"{max(nums or [0]) + 1}. {t}", before_parked=True)
            else: append_item(b, f"- {t}")
        done.append(f"{sec} +{len(items)}")
    for sec, needle, marker in spec.get("mark") or []:
        if sec.lower() == "sequence":
            if marker.split(":")[0].strip().lower() not in SEQ_STATES: die(f"Sequence state {marker!r} is not one of {sorted(SEQ_STATES)}; nothing was written")
            b = sec_body(secs, sec); s, _ = find_item(b, sec, needle); m = ITEM.match(b[s])
            txt = re.sub(r"^\[(?:" + "|".join(SEQ_STATES) + r")(?::[^\]]*)?\]\s*", "", m.group(3), flags=re.I)
            b[s] = f"{m.group(1)}{m.group(2)} [{marker.strip()}] {txt}"; done.append(f"Sequence [{marker.strip()}]"); continue
        if marker not in MARKERS: die(f"marker {marker!r} is not one of {sorted(MARKERS)}; nothing was written")
        b = sec_body(secs, sec); s, _ = find_item(b, sec, needle); m = ITEM.match(b[s])
        if not m.group(3).lower().startswith(f"[{marker}]"): b[s] = f"{m.group(1)}{m.group(2)} [{marker}] {m.group(3)}"
        done.append(f"{sec} [{marker}]")
    for sec, needle, new in spec.get("edit") or []:
        b = sec_body(secs, sec); s, e = find_item(b, sec, needle); m = ITEM.match(b[s])
        b[s:e] = [f"{m.group(1)}{m.group(2)} {one_line(new, sec)}"]; done.append(f"{sec} edited")
    if "glance" in spec:
        # "At a glance" (work) or "Sheet" (game): set, replace or (value null) remove items by label; created above Now
        name_g = "Sheet" if "**Kind:** game" in "\n".join(pre) else "At a glance"
        b = get(secs, name_g)
        if b is None:
            b = [""]; i = next((n for n, (h, _) in enumerate(secs) if h.lower() == "now"), 0); secs.insert(i, (name_g, b))
        for label, val in spec["glance"].items():
            hit = [(s, e) for s, e in spans(b) if re.match(rf"\s*-\s+\*\*{re.escape(label)}:\*\*", b[s], re.I)]
            if val is None:
                for s, e in reversed(hit): del b[s:e]
                continue
            line = f"- **{label}:** {one_line(val, label)}"
            if hit: s, e = hit[0]; b[s:e] = [line]
            else: append_item(b, line)
        if b and b[0].strip(): b.insert(0, "")
        done.append(f"{name_g} {len(spec['glance'])} field(s)")
    for sec, body in (spec.get("section") or {}).items():
        b = sec_body(secs, sec); b[:] = [""] + str(body).strip("\n").split("\n") + [""]; done.append(f"{sec} replaced")
    unknown = set(spec) - {"now", "next", "next_game", "session", "add", "mark", "edit", "section", "glance"}
    if unknown: die(f"unknown patch keys {sorted(unknown)}; nothing was written")
    open(path, "w", encoding="utf-8").write(unparse(pre, secs, trailer))
    print("PATCHED=" + (", ".join(done) or "nothing"))

def stamp(path):
    s = open(path, encoding="utf-8").read()
    s = re.sub(r"(\*\*Checkpoint:\*\*\s*)[^·\n]*?(\s*·|\s*$)", lambda m: m.group(1) + STAMP + m.group(2), s, count=1, flags=re.M)
    open(path, "w", encoding="utf-8").write(s)

def render(name, out):
    os.makedirs(out, exist_ok=True)
    dst = os.path.join(out, name + ".html")
    subprocess.run([sys.executable, os.path.join(HERE, "render.py"), os.path.join(REG, name + ".md"), dst], check=True, capture_output=True)
    return dst

def attachments(name):
    """<name>.<part>.md files beside the checkpoint (e.g. migration.facts.md): committed with it, listed on the page."""
    return sorted(f for f in os.listdir(REG) if f.startswith(name + ".") and f.endswith(".md") and f not in (name + ".md", name + ".archive.md"))
def files(name):
    return [f for f in (name + ".md", name + ".archive.md", *attachments(name), "README.md") if os.path.exists(os.path.join(REG, f))]

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
        touched = [t for t in git("show", "--name-only", "--format=", c).split("\n") if t.strip()]  # paths may contain spaces
        if any(not t.startswith(prefix) for t in touched):
            foreign.append(git("log", "-1", "--format=%h %s", c).strip())
    if foreign:
        return f"{sha} committed, PUSH HELD: {len(foreign)} unpushed commit(s) outside the register would go with it: " + "; ".join(foreign)
    r = subprocess.run(["git", "-C", REG, "push", "-q"], capture_output=True, text=True)
    return f"{sha} pushed ({len(ahead)} checkpoint commit(s))" if r.returncode == 0 else f"{sha} committed, PUSH FAILED: {r.stderr.strip()}"

def url_of(name):
    _, cells = find_row(register_rows(), name)
    return cells[3] if cells and cells[3].startswith("http") else ""

def cmd_finish(name, out, nogit, force):
    safe(name)
    if find_row(register_rows(), name)[0] is None: die(f"{name} is not in the register; run new first")
    path, apath, moved = apply_rules(name)
    rel = [os.path.relpath(p, REG) for p in (path, apath) if os.path.exists(p)] + attachments(name)
    changed = force or nogit or bool(git("status", "--porcelain", "--", *rel).strip())
    if not changed:
        print(f"PUBLISH=no\nREASON=no changes since the last committed checkpoint\nURL={url_of(name)}"); return
    stamp(path); set_row(name, date=TODAY)
    html_path = render(name, out)
    res = commit(name, f"checkpoint: {name} {STAMP}", nogit)
    url = url_of(name)
    print(f"PUBLISH=yes\nHTML={html_path}\nURL={url or 'none yet: first publish, pass icon, then run set-url'}\nMOVED={moved or 'nothing'}\nGIT={res}")
    for w in size_report(path): print("WARN=" + w)

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
    out, nogit, force, fin = opt("--out"), flag("--no-git"), flag("--force"), flag("--finish")
    kind, system = opt("--kind"), opt("--system")
    if not a: print(__doc__); sys.exit(1)
    if a[0] == "patch" and len(a) == 3:
        cmd_patch(a[1], a[2])
        if fin: cmd_finish(a[1], out, nogit, force) if out else die("--finish needs --out DIR")
    elif a[0] == "new" and len(a) == 3: cmd_new(a[1], a[2], kind, system)
    elif a[0] == "finish" and len(a) == 2 and out: cmd_finish(a[1], out, nogit, force)
    elif a[0] == "set-url" and len(a) == 3 and out: cmd_set_url(a[1], a[2], out, nogit)
    else: print(__doc__); sys.exit(1)
