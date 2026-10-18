import { test, expect } from '@playwright/test';
import { mockApi, videos } from '../fixtures/api.js';

test.beforeEach(async ({ page, context }) => {
  await page.setViewportSize({ width: 1440, height: 900 });
  await mockApi(context);
});

test('home sorting, pagination and persistence', async ({ page }) => {
  await page.goto('/');
  await expect(page.locator('.card-item').first()).toContainText('测试作者 001');
  await page.getByRole('button', { name: '视频数', exact: true }).click();
  await expect(page.locator('.card-item').first()).toContainText('测试作者 100');
  await expect(page).toHaveURL(/sort=worksCount/);
  await page.locator('.page-btn').filter({hasText: /^2$/}).click();
  await expect(page).toHaveURL(/page=2/);
  await page.reload();
  await expect(page.locator('.page-btn.active')).toHaveText('2');
  await expect.poll(() => page.evaluate(() => JSON.parse(localStorage.getItem('authorGrid-sortSettings')))).toEqual({sortBy:'worksCount',sortOrder:'desc'});
});

test('video sorting, page input and reload restore the same cards', async ({ page }) => {
  await page.goto('/author/1');
  await expect(page.locator('.video-column').first()).toBeVisible();
  await page.getByRole('button', {name:'按时间',exact:true}).click();
  await expect(page).toHaveURL(/sort=date/);
  await page.locator('.page-input input').fill('2');
  await page.locator('.page-input input').press('Enter');
  await expect(page).toHaveURL(/page=2/);
  const titles=await page.locator('.video-title').allTextContents();
  await page.reload();
  await expect(page.locator('.page-btn.active')).toHaveText('2');
  await expect.poll(() => page.locator('.video-title').allTextContents()).toEqual(titles);
});

test('native video links preserve href, context menu and one popup per ordinary click', async ({ page, context }) => {
  await page.goto('/author/1?sort=date');
  const link=page.locator('a.video-column').first();
  await expect(link).toHaveAttribute('href', /^https:\/\//);
  await expect(link).toHaveAttribute('target','_blank');
  expect(await link.evaluate(el => {
    const event=new MouseEvent('contextmenu',{bubbles:true,cancelable:true,button:2});
    el.dispatchEvent(event);
    return event.defaultPrevented;
  })).toBe(false);
  const popupPromise=context.waitForEvent('page');
  const expected=await link.getAttribute('href');
  await link.click();
  const popup=await popupPromise;
  await expect.poll(() => popup.url()).toBe(expected);
  expect(context.pages()).toHaveLength(2);
  await popup.close();
  const middlePopup=context.waitForEvent('page');
  await link.click({button:'middle'});
  await (await middlePopup).close();
  const modifiedPopup=context.waitForEvent('page');
  await link.click({modifiers:['Control']});
  await (await modifiedPopup).close();
  await expect(page.locator('.disabled-column').first()).not.toHaveAttribute('href');
});

for(const width of [390,1440]) {
  test(`header search opens a new results tab and resets at ${width}px`, async ({page, context}) => {
    await page.setViewportSize({width,height:900});
    await page.goto('/');
    await expect(page.locator('.card-item').first()).toBeVisible();
    const mobile=width===390;
    if(mobile) await page.locator('.mobile-search-btn').click();
    const panel=page.locator(mobile?'.mobile-search-popup':'.search-panel');
    const input=page.locator(mobile?'.mobile-search-input input':'.desktop-search input');
    await input.fill('东方');
    await expect(panel).toBeVisible();
    const popupPromise=context.waitForEvent('page');
    await panel.getByRole('button',{name:'搜索',exact:true}).click();
    const popup=await popupPromise;
    await expect.poll(()=>new URL(popup.url()).searchParams.get('q')).toBe('东方');
    await expect(panel).not.toBeVisible();
    await popup.close();
    if(mobile) await page.locator('.mobile-search-btn').click();
    else await input.click();
    await expect(input).toHaveValue('');
  });
}

test('legacy video query filters and empty-state delay', async ({page}) => {
  await page.goto('/author/1?minDuration=999999&includeUnknownDuration=0');
  await expect(page.locator('.filter-empty')).toBeVisible({timeout:5000});
  await expect(page.locator('.video-row')).toHaveCount(0);
  await expect(page).toHaveURL(/minDur=999999/);
});

test('video search result count, order and author search remain available', async ({page}) => {
  await page.goto('/search?q=东方&type=videos');
  await expect(page.locator('.search-stats')).toContainText(`找到 ${videos.length} 个视频`);
  await expect(page.locator('.video-row')).toHaveCount(44);
  await page.getByRole('button',{name:'按时间',exact:true}).click();
  await expect.poll(()=>page.evaluate(()=>JSON.parse(localStorage.getItem('searchView-sortSettings')))).toEqual({sortType:'date',sortOrder:'asc'});
  await page.goto('/search?q=测试&type=authors');
  await expect(page.locator('.author-link')).toHaveCount(100);
});

test('empty and failed video requests preserve existing UI', async ({page}) => {
  await mockApi(page,{empty:true});
  await page.goto('/author/1');
  await expect(page.locator('.filter-empty')).toBeVisible();
  await mockApi(page,{fail:true});
  await page.reload();
  await expect(page.locator('.filter-empty')).toBeVisible();
  await expect(page.locator('.video-row')).toHaveCount(0);
  await page.goto('/search?q=东方&type=videos');
  await expect(page.locator('.video-row')).toHaveCount(0);
});

test('filter drafts validate bounds, apply, persist and reset', async ({page}) => {
  await page.goto('/');
  await expect(page.locator('.card-item').first()).toBeVisible();
  await page.locator('.filter-btn').click();
  const range=page.locator('.filter-card .range-filter').first();
  await range.getByLabel('最小',{exact:true}).fill('30');
  await range.getByLabel('最大',{exact:true}).fill('10');
  await expect(page.locator('.apply-filter-btn')).toBeDisabled();
  await range.getByLabel('最大',{exact:true}).fill('40');
  await page.locator('.apply-filter-btn').click();
  await expect(page.locator('.card-item')).toHaveCount(11);
  await expect(page).toHaveURL(/minW=30/);
  await expect(page.locator('.filter-count')).toHaveText('1');
  await page.reload();
  await expect(page.locator('.card-item')).toHaveCount(11);
  await page.locator('.filter-btn').click();
  await page.locator('.reset-filter-btn').click();
  await expect(page.locator('.filter-count')).toHaveCount(0);
  await expect(page.locator('.card-item')).toHaveCount(48);
});

test('browser back and forward restore the previous route and results', async ({page}) => {
  await page.goto('/author/1?sort=date&page=2');
  await expect(page.locator('.page-btn.active')).toHaveText('2');
  const before=await page.locator('.video-title').allTextContents();
  await page.locator('.nav-menu .nav-button').last().click();
  await expect(page).toHaveURL(/\/about$/);
  await page.goBack();
  await expect(page.locator('.page-btn.active')).toHaveText('2');
  await expect.poll(()=>page.locator('.video-title').allTextContents()).toEqual(before);
  await page.goForward();
  await expect(page).toHaveURL(/\/about$/);
});

test('deleted originals and failed repost checks keep their existing labels', async ({page}) => {
  await page.route('https://api.bilibili.com/**',route=>{
    const callback=new URL(route.request().url()).searchParams.get('callback');
    return route.fulfill({contentType:'application/javascript',body:`${callback}({code:-404})`});
  });
  await page.goto('/search?q=东方&type=videos');
  await expect(page.locator('.original-column.disabled-column')).toHaveCount(2);
  await expect(page.locator('.original-column.disabled-column').filter({hasText:'暂无原视频'})).toHaveCount(1);
  await expect(page.locator('.repost-column').filter({hasText:'转载失效'}).first()).toBeVisible();
});

test('desktop and mobile header searches share the same filters across resize', async ({page, context}) => {
  await page.goto('/');
  await expect(page.locator('.card-item').first()).toBeVisible();
  await page.locator('.desktop-search input').fill('东方');
  const desktop = page.locator('.search-panel');
  await desktop.locator('.v-combobox input').fill('测试作者 001');
  await desktop.locator('.v-combobox input').press('Tab');
  await desktop.locator('.v-select').click();
  await page.getByRole('option', {name:'CC字幕', exact:true}).click();
  await desktop.locator('.date-input input:not([type=date])').first().fill('2026/10/01');
  await desktop.locator('.date-input input:not([type=date])').first().press('Tab');
  await desktop.locator('.range-filter').getByLabel('最小', {exact:true}).fill('1');
  await desktop.locator('.range-filter').getByLabel('最大', {exact:true}).fill('2');

  await page.setViewportSize({width:390,height:900});
  await page.locator('.mobile-search-btn').click();
  const mobile = page.locator('.mobile-search-popup');
  await expect(mobile.locator('.mobile-search-input input')).toHaveValue('东方');
  await expect(mobile.locator('.v-combobox input')).toHaveValue('测试作者 001');
  await expect(mobile.locator('.v-select')).toContainText('CC字幕');
  await expect(mobile.locator('.mobile-date-input input:not([type=date])').first()).toHaveValue('2026/10/01');
  await expect(mobile.locator('.range-filter').getByLabel('最小', {exact:true})).toHaveValue('1');
  await expect(mobile.locator('.range-filter').getByLabel('最大', {exact:true})).toHaveValue('2');

  const popupPromise = context.waitForEvent('page');
  await mobile.getByRole('button', {name:'搜索',exact:true}).click();
  const popup = await popupPromise;
  await expect.poll(() => {
    const query = new URL(popup.url()).searchParams;
    return Object.fromEntries(query);
  }).toEqual({q:'东方',type:'videos',limit:'100',author:'1',status:'2',from:'2026-10-01',minDur:'60',maxDur:'120'});
  await popup.close();
});
