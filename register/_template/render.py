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
         "unverified": ("unverified", "resolved items"), "recent-sessions": ("recent-sessions", "older sessions")}
ARCH_TITLES = {"done": "Done", "facts": "Facts", "decisions": "Superseded decisions",
               "traps": "Obsolete traps", "unverified": "Resolved unverified", "recent-sessions": "Older sessions"}

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

lis = lambda h: re.findall(r"<li>(.*?)</li>", h, re.S)

def dated_rows(items):
    out = []
    for li in items:
        d = re.match(r"\s*(\d{4}-\d{2}-\d{2}):\s*(.*)", li, re.S)
        out.append(f"<li><time>{d.group(1)}</time><div>{d.group(2)}</div></li>" if d else f"<li><div>{li}</div></li>")
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
        nxt_html = f'<div class="next"><span class="next-label">Next step</span><p>{nxt}</p></div>' if nxt else ""
        now_html = f'<section class="now" aria-labelledby="h-now"><h2 id="h-now">Now</h2><div class="now-state">{h}</div>{nxt_html}</section>'

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

    aside, main = [], []
    S = lambda k: sec[k][1]
    if "waiting-on" in sec: aside.append(block("waiting-on", "Waiting on", waiting(S("waiting-on")), "attn"))
    if "traps" in sec: aside.append(block("traps", "Traps", folded(plain_rows(lis(S("traps"))), "traps", "traps")))
    if "up-next" in sec: main.append(block("up-next", "Up next", upnext(S("up-next"))))
    if "last-touched" in sec: main.append(block("last-touched", "Last touched", '<ul class="dots">' + "".join(plain_rows(lis(S("last-touched")))) + "</ul>"))
    if "recent-sessions" in sec: main.append(block("recent-sessions", "Recent sessions", '<ol class="timeline">' + "".join(dated_rows(lis(S("recent-sessions")))) + "</ol>"))
    if "topic" in sec: main.append(block("topic", "Topic", topic(S("topic"))))
    if "decisions" in sec: main.append(block("decisions", "Decisions", folded(dated_rows(lis(S("decisions"))), "ledger", "decisions")))
    if "facts" in sec: main.append(block("facts", "Facts", '<ul class="facts">' + "".join(plain_rows(lis(S("facts")))) + "</ul>"))
    if "unverified" in sec: main.append(block("unverified", "Unverified", '<ul class="unv">' + "".join(unv_rows(lis(S("unverified")))) + "</ul>"))
    if "references" in sec: main.append(block("references", "References", '<ul class="refs">' + "".join(plain_rows(lis(S("references")))) + "</ul>"))
    known = {"now","waiting-on","traps","up-next","last-touched","recent-sessions","topic","decisions","facts","unverified","references"}
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

    reading = ["waiting-on","up-next","last-touched","recent-sessions","topic","decisions","facts","unverified","traps","references"]
    navitems.sort(key=lambda t: reading.index(t[0]) if t[0] in reading else 99)
    nav = "".join(f'<li><a href="#s-{k}" class="{"attn" if k in ("waiting-on","traps") else ""}"><span>{t}</span>' + (f"<b>{n}</b>" if n and k != "topic" else "") + "</a></li>" for k, t, n in navitems)
    if arch_total: nav += f'<li><a href="#archive" class="arch"><span>Archive</span><b>{arch_total}</b></a></li>'
    nav_html = f'<nav class="toc" aria-label="Sections"><ul>{nav}</ul></nav>'

    ck, art, tl = meta.get("checkpoint", ""), meta.get("artifact", ""), meta.get("topic", "")
    header = ('<header><div class="eyebrow">Session checkpoint</div>' f"<h1>{name_html}</h1>" +
              (f'<p class="subtitle">{tl}</p>' if tl else "") +
              f'<div class="stamp"><span>last checkpoint</span><b>{ck}</b>' +
              (f'<a href="{strip(art)}">artifact link</a>' if art.startswith("<a") else "") + "</div></header>")
    shell = open(os.path.join(HERE, "shell.html"), encoding="utf-8").read()
    css = open(os.path.join(HERE, "checkpoint.css"), encoding="utf-8").read()
    for k, v in {"TITLE": html.escape(strip(name_html)), "CSS": css, "HEADER": header, "NOW": now_html, "NAV": nav_html,
                 "ASIDE": "".join(aside), "MAIN": "".join(main), "ARCHIVE": arch_html, "FOOTER": footer}.items():
        shell = shell.replace("{{" + k + "}}", v)
    open(out, "w", encoding="utf-8").write(shell)
    return out

if __name__ == "__main__":
    print(render(sys.argv[1], sys.argv[2]))
