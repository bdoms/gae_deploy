import os
import time

try:
    from static_map import TIMESTAMP, STATIC_MAP
except ImportError:
    TIMESTAMP = str(int(time.time()))
    STATIC_MAP = {}

DEBUG = os.environ.get('SERVER_SOFTWARE', '').startswith('Development')
STATIC_FILE = "static_map.py"


def static(url):
    # in development, do nothing
    if DEBUG:
        return url

    # in production, look up this thing in the dictionary and reference that version if it exists
    if url in STATIC_MAP:
        return STATIC_MAP[url]

    # if it can't be found, just attach the timestamp as the query param as a fall back
    return "?".join([url, TIMESTAMP])

