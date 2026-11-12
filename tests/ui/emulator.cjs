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

async function connected(page) {
  const base = 'http://127.0.0.1:8032';
  const trainer = process.env.TRACKFIT_TEST_CODE;
  async function post(path, body) {
    const response = await fetch(base+path, {method:'POST',headers:{'Content-Type':'application/json',
      'Authorization':'Bearer '+trainer},body:JSON.stringify(body)});
    assert.ok(response.ok, path+' falhou: '+response.status);
    return response.json();
  }
  const student = await post('/students',{name:'Aluno fictício'});
  const exercise = {name:'Exercício teste',sets:1,reps:10,rest_seconds:60};
  await post('/v1/workouts',{student_id:student.id,exercises:[exercise]});
  const template = await post('/templates',{name:'Exemplo',goal:'condicionamento',experience:'iniciante',equipment:'academia',
    minutes:30,min_age:18,max_age:60,days:[{title:'Dia fictício',exercises:[{...exercise,instructions:'Teste de software.'}]}]});
  await post('/templates/'+template.id+'/approval',{approved:true});
  async function login(code) {
    await page.locator('#logout').click();
    await page.locator('#server').fill(base);
    await page.locator('#code').fill(code);
    await page.locator('#enter').click();
  }
  await login(student.access_code);
  await page.locator('#newNav').click();
  await page.locator('#age').fill('30');
  await page.locator('#review').selectOption('no');
  await page.locator('#consent').check();
  await page.locator('#generate').click();
  await page.locator('#start').click();
  await page.locator('.weight').fill('12,5');
  await page.locator('.reps').fill('10');
  await page.locator('#finish').click();
  await page.locator('#sessions button').waitFor();
  await login(trainer);
  await page.locator('#timeline').click();
  for (const title of ['Ficha da API anterior','Ficha do Android','Treino registrado'])
    await page.locator('#records summary').filter({hasText:title}).waitFor();
  await page.locator('#alertsNav').click();
  await page.locator('#alerts button').first().click();
  await page.locator('#approve').click();
  await page.locator('#note').fill('Revisado durante o teste.');
  await page.locator('#save').click();
  await page.getByText('Ficha • versão 2',{exact:true}).waitFor();
}
(async () => {
  const devices = await android.devices();
  assert.equal(devices.length, 1, 'O teste precisa de um emulador conectado');
  const device = devices[0];
  try {
    const webview = await device.webView({ pkg: 'br.com.trackfit.piloto' }, { timeout: 60000 });
    const page = await webview.page();
    await run(page);
    await connected(page);
    console.log('Passou: ficha disponível, aviso ao treinador, revisão, histórico e avaliação pendente.');
  } finally {
    await device.close();
  }
})().catch(error => { console.error(error); process.exitCode = 1; });
