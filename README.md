# Kingdom Brothers – WhatsApp-previewable Short links

Each Short has a page at /s/<videoId>/ that sets og:title, og:image and the twitter card for link previews, then redirects visitors to https://www.youtube.com/shorts/<videoId>.

## Regenerate / add new Shorts
    pip install pillow
    python3 build.py --base-url https://watch.kingdombrothers.in      # fetch channel Shorts, add new ones, rebuild everything
    python3 build.py --base-url https://watch.kingdombrothers.in --ids <id-or-url> ...   # add specific Shorts
    python3 build.py --no-fetch --base-url https://watch.kingdombrothers.in              # just rewrite HTML (offline)
The script keeps known videos in shorts.json and only downloads thumbnails that are missing (use --force-thumbs to refresh them).
Use no trailing slash in --base-url. The og:url and og:image values need absolute URLs.

## Share
Share https://watch.kingdombrothers.in/s/<videoId>/ instead of the YouTube link.

Hosted on GitHub Pages (vcharles-coder/kingdombrothers-links) at https://watch.kingdombrothers.in (CNAME file). After rebuilding, commit and push to main.
