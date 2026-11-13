// Drive the installed debug APK's own WebView through adb's local CDP tunnel.
const { _android: android } = require('playwright');
const assert = require('node:assert/strict');
const {execFileSync} = require('node:child_process');
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
  await page.locator('#alerts').getByRole('button',{name:'Ver ficha'}).first().click();
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
    minutes:30,min_age:18,max_age:60,days:[{title:'Dia fictício',exercises:[{...exercise,exercise_id:'seated_row',name:'Remada sentada',instructions:'Teste de software.'}]}]});
  await post('/templates/'+template.id+'/approval',{approved:true});
  async function login(code) {
    await page.locator('#logout').click();
    await page.locator('#server').fill(base);
    await page.locator('#code').fill(code);
    await page.locator('#enter').click();
  }
  await login(trainer);
  await page.locator('#videosNav').click();
  await page.locator('#exercise').selectOption('seated_row');
  await page.locator('#creator').fill('Canal fictício');
  await page.locator('#link').fill('https://youtu.be/abc_DEF-123');
  await page.locator('#saveVideo').click();
  await page.locator('#curated').getByText(/Canal fictício/).waitFor();
  await login(student.access_code);
  await page.locator('#newNav').click();
  await page.locator('#age').fill('30');
  await page.locator('#review').selectOption('no');
  await page.locator('#consent').check();
  await page.evaluate(()=>{
    const inventory=document.querySelector('#inventory');
    inventory.dataset.request='test-photo';
    window.equipmentPhotoResult('test-photo','SEATED ROW');
  });
  const rowEquipment=page.getByRole('checkbox',{name:'Remada sentada (máquina)'});
  assert.equal(await rowEquipment.isChecked(),false);
  await page.getByRole('button',{name:'Confirmar Remada sentada (máquina)'}).click();
  assert.equal(await rowEquipment.isChecked(),true);
  await page.locator('#generate').click();
  await page.getByText('Consultar catálogo',{exact:true}).click();
  await page.getByRole('button',{name:/Canal fictício/}).click();
  let opened=false;
  for(let attempt=0;attempt<20;attempt++){
    const current=execFileSync('adb',['shell','dumpsys','activity','activities'],{encoding:'utf8'});
    if(current.split('\n').some(line=>/ResumedActivity|topResumedActivity/.test(line)&&line.includes('VideoActivity'))){opened=true;break;}
    await new Promise(resolve=>setTimeout(resolve,250));
  }
  assert.ok(opened,'O player de vídeo deve abrir em sua própria tela');
  execFileSync('adb',['shell','input','keyevent','4']);
  await page.locator('#openSupport').click();
  await page.locator('#question').fill('Dúvida fictícia sobre o aparelho');
  await page.locator('#sendMessage').click();
  await page.locator('#messages').getByText('Dúvida fictícia sobre o aparelho').waitFor();
  await page.locator('#backPlan').click();
  await page.locator('#start').click();
  // Server disappears mid-session; a new instance resumes from a verified backup.
  execFileSync('bash',['tests/ui/restore-server.sh'],{stdio:'inherit'});
  await page.locator('#historyNav').click();
  await page.locator('#sessions button').click();
  await page.locator('.weight').fill('12,5');
  await page.locator('#note').fill('Parcial do teste');
  await page.reload();
  await page.locator('#server').fill(base);
  await page.locator('#code').fill(student.access_code);
  await page.locator('#enter').click();
  await page.locator('#historyNav').click();
  await page.locator('#sessions button').click();
  await page.getByText(/Rascunho recuperado neste aparelho/).waitFor();
  assert.equal(await page.locator('.weight').inputValue(),'12,5');
  assert.equal(await page.locator('.reps').inputValue(),'');
  assert.equal(await page.locator('#note').inputValue(),'Parcial do teste');
  execFileSync('docker',['stop','trackfit-emulator-restored']);
  try {
    await page.reload();
    assert.equal(await page.locator('#server').inputValue(),base);
    await page.locator('#code').fill('codigo-de-outra-pessoa');
    await page.locator('#resumeOffline').click();
    await page.getByText(/Nenhum treino baixado/).waitFor();
    await page.locator('#code').fill(student.access_code);
    await page.locator('#resumeOffline').click();
    await page.locator('.rest-start').first().click();
    await page.getByRole('timer').waitFor();
    await page.getByRole('button',{name:'Encerrar descanso'}).click();
    assert.equal(await page.getByRole('timer').count(),0);
    await page.getByText('Consultar ficha baixada').click();
    assert.equal(await page.locator('.weight').inputValue(),'12,5');
    assert.equal(await page.locator('#note').inputValue(),'Parcial do teste');
    await page.locator('.reps').fill('10');
    await page.locator('#finish').click();
    await page.getByText(/Gravação ainda não confirmada|Treino guardado no aparelho/).waitFor();
    await page.reload();
    await page.locator('#code').fill(student.access_code);
    await page.locator('#resumeOffline').click();
    await page.getByText(/Os dados desta tentativa foram recuperados/).waitFor();
    assert.equal(await page.locator('.weight').inputValue(),'12.5');
  } finally {
    execFileSync('docker',['start','trackfit-emulator-restored']);
    for(let attempt=0;attempt<40;attempt++){
      try{if((await fetch(base+'/health')).ok)break;}catch{}
      await new Promise(resolve=>setTimeout(resolve,250));
    }
  }
  // Drop only the finish acknowledgement after the real server committed it.
  await page.evaluate(()=>{
    const original=window.receiveNative;
    window.receiveNative=(id,response)=>{
      if(response.body?.state==='finished'){
        window.receiveNative=original;
        return original(id,{status:0,body:{detail:'Resposta interrompida pelo teste.'}});
      }
      return original(id,response);
    };
  });
  await page.locator('#finish').click();
  await page.getByText(/Gravação ainda não confirmada/).waitFor();
  await page.locator('#finish').click();
  await page.getByText('Treino sincronizado com o servidor.').waitFor();
  const records=await (await fetch(base+'/sessions',{headers:{Authorization:'Bearer '+student.access_code}})).json();
  assert.equal(records.length,1);
  assert.deepEqual(records[0].actual.sets,[{exercise_index:0,set_index:0,weight_kg:12.5,reps:10}]);
  await login(trainer);
  await page.locator('#week').click();
  await page.getByText('1 treino(s) concluído(s) • 0 agendamento(s)').waitFor();
  await page.getByRole('button',{name:'Responder aluno'}).click();
  await page.locator('#question').fill('Resposta do treinador para teste');
  await page.locator('#sendMessage').click();
  await page.locator('#messages').getByText('Resposta do treinador para teste').waitFor();
  await page.locator('#homeNav').click();
  await page.locator('#timeline').click();
  for (const title of ['Ficha da API anterior','Ficha do Android','Treino registrado'])
    await page.locator('#records summary').filter({hasText:title}).waitFor();
  await page.locator('#alertsNav').click();
  await page.locator('#alerts').getByRole('button',{name:'Ver ficha'}).first().click();
  const week=await (await fetch(base+'/week/0',{headers:{Authorization:'Bearer '+trainer}})).json();
  await page.locator('#scheduledDate').fill(week.today);
  await page.locator('#schedule').click();
  await page.getByText(/Treino agendado para/).waitFor();
  await page.locator('#approve').click();
  await page.locator('#note').fill('Revisado durante o teste.');
  await page.locator('#save').click();
  await page.getByText('Ficha • versão 2',{exact:true}).waitFor();
  await login(student.access_code);
  await page.locator('#week').click();
  await page.getByText('1 treino(s) concluído(s) • 1 agendamento(s)').waitFor();
  await page.locator('#alertsNav').click();
  await page.getByRole('button',{name:'Abrir conversa'}).click();
  await page.locator('#messages').getByText('Resposta do treinador para teste').waitFor();

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
