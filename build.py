#!/usr/bin/env python3
"""Build WhatsApp-previewable landing pages for a YouTube channel's Shorts.

Usage:
  python3 build.py                                   # pages use __BASE_URL__ placeholder
  python3 build.py --base-url https://example.github.io/kb
  python3 build.py --ids abc123def45 xyz...          # add specific Shorts (e.g. ones not listed yet)
  python3 build.py --no-fetch                        # rebuild HTML from shorts.json only (offline)
  python3 build.py --channel @SomeOtherChannel --force-thumbs

Output (next to this script):
  index.html, shorts.json, s/<videoId>/index.html, s/<videoId>/thumb.jpg
Needs: Python 3.8+, Pillow (pip install pillow). Uses only public YouTube endpoints, no login.
"""
import hashlib
import argparse, html, io, json, os, re, sys, time, urllib.parse, urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/129.0 Safari/537.36"
MAX_BYTES = 300 * 1024
ID_RE = re.compile(r"^[A-Za-z0-9_-]{11}$")


def get(url, data=None, headers=None, timeout=30):
    h = {"User-Agent": UA, "Accept-Language": "en"}
    h.update(headers or {})
    req = urllib.request.Request(url, data=data, headers=h)
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return r.read()


def walk(o, key):
    if isinstance(o, dict):
        for k, v in o.items():
            if k == key:
                yield v
            yield from walk(v, key)
    elif isinstance(o, list):
        for x in o:
            yield from walk(x, key)


def ids_from(data):
    out = []
    for v in walk(data, "shortsLockupViewModel"):
        m = re.search(r"([A-Za-z0-9_-]{11})$", v.get("entityId", ""))
        if m: out.append(m.group(1))
    for v in walk(data, "reelItemRenderer"):
        if "videoId" in v: out.append(v["videoId"])
    return out


def list_channel_shorts(channel, max_pages=20):
    url = f"https://www.youtube.com/{channel}/shorts" if channel.startswith("@") else channel
    page = get(url).decode("utf-8", "replace")
    data = json.loads(re.search(r"var ytInitialData = (\{.*?\});</script>", page).group(1))
    m = re.search(r'"INNERTUBE_CLIENT_VERSION":"([^"]+)"', page)
    cver = m.group(1) if m else "2.20261001.00.00"
    ids = ids_from(data)
    tokens = [c["token"] for c in walk(data, "continuationCommand")]
    seen_tok = set()
    pages = 0
    while tokens and pages < max_pages:
        tok = tokens.pop(0)
        if tok in seen_tok: continue
        seen_tok.add(tok); pages += 1
        body = json.dumps({"context": {"client": {"clientName": "WEB", "clientVersion": cver, "hl": "en"}},
                           "continuation": tok}).encode()
        try:
            d = json.loads(get("https://www.youtube.com/youtubei/v1/browse?prettyPrint=false", body,
                               {"Content-Type": "application/json"}))
        except Exception as e:
            print("  continuation failed:", e, file=sys.stderr); continue
        new = ids_from(d)
        ids += new
        if new:
            tokens += [c["token"] for c in walk(d, "continuationCommand")]
        time.sleep(0.5)
    uniq = []
    for i in ids:
        if i not in uniq: uniq.append(i)
    return uniq


def oembed(vid):
    u = "https://www.youtube.com/oembed?format=json&url=" + urllib.parse.quote(f"https://www.youtube.com/shorts/{vid}")
    return json.loads(get(u))


def make_thumb(vid, dest):
    from PIL import Image
    src = None
    for name in ("maxresdefault", "hq720", "sddefault", "hqdefault"):
        try:
            b = get(f"https://i.ytimg.com/vi/{vid}/{name}.jpg")
            im = Image.open(io.BytesIO(b))
            if name == "hqdefault" or im.size[0] >= 640:
                src = (name, b, im); break
        except Exception:
            continue
    if not src:
        raise RuntimeError("no thumbnail")
    name, b, im = src
    im = im.convert("RGB")
    # hqdefault/sddefault are 4:3 with letterbox bars: crop to 16:9
    w, h = im.size
    if abs(w / h - 16 / 9) > 0.02:
        nh = int(w * 9 / 16); top = (h - nh) // 2
        im = im.crop((0, top, w, top + nh))
    if im.size != (1280, 720):
        im = im.resize((1280, 720), Image.LANCZOS)
    if name in ("maxresdefault", "hq720") and len(b) <= MAX_BYTES and Image.open(io.BytesIO(b)).size == (1280, 720):
        data = b
    else:
        data = None
        for q in (88, 82, 76, 70, 62, 55):
            buf = io.BytesIO(); im.save(buf, "JPEG", quality=q, optimize=True, progressive=True)
            data = buf.getvalue()
            if len(data) <= MAX_BYTES: break
    with open(dest, "wb") as f:
        f.write(data)
    return name, len(data)


def esc(s):
    return html.escape(s, quote=True)


PAGE = """<!doctype html>
<html lang="ta">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>{title}</title>
<meta name="description" content="{desc}">
<meta property="og:type" content="video.other">
<meta property="og:site_name" content="{author}">
<meta property="og:title" content="{title}">
<meta property="og:description" content="{desc}">
<meta property="og:url" content="{page}">
<meta property="og:image" content="{img}">
<meta property="og:image:secure_url" content="{img}">
<meta property="og:image:type" content="image/jpeg">
<meta property="og:image:width" content="1280">
<meta property="og:image:height" content="720">
<meta property="og:image:alt" content="{title}">
<meta name="twitter:card" content="summary_large_image">
<meta name="twitter:title" content="{title}">
<meta name="twitter:description" content="{desc}">
<meta name="twitter:image" content="{img}">
<meta http-equiv="refresh" content="0;url={yt}">
<style>
body{{margin:0;font-family:system-ui,-apple-system,Segoe UI,Roboto,sans-serif;background:#0f0f0f;color:#fff;display:flex;min-height:100vh;align-items:center;justify-content:center}}
main{{max-width:640px;padding:16px;text-align:center}}
img{{width:100%;border-radius:12px}}
a.btn{{display:inline-block;margin-top:16px;padding:12px 22px;background:#f00;color:#fff;border-radius:24px;text-decoration:none;font-weight:600}}
h1{{font-size:1.1rem;line-height:1.4}}
</style>
</head>
<body>
<main>
<a href="{yt}"><img src="{thumb}" alt="{title}" width="1280" height="720"></a>
<h1>{title}</h1>
<a class="btn" href="{yt}">&#9654; Watch on YouTube</a>
<p><small>Redirecting&hellip; If nothing happens, tap the button.</small></p>
</main>
<script>location.replace({yt_js});</script>
</body>
</html>
"""

INDEX = """<!doctype html>
<html lang="ta">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>{author} – Shorts</title>
<meta property="og:type" content="website">
<meta property="og:title" content="{author} – Shorts">
<meta property="og:description" content="{n} song covers · Watch on YouTube">
<meta property="og:url" content="{base}/">
{og_img}
<meta name="twitter:card" content="summary_large_image">
<style>
body{{margin:0;font-family:system-ui,-apple-system,Segoe UI,Roboto,sans-serif;background:#0f0f0f;color:#fff}}
header{{padding:20px 16px}} h1{{margin:0;font-size:1.4rem}} header a{{color:#aaa}}
.grid{{display:grid;grid-template-columns:repeat(auto-fill,minmax(240px,1fr));gap:16px;padding:0 16px 32px}}
.card{{color:#fff;text-decoration:none}} .card img{{width:100%;border-radius:10px;aspect-ratio:16/9;object-fit:cover}}
.card p{{margin:6px 0 0;font-size:.9rem;line-height:1.35}}
</style>
</head>
<body>
<header><h1>{author} – Shorts</h1><a href="{author_url}">YouTube channel</a></header>
<div class="grid">
{cards}
</div>
</body>
</html>
"""


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--channel", default="@KingdomBrothersOfficial")
    ap.add_argument("--base-url", default="__BASE_URL__", help="e.g. https://user.github.io/repo (no trailing slash)")
    ap.add_argument("--ids", nargs="*", default=[], help="extra Short video IDs or URLs to include")
    ap.add_argument("--no-fetch", action="store_true", help="don't contact YouTube; rebuild HTML from shorts.json")
    ap.add_argument("--force-thumbs", action="store_true")
    a = ap.parse_args()
    base = a.base_url.rstrip("/")
    man_path = os.path.join(HERE, "shorts.json")
    manifest = json.load(open(man_path, encoding="utf-8")) if os.path.exists(man_path) else {"order": [], "videos": {}}

    extra = []
    for x in a.ids:
        m = re.search(r"([A-Za-z0-9_-]{11})(?:[?&/#]|$)", x)
        if m: extra.append(m.group(1))
    found = []
    if not a.no_fetch:
        print(f"Listing Shorts for {a.channel} ...")
        found = list_channel_shorts(a.channel)
        print(f"  found {len(found)} on channel page")
    # newest first: channel order, then extras, then anything previously known
    order = []
    for i in found + extra + manifest["order"]:
        if ID_RE.match(i) and i not in order: order.append(i)

    for vid in order:
        v = manifest["videos"].get(vid)
        if not a.no_fetch and (v is None or not v.get("title")):
            try:
                o = oembed(vid)
                v = {"title": o["title"], "author": o["author_name"], "author_url": o["author_url"]}
                manifest["videos"][vid] = v
                print(f"  + {vid}  {o['title'][:70]}")
            except Exception as e:
                print(f"  ! {vid} oEmbed failed ({e}); skipping", file=sys.stderr)
                continue
        if v is None: continue
        d = os.path.join(HERE, "s", vid); os.makedirs(d, exist_ok=True)
        tp = os.path.join(d, "thumb.jpg")
        if not a.no_fetch and (a.force_thumbs or not os.path.exists(tp)):
            src, size = make_thumb(vid, tp)
            v["thumb_src"], v["thumb_bytes"] = src, size
            # content-hashed copy so WhatsApp/CDN caches see a new URL when the image changes
            data = open(tp, "rb").read()
            hf = f"thumb-{hashlib.sha1(data).hexdigest()[:8]}.jpg"
            for old in os.listdir(d):
                if old.startswith("thumb-") and old.endswith(".jpg") and old != hf:
                    os.remove(os.path.join(d, old))
            open(os.path.join(d, hf), "wb").write(data)
            v["thumb_file"] = hf
        tf = v.get("thumb_file") if v.get("thumb_file") and os.path.exists(os.path.join(d, v["thumb_file"])) else "thumb.jpg"
        yt = f"https://www.youtube.com/shorts/{vid}"
        desc = f"Watch on YouTube · {v['author']}"
        with open(os.path.join(d, "index.html"), "w", encoding="utf-8") as f:
            f.write(PAGE.format(title=esc(v["title"]), desc=esc(desc), author=esc(v["author"]), yt=esc(yt),
                                yt_js=json.dumps(yt), page=esc(f"{base}/s/{vid}/"), img=esc(f"{base}/s/{vid}/{tf}"), thumb=esc(tf)))
    manifest["order"] = [i for i in order if i in manifest["videos"]]
    json.dump(manifest, open(man_path, "w", encoding="utf-8"), ensure_ascii=False, indent=1)

    vids = manifest["order"]
    author = manifest["videos"][vids[0]]["author"] if vids else a.channel
    author_url = manifest["videos"][vids[0]]["author_url"] if vids else ""
    cards = "\n".join(
        f'<a class="card" href="s/{i}/"><img loading="lazy" src="s/{i}/{manifest['videos'][i].get('thumb_file') or 'thumb.jpg'}" alt=""><p>{esc(manifest["videos"][i]["title"])}</p></a>'
        for i in vids)
    og_img = (f'<meta property="og:image" content="{esc(base)}/s/{vids[0]}/{manifest['videos'][vids[0]].get('thumb_file') or 'thumb.jpg'}">\n'
              f'<meta property="og:image:width" content="1280">\n<meta property="og:image:height" content="720">') if vids else ""
    with open(os.path.join(HERE, "index.html"), "w", encoding="utf-8") as f:
        f.write(INDEX.format(author=esc(author), author_url=esc(author_url), n=len(vids), base=esc(base),
                             og_img=og_img, cards=cards))
    print(f"Built {len(vids)} pages + index.html (base URL: {base})")


if __name__ == "__main__":
    main()
