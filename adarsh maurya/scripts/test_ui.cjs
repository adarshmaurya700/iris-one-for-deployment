/* Run with Playwright installed: node scripts/test_ui.cjs */
const assert = require('node:assert/strict');
const fs = require('node:fs');
const os = require('node:os');
const path = require('node:path');
const { spawn, spawnSync } = require('node:child_process');
const { chromium } = require(process.env.PLAYWRIGHT_MODULE || 'playwright');

const project = path.resolve(__dirname, '..');
const directory = fs.mkdtempSync(path.join(os.tmpdir(), 'iris-ui-'));
const port = process.env.IRIS_UI_PORT || '8766';
const base = `http://127.0.0.1:${port}`;
const env = { ...process.env, DATABASE_PATH: path.join(directory, 'ui.db'), DATABASE_URL: '',
  IRIS_DISABLE_SCHEDULER: '1', TINYFISH_API_KEY: '', GEMINI_API_KEY: '', GROQ_API_KEY: '', OLLAMA_BASE_URL: '' };
const server = spawn(process.env.PYTHON || 'python', ['-B', '-m', 'uvicorn', 'main:app', '--host', '127.0.0.1', '--port', port],
  { cwd: path.join(project, 'backend'), env, stdio: ['ignore', 'ignore', 'pipe'], windowsHide: true });
let logs = '';
server.stderr.on('data', data => { logs += data.toString(); });
const pause = ms => new Promise(resolve => setTimeout(resolve, ms));

(async () => {
  let browser;
  try {
    let ready = false;
    for (let attempt = 0; attempt < 80; attempt++) {
      try { ready = (await fetch(`${base}/api/health`)).ok; } catch {}
      if (ready) break;
      if (server.exitCode !== null) throw new Error(logs);
      await pause(250);
    }
    assert(ready, 'Preview server did not start: ' + logs);
    browser = await chromium.launch({ headless: true, ...(process.env.PLAYWRIGHT_CHANNEL ? { channel: process.env.PLAYWRIGHT_CHANNEL } : {}) });
    const page = await browser.newPage({ viewport: { width: 1440, height: 1000 }, acceptDownloads: true });
    const errors = [];
    page.on('pageerror', error => errors.push(error.message));
    // Simulate venue Wi-Fi loss for external assets; the local app must still work.
    await page.route('**/*', route => route.request().url().startsWith(base) ? route.continue() : route.abort());
    await page.goto(`${base}/#dashboard`, { waitUntil: 'domcontentloaded' });
    await page.evaluate(() => window.openApplyOptionsModal('airtel'));
    await page.locator('#guide-track-button').waitFor();
    assert.equal(await page.locator('#apply-options-modal-body ol li').count(), 5);
    assert((await page.locator('#apply-options-modal-body').innerText()).includes('SEEDED_CACHE'));
    await page.locator('[data-guide-document="0"]').check();
    await page.waitForFunction(() => document.getElementById('guide-document-status')?.textContent.includes('saved to IRIS'));
    await page.locator('#guide-track-button').click();
    await page.waitForFunction(() => document.getElementById('guide-track-button')?.textContent.includes('Tracked'));
    await page.evaluate(() => window.closeApplyOptionsModal());
    await page.reload({ waitUntil: 'domcontentloaded' });
    await page.evaluate(() => window.openApplyOptionsModal('airtel'));
    await page.locator('#guide-track-button').waitFor();
    assert(await page.locator('[data-guide-document="0"]').isChecked());
    assert((await page.locator('#guide-track-button').innerText()).includes('Tracked'));
    await page.evaluate(() => window.openApplyOptionsModal('delhi-mcm'));
    assert((await page.locator('#apply-options-modal-body').innerText()).includes('Policy Conflict Alert'));
    await page.evaluate(() => window.openApplyOptionsModal('reliance'));
    const downloadPromise = page.waitForEvent('download');
    await page.locator('#guide-calendar-button').click();
    const download = await downloadPromise;
    assert(download.suggestedFilename().endsWith('.ics'));
    await page.evaluate(() => { window.closeApplyOptionsModal(); window.openAiChatModal(); });
    await page.locator('#ai-chat-input').fill('How do I apply for Airtel and combine it with Delhi MCM and Google Gemini?');
    await page.locator('#ai-chat-send-btn').click();
    await page.waitForFunction(() => document.getElementById('ai-chat-messages')?.textContent.includes('Last completed cache sync'));
    const chat = await page.locator('#ai-chat-messages').innerText();
    assert(chat.includes('exclusive tuition'));
    assert(chat.includes('stackable'));
    assert(!chat.includes('$0'), 'Assistant lists must render their actual contents');
    await page.evaluate(() => { window.closeAiChatModal(); window.openApplyOptionsModal('adobe-insider'); });
    await page.setViewportSize({ width: 390, height: 844 });
    await page.locator('#guide-calendar-button').scrollIntoViewIfNeeded();
    const bounds = await page.locator('[aria-labelledby="application-guide-title"]').boundingBox();
    assert(bounds.x >= 0 && bounds.x + bounds.width <= 391, 'Modal exceeds mobile viewport');
    assert(await page.locator('#guide-calendar-button').isVisible());
    await page.screenshot({ path: path.join(directory, 'guide-mobile.png') });
    assert.deepEqual(errors, [], 'Browser JavaScript errors');
    console.log('PASS: offline assets, guides, checklist persistence, tracking, policy conflicts, calendar download, local RAG chat and mobile layout.');
    console.log('Mobile screenshot: ' + path.join(directory, 'guide-mobile.png'));
  } finally {
    if (browser) await browser.close();
    if (process.platform === 'win32') spawnSync('taskkill', ['/PID', String(server.pid), '/T', '/F'], { windowsHide: true, stdio: 'ignore' });
    else server.kill();
    server.stderr.destroy();
    server.unref();
  }
})().catch(error => { console.error(error); process.exitCode = 1; });
