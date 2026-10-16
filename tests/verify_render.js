/* Metro-3D · 无头浏览器渲染验证（headless render verification）
 *
 * 用法 / Usage:
 *   npm install                 # 安装 playwright-core（复用系统 Edge/Chrome，无需下载浏览器）
 *   node tests/verify_render.js
 *
 * 检查：JS 报错、WebGL 可用、三视角截图、站点点击、线路开关、绘制调用数。
 * 截图输出在 tests/output/；退出码非 0 表示验证失败。
 */
const fs = require('fs');
const path = require('path');
const { pathToFileURL } = require('url');
const { chromium } = require('playwright-core');

const HTML = pathToFileURL(path.resolve(__dirname, '..', 'dist', 'beijing.html')).href;
const OUT = path.resolve(__dirname, 'output');

async function launch() {
  const opts = { headless: true, args: ['--use-angle=swiftshader'] };
  for (const channel of ['msedge', 'chrome']) {
    try { return await chromium.launch({ channel, ...opts }); } catch (e) { /* try next */ }
  }
  return chromium.launch(opts); // 回退：自带 chromium（若已安装）
}

(async () => {
  fs.mkdirSync(OUT, { recursive: true });
  const browser = await launch();
  const page = await browser.newPage({ viewport: { width: 1440, height: 900 }, deviceScaleFactor: 1 });
  const logs = [];
  page.on('console', m => { if (m.type() === 'error' || m.type() === 'warning') logs.push(m.type() + ': ' + m.text()); });
  page.on('pageerror', e => logs.push('PAGEERROR: ' + e.message));

  await page.goto(HTML);
  await page.waitForTimeout(4000);
  await page.screenshot({ path: path.join(OUT, 'a_iso.png') });
  console.log('渲染统计:', JSON.stringify(await page.evaluate(() => window.__debug.info())));

  const fps = await page.evaluate(() => new Promise(res => {
    let n = 0; const t0 = performance.now();
    (function tick() { n++; if (n >= 40) res(40000 / (performance.now() - t0)); else requestAnimationFrame(tick); })();
  }));
  console.log('帧率(软件渲染参考):', fps.toFixed(1), 'fps');

  await page.click('#ckRotate');
  await page.click('#vSide');
  await page.waitForTimeout(1600);
  await page.screenshot({ path: path.join(OUT, 'b_side.png') });

  await page.click('#vTop');
  await page.waitForTimeout(1600);
  await page.screenshot({ path: path.join(OUT, 'c_top.png') });

  await page.$eval('#kRange', el => { el.value = 80; el.dispatchEvent(new Event('input')); });
  await page.waitForTimeout(900);
  await page.screenshot({ path: path.join(OUT, 'd_k80.png') });

  // 点击「东四」站（真值站）：固定视角 → 命中校验 → 点击（保证确定性）
  await page.$eval('#kRange', el => { el.value = 50; el.dispatchEvent(new Event('input')); });
  await page.click('#vIso');
  await page.waitForTimeout(1400);
  await page.evaluate(() => {
    const D = window.METRO_DATA, M = D.meta;
    const st = D.lines.find(l => l.id === '6').stations.find(s => s.n === '东四');
    const KX = 111320 * Math.cos(M.lat0 * Math.PI / 180);
    const o = window.__debug.orbit;
    o.target.x = (st.lon - M.lon0) * KX;
    o.target.z = -(st.lat - M.lat0) * 110540;
    o.target.y = -1200;
    o.dist = 9000; o.phi = 1.30; o.theta = Math.PI / 2 - 0.3;
  });
  await page.waitForTimeout(1200);
  const pos = await page.evaluate(() => {
    const p = window.__debug.screenOf('东四');
    if (!p) return null;
    if (window.__debug.pick(p.x, p.y) === '东四') return { x: p.x, y: p.y, ok: true };
    for (let dy = -40; dy <= 40; dy += 4) {
      for (let dx = -24; dx <= 24; dx += 4) {
        if (window.__debug.pick(p.x + dx, p.y + dy) === '东四') return { x: p.x + dx, y: p.y + dy, ok: true };
      }
    }
    return { x: p.x, y: p.y, ok: false };
  });
  if (pos && pos.ok) {
    await page.mouse.click(pos.x, pos.y);
    await page.waitForTimeout(500);
    await page.screenshot({ path: path.join(OUT, 'e_card.png') });
    const cardText = await page.$eval('#card', el => el.style.display !== 'none' ? el.innerText.replace(/\n+/g, ' | ') : '(卡片未打开)');
    console.log('卡片内容:', cardText);
  } else {
    console.log('未定位到东四可点击位置（ok=' + (pos && pos.ok) + '），尝试坐标拾取:', await page.evaluate(() => window.__debug.pick(720, 430)));
  }

  // 线路开关：全隐 / 全显
  await page.click('#lnOff');
  await page.waitForTimeout(500);
  await page.screenshot({ path: path.join(OUT, 'f_alloff.png') });
  const infoOff = await page.evaluate(() => window.__debug.info());
  await page.click('#lnOn');
  await page.waitForTimeout(500);
  const infoOn = await page.evaluate(() => window.__debug.info());
  console.log('全隐 calls:', infoOff.calls, '| 全显 calls:', infoOn.calls);

  const info = await page.evaluate(() => ({
    webgl: !!(document.getElementById('scene').getContext('webgl2') || document.getElementById('scene').getContext('webgl')),
    fatalShown: getComputedStyle(document.getElementById('fatal')).display !== 'none',
    errShown: getComputedStyle(document.getElementById('err')).display !== 'none',
    errText: document.getElementById('err').textContent || '',
    labels: document.querySelectorAll('.lbl').length,
    visibleLabels: Array.from(document.querySelectorAll('.lbl')).filter(e => e.style.display !== 'none').length,
    chips: document.querySelectorAll('#lineChips .lchip').length
  }));
  console.log(JSON.stringify(info, null, 2));
  console.log('---- 控制台输出 ----');
  console.log(logs.length ? logs.join('\n') : '(无错误)');
  await browser.close();

  const hardErrors = logs.filter(l => l.startsWith('PAGEERROR') || l.startsWith('error'));
  if (!info.webgl || info.fatalShown || info.errShown || hardErrors.length) {
    console.error('验证失败 / verification FAILED');
    process.exit(1);
  }
  console.log('验证通过 / verification OK');
})().catch(e => { console.error('FAILED:', e.message); process.exit(1); });
