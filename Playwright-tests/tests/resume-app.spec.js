const { test, expect } = require('@playwright/test');
const path = require('path');

test('Resume Analyzer full flow', async ({ page }) => {

  // Open app
  await page.goto('http://localhost:3000');

  // Wait for login form
  await expect(page.locator('#username')).toBeVisible();
  await expect(page.locator('#password')).toBeVisible();

  // Login
  await page.fill('#username', 'admin');
  await page.fill('#password', 'password');

  // Click login and wait for dashboard
  await page.locator('button:has-text("Login")').click();

  // Wait for upload element after login
  const uploadInput = page.locator('#resume-upload');
  await expect(uploadInput).toBeVisible({ timeout: 20000 });

  // Upload resume
  const filePath = path.resolve(__dirname, 'Shilpa_Resume.pdf');

  await uploadInput.setInputFiles(filePath);

  // JD input
  const jdInput = page.locator('#jd-input');

  await expect(jdInput).toBeVisible();

  await jdInput.fill('.NET, Python, APIs, Microservices');

  // Analyze button
  const analyzeBtn = page.locator('#analyze-btn');

  await expect(analyzeBtn).toBeEnabled();

  await analyzeBtn.click();

  // Wait for results
  const resultWrapper = page.locator('.resume-wrapper');

  await expect(resultWrapper).toBeVisible({ timeout: 30000 });

  // ATS Score validation
  await expect(
  page.getByText('ATS Score', { exact: true })
).toBeVisible();

});