"""纯标准库光栅化: 将 solve.py 的三视图与轴测图输出为 PNG。"""
import math
import struct
import zlib

SS = 3  # 超采样


class Canvas:
    def __init__(self, w, h, bg=(255, 255, 255)):
        self.w, self.h = w, h
        self.W, self.H = w * SS, h * SS
        self.buf = bytearray(bg * (self.W * self.H))

    def _set(self, x, y, c):
        i = (y * self.W + x) * 3
        self.buf[i:i + 3] = bytes(c)

    def fill_poly(self, pts, color):
        p = [(x * SS, y * SS) for x, y in pts]
        ys = [q[1] for q in p]
        y0, y1 = max(0, int(min(ys))), min(self.H - 1, int(max(ys)) + 1)
        n = len(p)
        for y in range(y0, y1 + 1):
            yc = y + 0.5
            xs = []
            for i in range(n):
                ax, ay = p[i]
                bx, by = p[(i + 1) % n]
                if (ay <= yc < by) or (by <= yc < ay):
                    xs.append(ax + (yc - ay) * (bx - ax) / (by - ay))
            xs.sort()
            for k in range(0, len(xs) - 1, 2):
                a, b = int(max(0, xs[k])), int(min(self.W - 1, xs[k + 1]))
                for x in range(a, b + 1):
                    self._set(x, y, color)

    def seg(self, p, q, width, color, dash=None):
        if dash:
            on, off = dash
            dx, dy = q[0] - p[0], q[1] - p[1]
            ln = math.hypot(dx, dy)
            if ln < 1e-9:
                return
            ux, uy, t = dx / ln, dy / ln, 0.0
            while t < ln:
                e = min(ln, t + on)
                self.seg((p[0] + ux * t, p[1] + uy * t),
                         (p[0] + ux * e, p[1] + uy * e), width, color)
                t = e + off
            return
        ax, ay = p[0] * SS, p[1] * SS
        bx, by = q[0] * SS, q[1] * SS
        rad = width * SS / 2.0
        x0 = max(0, int(min(ax, bx) - rad - 1))
        x1 = min(self.W - 1, int(max(ax, bx) + rad + 1))
        y0 = max(0, int(min(ay, by) - rad - 1))
        y1 = min(self.H - 1, int(max(ay, by) + rad + 1))
        vx, vy = bx - ax, by - ay
        L2 = vx * vx + vy * vy
        r2 = rad * rad
        for y in range(y0, y1 + 1):
            for x in range(x0, x1 + 1):
                px, py = x + 0.5 - ax, y + 0.5 - ay
                t = 0.0 if L2 == 0 else max(0.0, min(1.0, (px * vx + py * vy) / L2))
                dx, dy = px - t * vx, py - t * vy
                if dx * dx + dy * dy <= r2:
                    self._set(x, y, color)

    def polyline(self, pts, width, color, close=False, dash=None):
        n = len(pts)
        rng = range(n) if close else range(n - 1)
        for i in rng:
            self.seg(pts[i], pts[(i + 1) % n], width, color, dash)

    def downsample(self):
        w, h = self.w, self.h
        rows = []
        W = self.W
        for y in range(h):
            row = bytearray()
            for x in range(w):
                r = g = b = 0
                for sy in range(SS):
                    base = ((y * SS + sy) * W + x * SS) * 3
                    for sx in range(SS):
                        i = base + sx * 3
                        r += self.buf[i]
                        g += self.buf[i + 1]
                        b += self.buf[i + 2]
                n = SS * SS
                row += bytes((r // n, g // n, b // n))
            rows.append(row)
        return rows

    def save(self, path):
        rows = self.downsample()
        raw = b"".join(b"\x00" + bytes(r) for r in rows)

        def chunk(tag, data):
            c = struct.pack(">I", len(data)) + tag + data
            return c + struct.pack(">I", zlib.crc32(tag + data) & 0xFFFFFFFF)

        png = (b"\x89PNG\r\n\x1a\n"
               + chunk(b"IHDR", struct.pack(">IIBBBBB", self.w, self.h, 8, 2, 0, 0, 0))
               + chunk(b"IDAT", zlib.compress(raw, 9))
               + chunk(b"IEND", b""))
        open(path, "wb").write(png)


# ---- 简易矢量字体 (大写字母/数字, 0..1 方格, y 向下) ----
GLYPH = {
    "F": [[(1, 0), (0, 0), (0, 1)], [(0, .5), (.75, .5)]],
    "R": [[(0, 1), (0, 0), (.72, 0), (.72, .5), (0, .5)], [(.3, .5), (.8, 1)]],
    "O": [[(.12, 0), (.88, 0), (1, .2), (1, .8), (.88, 1), (.12, 1), (0, .8), (0, .2), (.12, 0)]],
    "N": [[(0, 1), (0, 0), (1, 1), (1, 0)]],
    "T": [[(0, 0), (1, 0)], [(.5, 0), (.5, 1)]],
    "V": [[(0, 0), (.5, 1), (1, 0)]],
    "I": [[(.5, 0), (.5, 1)]],
    "E": [[(1, 0), (0, 0), (0, 1), (1, 1)], [(0, .5), (.72, .5)]],
    "W": [[(0, 0), (.25, 1), (.5, .4), (.75, 1), (1, 0)]],
    "L": [[(0, 0), (0, 1), (1, 1)]],
    "P": [[(0, 1), (0, 0), (.75, 0), (.75, .5), (0, .5)]],
    "D": [[(0, 0), (.6, 0), (1, .25), (1, .75), (.6, 1), (0, 1), (0, 0)]],
    "3": [[(.05, .05), (.85, 0), (.4, .45), (.9, .55), (.8, .97), (.08, .95)]],
    "M": [[(0, 1), (0, 0), (.5, .55), (1, 0), (1, 1)]],
    "S": [[(1, .05), (.15, 0), (0, .3), (.85, .62), (.8, .97), (.02, .92)]],
    "U": [[(0, 0), (0, .8), (.2, 1), (.8, 1), (1, .8), (1, 0)]],
    "A": [[(0, 1), (.5, 0), (1, 1)], [(.2, .6), (.8, .6)]],
    "G": [[(1, .1), (.6, 0), (.1, .15), (0, .5), (.15, .9), (.65, 1), (1, .85), (1, .55), (.6, .55)]],
    "C": [[(1, .1), (.6, 0), (.1, .15), (0, .5), (.15, .9), (.6, 1), (1, .9)]],
    " ": [],
}


def text(cv, x, y, s, size=16, color=(17, 17, 17), width=1.6):
    cw = size * 0.62
    for ch in s.upper():
        g = GLYPH.get(ch)
        if g:
            for pl in g:
                pts = [(x + px * size * 0.55, y + py * size) for px, py in pl]
                cv.polyline(pts, width, color)
        x += cw
    return x


def main():
    import os
    import solve
    d = os.path.dirname(os.path.abspath(__file__))

    kinds = {
        "solid": (2.1, (18, 48, 110), None),
        "thin": (1.1, (18, 48, 110), None),
        "hidden": (1.4, (18, 48, 110), (7, 4)),
        "inter": (3.0, (216, 30, 44), None),
        "interh": (2.7, (216, 30, 44), (7, 4)),
        "axis": (1.0, (140, 140, 140), (14, 4)),
    }

    cv = Canvas(780, 690)
    for p, q, k in solve.SEGS:
        w, c, dash = kinds[k]
        cv.seg(p, q, w, c, dash)
    text(cv, 60, 30, "COMPLETED 3 VIEWS", 20, (17, 17, 17), 2.0)
    text(cv, 60, 58, "RED = INTERSECTION CURVE", 14, (216, 30, 44), 1.5)
    text(cv, solve.VX - 48, solve.VZ - solve.S * solve.H - 46, "V FRONT", 15, (18, 48, 110), 1.7)
    text(cv, solve.VX - 40, solve.TY + solve.S * solve.L + 32, "H TOP", 15, (18, 48, 110), 1.7)
    text(cv, solve.WX - 44, solve.VZ - solve.S * solve.H - 46, "W LEFT", 15, (18, 48, 110), 1.7)
    cv.save(os.path.join(d, "three_views.png"))

    cv2 = Canvas(660, 560)
    for pts, rgb in solve.ISO_FACES:
        cv2.fill_poly(pts, rgb)
        cv2.polyline(pts, 1.4, (27, 42, 74), close=True)
    for pts in solve.ISO_LINES:
        cv2.polyline(pts, 3.4, (216, 30, 44), close=True)
    text(cv2, 40, 28, "3D SOLID", 20, (17, 17, 17), 2.0)
    text(cv2, 40, 56, "RED = INTERSECTION CURVE", 14, (216, 30, 44), 1.5)
    cv2.save(os.path.join(d, "iso.png"))
    print("PNG written")


if __name__ == "__main__":
    main()
