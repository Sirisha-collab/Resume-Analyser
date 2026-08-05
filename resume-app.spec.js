const { test, expect } = require('@playwright/test');
const path = require('path');

test('Resume Analyzer full flow', async ({ page }) => {

  // 1. Open app
  await page.goto('http://localhost:3000', {
    waitUntil: 'domcontentloaded'
  });

  // 2. LOGIN
  await page.fill('#username', 'admin');
  await page.fill('#password', 'password');

  await Promise.all([
    page.waitForLoadState('networkidle'),
    page.click('button:has-text("Login")')
  ]);

  // 3. Wait for dashboard element (more reliable than upload wait)
  await expect(page.locator('#resume-upload')).toBeVisible({ timeout: 15000 });

  // 4. UPLOAD FILE (safe path)
  await page.setInputFiles(
    '#resume-upload',
    path.resolve(__dirname, 'Shilpa_Resume.pdf')
  );

  // 5. JD INPUT
  await expect(page.locator('#jd-input')).toBeVisible();
  await page.fill('#jd-input', 'Java, Python, APIs, Microservices');

  // 6. ANALYZE BUTTON
  await expect(page.locator('#analyze-btn')).toBeEnabled();
  await page.click('#analyze-btn');

  // 7. RESULT
  await expect(page.locator('.resume-wrapper')).toBeVisible({ timeout: 20000 });
  await expect(page.locator('.score-label', { hasText: 'ATS Score' })).toBeVisible();
  

});