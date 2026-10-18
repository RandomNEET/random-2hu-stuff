import { test, expect } from '@playwright/test';
import { mockApi } from '../fixtures/api.js';

for (const width of [390, 768, 834, 1440]) {
  for (const [name, path, ready] of [
    ['home', '/', '.card-item'],
    ['author', '/author/1', '.video-column'],
    ['search-videos', '/search?q=东方&type=videos', '.video-column'],
    ['search-authors', '/search?q=测试&type=authors', '.author-link'],
    ['announce', '/announce', '.update-item'],
    ['about', '/about', '.v-main h1'],
  ]) {
    test(`${name} at ${width}px`, async ({ page }) => {
      await page.setViewportSize({ width, height: 900 });
      await mockApi(page);
      await page.goto(path);
      await expect(page.locator(ready).first()).toBeVisible();
      await page.addStyleTag({ content: '[class*="sakana"] { visibility: hidden !important; }' });
      await page.evaluate(() => document.fonts.ready);
      await page.waitForTimeout(1800);
      await expect(page).toHaveScreenshot(`${name}-${width}.png`, {
        fullPage: true,
        animations: 'disabled',
        style: '.sakana-container, .sakana-container * { visibility: hidden !important; }',
      });
    });
  }
}

for (const width of [390, 1440]) {
  test(`search panels at ${width}px`, async ({ page }) => {
    await page.setViewportSize({ width, height: 900 });
    await mockApi(page);
    await page.goto('/');
    await expect(page.locator('.card-item').first()).toBeVisible();
    await page.addStyleTag({ content: '[class*="sakana"] { visibility: hidden !important; }' });
    if (width === 390) await page.locator('.mobile-search-btn').click();
    else await page.locator('.desktop-search input').click();
    await page.waitForTimeout(800);
    await expect(page).toHaveScreenshot(`search-panel-${width}.png`, {
      animations: 'disabled',
      style: '.sakana-container, .sakana-container * { visibility: hidden !important; }',
    });
  });
}
