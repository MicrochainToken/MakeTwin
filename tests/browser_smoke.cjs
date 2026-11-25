/* Browser integration check. Install playwright separately; no production dependency. */
const {chromium} = require('playwright');
const assert = require('node:assert/strict');
const fs = require('node:fs/promises');
const path = require('node:path');

(async () => {
  const url = process.argv[2] || 'http://127.0.0.1:8000';
  const out = path.resolve(process.argv[3] || 'browser-output');
  await fs.mkdir(out, {recursive: true});
  const browser = await chromium.launch({headless: true, args: [
    '--no-sandbox', '--use-angle=swiftshader', '--enable-unsafe-swiftshader'
  ]});
  const errors = [], warnings = [], responses = [], failedRequests = [];
  try {
    const page = await browser.newPage({viewport: {width: 1280, height: 900}});
    page.on('pageerror', e => errors.push(e.message));
    page.on('console', m => {
      if (m.type() === 'error') errors.push(m.text());
      if (m.type() === 'warning') warnings.push(m.text());
    });
    page.on('response', r => responses.push({url: r.url(), status: r.status()}));
    page.on('requestfailed', r => failedRequests.push({url: r.url(), error: r.failure()}));
    await page.goto(url, {waitUntil: 'networkidle'});
    await page.locator('#explorer-panel select').waitFor({timeout: 90000});
    await page.waitForFunction(() => document.querySelector('#loading').hidden);
    await page.locator('#play').click();
    const slider = page.getByRole('slider', {name: 'Illustrative separation'});
    for (const amount of [0, .25, .5, .75, 1]) {
      await slider.evaluate((el, value) => {el.value = value; el.dispatchEvent(new Event('input', {bubbles: true}));}, String(amount));
      assert.equal(await page.locator('.step-instruction').isVisible(), false, 'Physical guide caption is hidden during display inspection');
      await page.waitForTimeout(800);
      await page.screenshot({path: path.join(out, `separation-${amount}.png`), fullPage: true});
    }
    await page.getByRole('combobox', {name: 'Assembly to inspect'}).selectOption({index: 1});
    for (const name of ['Isolate', 'Section preview', 'Transparent context']) {
      await page.getByRole('button', {name, exact: true}).click();
    }
    await page.locator('#tour').click();
    assert.equal(await slider.inputValue(), '0', 'Playback restores assembled display');
    assert.equal(await page.locator('.step-instruction').isVisible(), true, 'Playback restores guide captions');
    await page.waitForTimeout(500);
    await page.locator('#play').click();
    await page.locator('#replay').click();
    await page.setViewportSize({width: 390, height: 844});
    await page.waitForTimeout(500);
    await page.screenshot({path: path.join(out, 'mobile.png'), fullPage: true});
    assert(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth + 1), 'Mobile page must not overflow horizontally');
    for (const id of ['tour', 'replay', 'play', 'speed', 'back', 'next']) {
      const box = await page.locator('#' + id).boundingBox();
      assert(box && box.x >= 0 && box.x + box.width <= 391, `${id} must fit the mobile viewport`);
    }
    await page.locator('#next').click();
    await page.locator('#replay').click();
    for (const filename of ['model.glb', 'model.manifest.json', 'explorer.json']) {
      assert(responses.some(r => new URL(r.url).pathname.endsWith('/' + filename) && r.status === 200), `${filename} must load`);
    }
    assert(!warnings.some(w => w.includes('automatic take-apart')), 'Authored layout must be used');
    assert.deepEqual(errors, [], 'Browser console/page errors');
    assert.deepEqual(failedRequests, [], 'Failed resource requests');
    assert(!responses.some(r => r.status >= 400), 'HTTP errors');
    console.log('PASS: model, manifest, authored layout, exploration, reset/replay and mobile browser smoke');
  } finally {
    await fs.writeFile(path.join(out, 'browser-report.json'), JSON.stringify({errors, warnings, failedRequests, responses}, null, 2));
    await browser.close();
  }
})().catch(e => { console.error(e); process.exitCode = 1; });
