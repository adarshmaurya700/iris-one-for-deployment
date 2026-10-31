/* Focused reference-homepage checks; actual local backend records, no provider calls. */
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const { chromium } = require('playwright');
(async () => {
 const output = path.resolve(__dirname, '../docs/screenshots'); fs.mkdirSync(output, {recursive:true});
 const browser = await chromium.launch({headless:true,channel:process.env.PLAYWRIGHT_CHANNEL || 'chrome'});
 try {
  const page = await browser.newPage({viewport:{width:1440,height:900}});
  const errors=[]; page.on('pageerror',error=>errors.push(error.message));
  const base=process.env.IRIS_HOME_URL || 'http://127.0.0.1:8000';
  await page.route('**/*',route=>route.request().url().startsWith(base) ? route.continue() : route.abort());
  const home=async()=>{await page.goto(base+'/#home');await page.waitForFunction(()=>irisState.ready && irisState.view==='home');};
  await home();
  assert.equal(await page.locator('.featured-opportunity').count(),2);
  const expected=await page.evaluate(()=>irisState.opportunities.map(o=>({id:String(o.slug||o.id),score:Math.round(o.match_score)})));
  for(const card of await page.locator('.featured-opportunity').all()){
   const id=await card.getAttribute('data-id'); assert((await card.innerText()).includes(expected.find(o=>o.id===id).score+'% Match'));
  }
  await page.screenshot({path:path.join(output,'home-desktop.png'),fullPage:true});
  await page.locator('#home-search-input').fill('Reliance'); await page.locator('#home-search-input').press('Enter');
  await page.waitForFunction(()=>irisState.view==='opportunities');
  assert.equal(await page.locator('#opportunity-search').inputValue(),'Reliance');
  assert.equal(await page.locator('#opportunity-results .opportunity-card').count(),1);
  for(const category of ['Hackathons','Scholarships','Internships','Competitions','Student Offers','Olympiads','AI Assistant']){
   await home();await page.locator('.home-category').filter({hasText:category}).click();
   await page.waitForFunction(()=>irisState.view!=='home');
   if(category==='AI Assistant') assert.equal(await page.evaluate(()=>irisState.view),'ai-assistant');
   else {assert.equal(await page.evaluate(()=>irisState.filter.category),category);assert((await page.locator('#opportunity-count').innerText()).includes('opportunit'));}
  }
  await home();await page.locator('.featured-opportunity').first().focus();await page.keyboard.press('Enter');
  await page.waitForFunction(()=>irisState.view==='detail');assert.equal(await page.locator('[data-view]:not([hidden])').count(),1);
  for(const width of [1440,1024,768,430,375]){
   await page.setViewportSize({width,height:900});await home();
   assert(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth+1),'Page overflow at '+width);
   assert.equal(await page.locator('.home-category').count(),7);
   if(width===375) {
    await page.screenshot({path:path.join(output,'home-mobile.png'),fullPage:true});
    await page.locator('#menu-toggle').click();await page.locator('#primary-navigation a[href="#profile"]').click();
    await page.waitForFunction(()=>irisState.view==='profile');
   }
  }
  assert.deepEqual(errors,[]);console.log('PASS: homepage search, seven categories, backend match scores, keyboard detail links, mobile menu and five responsive widths.');
  console.log('Screenshots: '+output);
 } finally {await browser.close();}
})().catch(error=>{console.error(error);process.exitCode=1;});
