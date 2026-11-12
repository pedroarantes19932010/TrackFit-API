// Drive the installed debug APK's own WebView through adb's local CDP tunnel.
const { _android: android } = require('playwright');
const assert = require('node:assert/strict');
async function run(page) {
  const errors = [];
  page.on('pageerror', error => errors.push(error.message));
  const click = id => page.locator(id).click();
  const waitText = text => page.getByText(text, {exact: true}).first().waitFor();
  await click('#demo');
  await click('#switchDemo');
  await click('#newNav');
  await page.locator('#age').fill('30');
  await page.locator('#review').selectOption('no');
  await page.locator('#consent').check();
  await click('#generate');
  await waitText('Revisão pendente');
  await click('#start');
  await page.locator('.weight').first().fill('12,5');
  await page.locator('.reps').first().fill('10');
  await click('#finish');
  await click('#sessions button');
  assert.equal(await page.locator('.weight').first().inputValue(), '12.5');

  await click('#homeNav');
  await click('#switchDemo');
  await click('#alertsNav');
  await waitText('Ficha completa de Ana Demo disponível.');
  await page.locator('#alerts button').first().click();
  await click('#edit');
  await page.locator('#title0').fill('Ficha revisada no Android');
  await page.locator('#note').fill('Revisão fictícia do teste');
  await click('#save');
  await waitText('Ficha • versão 2');
  await waitText('Ficha revisada no Android');

  await click('#homeNav');
  await click('#switchDemo');
  await click('#historyNav');
  await click('#sessions button');
  await waitText('TREINO • VERSÃO 1');
  assert.equal(await page.locator('.weight').first().inputValue(), '12.5');

  await click('#newNav');
  await page.locator('#age').fill('30');
  await page.locator('#review').selectOption('yes');
  await page.locator('#consent').check();
  await click('#generate');
  await waitText('Aguardando avaliação');
  assert.equal(await page.locator('#start').count(), 0);
  assert.deepEqual(errors, []);
}

(async () => {
  const devices = await android.devices();
  assert.equal(devices.length, 1, 'O teste precisa de um emulador conectado');
  const device = devices[0];
  try {
    const webview = await device.webView({ pkg: 'br.com.trackfit.piloto' }, { timeout: 60000 });
    const page = await webview.page();
    await run(page);
    console.log('Passou: ficha disponível, aviso ao treinador, revisão, histórico e avaliação pendente.');
  } finally {
    await device.close();
  }
})().catch(error => { console.error(error); process.exitCode = 1; });
