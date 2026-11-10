"""导出可交互 3D 网页 (单文件, 无外部依赖)。"""
import json
import os

import solve

d = os.path.dirname(os.path.abspath(__file__))

def rnd(v):
    return [round(c, 4) + 0.0 for c in v]


data = {
    "solids": [
        {"faces": [[rnd(v) for v in f] for f in solve.SOLIDS[0]], "color": [96, 134, 202],
         "name": "六棱台"},
        {"faces": [[rnd(v) for v in f] for f in solve.SOLIDS[1]], "color": [226, 136, 100],
         "name": "三棱柱(后段)"},
        {"faces": [[rnd(v) for v in f] for f in solve.SOLIDS[2]], "color": [226, 136, 100],
         "name": "三棱柱(前段)"},
    ],
    "curves": [[rnd(v) for v in solve.INTER_BACK], [rnd(v) for v in solve.INTER_FRONT]],
    "dims": {"R": solve.R, "r": solve.r, "H": solve.H,
             "a": solve.A, "zt": solve.ZT, "zb": solve.ZB, "L": solve.L},
}

HTML = """<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1,user-scalable=no">
<title>六棱台与三棱柱相贯 - 交互式 3D</title>
<style>
  html,body{margin:0;height:100%%;background:#eef1f6;font-family:system-ui,"Microsoft YaHei",sans-serif;overflow:hidden}
  #cv{display:block;width:100%%;height:100%%;touch-action:none;cursor:grab}
  #cv.drag{cursor:grabbing}
  .panel{position:fixed;left:14px;top:14px;background:rgba(255,255,255,.92);border:1px solid #c9d2e0;
         border-radius:10px;padding:12px 14px;font-size:13px;color:#22304a;line-height:1.8;
         box-shadow:0 4px 14px rgba(0,0,0,.08);max-width:260px}
  .panel h1{font-size:15px;margin:0 0 6px}
  .panel b{color:#d81e2c}
  label{display:block;cursor:pointer;user-select:none}
  #hint{position:fixed;right:14px;bottom:12px;font-size:12px;color:#5a6882}
  button{font:inherit;margin-top:6px;padding:4px 10px;border:1px solid #9fb0c9;background:#fff;
         border-radius:6px;cursor:pointer}
</style>
</head>
<body>
<canvas id="cv"></canvas>
<div class="panel">
  <h1>六棱台 × 三棱柱 相贯</h1>
  <div><b>红色</b> = 相贯线（前后各一个空间三角形）</div>
  <label><input type="checkbox" id="ck_curve" checked> 显示相贯线</label>
  <label><input type="checkbox" id="ck_edge" checked> 显示棱线</label>
  <label><input type="checkbox" id="ck_prism" checked> 显示三棱柱</label>
  <label><input type="checkbox" id="ck_spin"> 自动旋转</label>
  <button id="reset">复位视角</button>
</div>
<div id="hint">拖拽旋转 · 滚轮/双指缩放 · 右键拖拽平移</div>
<script>
const DATA = %s;
const cv = document.getElementById('cv'), ctx = cv.getContext('2d');
let yaw = -0.62, pitch = 0.52, zoom = 3.4, panX = 0, panY = 0, dpr = 1;

function resize(){
  dpr = Math.min(window.devicePixelRatio || 1, 2);
  cv.width = Math.floor(innerWidth * dpr);
  cv.height = Math.floor(innerHeight * dpr);
  draw();
}
addEventListener('resize', resize);

function rot(p){
  const cy = Math.cos(yaw), sy = Math.sin(yaw);
  const cp = Math.cos(pitch), sp = Math.sin(pitch);
  const x = p[0]*cy + p[1]*sy;
  const y = -p[0]*sy + p[1]*cy;
  const z = p[2];
  // pitch 绕屏幕水平轴
  return [x, y*cp - z*sp, y*sp + z*cp];
}
// 相机坐标: X 右, Y 深度(越大越远), Z 上 -> 屏幕
function project(p){
  const q = rot([p[0], p[1], p[2] - DATA.dims.H/2]);
  return [cv.width/2 + panX*dpr + zoom*dpr*q[0], cv.height/2 + panY*dpr - zoom*dpr*q[2], q[1]];
}
function sub(a,b){return [a[0]-b[0],a[1]-b[1],a[2]-b[2]];}
function cross(a,b){return [a[1]*b[2]-a[2]*b[1],a[2]*b[0]-a[0]*b[2],a[0]*b[1]-a[1]*b[0]];}
function norm(v){const m=Math.hypot(v[0],v[1],v[2])||1;return [v[0]/m,v[1]/m,v[2]/m];}
function cen(f){const n=f.length;const s=[0,0,0];for(const v of f){s[0]+=v[0];s[1]+=v[1];s[2]+=v[2];}
  return [s[0]/n,s[1]/n,s[2]/n];}

const LIGHT = norm([-0.35, -0.75, 0.56]);  // 相机空间光源

function draw(){
  ctx.setTransform(1,0,0,1,0,0);
  ctx.fillStyle = '#eef1f6';
  ctx.fillRect(0,0,cv.width,cv.height);
  const showPrism = ck_prism.checked, showEdge = ck_edge.checked, showCurve = ck_curve.checked;
  const items = [];

  DATA.solids.forEach((sol, si) => {
    if (si > 0 && !showPrism) return;
    sol.faces.forEach(f => {
      const cf = cen(f);
      const nWorld = norm(cross(sub(f[1],f[0]), sub(f[2],f[0])));
      // 判断外法向
      const allc = cen(sol.faces.flat());
      const sgn = (nWorld[0]*(cf[0]-allc[0]) + nWorld[1]*(cf[1]-allc[1]) + nWorld[2]*(cf[2]-allc[2])) >= 0 ? 1 : -1;
      const nr = rot([nWorld[0]*sgn, nWorld[1]*sgn, nWorld[2]*sgn]);
      if (nr[1] >= -1e-6) return;                       // 背面剔除 (相机在 -Y 方向)
      const pts = f.map(project);
      const depth = rot(cf)[1];
      const lam = Math.max(0, nr[0]*LIGHT[0] + nr[1]*LIGHT[1] + nr[2]*LIGHT[2]);
      const sh = 0.42 + 0.58*lam;
      const c = sol.color.map(v => Math.min(255, Math.round(v*sh + 38)));
      items.push({d: depth, kind: 'face', pts, fill: 'rgb('+c+')'});
    });
  });

  if (showCurve) {
    const YB = DATA.dims.R*Math.sqrt(3)/2, YT = DATA.dims.r*Math.sqrt(3)/2;
    const SLOPE = (YB - YT) / DATA.dims.H;
    DATA.curves.forEach(loop => {
      const sgn = loop[0][1] >= 0 ? 1 : -1;
      // 相贯线所在的棱台侧面: 外法向与面心
      const nr = rot(norm([0, sgn, sgn*SLOPE]));
      if (nr[1] >= -1e-6) return;                       // 宿主面背对观察者 -> 相贯线不可见
      const hostD = rot([0, sgn*(YB+YT)/2, DATA.dims.H/2])[1] - 0.5;
      for (let i = 0; i < loop.length; i++) {
        const a = loop[i], b = loop[(i+1)%%loop.length];
        items.push({d: hostD, kind: 'line',
                    pts: [project(a), project(b)], stroke: '#d81e2c', w: 3.4});
      }
    });
  }

  items.sort((p,q) => q.d - p.d);                       // 远的先画
  for (const it of items) {
    ctx.beginPath();
    ctx.moveTo(it.pts[0][0], it.pts[0][1]);
    for (let i = 1; i < it.pts.length; i++) ctx.lineTo(it.pts[i][0], it.pts[i][1]);
    if (it.kind === 'face') {
      ctx.closePath();
      ctx.fillStyle = it.fill; ctx.fill();
      if (showEdge) { ctx.lineWidth = 1.2*dpr; ctx.strokeStyle = '#1b2a4a'; ctx.lineJoin='round'; ctx.stroke(); }
    } else {
      ctx.lineWidth = it.w*dpr; ctx.strokeStyle = it.stroke;
      ctx.lineCap = 'round'; ctx.stroke();
    }
  }
}

// ---- 交互 ----
let drag = null;
cv.addEventListener('pointerdown', e => {
  try { cv.setPointerCapture(e.pointerId); } catch (_) {}
  drag = {x: e.clientX, y: e.clientY, pan: e.button === 2};
  cv.classList.add('drag');
});
cv.addEventListener('pointermove', e => {
  if (!drag) return;
  const dx = e.clientX - drag.x, dy = e.clientY - drag.y;
  drag.x = e.clientX; drag.y = e.clientY;
  if (drag.pan) { panX += dx; panY += dy; }
  else {
    yaw += dx * 0.009;
    pitch = Math.max(-1.52, Math.min(1.52, pitch + dy * 0.009));
  }
  draw();
});
function endDrag(e){ drag = null; cv.classList.remove('drag'); }
cv.addEventListener('pointerup', endDrag);
cv.addEventListener('pointercancel', endDrag);
cv.addEventListener('contextmenu', e => e.preventDefault());
cv.addEventListener('wheel', e => {
  e.preventDefault();
  zoom = Math.max(0.8, Math.min(22, zoom * Math.exp(-e.deltaY * 0.0012)));
  draw();
}, {passive: false});

// 双指缩放
let pinch = null;
cv.addEventListener('touchmove', e => {
  if (e.touches.length !== 2) return;
  e.preventDefault();
  const d = Math.hypot(e.touches[0].clientX - e.touches[1].clientX,
                       e.touches[0].clientY - e.touches[1].clientY);
  if (pinch) { zoom = Math.max(0.8, Math.min(22, zoom * d / pinch)); draw(); }
  pinch = d;
}, {passive: false});
cv.addEventListener('touchend', () => { pinch = null; });

for (const id of ['ck_curve','ck_edge','ck_prism']) document.getElementById(id).onchange = draw;
document.getElementById('reset').onclick = () => {
  yaw = -0.62; pitch = 0.52; zoom = 3.4; panX = 0; panY = 0; draw();
};
let spinning = false;
ck_spin.onchange = () => {
  spinning = ck_spin.checked;
  if (spinning) requestAnimationFrame(tick);
};
function tick(){ if (!spinning) return; yaw += 0.008; draw(); requestAnimationFrame(tick); }

resize();
</script>
</body>
</html>
"""

open(os.path.join(d, "model_3d.html"), "w").write(HTML % json.dumps(data))
print("model_3d.html written,", os.path.getsize(os.path.join(d, "model_3d.html")), "bytes")
