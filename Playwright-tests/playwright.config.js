const { defineConfig } = require('@playwright/test');

module.exports = defineConfig({
  testDir: './tests',

  use: {
    browserName: 'firefox',
    headless: false,
    launchOptions: {
      slowMo: 700
    },

    actionTimeout: 15000,
    navigationTimeout: 30000
  }
});