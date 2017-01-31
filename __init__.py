import os
import time

try:
    from static_map import TIMESTAMP, STATIC_MAP, SYMBOLIC_MAP, INTEGRITY_MAP
except ImportError:
    TIMESTAMP = str(int(time.time()))
    STATIC_MAP = SYMBOLIC_MAP = INTEGRITY_MAP = {}

DEBUG = os.environ.get('SERVER_SOFTWARE', '').startswith('Development')
STATIC_FILE = "static_map.py"


def static(url):
    # in development, do nothing
    if DEBUG:
        return url

    # in production, look up this thing in the dictionaries and reference that version if it exists
    if url in SYMBOLIC_MAP:
        url = SYMBOLIC_MAP[url]

    if url in STATIC_MAP:
        return STATIC_MAP[url]

    # if it can't be found, just attach the timestamp as the query param as a fall back
    return "?".join([url, TIMESTAMP])

def integrity(url):
    # in development, do nothing
    if DEBUG:
        return ""

    # look up in production
    if url in INTEGRITY_MAP:
        return INTEGRITY_MAP[url]

    # workable fallback
    return ""

def script(url, async=False, defer=False, crossorigin=None):
    src = static(url)
    sri = integrity(url)
    s = '<script src="' + src + '" '

    if sri:
        s += 'integrity="' + sri + '" '

    if async:
        s += 'async '

    if defer:
        s += 'defer '

    if crossorigin:
        s += 'crossorigin="' + crossorigin + '"'

    s += '></script>'
    return s

def style(url, crossorigin=None, media=None, title=None):
    href = static(url)
    sri = integrity(url)
    s = '<link rel="stylesheet" href="' + href + '" '

    if sri:
        s += 'integrity="' + sri + '" '

    if crossorigin:
        s += 'crossorigin="' + crossorigin + '" '

    if media:
        s += 'media="' + media + '" '

    if title:
        s += 'title="' + title + '"'

    s += '/>'
    return s
