"""六棱台与三棱柱相贯：求相贯线、补全三投影、生成 3D 模型 (STL)。

坐标系: X 右, Y 向后(远离观察者), Z 上。
六棱台: 底面 z=0 正六边形 R=44 (顶点在 ±X 轴, 前后为平边), 顶面 z=H r=18。
三棱柱: 截面(XZ)倒三角 (-a,zt),(a,zt),(0,zb), 沿 Y 由 -L 到 +L 贯穿。
"""
import math

R, r, H = 44.0, 18.0, 48.0
A, ZT, ZB, L = 12.0, 26.0, 8.0, 42.0

SQ3 = math.sqrt(3.0)


def hexagon(rad, z):
    return [(rad * math.cos(math.radians(60 * k)),
             rad * math.sin(math.radians(60 * k)), z) for k in range(6)]


BOT = hexagon(R, 0.0)
TOP = hexagon(r, H)

# 棱台前后两个侧面所在平面: y = +-(YB - SLOPE*z)
YB = R * SQ3 / 2.0          # 底面平边的 y (38.1051)
YT = r * SQ3 / 2.0          # 顶面平边的 y (15.5885)
SLOPE = (YB - YT) / H


def face_y(z):
    """棱台前/后侧面在高度 z 处的 y (取正值)。"""
    return YB - SLOPE * z


def half_width(z):
    """棱台前/后侧面在高度 z 处的 x 半宽。"""
    return (R / 2.0) + ((r / 2.0) - (R / 2.0)) * z / H


# ---------------- 相贯线 ----------------
# 棱柱三条棱与棱台前后侧面的交点
EDGES = [(-A, ZT), (A, ZT), (0.0, ZB)]
INTER_BACK = [(x, face_y(z), z) for x, z in EDGES]
INTER_FRONT = [(x, -face_y(z), z) for x, z in EDGES]

# ---------------- 几何体 ----------------


def frustum_faces():
    f = [list(reversed(BOT)), TOP]
    for i in range(6):
        j = (i + 1) % 6
        f.append([BOT[i], BOT[j], TOP[j], TOP[i]])
    return f


def prism_segment(sign):
    """棱柱伸出棱台外的一段: sign=+1 为后段 (y 大), -1 为前段。"""
    end = [(x, sign * L, z) for x, z in EDGES]
    cut = [(x, sign * face_y(z), z) for x, z in EDGES]
    if sign > 0:
        lo, hi = cut, end
    else:
        lo, hi = end, cut
    faces = [list(reversed(lo)), hi]
    for i in range(3):
        j = (i + 1) % 3
        faces.append([lo[i], lo[j], hi[j], hi[i]])
    return faces


SOLIDS = [frustum_faces(), prism_segment(1), prism_segment(-1)]


def normal(p):
    ax = (p[1][0] - p[0][0], p[1][1] - p[0][1], p[1][2] - p[0][2])
    bx = (p[2][0] - p[0][0], p[2][1] - p[0][1], p[2][2] - p[0][2])
    n = (ax[1] * bx[2] - ax[2] * bx[1],
         ax[2] * bx[0] - ax[0] * bx[2],
         ax[0] * bx[1] - ax[1] * bx[0])
    m = math.sqrt(sum(c * c for c in n)) or 1.0
    return tuple(c / m for c in n)


def centroid(p):
    n = len(p)
    return tuple(sum(v[i] for v in p) / n for i in range(3))


def outward(faces):
    """保证每个面法向朝外(相对该实体质心)。"""
    allp = [v for f in faces for v in f]
    c = centroid(allp)
    fixed = []
    for f in faces:
        n = normal(f)
        fc = centroid(f)
        d = sum(n[i] * (fc[i] - c[i]) for i in range(3))
        fixed.append(f if d > 0 else list(reversed(f)))
    return fixed


SOLIDS = [outward(s) for s in SOLIDS]


def write_stl(path):
    tris = []
    for solid in SOLIDS:
        for f in solid:
            for i in range(1, len(f) - 1):
                tris.append((f[0], f[i], f[i + 1]))
    with open(path, "w") as fh:
        fh.write("solid hex_frustum_tri_prism\n")
        for t in tris:
            n = normal(t)
            fh.write("  facet normal %.6f %.6f %.6f\n    outer loop\n" % n)
            for v in t:
                fh.write("      vertex %.6f %.6f %.6f\n" % v)
            fh.write("    endloop\n  endfacet\n")
        fh.write("endsolid hex_frustum_tri_prism\n")
    return len(tris)


# ---------------- SVG ----------------
S = 2.6        # 缩放
VX, VZ = 250.0, 360.0      # 主视图原点 (X=0,Z=0)
TY = 496.0                 # 俯视图 Y=0 的屏幕 y
WX = 600.0                 # 左视图 Y=0 的屏幕 x


def pV(x, z):
    return (VX + S * x, VZ - S * z)


def pH(x, y):
    return (VX + S * x, TY + S * y)


def pW(y, z):
    return (WX + S * y, VZ - S * z)


ST = {
    "solid": 'stroke="#12306e" stroke-width="2.1" fill="none" stroke-linecap="round"',
    "thin": 'stroke="#12306e" stroke-width="1.1" fill="none"',
    "hidden": 'stroke="#12306e" stroke-width="1.3" fill="none" stroke-dasharray="7,4"',
    "inter": 'stroke="#d81e2c" stroke-width="3" fill="none" stroke-linecap="round"',
    "interh": 'stroke="#d81e2c" stroke-width="2.6" fill="none" stroke-dasharray="7,4"',
    "axis": 'stroke="#7a7a7a" stroke-width="1" fill="none" stroke-dasharray="14,3,3,3"',
}
out = []
SEGS = []


def line(p, q, kind):
    SEGS.append((p, q, kind))
    out.append('<line x1="%.2f" y1="%.2f" x2="%.2f" y2="%.2f" %s/>' % (p[0], p[1], q[0], q[1], ST[kind]))


def poly(pts, kind, close=True):
    for i in range(len(pts) - (0 if close else 1)):
        line(pts[i], pts[(i + 1) % len(pts)], kind)


def text(x, y, s, size=15, color="#111", anchor="start", weight="normal"):
    out.append('<text x="%.1f" y="%.1f" font-size="%d" fill="%s" text-anchor="%s" '
               'font-weight="%s" font-family="DejaVu Sans, Noto Sans CJK SC, sans-serif">%s</text>'
               % (x, y, size, color, anchor, weight, s))


# ===== 主视图 (V面, XZ) =====
line(pV(-R, 0), pV(R, 0), "solid")
line(pV(-r, H), pV(r, H), "solid")
line(pV(R, 0), pV(r, H), "solid")
line(pV(-R, 0), pV(-r, H), "solid")
# 前后侧棱 x=±R/2 -> ±r/2
line(pV(R / 2, 0), pV(r / 2, H), "solid")
line(pV(-R / 2, 0), pV(-r / 2, H), "solid")
# 三棱柱端面三角 (可见)
tri = [pV(-A, ZT), pV(A, ZT), pV(0, ZB)]
poly(tri, "solid")
# 相贯线在 V 面积聚于三角形上
poly(tri, "inter")
line(pV(0, -14), pV(0, H + 14), "axis")

# ===== 俯视图 (H面, XY) =====
poly([pH(v[0], v[1]) for v in BOT], "solid")
poly([pH(v[0], v[1]) for v in TOP], "solid")
for i in range(6):
    line(pH(BOT[i][0], BOT[i][1]), pH(TOP[i][0], TOP[i][1]), "solid")
# 棱柱两条侧边 x=±A
for sx in (-A, A):
    line(pH(sx, -L), pH(sx, -YB), "solid")
    line(pH(sx, YB), pH(sx, L), "solid")
    line(pH(sx, -YB), pH(sx, YB), "hidden")
# 棱柱端面
line(pH(-A, L), pH(A, L), "solid")
line(pH(-A, -L), pH(A, -L), "solid")
# 棱柱下棱 x=0 (棱台外可见)
line(pH(0, YB), pH(0, L), "solid")
line(pH(0, -L), pH(0, -YB), "solid")
# 相贯线水平投影: 两个三角形 (被棱台顶面遮挡 -> 虚线)
for s in (1, -1):
    pts = [pH(p[0], p[1]) for p in (INTER_BACK if s > 0 else INTER_FRONT)]
    poly(pts, "interh")
line(pH(0, -L - 14), pH(0, L + 14), "axis")
line(pH(-R - 14, 0), pH(R + 14, 0), "axis")

# ===== 左视图 (W面, YZ) =====
line(pW(-YB, 0), pW(YB, 0), "solid")
line(pW(-YT, H), pW(YT, H), "solid")
line(pW(YB, 0), pW(YT, H), "solid")
line(pW(-YB, 0), pW(-YT, H), "solid")
# 相贯线在 W 面积聚于棱台侧面轮廓线 z∈[ZB,ZT]
for s in (1, -1):
    line(pW(s * face_y(ZB), ZB), pW(s * face_y(ZT), ZT), "inter")
# 棱柱顶面边 z=ZT
line(pW(-face_y(ZT), ZT), pW(face_y(ZT), ZT), "hidden")
line(pW(face_y(ZT), ZT), pW(L, ZT), "solid")
line(pW(-L, ZT), pW(-face_y(ZT), ZT), "solid")
# 棱柱下棱 z=ZB
line(pW(-face_y(ZB), ZB), pW(face_y(ZB), ZB), "hidden")
line(pW(face_y(ZB), ZB), pW(L, ZB), "solid")
line(pW(-L, ZB), pW(-face_y(ZB), ZB), "solid")
# 棱柱端面
line(pW(L, ZB), pW(L, ZT), "solid")
line(pW(-L, ZB), pW(-L, ZT), "solid")
line(pW(0, -14), pW(0, H + 14), "axis")

text(VX, VZ - S * H - 34, "主视图 (V)", 17, "#12306e", "middle", "bold")
text(VX, TY + S * L + 46, "俯视图 (H)", 17, "#12306e", "middle", "bold")
text(WX, VZ - S * H - 34, "左视图 (W)", 17, "#12306e", "middle", "bold")
text(70, 44, "六棱台与三棱柱相贯线的三投影", 22, "#111", "start", "bold")
text(70, 70, "红色 = 相贯线；虚线 = 不可见；V 面与 W 面上相贯线积聚", 14, "#d81e2c")

svg_views = ('<svg xmlns="http://www.w3.org/2000/svg" width="780" height="690" '
             'viewBox="0 0 780 690"><rect width="780" height="690" fill="#ffffff"/>'
             + "\n".join(out) + "</svg>")

# ===== 轴测图 =====
iso = []
_v = (1 / SQ3, -1 / SQ3, 1 / SQ3)          # 由物体指向观察者 (右前上方)
_r = (0.70710678, 0.70710678, 0.0)         # 屏幕右 = normalize(up x v)
_u = (_v[1] * _r[2] - _v[2] * _r[1],       # 屏幕上 = v x r
      _v[2] * _r[0] - _v[0] * _r[2],
      _v[0] * _r[1] - _v[1] * _r[0])

ISO_S = 3.2


def piso(p):
    sx = sum(p[i] * _r[i] for i in range(3))
    sy = sum(p[i] * _u[i] for i in range(3))
    return (330 + ISO_S * sx, 300 - ISO_S * sy)


view_dir = _v
faces = []
for si, solid in enumerate(SOLIDS):
    for f in solid:
        n = normal(f)
        dot = sum(n[i] * view_dir[i] for i in range(3))
        if dot <= 1e-9:
            continue
        c = centroid(f)
        depth = sum(c[i] * view_dir[i] for i in range(3))
        shade = 0.45 + 0.55 * dot
        faces.append((depth, f, shade, si))
faces.sort(key=lambda t: t[0])
ISO_FACES = []
ISO_LINES = []
for depth, f, shade, si in faces:
    base = (116, 152, 214) if si == 0 else (232, 150, 120)
    rgb = tuple(min(255, int(c * shade + 40)) for c in base)
    col = "#%02x%02x%02x" % rgb
    pts2 = [piso(v) for v in f]
    ISO_FACES.append((pts2, rgb))
    pts = " ".join("%.2f,%.2f" % p for p in pts2)
    iso.append('<polygon points="%s" fill="%s" stroke="#1b2a4a" stroke-width="1.4" '
               'stroke-linejoin="round"/>' % (pts, col))
for s in (-1,):
    pts = INTER_BACK if s > 0 else INTER_FRONT
    pts2 = [piso(v) for v in pts]
    ISO_LINES.append(pts2)
    pp = " ".join("%.2f,%.2f" % p for p in pts2)
    iso.append('<polygon points="%s" fill="none" stroke="#d81e2c" stroke-width="3.4" '
               'stroke-linejoin="round"/>' % pp)
iso.append('<text x="40" y="44" font-size="21" font-weight="bold" fill="#111" '
           'font-family="DejaVu Sans, Noto Sans CJK SC, sans-serif">3D 立体 (红线为相贯线)</text>')
svg_iso = ('<svg xmlns="http://www.w3.org/2000/svg" width="660" height="560" '
           'viewBox="0 0 660 560"><rect width="660" height="560" fill="#ffffff"/>'
           + "\n".join(iso) + "</svg>")

if __name__ == "__main__":
    import os
    d = os.path.dirname(os.path.abspath(__file__))
    open(os.path.join(d, "three_views.svg"), "w").write(svg_views)
    open(os.path.join(d, "iso.svg"), "w").write(svg_iso)
    n = write_stl(os.path.join(d, "model.stl"))
    print("STL triangles:", n)
    print("YB=%.4f YT=%.4f slope=%.6f" % (YB, YT, SLOPE))
    print("相贯线(后) :", [tuple(round(c, 4) for c in p) for p in INTER_BACK])
    print("相贯线(前) :", [tuple(round(c, 4) for c in p) for p in INTER_FRONT])
    print("半宽 z=ZT: %.4f  z=ZB: %.4f (需 > a=%.1f)" % (half_width(ZT), half_width(ZB), A))
    print("棱台最大 y at ZB: %.4f (需 < L=%.1f)" % (face_y(ZB), L))
