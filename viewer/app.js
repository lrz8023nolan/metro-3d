/* metro-3d · 立体地铁线路图查看器（数据驱动，任意城市）
   交互：拖动旋转 / 滚轮缩放 / 右键(或 Shift)平移 / 点击站点查看详情
   纵向映射：y = SOFT·tanh((alt-REF)/SOFT)·k（远山软压缩）
   地下段：y = 地面映射值 − 埋深 × 埋深强化 × k
   拾取：屏幕空间最近站点（数百站台层实例仍流畅）
*/
(function () {
  'use strict';

  var DATA = window.METRO_DATA;
  if (!DATA) { document.getElementById('fatal').style.display = 'flex'; return; }
  var M = DATA.meta;
  var APP = window.METRO_APP || {};

  var KX = 111320 * Math.cos(M.lat0 * Math.PI / 180);
  var KY = 110540;
  var REF = M.ref_alt;
  var SOFT = 80;
  var xOf = function (lon) { return (lon - M.lon0) * KX; };
  var zOf = function (lat) { return -(lat - M.lat0) * KY; };
  var visY = function (alt, k) { return SOFT * Math.tanh((alt - REF) / SOFT) * k; };

  var state = { k: 80, g: 3, labels: true, terrain: true, rotate: true, dirty: false };

  /* ---------- 渲染器 ---------- */
  var canvas = document.getElementById('scene');
  var renderer;
  try {
    renderer = new THREE.WebGLRenderer({ canvas: canvas, antialias: true, alpha: true });
  } catch (err) {
    document.getElementById('fatal').style.display = 'flex';
    return;
  }
  renderer.setPixelRatio(Math.min(window.devicePixelRatio || 1, 2));
  renderer.setSize(window.innerWidth, window.innerHeight);
  renderer.outputEncoding = THREE.sRGBEncoding;
  renderer.toneMapping = THREE.ACESFilmicToneMapping;
  renderer.toneMappingExposure = 1.12;

  var scene = new THREE.Scene();
  var camera = new THREE.PerspectiveCamera(45, window.innerWidth / window.innerHeight, 50, 500000);

  scene.add(new THREE.HemisphereLight(0xbcd2ff, 0x10141c, 0.6));
  var sun = new THREE.DirectionalLight(0xffffff, 0.72);
  sun.position.set(60000, 95000, 42000);
  scene.add(sun);
  var fill = new THREE.DirectionalLight(0x88aaff, 0.22);
  fill.position.set(-55000, 38000, -62000);
  scene.add(fill);

  /* ---------- 范围与轨道参数 ---------- */
  var minX = 1e18, maxX = -1e18, minZ = 1e18, maxZ = -1e18;
  DATA.lines.forEach(function (L) {
    L.geometry.forEach(function (p) {
      var x = xOf(p[0]), z = zOf(p[1]);
      if (x < minX) minX = x; if (x > maxX) maxX = x;
      if (z < minZ) minZ = z; if (z > maxZ) maxZ = z;
    });
  });
  var CENTER = { x: (minX + maxX) / 2, z: (minZ + maxZ) / 2 };
  var SPAN_X = maxX - minX, SPAN_Z = maxZ - minZ;
  var FIT_ISO = Math.max(SPAN_Z * 0.8, SPAN_X * 0.72);
  var FIT_TOP = SPAN_Z / 0.828 * 0.95;
  var FIT_SIDE = SPAN_X * 0.85;
  var WIDE_T = FIT_ISO * 0.62;         // 低于该视距显示全部站名，否则只显示枢纽/实测站
  var plainY = function () { return visY(55, state.k); };

  var orbit = { theta: 1.24, phi: 1.12, dist: FIT_ISO, target: new THREE.Vector3(CENTER.x, plainY(), CENTER.z) };

  /* ---------- 地形 ---------- */
  var T = M.terrain;
  var terrGeo = new THREE.BufferGeometry();
  var terrElev = T.elev;
  (function buildTerrain() {
    var cols = T.cols, rows = T.rows, step = T.step, pos = new Float32Array(cols * rows * 3), i = 0;
    for (var r = 0; r < rows; r++) {
      for (var c = 0; c < cols; c++) {
        pos[i++] = xOf(T.lon0 + c * step);
        pos[i++] = 0;
        pos[i++] = zOf(T.lat0 + r * step);
      }
    }
    var idx = [];
    for (var r2 = 0; r2 < rows - 1; r2++) {
      for (var c2 = 0; c2 < cols - 1; c2++) {
        var a = r2 * cols + c2, b = a + 1, d = a + cols, e = d + 1;
        idx.push(a, b, d, b, e, d);
      }
    }
    terrGeo.setIndex(idx);
    terrGeo.setAttribute('position', new THREE.BufferAttribute(pos, 3));
  })();
  var terrMat = new THREE.MeshStandardMaterial({
    color: 0x39465c, roughness: 1, metalness: 0, transparent: true, opacity: 0.3,
    side: THREE.DoubleSide, depthWrite: false
  });
  var terrain = new THREE.Mesh(terrGeo, terrMat);
  scene.add(terrain);

  function updateTerrain() {
    var attr = terrGeo.getAttribute('position');
    for (var i = 0; i < terrElev.length; i++) attr.setY(i, visY(terrElev[i], state.k));
    attr.needsUpdate = true;
    terrGeo.computeVertexNormals();
  }

  /* ---------- 线路与车站 ---------- */
  var sphereGeo = new THREE.SphereGeometry(1, 14, 10);
  var ringMat = new THREE.MeshBasicMaterial({ color: 0xffffff, wireframe: true, transparent: true, opacity: 0.3 });
  var dropMat = new THREE.LineBasicMaterial({ color: 0xcfe0ff, transparent: true, opacity: 0.15 });

  function lineY(p) {
    var d = p[2] - p[3];
    if (d > 0) return visY(p[2], state.k) - d * state.g * state.k;
    return visY(p[3], state.k);
  }
  function stationY(st) {
    var d = st.g - st.t;
    if (d > 0) return visY(st.g, state.k) - d * state.g * state.k;
    return visY(st.t, state.k);
  }

  var LINES = DATA.lines.map(function (def) {
    var group = new THREE.Group();
    scene.add(group);
    var tubeMat = new THREE.MeshStandardMaterial({
      color: new THREE.Color(def.colour), emissive: new THREE.Color(def.colour),
      emissiveIntensity: 0.5, roughness: 0.35, metalness: 0.25
    });
    var rec = { def: def, group: group, tubeMat: tubeMat, tube: null, stations: [], drops: null };

    def.stations.forEach(function (st, idx) {
      var big = st.lines.length > 1;
      var sr = big ? 170 : 130;
      var mesh = new THREE.Mesh(sphereGeo, tubeMat);
      mesh.scale.setScalar(sr);
      mesh.userData = { sr: sr };
      group.add(mesh);
      var ring = null;
      if (st.dk === 'truth') {
        ring = new THREE.Mesh(sphereGeo, ringMat);
        ring.scale.setScalar(sr * 1.8);
        group.add(ring);
      }
      var sObj = { st: st, mesh: mesh, ring: ring, x: xOf(st.lon), z: zOf(st.lat), label: null };
      // 站名标注（同名站只在"实测/最深"实例上创建，避免重复标签）
      if (st.lab) {
        var el = document.createElement('div');
        var cls = st.dk === 'truth' ? '' : (st.dk === 'est' ? ' est' : ' up');
        var tag = st.dk === 'truth' ? (st.dep + 'm') : (st.dk === 'est' ? ('~' + st.dep + 'm') : '');
        el.className = 'lbl' + cls;
        el.innerHTML = st.n + (tag ? '<span class="d">' + tag + '</span>' : '');
        el.style.display = 'none';
        document.getElementById('labels').appendChild(el);
        sObj.label = el;
        sObj.major = (st.lines.length >= 3 || st.dk === 'truth');
      }
      rec.stations.push(sObj);
    });

    // 落地指示线：整条线合并为一个 LineSegments
    var dropGeo = new THREE.BufferGeometry();
    dropGeo.setAttribute('position', new THREE.BufferAttribute(new Float32Array(def.stations.length * 6), 3));
    rec.drops = new THREE.LineSegments(dropGeo, dropMat);
    group.add(rec.drops);

    return rec;
  });

  function rebuildTube(rec) {
    var pts = rec.def.geometry.map(function (p) {
      return new THREE.Vector3(xOf(p[0]), lineY(p), zOf(p[1]));
    });
    var curve = new THREE.CatmullRomCurve3(pts, false, 'centripetal', 0.5);
    var segs = Math.min(1000, Math.max(160, pts.length * 2));
    curve.arcLengthDivisions = segs;
    var geo = new THREE.TubeGeometry(curve, segs, 100, 7, false);
    if (rec.tube) { rec.tube.geometry.dispose(); rec.tube.geometry = geo; }
    else { rec.tube = new THREE.Mesh(geo, rec.tubeMat); rec.group.add(rec.tube); }

    // 地表投影线（帮助对照地下段走向与深度偏移）
    var tracePts = rec.def.geometry.map(function (p) {
      return new THREE.Vector3(xOf(p[0]), visY(p[2], state.k) + 20, zOf(p[1]));
    });
    if (!rec.trace) {
      rec.trace = new THREE.Line(
        new THREE.BufferGeometry().setFromPoints(tracePts),
        new THREE.LineBasicMaterial({ color: new THREE.Color(rec.def.colour), transparent: true, opacity: 0.3 })
      );
      rec.group.add(rec.trace);
    } else {
      rec.trace.geometry.dispose();
      rec.trace.geometry = new THREE.BufferGeometry().setFromPoints(tracePts);
    }
  }

  function updateStations(rec) {
    var arr = rec.drops.geometry.getAttribute('position');
    rec.stations.forEach(function (s, i) {
      var y = stationY(s.st), yg = visY(s.st.g, state.k), x = s.x, z = s.z;
      s.mesh.position.set(x, y, z);
      if (s.ring) s.ring.position.set(x, y, z);
      arr.setXYZ(i * 2, x, y, z);
      arr.setXYZ(i * 2 + 1, x, yg, z);
    });
    arr.needsUpdate = true;
    rec.drops.geometry.computeBoundingSphere();
  }

  function rebuildAll() {
    updateTerrain();
    LINES.forEach(function (rec) { rebuildTube(rec); updateStations(rec); });
    orbit.target.y = plainY();
  }
  rebuildAll();

  /* ---------- 屏幕投影（标注 + 拾取共用） ---------- */
  var v3 = new THREE.Vector3();
  function projectStations() {
    for (var li = 0; li < LINES.length; li++) {
      var rec = LINES[li];
      var vis = rec.group.visible;
      for (var si = 0; si < rec.stations.length; si++) {
        var s = rec.stations[si];
        if (!vis) { s.svis = false; continue; }
        v3.set(s.x, stationY(s.st), s.z).project(camera);
        if (v3.z > 1) { s.svis = false; continue; }
        s.sx = (v3.x * 0.5 + 0.5) * window.innerWidth;
        s.sy = (-v3.y * 0.5 + 0.5) * window.innerHeight;
        s.svis = s.sx > -60 && s.sx < window.innerWidth + 60 && s.sy > -60 && s.sy < window.innerHeight + 60;
      }
    }
  }
  function nearestStation(cx, cy, rad) {
    var best = null, bd = rad * rad;
    for (var li = 0; li < LINES.length; li++) {
      var rec = LINES[li];
      if (!rec.group.visible) continue;
      for (var si = 0; si < rec.stations.length; si++) {
        var s = rec.stations[si];
        if (!s.svis) continue;
        var dx = s.sx - cx, dy = s.sy - cy, d2 = dx * dx + dy * dy;
        if (d2 < bd) { bd = d2; best = s; }
      }
    }
    return best;
  }

  /* ---------- 标签（含简单防重叠） ---------- */
  var rects = [];
  function overlaps(x, y, w) {
    for (var i = 0; i < rects.length; i++) {
      var r = rects[i];
      if (Math.abs(x - r.x) < (w + r.w) / 2 + 10 && Math.abs(y - r.y) < 17) return true;
    }
    return false;
  }
  function updateLabels() {
    rects.length = 0;
    var wide = orbit.dist < WIDE_T;
    var cands = [];
    for (var li = 0; li < LINES.length; li++) {
      var rec = LINES[li];
      for (var si = 0; si < rec.stations.length; si++) {
        var s = rec.stations[si];
        var el = s.label;
        if (!el) continue;
        if (!state.labels || !s.svis || (!wide && !s.major)) { el.style.display = 'none'; continue; }
        cands.push({ el: el, x: s.sx, y: s.sy - 16, prio: (s.st.dk === 'truth' ? 2 : 0) + (s.major ? 1 : 0) + (wide ? 1 : 0) });
      }
    }
    cands.sort(function (a, b) { return b.prio - a.prio; });
    cands.forEach(function (c) {
      if (c.el._w == null) {
        c.el.style.display = 'block';
        c.el._w = c.el.offsetWidth || 60;
      }
      if (overlaps(c.x, c.y, c.el._w)) { c.el.style.display = 'none'; return; }
      rects.push({ x: c.x, y: c.y, w: c.el._w });
      c.el.style.display = 'block';
      c.el.style.transform = 'translate(' + c.x.toFixed(1) + 'px,' + c.y.toFixed(1) + 'px) translate(-50%,-100%)';
    });
  }

  /* ---------- 相机与控制 ---------- */
  function applyCamera() {
    var sp = Math.sin(orbit.phi), cp = Math.cos(orbit.phi);
    camera.position.set(
      orbit.target.x + orbit.dist * sp * Math.cos(orbit.theta),
      orbit.target.y + orbit.dist * cp,
      orbit.target.z + orbit.dist * sp * Math.sin(orbit.theta)
    );
    camera.lookAt(orbit.target);
  }

  var drag = null;
  var pointer = { x: 0, y: 0, inside: false, moved: false };

  function pan(dx, dy) {
    var scale = 2 * orbit.dist * Math.tan(camera.fov * Math.PI / 360) / canvas.clientHeight;
    var right = new THREE.Vector3().setFromMatrixColumn(camera.matrix, 0);
    var up = new THREE.Vector3().setFromMatrixColumn(camera.matrix, 1);
    orbit.target.addScaledVector(right, -dx * scale);
    orbit.target.addScaledVector(up, dy * scale);
  }

  canvas.addEventListener('contextmenu', function (e) { e.preventDefault(); });
  canvas.addEventListener('pointerdown', function (e) {
    drag = { x: e.clientX, y: e.clientY, btn: e.button, moved: 0, mode: (e.button === 2 || e.shiftKey) ? 'pan' : 'rot' };
    pointer.moved = false;
    canvas.setPointerCapture(e.pointerId);
    if (state.rotate) { state.rotate = false; document.getElementById('ckRotate').checked = false; }
  });
  canvas.addEventListener('pointermove', function (e) {
    pointer.x = e.clientX; pointer.y = e.clientY; pointer.inside = true;
    if (!drag) return;
    var dx = e.clientX - drag.x, dy = e.clientY - drag.y;
    drag.moved += Math.abs(dx) + Math.abs(dy);
    if (drag.moved > 4) pointer.moved = true;
    if (drag.mode === 'rot') {
      orbit.theta -= dx * 0.005;
      orbit.phi = Math.max(0.12, Math.min(1.52, orbit.phi - dy * 0.005));
    } else {
      pan(dx, dy);
    }
    drag.x = e.clientX; drag.y = e.clientY;
  });
  canvas.addEventListener('pointerup', function (e) {
    if (drag && drag.moved < 6) pick(e.clientX, e.clientY);
    drag = null;
  });
  canvas.addEventListener('pointerleave', function () { drag = null; pointer.inside = false; });
  canvas.addEventListener('wheel', function (e) {
    e.preventDefault();
    orbit.dist = Math.max(2200, Math.min(220000, orbit.dist * Math.pow(1.0016, e.deltaY * (e.deltaMode === 1 ? 16 : 1))));
  }, { passive: false });

  // 双指捏合
  var pinch = null;
  canvas.addEventListener('touchstart', function (e) {
    if (e.touches.length === 2) {
      drag = null;
      pinch = Math.hypot(e.touches[0].clientX - e.touches[1].clientX, e.touches[0].clientY - e.touches[1].clientY);
    }
  }, { passive: true });
  canvas.addEventListener('touchmove', function (e) {
    if (e.touches.length === 2 && pinch) {
      var d = Math.hypot(e.touches[0].clientX - e.touches[1].clientX, e.touches[0].clientY - e.touches[1].clientY);
      orbit.dist = Math.max(2200, Math.min(220000, orbit.dist * pinch / d));
      pinch = d;
      if (state.rotate) { state.rotate = false; document.getElementById('ckRotate').checked = false; }
    }
  }, { passive: true });
  canvas.addEventListener('touchend', function () { pinch = null; }, { passive: true });

  /* ---------- 视角切换 ---------- */
  var tween = { on: false, t: 0, dur: 0.9, from: null, to: null };
  function tweenTo(o) {
    tween.from = { theta: orbit.theta, phi: orbit.phi, dist: orbit.dist, x: orbit.target.x, y: orbit.target.y, z: orbit.target.z };
    tween.to = o;
    tween.t = 0; tween.on = true;
  }
  function stepTween(dt) {
    tween.t += dt / tween.dur;
    var t = Math.min(1, tween.t), e = t * t * (3 - 2 * t);
    var f = tween.from, o = tween.to;
    orbit.theta = f.theta + (o.theta - f.theta) * e;
    orbit.phi = f.phi + (o.phi - f.phi) * e;
    orbit.dist = f.dist + (o.dist - f.dist) * e;
    orbit.target.set(f.x + (o.x - f.x) * e, f.y + (o.y - f.y) * e, f.z + (o.z - f.z) * e);
    if (t >= 1) tween.on = false;
  }
  document.getElementById('vIso').onclick = function () {
    tweenTo({ theta: 1.24, phi: 1.12, dist: FIT_ISO, x: CENTER.x, y: plainY(), z: CENTER.z });
  };
  document.getElementById('vSide').onclick = function () {
    tweenTo({ theta: Math.PI / 2 - 0.3, phi: 1.42, dist: FIT_SIDE, x: CENTER.x, y: -1200, z: CENTER.z });
  };
  document.getElementById('vTop').onclick = function () {
    tweenTo({ theta: Math.PI / 2, phi: 0.13, dist: FIT_TOP, x: CENTER.x, y: 0, z: CENTER.z });
  };

  /* ---------- 站点拾取与信息卡 ---------- */
  var hovered = null;
  var card = document.getElementById('card');

  function pick(cx, cy) {
    var s = nearestStation(cx, cy, 22);
    if (s) showCard(s.st);
    else card.style.display = 'none';
  }

  function chipHTML(id) {
    var c = M.palette[id] || '#8b9ab0';
    var nm = M.line_names[id] || (id + '号线');
    return '<span class="chip-s"><i style="background:' + c + '"></i>' + nm + '</span>';
  }
  function showCard(st) {
    var rows = [];
    rows.push(['线路', st.lines.map(chipHTML).join('')]);
    var layTxt = st.lay + (st.dk === 'above' ? '（轨面高于地面约 ' + Math.round(st.above) + ' m）' : '');
    rows.push(['敷设方式', layTxt]);
    if (st.dk === 'truth') rows.push(['埋深', '<b>' + st.dep + ' m</b><span class="pill">实测</span><br><span style="color:#8b9ab0;font-size:11px">' + st.meas + '</span>']);
    else if (st.dk === 'est') rows.push(['埋深', '<b>≈' + st.dep + ' m</b><span class="pill lo">估算</span>']);
    else rows.push(['埋深', '—']);
    rows.push(['地面高程', st.g + ' m <span style="color:#8b9ab0;font-size:10.5px">（SRTM 30m）</span>']);
    if (st.open) rows.push(['开通', st.open]);
    if (st.status) rows.push(['状态', '暂停运营']);
    if (st.dk === 'truth' || st.dk === 'est') rows.push(['数据来源', '<span style="font-size:11px">' + st.src + '</span>']);
    if (st.note) rows.push(['备注', '<span style="font-size:11px">' + st.note + '</span>']);

    card.innerHTML =
      '<div class="hd"><h2>' + st.n + (st.en ? '<small>' + st.en + '</small>' : '') + '</h2><span class="x" id="cardX">✕</span></div>' +
      '<div class="kv">' + rows.map(function (r) {
        return '<div class="kk">' + r[0] + '</div><div class="vv">' + r[1] + '</div>';
      }).join('') + '</div>' +
      '<div class="src">' + (M.credits ? M.credits + ' ｜ ' : '') + 'metro-3d v' + (APP.version || '') + '</div>';
    card.style.display = 'block';
    document.getElementById('cardX').onclick = function () { card.style.display = 'none'; };
  }

  function hoverCheck() {
    if (!pointer.inside || drag) {
      if (hovered) { hovered.mesh.scale.setScalar(hovered.mesh.userData.sr); hovered = null; canvas.style.cursor = 'grab'; }
      return;
    }
    var s = nearestStation(pointer.x, pointer.y, 16);
    if (s !== hovered) {
      if (hovered) hovered.mesh.scale.setScalar(hovered.mesh.userData.sr);
      hovered = s;
      if (hovered) hovered.mesh.scale.setScalar(hovered.mesh.userData.sr * 1.45);
    }
    canvas.style.cursor = hovered ? 'pointer' : 'grab';
  }

  /* ---------- UI 绑定 ---------- */
  var kRange = document.getElementById('kRange'), kVal = document.getElementById('kVal');
  var gRange = document.getElementById('gRange'), gVal = document.getElementById('gVal');
  kRange.addEventListener('input', function () {
    state.k = +kRange.value; kVal.textContent = '×' + state.k; state.dirty = true;
  });
  gRange.addEventListener('input', function () {
    state.g = +gRange.value; gVal.textContent = '×' + state.g; state.dirty = true;
  });
  document.getElementById('ckTerrain').addEventListener('change', function () {
    state.terrain = this.checked; terrain.visible = state.terrain;
  });
  document.getElementById('ckLabels').addEventListener('change', function () {
    state.labels = this.checked;
    if (!state.labels) LINES.forEach(function (r) { r.stations.forEach(function (s) { if (s.label) s.label.style.display = 'none'; }); });
  });
  document.getElementById('ckRotate').addEventListener('change', function () { state.rotate = this.checked; });

  var chipsBox = document.getElementById('lineChips');
  var chipEls = [];
  LINES.forEach(function (rec) {
    var el = document.createElement('span');
    el.className = 'lchip';
    el.title = rec.def.name + '（' + rec.def.stations.length + ' 站）';
    el.innerHTML = '<i style="background:' + rec.def.colour + '"></i>' + (M.line_names[rec.def.id] || rec.def.name);
    el.onclick = function () {
      rec.group.visible = !rec.group.visible;
      el.className = 'lchip' + (rec.group.visible ? '' : ' off');
    };
    chipsBox.appendChild(el);
    chipEls.push({ el: el, rec: rec });
  });
  function setAllLines(v) {
    chipEls.forEach(function (c) {
      c.rec.group.visible = v;
      c.el.className = 'lchip' + (v ? '' : ' off');
    });
  }
  document.getElementById('lnOn').onclick = function () { setAllLines(true); };
  document.getElementById('lnOff').onclick = function () { setAllLines(false); };

  /* ---------- 主循环 ---------- */
  var last = 0;
  setTimeout(function () {
    var h = document.getElementById('hint'); if (h) h.style.opacity = '0';
  }, 7000);

  function frame(t) {
    requestAnimationFrame(frame);
    var dt = Math.min(0.05, (t - last) / 1000 || 0.016);
    last = t;
    if (tween.on) stepTween(dt);
    if (state.rotate && !drag && !tween.on) orbit.theta += 0.028 * dt;
    if (state.dirty) { rebuildAll(); state.dirty = false; }
    applyCamera();
    camera.updateMatrixWorld();
    projectStations();
    hoverCheck();
    updateLabels();
    renderer.render(scene, camera);
  }
  requestAnimationFrame(frame);

  window.addEventListener('resize', function () {
    camera.aspect = window.innerWidth / window.innerHeight;
    camera.updateProjectionMatrix();
    renderer.setSize(window.innerWidth, window.innerHeight);
  });

  // 调试钩子（无界面影响）
  window.__debug = {
    pick: function (x, y) { var s = nearestStation(x, y, 22); return s ? s.st.n : null; },
    screenOf: function (name) {
      for (var li = 0; li < LINES.length; li++) {
        var rec = LINES[li];
        if (!rec.group.visible) continue;
        for (var si = 0; si < rec.stations.length; si++) {
          var s = rec.stations[si];
          if (s.st.n === name && s.svis) return { x: s.sx, y: s.sy };
        }
      }
      return null;
    },
    state: state, orbit: orbit, tween: tween,
    visibleStations: function () {
      var out = [];
      for (var li = 0; li < LINES.length; li++) {
        var rec = LINES[li];
        if (!rec.group.visible) continue;
        for (var si = 0; si < rec.stations.length; si++) {
          var s = rec.stations[si];
          if (s.svis && s.sx > 0 && s.sx < window.innerWidth && s.sy > 0 && s.sy < window.innerHeight) {
            out.push(rec.def.id + '/' + s.st.n + '/' + Math.round(s.sx) + ',' + Math.round(s.sy));
          }
        }
      }
      return out;
    },
    info: function () { var r = renderer.info.render; return { calls: r.calls, tris: r.triangles, lines: LINES.length }; }
  };
})();
