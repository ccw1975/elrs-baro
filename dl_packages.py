# -*- coding: utf-8 -*-
"""Multi-thread download PlatformIO packages into its download cache.
Cache filename = sha1(download_url + sha256) so `pio run` hits the cache.
"""
import hashlib
import http.client
import json
import os
import shutil
import sys
import tempfile
import threading
import time
import urllib.request

CACHE_DIR = os.path.expanduser(r"~\.platformio\.cache\downloads")
THREADS = 48
SEG = 512 * 1024  # per-segment size

PACKAGES = [
    ("espressif", "tool", "toolchain-riscv32-esp", "8.4.0+2021r2-patch5"),
    ("platformio", "tool", "tool-esptoolpy", "1.40501.0"),
    ("platformio", "tool", "framework-arduinoespressif32", "3.20011.230801"),
]


def api_get(url):
    req = urllib.request.Request(url, headers={"User-Agent": "curl"})
    return json.load(urllib.request.urlopen(req, timeout=30))


def get_meta(owner, typ, name, want_version):
    d = api_get(
        "https://api.registry.platformio.org/v3/packages/%s/%s/%s"
        % (owner, typ, name)
    )
    for v in d.get("versions", []):
        if v["name"] != want_version:
            continue
        for f in v.get("files", []):
            sysname = f.get("system") or "*"
            if sysname in ("windows_amd64", "*"):
                return v["name"], f["download_url"], f["checksum"]["sha256"]
    return None


def cache_name(url, sha256):
    h = hashlib.sha1((url + sha256).encode("utf-8"))
    return h.hexdigest()


def http_head(url):
    req = urllib.request.Request(url, method="HEAD", headers={"User-Agent": "curl"})
    r = urllib.request.urlopen(req, timeout=30)
    return int(r.headers.get("Content-Length") or 0)


def seg_download(url, start, end, results, idx):
    try:
        req = urllib.request.Request(
            url,
            headers={"User-Agent": "curl", "Range": "bytes=%d-%d" % (start, end)},
        )
        r = urllib.request.urlopen(req, timeout=180)
        data = r.read()
        if r.status in (200, 206):
            results[idx] = data
        else:
            print("  seg %d status %d" % (idx, r.status))
    except Exception as exc:  # noqa
        print("  seg %d ERR %s" % (idx, exc))
        results[idx] = None


def download_multithread(url, length, dest):
    n = THREADS
    segs = [length // n] * n
    for i in range(length % n):
        segs[i] += 1
    results = {}
    threads = []
    pos = 0
    for i in range(n):
        s, e = pos, pos + segs[i] - 1
        pos += segs[i]
        t = threading.Thread(target=seg_download, args=(url, s, e, results, i))
        t.start()
        threads.append(t)
    for t in threads:
        t.join()
    if len(results) != n or any(v is None for v in results.values()):
        return False
    with open(dest, "wb") as f:
        for i in range(n):
            f.write(results[i])
    return os.path.getsize(dest) == length


def main():
    os.makedirs(CACHE_DIR, exist_ok=True)
    for owner, typ, name, ver in PACKAGES:
        meta = get_meta(owner, typ, name, ver)
        if not meta:
            print("NO META for", name, ver)
            continue
        vname, url, sha = meta
        cname = cache_name(url, sha)
        final = os.path.join(CACHE_DIR, cname)
        if os.path.isfile(final) and os.path.getsize(final) > 0:
            print("CACHE HIT %s (%s)" % (name, cname))
            continue
        print("== %s %s  size=?" % (name, vname))
        try:
            length = http_head(url)
        except Exception as exc:  # noqa
            print("  HEAD ERR", exc)
            continue
        print("   length=%d cache=%s" % (length, cname))
        tmp = tempfile.mktemp(dir=CACHE_DIR)
        t0 = time.time()
        ok = download_multithread(url, length, tmp)
        dt = time.time() - t0
        if ok:
            os.replace(tmp, final)
            print("   OK %.2f MB in %.0fs = %.2f MB/s" % (
                length / 1048576, dt, length / dt / 1048576))
        else:
            try:
                os.remove(tmp)
            except OSError:
                pass
            print("   FAILED segments")
    print("DONE")


if __name__ == "__main__":
    main()
