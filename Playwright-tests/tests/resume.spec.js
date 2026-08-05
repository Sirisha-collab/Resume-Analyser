const { test, expect } = require('@playwright/test');
const path = require('path');

test('Resume Analyzer basic test', async ({ page }) => {

  await page.goto('http://localhost:3000');

  await page.fill('#username', 'admin');
  await page.fill('#password', 'password');
  await page.click('button:has-text("Login")');

  await page.waitForSelector('#resume-upload');

  await page.setInputFiles(
    '#resume-upload',
    path.join(__dirname, 'Shilpa_Resume.pdf')
  );

  await page.fill('#jd-input', 'Java, Python, APIs');

  await page.click('#analyze-btn');

  await expect(page.locator('#results')).toBeVisible();

  const results = await page.textContent('#results');

  console.log(results);

  expect(results).toBeTruthy();
});