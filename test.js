const { firefox } = require('playwright');

(async () => {

  // ----------------------------
  // 1. Launch browser
  // ----------------------------
  const browser = await firefox.launch({
    headless: false,
    slowMo: 300   // slows actions so you can SEE everything
  });

  const context = await browser.newContext();
  const page = await context.newPage();

  // ----------------------------
  // 2. Go to practice site
  // ----------------------------
  await page.goto('https://the-internet.herokuapp.com');

  // ----------------------------
  // 3. Click a link (navigation)
  // ----------------------------
  await page.click('text=Form Authentication');

  // ----------------------------
  // 4. Fill login form
  // ----------------------------
  await page.fill('#username', 'siri');
  await page.fill('#password', 'Password!');

  // ----------------------------
  // 5. Click login button
  // ----------------------------
  await page.click('button[type="submit"]');

  // ----------------------------
  // 6. Wait + read message
  // ----------------------------
  const message = await page.textContent('#flash');
  console.log("Login Message:", message);

  // ----------------------------
  // 7. Take screenshot
  // ----------------------------
  await page.screenshot({ path: 'login-result.png' });

  // ----------------------------
  // 8. Open new tab (multi-page feature)
  // ----------------------------
  const newPage = await context.newPage();
  await newPage.goto('https://example.com');

  console.log("New tab title:", await newPage.title());

  // ----------------------------
  // 9. Play with waiting
  // ----------------------------
  await page.waitForTimeout(3000);

  // ----------------------------
  // 10. Close browser
  // ----------------------------
  //await browser.close();

})();