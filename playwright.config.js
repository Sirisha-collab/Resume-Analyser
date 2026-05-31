const { defineConfig } = require('@playwright/test');

module.exports = defineConfig({
  testDir: './tests',

  use: {
    browserName: 'firefox',
    headless: false,   // ⭐ IMPORTANT
    slowMo: 500        // optional (slows actions so you SEE them)
  }
});