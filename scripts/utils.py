import json
import os
import urllib.request  # avoiding requests dep bc we can
import subprocess

HEADERS = {  # pretend to be Chrome 121 for Discord links
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.3"
}


def download(url: str) -> bytes:
    urllib.parse.quote(url)
    req = urllib.request.Request(url, headers=HEADERS)
    resp = urllib.request.urlopen(req).read()
    return resp


def download_json(url: str) -> dict:
    """
    Fetches JSON from a URL. Uses urllib for HTTP and falls back to curl for HTTPS.
    Returns the parsed JSON as a Python dict.
    """
    # Download raw bytes
    if url.lower().startswith("https://"):
        raw = subprocess.check_output(["curl", "-sL", url])
    else:
        req = urllib.request.Request(url)
        raw = urllib.request.urlopen(req).read()

    # Decode and parse JSON
    text = raw.decode("utf-8")
    return json.loads(text)


### Typing utils for argparse
def existing_directory(dir_path: str) -> str:
    if os.path.isdir(dir_path):
        return dir_path
    raise NotADirectoryError(dir_path)


def existing_file(file_path: str) -> str:
    if os.path.isfile(file_path):
        return file_path
    raise FileNotFoundError(file_path)
