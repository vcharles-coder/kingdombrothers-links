# Kingdom Brothers – WhatsApp-previewable Short links

Each Short has a page at /s/<videoId>/ that sets og:title, og:image and the twitter card for link previews, then redirects visitors to https://www.youtube.com/shorts/<videoId>.

## Regenerate / add new Shorts
    pip install pillow
    python3 build.py --base-url https://YOUR-HOST/path      # fetch channel Shorts, add new ones, rebuild everything
    python3 build.py --base-url https://YOUR-HOST/path --ids <id-or-url> ...   # add specific Shorts
    python3 build.py --no-fetch --base-url https://YOUR-HOST/path              # just rewrite HTML (offline)
The script keeps known videos in shorts.json and only downloads thumbnails that are missing (use --force-thumbs to refresh them).
Use no trailing slash in --base-url. The og:url and og:image values need absolute URLs.

## Share
Share https://YOUR-HOST/path/s/<videoId>/ instead of the YouTube link.
