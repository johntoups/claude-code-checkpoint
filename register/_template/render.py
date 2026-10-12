#!/usr/bin/env python3
"""Render a session checkpoint .md (plus its .archive.md, if present) into the
designed HTML artifact page. Usage: render.py <checkpoint.md> <out.html>
Design lives in checkpoint.css and shell.html beside this file."""
import html, os, re, subprocess, sys

HERE = os.path.dirname(os.path.realpath(__file__))
FOLD_AT = 12          # decisions and traps shown before older ones fold
strip = lambda s: re.sub(r"<[^>]+>", "", s).strip()
ALIAS = {"where-we-are": "now", "open-items": "up-next", "decisions-made": "decisions",
         "facts-established": "facts", "pointers": "references"}
# which archive section each view section points to, and the breadcrumb noun
CRUMB = {"up-next": ("done", "done items"), "facts": ("facts", "older facts"),
         "decisions": ("decisions", "superseded decisions"), "traps": ("traps", "obsolete traps"),
         "unverified": ("unverified", "resolved items"), "recent-sessions": ("recent-sessions", "older sessions"),
         "between-games": ("done", "done items"), "threads": ("resolved-threads", "resolved threads"),
         "table-rulings": ("superseded-rulings", "superseded rulings")}
ARCH_TITLES = {"done": "Done", "facts": "Facts", "decisions": "Superseded decisions",
               "traps": "Obsolete traps", "unverified": "Resolved unverified", "recent-sessions": "Older sessions",
               "resolved-threads": "Resolved threads", "superseded-rulings": "Superseded rulings"}
SYSTEMS = {"dragonbane": "Dragonbane", "traveller": "Traveller", "fengshui2": "Feng Shui 2", "cyberpunk_red": "Cyberpunk RED"}
# Sections each kind lays out itself. Anything else renders as a plain block, so a work section that happens to be
# called "Threads" or "Party" is never swallowed by the game layout.
WORK_SECS = {"now","waiting-on","traps","up-next","last-touched","recent-sessions","topic","decisions","facts","unverified","references"}
GAME_SECS = {"between-games","character","party","adventure-log","threads","npcs","table-rulings"}
SHARED_SECS = {"attachments","sequence","at-a-glance","sheet"}
SEQ_STATES = ("done", "now", "gated", "blocked", "todo")

def system_def(system):
    """kinds/game/systems/<system>.json: the sheet's identity, stat and track labels, in display order."""
    import json
    f = os.path.join(HERE, "kinds", "game", "systems", f"{system}.json")
    return json.load(open(f, encoding="utf-8")) if system and os.path.exists(f) else {}

WEEKDAY = re.compile(r"\b(?:Mon|Tues?|Wed(?:nes)?|Thu(?:rs)?|Fri|Sat(?:ur)?|Sun)(?:day)?\.?,?\s+(?=\d{4}-\d{2}-\d{2})", re.I)
def date_chip(txt):
    """First YYYY-MM-DD in the text becomes a weekday date chip."""
    import datetime as dt
    txt = WEEKDAY.sub("", txt, count=1)   # the chip carries the weekday
    m = re.search(r"\d{4}-\d{2}-\d{2}", txt)
    if not m: return txt
    try: d = dt.date.fromisoformat(m.group(0))
    except ValueError: return txt
    chip = f'<time class="gdate" datetime="{m.group(0)}">{d.strftime("%a %d %b %Y")}</time>'
    return txt[:m.start()] + chip + txt[m.end():]

def pandoc(md):
    return subprocess.run(["pandoc", "-f", "gfm", "-t", "html", "--wrap=none"],
                          input=md, capture_output=True, text=True, check=True).stdout

def decorate(h):
    h = re.sub(r"<strong>needs (\w+)</strong>", r'<span class="chip">needs \1</span>', h)
    h = h.replace('<input type="checkbox" />', "")
    h = re.sub(r"\[pinned\]\s*", '<span class="pin">pinned</span>', h)
    return re.sub(r"\s*\(source: (.*?)\)(?=\s*</li>)", r'<span class="src">\1</span>', h)

def split_sections(h):
    parts = re.split(r"<h2[^>]*>(.*?)</h2>", h, flags=re.S)
    sec, order = {}, []
    for i in range(1, len(parts), 2):
        k = re.sub(r"[^a-z]+", "-", strip(parts[i]).lower()).strip("-")
        k = ALIAS.get(k, k)
        sec[k] = (strip(parts[i]), parts[i + 1].strip()); order.append(k)
    return sec, order

def lis(h):
    """List items, with a lone <p> unwrapped (a list with blank lines between items is "loose" in Markdown)."""
    out = []
    for li in re.findall(r"<li>(.*?)</li>", h, re.S):
        m = re.fullmatch(r"\s*<p>(.*?)</p>\s*", li, re.S)
        out.append(m.group(1) if m and "<p>" not in m.group(1) else li)
    return out

# "2026-09-28:", "2026-09-28 (later):", "2026-10-01 PM:", "2026-10-08/09:", "2026-09-29 (Sam; relayed by x):"
DATED = re.compile(r"\s*(\d{4}-\d{2}-\d{2})((?:/\d{2})?)((?:[^:<]|<[^>]*>){0,200}?):\s*(.*)", re.S)
QUAL_MAX = 18         # a qualifier this short sits under the date; a longer one leads the text

def dated_rows(items):
    out = []
    for li in items:
        d = DATED.match(li)
        if not d:
            out.append(f'<li><time aria-hidden="true"></time><div>{li}</div></li>'); continue
        date, span, q, txt = d.group(1), d.group(2), d.group(3).strip().strip("()").strip(), d.group(4)
        t = date + (f"<i>{span}</i>" if span else "")
        if q and len(strip(q)) <= QUAL_MAX: t += f"<small>{q}</small>"
        elif q: txt = f'<span class="q">{q}</span> {txt}'
        out.append(f"<li><time>{t}</time><div>{txt}</div></li>")
    return out

def folded(rows, cls, noun):
    """Show the newest FOLD_AT rows (file order is oldest first); fold the rest above them."""
    if len(rows) <= FOLD_AT:
        return f'<ol class="{cls}">' + "".join(rows) + "</ol>"
    old, new = rows[:-FOLD_AT], rows[-FOLD_AT:]
    return (f'<details class="fold"><summary>Show {len(old)} older {noun}</summary><ol class="{cls}">' + "".join(old) +
            f'</ol></details><ol class="{cls}">' + "".join(new) + "</ol>")

def render(src, out):
    md = open(src, encoding="utf-8").read()
    body = decorate(pandoc(md))
    m = re.search(r"<h1[^>]*>(.*?)</h1>", body, re.S)
    name_html = m.group(1).strip() if m else "Checkpoint"
    body = body[m.end():] if m else body
    meta = {}
    mm = re.match(r"\s*<p>(.*?)</p>", body, re.S)
    if mm and "<strong>" in mm.group(1):
        for part in mm.group(1).split("·"):
            pm = re.match(r"\s*<strong>(.*?):?</strong>\s*:?\s*(.*)", part.strip(), re.S)
            if pm: meta[pm.group(1).rstrip(":").lower()] = pm.group(2).strip()
        body = body[mm.end():]
    kind, _, system = meta.get("kind", "work").partition("/")
    kind, system = strip(kind) or "work", strip(system)
    footer = ""
    fm = re.search(r"<hr\s*/?>\s*(<p>.*?</p>)\s*$", body, re.S)
    if fm: footer, body = strip(fm.group(1)), body[:fm.start()]
    sec, order = split_sections(body)

    # archive
    arch_path = re.sub(r"\.md$", ".archive.md", src)
    arch = {}
    if os.path.exists(arch_path):
        asec, _ = split_sections(decorate(pandoc(open(arch_path, encoding="utf-8").read())))
        arch = {k: v for k, v in asec.items() if k in ARCH_TITLES and lis(v[1])}

    navitems = []
    def block(key, title, inner, cls=""):
        countable = inner.split('<details class="fold">')[0] if key not in ("decisions", "traps") else inner
        countable = countable.split('<div class="parked">')[0]
        navitems.append((key, title, len(re.findall(r"<li[ >]", countable))))
        crumb = ""
        if key in CRUMB and CRUMB[key][0] in arch:
            n = len(lis(arch[CRUMB[key][0]][1]))
            crumb = f'<p class="crumb"><a href="#a-{CRUMB[key][0]}">&darr; {n} {CRUMB[key][1]} in archive</a></p>'
        return f'<section id="s-{key}" class="blk blk-{key} {cls}" aria-labelledby="h-{key}"><h2 id="h-{key}">{title}</h2>{crumb}{inner}</section>'

    now_html = ""
    if "now" in sec:
        h = sec["now"][1]; nxt = ""
        nm = re.search(r"<p><strong>Next step:?</strong>:?\s*(.*?)</p>", h, re.S)
        if nm: nxt, h = nm.group(1).strip(), h[:nm.start()] + h[nm.end():]
        gm = re.search(r"<p><strong>Next game:?</strong>:?\s*(.*?)</p>", h, re.S)
        game_html = ""
        if gm:
            h = h[:gm.start()] + h[gm.end():]
            game_html = f'<div class="next next-game"><span class="next-label">Next game</span><p>{date_chip(gm.group(1).strip())}</p></div>'
        nxt_html = game_html + (f'<div class="next"><span class="next-label">Next step</span><p>{nxt}</p></div>' if nxt else "")
        now_label = "Where we left off" if kind == "game" else "Now"
        now_html = f'<section class="now" aria-labelledby="h-now"><h2 id="h-now">{now_label}</h2><div class="now-state">{h}</div>{nxt_html}</section>'

    # At-a-glance band (work: "At a glance"; game: "Sheet"): "- **Label:** value" items, shown above Now
    glance_html = ""
    gkey = next((k for k in ("sheet", "at-a-glance") if k in sec), None)
    if gkey:
        rows = []
        for li in lis(sec[gkey][1]):
            m = re.match(r"\s*<strong>(.*?):?</strong>:?\s*(.*)", li, re.S)
            rows.append((strip(m.group(1)).rstrip(":"), m.group(2).strip()) if m else ("", li))
        asof = next((v for k, v in rows if k.lower() == "as of"), "")
        rows = [(k, v) for k, v in rows if k.lower() != "as of"]
        cell = lambda k, v, c="": f'<div class="g-cell {c}"><dt>{html.escape(k)}</dt><dd>{v}</dd></div>'
        parts, used = [], set()
        if kind == "game":
            sd = system_def(system); val = {k: v for k, v in rows}
            ident = [k for k in sd.get("identity", ["Name"]) if k in val]
            if ident:
                sub = " · ".join(val[k] for k in ident[1:])
                parts.append(f'<div class="g-who"><b>{val[ident[0]]}</b>' + (f"<span>{sub}</span>" if sub else "") + "</div>"); used |= set(ident)
            for grp, cls in (("stats", "g-stats"), ("tracks", "g-tracks")):
                ks = [k for k in sd.get(grp, []) if k in val]
                if ks: parts.append(f'<dl class="{cls}">' + "".join(cell(k, val[k]) for k in ks) + "</dl>"); used |= set(ks)
        rest = [(k, v) for k, v in rows if k not in used]
        if rest: parts.append('<dl class="g-cells">' + "".join(cell(k, v, "g-status" if k.lower() == "status" else "") for k, v in rest) + "</dl>")
        label = "Character sheet" if gkey == "sheet" else "At a glance"
        glance_html = (f'<section class="glance glance-{gkey}" aria-label="{label}"><div class="g-head"><span>{label}</span>' +
                       (f"<em>as of {asof}</em>" if asof else "") + "</div>" + "".join(parts) + "</section>")
        sec.pop(gkey)

    def waiting(h):
        rows = []
        for li in lis(h):
            w = re.match(r"\s*<strong>(.*?):?</strong>:?\s*(.*)", li, re.S)
            who, txt = (w.group(1).rstrip(":"), w.group(2)) if w else ("", li)
            rows.append(f'<li><span class="who">{who}</span><div>{txt}</div></li>')
        return '<ul class="waiting">' + "".join(rows) + "</ul>"
    def upnext(h):
        main, parked = h, ""
        pm = re.search(r"<h3[^>]*>\s*Parked\s*</h3>(.*)$", h, re.S)
        if pm: main, parked = h[:pm.start()], pm.group(1)
        o = '<ol class="queue">' + "".join(f"<li><div>{x}</div></li>" for x in lis(main)) + "</ol>"
        if parked and lis(parked):
            o += '<div class="parked"><h3>Parked</h3><ul>' + "".join(f"<li>{x}</li>" for x in lis(parked)) + "</ul></div>"
        return o
    def topic(h):
        rows = re.findall(r"<p><strong>(.*?):?</strong>:?\s*(.*?)</p>", h, re.S)
        return '<dl class="topic">' + "".join(f"<div><dt>{k.rstrip(':')}</dt><dd>{v}</dd></div>" for k, v in rows) + "</dl>" if rows else h
    def unv_rows(items):
        out = []
        for li in items:
            c = re.split(r"\s*Check:\s*", li, maxsplit=1)
            out.append(f"<li><div>{c[0]}</div>" + (f'<div class="check"><span>check</span> {c[1]}</div>' if len(c) > 1 else "") + "</li>")
        return out
    plain_rows = lambda items: [f"<li>{x}</li>" for x in items]

    def chapters(h):
        """Adventure log: one <h3> per game session, file order oldest first. Newest open, older folded."""
        parts = re.split(r"<h3[^>]*>(.*?)</h3>", h, flags=re.S)
        chs = [(parts[i].strip(), parts[i + 1].strip()) for i in range(1, len(parts), 2)]
        if not chs: return h
        out = []
        for n, (title, body) in enumerate(chs):
            bits = [b.strip() for b in re.split(r"\s*·\s*", strip(title))]
            num, rest = (bits[0], bits[1:]) if bits else ("", [])
            date = next((b for b in rest if re.match(r"\d{4}-\d{2}-\d{2}$", b)), "")
            name = " · ".join(b for b in rest if b != date) or num
            head = (f'<span class="ch-num">{num}</span><span class="ch-title">{name}</span>' +
                    (f'<time>{date}</time>' if date else ""))
            last = n == len(chs) - 1
            out.append(f'<details class="chapter"{" open" if last else ""}><summary>{head}</summary><div class="ch-body">{body}</div></details>')
        return '<div class="chapters">' + "".join(reversed(out)) + "</div>"

    aside, main = [], []
    S = lambda k: sec[k][1]
    if kind == "game":
        if "between-games" in sec: aside.append(block("between-games", "Between games", waiting(S("between-games")), "attn"))
        if "character" in sec: aside.append(block("character", "Character", topic(S("character"))))
        if "party" in sec: aside.append(block("party", "Party", '<ul class="dots">' + "".join(plain_rows(lis(S("party")))) + "</ul>"))
        if "traps" in sec: aside.append(block("traps", "Traps", folded(plain_rows(lis(S("traps"))), "traps", "traps")))
        if "adventure-log" in sec: main.append(block("adventure-log", "Adventure log", chapters(S("adventure-log"))))
        if "threads" in sec: main.append(block("threads", "Threads", '<ul class="facts">' + "".join(plain_rows(lis(S("threads")))) + "</ul>"))
        if "npcs" in sec: main.append(block("npcs", "NPCs", '<ul class="facts">' + "".join(plain_rows(lis(S("npcs")))) + "</ul>"))
        if "table-rulings" in sec: main.append(block("table-rulings", "Table rulings", folded(dated_rows(lis(S("table-rulings"))), "ledger", "rulings")))
        for k in ("between-games", "character", "party", "traps", "adventure-log", "threads", "npcs", "table-rulings"): sec.pop(k, None)
    if "waiting-on" in sec: aside.append(block("waiting-on", "Waiting on", waiting(S("waiting-on")), "attn"))
    if "traps" in sec: aside.append(block("traps", "Traps", folded(plain_rows(lis(S("traps"))), "traps", "traps")))
    def sequence(h):
        rows = []
        for li in lis(h):
            m = re.match(r"\s*\[(" + "|".join(SEQ_STATES) + r")(?::\s*([^\]]*))?\]\s*(.*)", li, re.S | re.I)
            st, note, txt = (m.group(1).lower(), (m.group(2) or "").strip(), m.group(3)) if m else ("todo", "", li)
            rows.append(f'<li class="st-{st}"><span class="pill">{st}{": " + note if note else ""}</span><div>{txt}</div></li>')
        return '<ol class="seq">' + "".join(rows) + "</ol>"
    if "sequence" in sec: main.append(block("sequence", "Sequence", sequence(S("sequence"))))
    if "up-next" in sec: main.append(block("up-next", "Up next", upnext(S("up-next"))))
    if "last-touched" in sec: main.append(block("last-touched", "Last touched", '<ul class="dots">' + "".join(plain_rows(lis(S("last-touched")))) + "</ul>"))
    if "recent-sessions" in sec: main.append(block("recent-sessions", "Recent sessions", '<ol class="timeline">' + "".join(dated_rows(lis(S("recent-sessions")))) + "</ol>"))
    if "topic" in sec: main.append(block("topic", "Topic", topic(S("topic"))))
    if "decisions" in sec: main.append(block("decisions", "Decisions", folded(dated_rows(lis(S("decisions"))), "ledger", "decisions")))
    if "facts" in sec: main.append(block("facts", "Facts", '<ul class="facts">' + "".join(plain_rows(lis(S("facts")))) + "</ul>"))
    if "unverified" in sec: main.append(block("unverified", "Unverified", '<ul class="unv">' + "".join(unv_rows(lis(S("unverified")))) + "</ul>"))
    if "references" in sec: main.append(block("references", "References", '<ul class="refs">' + "".join(plain_rows(lis(S("references")))) + "</ul>"))
    # attachments: <name>.<part>.md beside the checkpoint, committed with it, listed here (the page cannot link local files)
    base = re.sub(r"\.md$", "", os.path.basename(src)); folder = os.path.dirname(os.path.abspath(src))
    att = sorted(f for f in os.listdir(folder) if f.startswith(base + ".") and f.endswith(".md") and f not in (base + ".md", base + ".archive.md"))
    if att:
        rows = "".join(f'<li><code>{html.escape(f)}</code> <span class="src">{os.path.getsize(os.path.join(folder, f)) // 1024 or 1} KB, in the register repo</span></li>' for f in att)
        main.append(block("attachments", "Attachments", f'<ul class="refs">{rows}</ul>'))
    known = WORK_SECS | SHARED_SECS | (GAME_SECS if kind == "game" else set())
    for k in order:
        if k not in known: main.append(block(k, sec[k][0], sec[k][1]))

    arch_html, arch_total = "", 0
    if arch:
        parts = []
        for k in ARCH_TITLES:
            if k not in arch: continue
            items = lis(arch[k][1]); arch_total += len(items)
            rows = (dated_rows(items) if k in ("done", "decisions", "recent-sessions") else plain_rows(items))
            cls = {"done": "ledger", "decisions": "ledger", "recent-sessions": "timeline"}.get(k, "facts")
            parts.append(f'<details id="a-{k}"><summary>{ARCH_TITLES[k]} <b>{len(items)}</b></summary><ol class="{cls}">' + "".join(rows) + "</ol></details>")
        arch_html = '<section id="archive" class="archive" aria-labelledby="h-archive"><h2 id="h-archive">Archive</h2>' + "".join(parts) + "</section>"

    reading = ["waiting-on","sequence","up-next","last-touched","recent-sessions","topic","decisions","facts","unverified","traps","references","attachments"]
    if kind == "game":
        reading = ["adventure-log","between-games","threads","npcs","party","character","table-rulings","facts","unverified","traps","references","attachments"]
    navitems.sort(key=lambda t: reading.index(t[0]) if t[0] in reading else 99)
    nav = "".join(f'<li><a href="#s-{k}" class="{"attn" if k in ("waiting-on","traps","between-games") else ""}"><span>{t}</span>' + (f"<b>{n}</b>" if n and k not in ("topic","character") else "") + "</a></li>" for k, t, n in navitems)
    if arch_total: nav += f'<li><a href="#archive" class="arch"><span>Archive</span><b>{arch_total}</b></a></li>'
    nav_html = f'<nav class="toc" aria-label="Sections"><ul>{nav}</ul></nav>'

    ck, art, tl = meta.get("checkpoint", ""), meta.get("artifact", ""), meta.get("topic", "")
    eyebrow = f"Adventure log · {system_def(system).get('title') or SYSTEMS.get(system, system.title())}" if kind == "game" else "Session checkpoint"
    header = (f'<header><div class="eyebrow">{eyebrow}</div>' f"<h1>{name_html}</h1>" +
              (f'<p class="subtitle">{tl}</p>' if tl else "") +
              f'<div class="stamp"><span>last checkpoint</span><b>{ck}</b>' +
              (f'<a href="{strip(art)}">artifact link</a>' if art.startswith("<a") else "") + "</div></header>")
    shell = open(os.path.join(HERE, "shell.html"), encoding="utf-8").read()
    css = open(os.path.join(HERE, "checkpoint.css"), encoding="utf-8").read()
    head = ""
    if kind != "work":
        # kind layer, then system theme; each may name its fonts in a leading "/* @fonts <url> */"
        for f in (os.path.join(HERE, "kinds", kind, kind + ".css"), os.path.join(HERE, "kinds", kind, "themes", system + ".css")):
            if os.path.exists(f):
                t = open(f, encoding="utf-8").read()
                fm = re.match(r"\s*/\*\s*@fonts\s+(\S+)\s*\*/", t)
                if fm: head += f'<link rel="stylesheet" href="{fm.group(1)}">'
                css += "\n" + t
    shell = shell.replace("{{HEAD}}\n", head + "\n" if head else "")
    for k, v in {"TITLE": html.escape(strip(name_html)), "CSS": css, "HEADER": header, "GLANCE": glance_html, "NOW": now_html, "NAV": nav_html,
                 "ASIDE": "".join(aside), "MAIN": "".join(main), "ARCHIVE": arch_html, "FOOTER": footer}.items():
        shell = shell.replace("{{" + k + "}}", v)
    open(out, "w", encoding="utf-8").write(shell)
    return out

if __name__ == "__main__":
    print(render(sys.argv[1], sys.argv[2]))
