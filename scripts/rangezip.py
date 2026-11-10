"""A read-only, seekable file over HTTP range requests, so zipfile can pull single members out of a remote archive
without downloading it (fetch_gba.py: one 170 MB GeoTIFF out of a 107 GB zip). Blocks of `block` bytes are cached.

usage: python scripts/rangezip.py   lists the GBA Europe e015_n50 zip and the Budapest member
"""
import io, sys, zipfile, requests

class RangeFile(io.RawIOBase):
    def __init__(self, url, auth=None, headers=None, block=1 << 20):
        self.url, self.s, self.pos, self.block = url, requests.Session(), 0, block
        self.s.auth = auth
        self.s.headers.update(headers or {})
        self.size = int(self.s.head(url).headers["Content-Length"])
        self.cache = {}

    def seekable(self): return True
    def readable(self): return True
    def tell(self): return self.pos

    def seek(self, off, whence=0):
        self.pos = off if whence == 0 else self.pos + off if whence == 1 else self.size + off
        return self.pos

    def _blk(self, i):
        if i not in self.cache:
            a = i * self.block
            r = self.s.get(self.url, headers={"Range": f"bytes={a}-{min(a + self.block, self.size) - 1}"})
            r.raise_for_status()
            self.cache[i] = r.content
            if len(self.cache) > 64:
                self.cache.pop(next(iter(self.cache)))
        return self.cache[i]

    def read(self, n=-1):
        if n < 0: n = self.size - self.pos
        n = max(0, min(n, self.size - self.pos))
        out = bytearray()
        while n:
            i, o = divmod(self.pos, self.block)
            b = self._blk(i)[o:o + n]
            out += b; self.pos += len(b); n -= len(b)
        return bytes(out)

    def readinto(self, buf):
        d = self.read(len(buf)); buf[:len(d)] = d; return len(d)

if __name__ == "__main__":
    url = "https://dataserv.ub.tum.de/public.php/webdav/height/europe/e015_n50_e020_n45.zip"
    f = RangeFile(url, auth=("m1782307", "m1782307"), headers={"X-Requested-With": "XMLHttpRequest"})
    z = zipfile.ZipFile(f)
    names = z.namelist(); print(len(names), names[:3])
    hit = [i for i in z.infolist() if "19.0_47.6_19.2_47.4" in i.filename]
    for i in hit: print(i.filename, i.file_size, i.compress_size, i.compress_type)
