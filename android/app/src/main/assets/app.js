'use strict';
const $ = s => document.querySelector(s);
const esc = s => String(s ?? '').replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const app=$('#app'); let token='',origin='',me=null,demo=false,poller=null,requestCount=0;
const awaiting=new Map(), announced=new Set();
let catalog=[];
let generation=null, pushBinding=null;
const labels={pending:'Aguardando avaliação',released:'Revisão pendente',reviewed:'Revisada pelo treinador',suspended:'Suspensa'};
function uuid(){
 if(typeof crypto.randomUUID==='function')return crypto.randomUUID();
 const bytes=crypto.getRandomValues(new Uint8Array(16));
 bytes[6]=(bytes[6]&15)|64;
 bytes[8]=(bytes[8]&63)|128;
 const hex=Array.from(bytes,b=>b.toString(16).padStart(2,'0')).join('');
 return [hex.slice(0,8),hex.slice(8,12),hex.slice(12,16),hex.slice(16,20),hex.slice(20)].join('-');
}
const copy=value=>JSON.parse(JSON.stringify(value));
function toast(message){$('#toast').textContent=message;$('#toast').style.display='block';clearTimeout(toast.timer);toast.timer=setTimeout(()=>$('#toast').style.display='none',7000);}
window.receiveNative=(id,response)=>{const item=awaiting.get(id);if(!item)return;clearTimeout(item.timer);awaiting.delete(id);response.status>=200&&response.status<300?item.resolve(response.body):item.reject(new Error(typeof response.body?.detail==='string'?response.body.detail:'Confira os campos preenchidos.'));};
function api(method,path,body={}){
 if(demo)return demoApi(method,path,body);
 if(!window.TrackFitNative)return Promise.reject(new Error('Abra o aplicativo Android ou use a demonstração.'));
 return new Promise((resolve,reject)=>{const id=String(++requestCount);const timer=setTimeout(()=>{awaiting.delete(id);reject(new Error('A conexão demorou. Tente novamente.'));},55000);awaiting.set(id,{resolve,reject,timer});TrackFitNative.request(id,origin,token,method,path,JSON.stringify(body));});
}
function button(id,action){$('#'+id)?.addEventListener('click',async e=>{const b=e.currentTarget;b.disabled=true;try{await action();}catch(err){toast(err.message);}finally{b.disabled=false;}});}
function page(html){app.innerHTML=(demo?'<div class="demo-banner">DEMONSTRAÇÃO OFFLINE • Dados fictícios. Nada é enviado ou prescrito. Ao sair, tudo é apagado.</div>':'')+html;window.scrollTo(0,0);}
function input(id,label,value='',type='text'){return `<label for="${id}">${label}</label><input id="${id}" type="${type}" value="${esc(value)}">`;}
function select(id,label,options){return `<label for="${id}">${label}</label><select id="${id}">${options.map(([v,l])=>`<option value="${v}">${l}</option>`).join('')}</select>`;}
const goals=[['condicionamento','Condicionamento'],['hipertrofia','Hipertrofia']];
const levels=[['iniciante','Iniciante'],['intermediario','Intermediário']];
const equipment=[['academia','Academia'],['casa','Casa']];
function login(){
 if(me && !demo) window.TrackFitNative?.bindPush?.('');
 for(const item of awaiting.values()){
   clearTimeout(item.timer);
   item.reject(new Error('A sessão anterior foi encerrada.'));
 }
 awaiting.clear();
 pushBinding=null;clearInterval(poller);me=null;token='';demo=false;announced.clear();generation=null;$('#nav').hidden=true;$('#logout').hidden=true;
 page('<h1>Seu treino no TrackFit</h1><div class="hero"><h2>Experimente como aluno e treinador</h2><p>Abra uma ficha fictícia, registre uma série e revise o treino.</p><button id="demo" class="secondary">Conhecer a demonstração</button></div><h2>Entrar no piloto</h2>'+input('server','Endereço do servidor','http://10.0.2.2:8000','url')+input('code','Código privado de acesso','','password')+'<button id="enter">Entrar</button><p class="muted"><small>Peça o código ao seu treinador. Nesta fase, use somente dados de teste.</small></p>');
 button('enter',async()=>{origin=$('#server').value.trim().replace(/\/+$/,'');token=$('#code').value.trim();me=await api('GET','/me');catalog=await api('GET','/catalog');window.TrackFitNative?.bindPush?.('');shell();await home();});
 button('demo',async()=>{demo=true;catalog=[];resetDemo();me={name:'Pedro • demonstração',role:'trainer',provider:'demo'};shell();await home();});
}
function shell(){
 $('#logout').hidden=false;$('#nav').hidden=false;
 const trainer=me.role==='trainer';
 $('#nav').innerHTML=trainer?'<button id="homeNav">Visão geral</button><button id="modelsNav">Modelos</button><button id="alertsNav">Avisos</button>':'<button id="homeNav">Minhas fichas</button><button id="newNav">Avaliação</button><button id="historyNav">Histórico</button>';
 if (!demo && !trainer) $('#nav').insertAdjacentHTML('beforeend','<button id="alertsNav">Avisos</button>');
 if (!demo && trainer) { $('#nav').insertAdjacentHTML('beforeend','<button id="videosNav">Vídeos</button>'); button('videosNav',videoEditor); }
 button('homeNav',home);button('modelsNav',templates);button('alertsNav',notifications);button('newNav',assessment);button('historyNav',history);
 clearInterval(poller);if(trainer||!demo){poller=setInterval(()=>pollNotifications().catch(()=>{}),30000);pollNotifications().catch(()=>{});}
}
async function pollNotifications(){if(!me)return;const account=me;const rows=await api('GET','/notifications');if(me!==account)return;const count=rows.filter(n=>!n.seen).length;if($('#alertsNav'))$('#alertsNav').textContent=count?'Avisos ('+count+')':'Avisos';for(const n of rows){if(!n.seen&&!announced.has(n.id)){announced.add(n.id);if(!demo)window.TrackFitNative?.notifyReview(n.id);}}}
async function home(){
 const plans=await api('GET','/plans'), trainer=me.role==='trainer';
 page(`<span class="eyebrow">${trainer?'ÁREA DO TREINADOR':'ÁREA DO ALUNO'}</span><h1>Olá, ${esc(me.name.split(' ')[0])}.</h1><p class="muted">${trainer?'As fichas chegam completas. Você revisa e acompanha por aqui.':'Sua ficha e seu histórico, no mesmo lugar.'}</p>${me.provider==='demo'&&!demo?'<div class="notice">Servidor em modo demonstração: seleção por regras, sem IA real.</div>':''}<div class="hero"><small>${trainer?'PARA ACOMPANHAR':'SEU ESPAÇO'}</small><h2>${trainer?plans.filter(p=>['pending','released'].includes(p.state)).length+' fichas para revisar':'Vamos treinar?'}</h2><p>${trainer?'Revisões e avaliações individuais pendentes.':'Preencha a avaliação para receber sua ficha.'}</p></div>${demo?'<button id="switchDemo" class="secondary">Ver como '+(trainer?'aluno':'treinador')+'</button>':''}<button id="primary">${trainer?'Cadastrar aluno':'Preencher avaliação'}</button><h2>${trainer?'Fichas dos alunos':'Minhas fichas'}</h2><div id="plans"></div><div id="supportHome"></div><button id="timeline" class="secondary">Consultar histórico completo</button>`);
 if(!demo){$('#supportHome').innerHTML='<button id="inbox">Conversas sobre fichas</button>';button('inbox',supportInbox);}
 button('timeline',()=>timeline(0));button('primary',trainer?newStudent:assessment);button('switchDemo',async()=>{me.role=trainer?'student':'trainer';me.name=trainer?'Ana Demo':'Pedro Demo';shell();await home();});
 if(!plans.length)$('#plans').innerHTML='<div class="empty">Nenhuma ficha ainda. '+(trainer?'Comece cadastrando um aluno e criando seus modelos.':'Sua primeira ficha aparecerá aqui.')+'</div>';
 for(const p of plans){const el=document.createElement('div');el.className='card';el.innerHTML=`<span class="badge ${p.state}">${esc(labels[p.state])}</span><h2>${esc(p.student_name)}</h2><p>${p.days.length?p.days.length+' dias • versão '+p.version:'Avaliação aguardando atendimento'}</p><button>Abrir ficha</button>`;el.querySelector('button').onclick=()=>detail(p.id).catch(e=>toast(e.message));$('#plans').append(el);}
}
function newStudent(){page('<span class="eyebrow">NOVO ALUNO</span><h1>Vamos começar.</h1><p>O código dá acesso somente aos dados deste aluno. Compartilhe em privado.</p>'+input('name','Nome do aluno')+'<button id="create">Criar acesso</button><div id="result"></div>');button('create',async()=>{const name=$('#name').value.trim();if(name.length<2)throw Error('Informe o nome.');const r=await api('POST','/students',{name});$('#result').innerHTML='<div class="card"><h2>Acesso criado</h2><p>Guarde este código: ele é exibido uma única vez.</p><div class="code">'+esc(r.access_code)+'</div><p><small>Válido por 30 dias.</small></p></div>';});}
function assessment(){
 page('<span class="eyebrow">AVALIAÇÃO INICIAL</span><h1>Conte sobre você.</h1><p class="muted">Seu treinador usa estas respostas para definir uma ficha compatível.</p>'+input('age','Idade','','number')+select('goal','Objetivo',goals)+select('experience','Experiência',levels)+select('equipment','Onde vai treinar?',equipment)+'<div class="row"><div>'+input('days','Dias por semana',1,'number')+'</div><div>'+input('minutes','Minutos por treino',40,'number')+'</div></div>'+select('review','Você tem dor, lesão, condição de saúde, está gestante ou tem alguma dúvida sobre treinar?',[['','Selecione uma resposta'],['yes','Sim / tenho dúvida'],['no','Não']])+'<label for="limits">Restrições ou observações</label><textarea id="limits" placeholder="Se houver algo que seu treinador precisa saber"></textarea><div class="notice">Restrições e dúvidas serão encaminhadas para avaliação individual antes da liberação.</div><label><input id="consent" type="checkbox">Autorizo o uso dessas informações para montar e acompanhar minha ficha neste piloto.</label><button id="generate">Solicitar ficha completa</button>');
 button('generate',async()=>{if(!$('#review').value||!$('#consent').checked)throw Error('Responda à pergunta de saúde e marque a autorização.');const profile={age:Number($('#age').value),goal:$('#goal').value,experience:$('#experience').value,equipment:$('#equipment').value,days:Number($('#days').value),minutes:Number($('#minutes').value),needs_review:$('#review').value==='yes',limitations:$('#limits').value.trim(),consent:true};const serialized=JSON.stringify(profile);if(!generation||generation.serialized!==serialized)generation={serialized,id:uuid()};const p=await api('POST','/plans',{request_id:generation.id,profile});generation=null;await detail(p.id);});
}
function catalogHelp(id){
 const entry=catalog.find(item=>item.exercise_id===id);
 if(!entry)return '';
 return '<details><summary>Consultar catálogo</summary><p>'+esc(entry.name)+' • '+esc(entry.equipment)+'</p><ul>'+entry.instructions.map(line=>'<li>'+esc(line)+'</li>').join('')+'</ul>'+entry.videos.map(v=>'<button type="button" data-youtube="'+esc(v.youtube_id)+'">'+esc(videoKinds[v.kind])+' • '+esc(v.creator_name)+'</button>').join('')+'</details>';
}
const videoKinds={demonstration:'Demonstração',common_mistakes:'Erros comuns',tips:'Dicas'};
app.addEventListener('click',event=>{
 const id=event.target.closest('[data-youtube]')?.dataset.youtube;
 if(id && /^[A-Za-z0-9_-]{11}$/.test(id))window.TrackFitNative?.openVideo(id);
});
function youtubeId(value){
 const raw=value.trim(), valid=/^[A-Za-z0-9_-]{11}$/;
 if(valid.test(raw))return raw;
 try {
   const url=new URL(raw), parts=url.pathname.split('/');
   if(url.protocol==='https:'){
     const id=url.hostname==='youtu.be'?parts[1]:
       ['www.youtube.com','youtube.com','m.youtube.com'].includes(url.hostname)?
       (url.pathname==='/watch'?url.searchParams.get('v'):['shorts','embed'].includes(parts[1])?parts[2]:''):'';
     if(id && valid.test(id))return id;
   }
 }catch{}
 throw Error('Informe o link do YouTube ou o identificador de 11 caracteres.');
}
async function videoEditor(selected){
 catalog=await api('GET','/catalog');
 page('<h1>Vídeos dos exercícios</h1>'+select('exercise','Exercício',catalog.map(e=>[e.exercise_id,e.name]))+
     input('link','Link ou ID do YouTube')+input('creator','Nome do canal')+select('kind','Tipo de vídeo',Object.entries(videoKinds))+
     '<button id="saveVideo">Salvar vídeo</button><div id="curated"></div>');
 const exercise=$('#exercise');
 if(selected)exercise.value=selected;
 function render(){
   const videos=catalog.find(e=>e.exercise_id===exercise.value)?.videos||[], list=$('#curated');
   list.replaceChildren();
   for(const v of videos){
     const row=document.createElement('div');
     row.className='card';
     row.innerHTML='<button data-youtube="'+esc(v.youtube_id)+'">'+esc(videoKinds[v.kind])+' • '+esc(v.creator_name)+'</button><button class="secondary">Remover</button>';
     row.lastElementChild.onclick=async()=>{try{const id=exercise.value;await api('POST','/catalog/'+id+'/videos/'+v.youtube_id+'/remove');await videoEditor(id);}catch(e){toast(e.message);}};
     list.append(row);
   }
 }
 exercise.onchange=render;render();
 button('saveVideo',async()=>{
   const id=exercise.value,creator=$('#creator').value.trim();
   if(!creator)throw Error('Informe o nome do canal.');
   await api('POST','/catalog/'+id+'/videos',{youtube_id:youtubeId($('#link').value),creator_name:creator,kind:$('#kind').value});
   await videoEditor(id);
 });
}
function daysHtml(days){return days.map(d=>`<div class="card"><h2>${esc(d.title)}</h2>${d.exercises.map(e=>`<div class="exercise"><strong>${esc(e.name)}</strong><span>${e.sets} séries × ${e.reps} repetições • ${e.rest_seconds}s descanso</span><small>${esc(e.instructions)}</small>${catalogHelp(e.exercise_id)}</div>`).join('')}</div>`).join('');}
async function detail(id){
 const account=me;
 const [p, currentCatalog]=await Promise.all([api('GET','/plans/'+id),demo?catalog:api('GET','/catalog')]);
 if(me!==account)return;
 catalog=currentCatalog;const trainer=me.role==='trainer';
 page(`<span class="badge ${p.state}">${esc(labels[p.state])}</span><h1>${esc(p.student_name)}</h1><p class="muted">Ficha • versão ${p.version}</p><div class="notice">${esc(p.note)}</div>${trainer?`<details><summary>Ver avaliação</summary><div class="card">${Object.entries({Idade:p.profile.age,Objetivo:p.profile.goal,Experiência:p.profile.experience,Dias:p.profile.days,Minutos:p.profile.minutes,Local:p.profile.equipment,'Requer avaliação':p.profile.needs_review?'Sim':'Não',Observações:p.profile.limitations||'Nenhuma'}).map(([k,v])=>`<div class="summary"><span>${esc(k)}</span><strong>${esc(v)}</strong></div>`).join('')}</div></details>`:''}${daysHtml(p.days)}${!p.days.length?'<div class="empty">Seu treinador precisa concluir a avaliação antes de liberar os exercícios.</div>':''}<div id="actions"></div><div id="supportLink"></div>`);
 if(!demo){$('#supportLink').innerHTML='<button class="secondary" id="openSupport">Conversa sobre esta ficha</button>';button('openSupport',()=>conversation(id));}
 if(trainer){$('#actions').innerHTML='<button id="approve">Marcar como revisada</button><button id="edit" class="secondary">Editar ficha completa</button><button id="suspend" class="danger">Suspender ficha</button>';button('approve',()=>reviewNote(p,'approve'));button('edit',()=>editPlan(p));button('suspend',()=>reviewNote(p,'suspend'));}
 else if(['released','reviewed'].includes(p.state)){
 $('#actions').innerHTML=select('day','Qual treino fará agora?',p.days.map((d,i)=>[i,esc(d.title)]))+'<button id="start">Iniciar treino</button>';const requestId=uuid();button('start',async()=>{const s=await api('POST',`/plans/${id}/sessions`,{request_id:requestId,expected_version:p.version,day:Number($('#day').value)});sessionView(s);});}
}
async function supportInbox(){
 const rows=await api('GET','/support');
 page('<h1>Conversas sobre fichas</h1><div id="threads"></div>');
 if(!rows.length)$('#threads').textContent='Nenhuma conversa. Abra uma ficha para enviar uma mensagem.';
 for(const item of rows){
   const b=document.createElement('button');
   b.textContent=item.student_name+' • '+(item.role==='student'?'Última mensagem do aluno':'Última mensagem do treinador');
   b.onclick=()=>conversation(item.plan).catch(e=>toast(e.message));$('#threads').append(b);
 }
}
async function conversation(id){
 const rows=await api('GET','/plans/'+id+'/support');
 page('<h1>Conversa sobre a ficha</h1><button id="backPlan" class="secondary">Ver ficha</button><div id="messages"></div><label for="question">Mensagem</label><textarea id="question" maxlength="1200"></textarea><button id="sendMessage">Enviar</button>');
 button('backPlan',()=>detail(id));
 for(const row of rows){
   const card=document.createElement('div');card.className='card';
   const title=document.createElement('strong');title.textContent=(row.role==='trainer'?'Treinador':'Aluno')+' • versão '+row.version;
   const message=document.createElement('p');message.textContent=row.message;
   card.append(title,message);$('#messages').append(card);
 }
 let pending;
 button('sendMessage',async()=>{
   const message=$('#question').value.trim();if(!message)throw Error('Escreva uma mensagem.');
   if(pending?.message!==message)pending={message,request_id:uuid()};
   await api('POST','/plans/'+id+'/support',pending);
   await conversation(id);
 });
}
function reviewNote(p,action){page('<h1>'+ (action==='approve'?'Concluir revisão':'Suspender ficha')+'</h1><p>'+ (action==='approve'?'Confirme após avaliar a ficha e as informações do aluno.':'A suspensão impede novos treinos e interrompe sessões ativas.')+'</p><label for="note">Motivo / orientação</label><textarea id="note"></textarea><button id="save">Confirmar</button>');button('save',async()=>{await api('POST',`/plans/${p.id}/review`,{action,expected_version:p.version,note:$('#note').value});await detail(p.id);});}
function dayEditor(days){
 $('#editor').innerHTML='';days.forEach((d,i)=>{const box=document.createElement('section');box.className='card day-edit';box.innerHTML=input('title'+i,'Nome do treino',d.title)+'<div class="exercise-fields"></div><button class="secondary add-exercise">Adicionar exercício</button>';
 const list=box.querySelector('.exercise-fields');for(const ex of d.exercises)addExercise(list,ex);
 box.querySelector('.add-exercise').onclick=()=>addExercise(list);$('#editor').append(box);});
}
function addExercise(parent,e={name:'',sets:2,reps:10,rest_seconds:60,instructions:''}){
 const row=document.createElement('div');row.className='exercise editor-row';row.innerHTML='<label>Nome do exercício</label><input class="ex-name" value="'+esc(e.name)+'"><div class="row"><div><label>Séries</label><input class="ex-sets" type="number" value="'+e.sets+'"></div><div><label>Repetições</label><input class="ex-reps" type="number" value="'+e.reps+'"></div><div><label>Descanso (s)</label><input class="ex-rest" type="number" value="'+e.rest_seconds+'"></div></div><label>Orientações de execução e carga</label><textarea class="ex-instructions">'+esc(e.instructions)+'</textarea><button class="ghost remove">Remover</button>';row.dataset.catalogId=e.exercise_id||'';
 if(catalog.length){
   const label=document.createElement('label');label.textContent='Referência do catálogo';
   const picker=document.createElement('select');picker.add(new Option('Exercício personalizado',''));
   for(const entry of catalog)picker.add(new Option(entry.name,entry.exercise_id));
   picker.value=row.dataset.catalogId;
   picker.onchange=()=>{
     row.dataset.catalogId=picker.value;
     const entry=catalog.find(item=>item.exercise_id===picker.value);
     if(entry){row.querySelector('.ex-name').value=entry.name;row.querySelector('.ex-instructions').value=entry.instructions.join(' ');}
   };
   row.querySelector('.ex-name').oninput=()=>{picker.value='';row.dataset.catalogId='';};
   label.append(picker);row.prepend(label);
 }
 row.querySelector('.remove').onclick=()=>row.remove();parent.append(row);
}
function readDays(){return [...document.querySelectorAll('.day-edit')].map((d,i)=>({title:$('#title'+i).value,exercises:[...d.querySelectorAll('.editor-row')].map(e=>({...e.dataset.catalogId?{exercise_id:e.dataset.catalogId}:{},name:e.querySelector('.ex-name').value,sets:Number(e.querySelector('.ex-sets').value),reps:Number(e.querySelector('.ex-reps').value),rest_seconds:Number(e.querySelector('.ex-rest').value),instructions:e.querySelector('.ex-instructions').value}))}));}
function editPlan(p){page('<span class="eyebrow">REVISÃO PROFISSIONAL</span><h1>Ajustar ficha.</h1><p>A nova versão será usada nos próximos treinos. A sessão em andamento mantém sua ficha original.</p><div id="editor"></div><label for="note">O que você avaliou e alterou?</label><textarea id="note"></textarea><button id="save">Salvar e liberar versão revisada</button>');dayEditor(p.days.length?p.days:Array.from({length:p.profile.days},(_,i)=>({title:'Treino '+(i+1),exercises:[]})));button('save',async()=>{await api('POST',`/plans/${p.id}/review`,{action:'edit',expected_version:p.version,note:$('#note').value,days:readDays()});await detail(p.id);});}
async function templates(){const rows=await api('GET','/templates');page('<span class="eyebrow">SUA BASE PROFISSIONAL</span><h1>Modelos de treino.</h1><p>Somente modelos aprovados podem ser selecionados automaticamente. Aprovar um modelo não aprova todas as fichas já geradas.</p><button id="newTemplate">Criar modelo</button><div id="templates"></div>');button('newTemplate',newTemplate);for(const t of rows){const el=document.createElement('div');el.className='card';el.innerHTML=`<span class="badge">${t.approved?'Aprovado para seleção':'Rascunho'}</span><h2>${esc(t.data.name)}</h2><p>${esc(t.data.goal)} • ${t.data.days.length} dias • ${t.data.minutes} min<br>${esc(t.data.experience)} • ${esc(t.data.equipment)} • ${t.data.min_age}–${t.data.max_age} anos</p><details><summary>Ver ficha completa</summary>${daysHtml(t.data.days)}</details><button>${t.approved?'Retirar da seleção automática':'Aprovar este modelo'}</button>`;el.lastElementChild.onclick=async()=>{try{await api('POST',`/templates/${t.id}/approval`,{approved:!t.approved});await templates();}catch(e){toast(e.message);}};$('#templates').append(el);}if(!rows.length)$('#templates').innerHTML='<p class="empty">Nenhum modelo. A liberação automática está desativada até você criar e aprovar um.</p>';}
function newTemplate(){page('<span class="eyebrow">NOVO MODELO</span><h1>Sua ficha de referência.</h1>'+input('modelName','Nome do modelo')+select('goal','Objetivo',goals)+select('experience','Experiência',levels)+select('equipment','Equipamentos',equipment)+input('minutes','Duração estimada por treino (minutos)',40,'number')+'<div class="row"><div>'+input('minAge','Idade mínima',18,'number')+'</div><div>'+input('maxAge','Idade máxima',60,'number')+'</div></div>'+input('dayCount','Dias por semana',1,'number')+'<button id="makeDays" class="secondary">Preparar os dias</button><div id="editor"></div><button id="save">Salvar como rascunho</button>');dayEditor([{title:'Treino 1',exercises:[]}]);button('makeDays',()=>{const count=Number($('#dayCount').value);if(count<1||count>6||!Number.isInteger(count))throw Error('Escolha de 1 a 6 dias.');const current=readDays();if(count<current.length)throw Error('Para reduzir dias, abra um novo modelo. Isso evita apagar seu trabalho.');dayEditor(Array.from({length:count},(_,i)=>current[i]||{title:'Treino '+(i+1),exercises:[]}));});button('save',async()=>{await api('POST','/templates',{name:$('#modelName').value,goal:$('#goal').value,experience:$('#experience').value,equipment:$('#equipment').value,minutes:Number($('#minutes').value),min_age:Number($('#minAge').value),max_age:Number($('#maxAge').value),days:readDays()});await templates();});}
async function timeline(pageNumber) {
 const rows=await api('GET','/history/page/'+pageNumber);
 page('<h1>Histórico completo</h1><p>Fichas e sessões em ordem de registro.</p><div id="records"></div><div id="paging"></div>');
 for (const row of rows) {
   const card=document.createElement('details'); card.className='card';
   const title={plano:'Ficha do Android',ficha_v1:'Ficha da API anterior',sessao:'Treino registrado'}[row.kind];
   const summary=document.createElement('summary');
   summary.textContent=title+' • '+row.name+' • versão '+row.version;
   card.append(summary);
   const date=document.createElement('p');date.textContent=new Date(row.created*1000).toLocaleString('pt-BR');card.append(date);
   const days=row.kind==='sessao'?[row.payload.day]:row.kind==='ficha_v1'?[{title:'Exercícios',exercises:row.payload}]:row.payload;
   const content=document.createElement('div');content.innerHTML=daysHtml(days);card.append(content);
   if(row.kind==='sessao' && row.payload.actual){
     const actual=document.createElement('div');
     for(const set of row.payload.actual.sets){
       const line=document.createElement('p');
       line.textContent=row.payload.day.exercises[set.exercise_index].name+' • série '+(set.set_index+1)+': '+set.weight_kg+' kg × '+set.reps;
       actual.append(line);
     }
     card.append(actual);
   }
   $('#records').append(card);
 }
 if(!rows.length)$('#records').textContent='Nenhum registro nesta página.';
 $('#paging').innerHTML=(pageNumber?'<button id="prev">Página anterior</button>':'')+(rows.length===30?'<button id="next">Próxima página</button>':'');
 button('prev',()=>timeline(pageNumber-1));button('next',()=>timeline(pageNumber+1));
}
function enablePush(){
 if(!window.TrackFitNative?.enableReviewPush)throw Error('Use o aplicativo Android com suporte a notificações.');
 pushBinding=uuid();
 window.TrackFitNative.enableReviewPush(pushBinding);
}
window.receivePush=async(binding,deviceToken,error)=>{
 if(binding!==pushBinding||!me||demo)return;
 if(error){toast(error);return;}
 try{
   await api('POST','/push/devices',{binding,token:deviceToken});
   if(binding!==pushBinding)return;
   window.TrackFitNative.bindPush(binding);
   toast('Avisos ativados neste aparelho.');
 }catch(e){toast(e.message);}
};
async function notifications(){const rows=await api('GET','/notifications');page('<span class="eyebrow">ACOMPANHAMENTO</span><h1>Seus avisos.</h1><p class="muted">Consulte as mensagens de suporte e as atualizações da ficha.</p><div id="pushAction"></div><div id="alerts"></div>');if(!demo){$('#pushAction').innerHTML='<button id="push">Ativar avisos com o app fechado</button>';button('push',enablePush);}for(const n of rows){const el=document.createElement('div');el.className='card';el.innerHTML='<span class="badge">'+(n.seen?'Lido':'Novo')+'</span><p>'+esc(n.message)+'</p><button>'+(n.kind==='support'?'Abrir conversa':'Ver ficha')+'</button>';el.querySelector('button').onclick=async()=>{try{await api('POST',`/notifications/${n.id}/read`);if(n.kind==='support')await conversation(n.plan);else await detail(n.plan);}catch(e){toast(e.message);}};$('#alerts').append(el);}if(!rows.length)$('#alerts').innerHTML='<p class="empty">Nenhum aviso por enquanto.</p>';}
async function history(){const rows=await api('GET','/sessions');page('<span class="eyebrow">SEU REGISTRO</span><h1>Histórico de treinos.</h1><div id="sessions"></div>');for(const s of rows){const el=document.createElement('div');el.className='card';el.innerHTML='<span class="badge">'+esc({active:'Em andamento',finished:'Concluído',suspended:'Suspenso'}[s.state])+'</span><h2>'+esc(s.snapshot.title)+'</h2><p>Ficha versão '+s.version+'</p><button>Abrir registro</button>';el.querySelector('button').onclick=()=>sessionView(s);$('#sessions').append(el);}if(!rows.length)$('#sessions').innerHTML='<p class="empty">Os treinos iniciados aparecerão aqui.</p>';}
function finishPayload() {
 const sets=[];
 for(const row of document.querySelectorAll('.set-row')){
   const weight=row.querySelector('.weight').value.trim(), reps=row.querySelector('.reps').value.trim();
   if(!weight&&!reps)continue;
   const kg=Number(weight.replace(',','.')), count=Number(reps);
   if(!weight||!reps||!Number.isFinite(kg)||kg<0||kg>1000||!Number.isInteger(count)||count<0||count>100)
     throw Error('Confira a carga (0–1000 kg) e as repetições (0–100) de cada série.');
   sets.push({exercise_index:Number(row.dataset.exercise),set_index:Number(row.dataset.set),weight_kg:kg,reps:count});
 }
 if(!sets.length)throw Error('Registre ao menos uma série realizada.');
 return {sets,note:$('#note').value};
}
function sessionView(s){
 const native=demo?null:window.TrackFitNative;
 const scope=JSON.stringify([origin,me.id,s.id]);
 const viewUser=me;
 let pending=null, editing=null, unreadable=false;
 if(s.state==='active'){
   const saved=native?.loadFinish?.(scope);
   if(saved){
     try{
       const record=JSON.parse(saved);
       if(typeof record.note!=='string'||!Array.isArray(record.sets))throw Error();
       if(record.mode==='editing')editing=record;
       else pending=record;
     }catch{unreadable=true;}
   }
 }else{native?.storeFinish?.(scope,'');}

 page('<span class="eyebrow">TREINO • VERSÃO '+s.version+'</span><h1>'+esc(s.snapshot.title)+'</h1><div class="notice">Registre somente o que realizou. A carga não é sugerida automaticamente. Zero significa ausência de carga externa. Campos vazios não são registrados.</div><div id="sets"></div>'+ (s.state==='active'?'<label for="note">Observações</label><textarea id="note" maxlength="1000"></textarea><p id="saveState" role="status"></p><button id="finish">Salvar treino realizado</button>':'<p>Este registro está '+esc(s.state==='finished'?'concluído':'suspenso')+'.</p>'));
 for(let i=0;i<s.snapshot.exercises.length;i++){const e=s.snapshot.exercises[i];const box=document.createElement('div');box.className='card';box.innerHTML='<h2>'+esc(e.name)+'</h2><p>'+esc(e.instructions)+'</p><small>Referência: '+e.sets+' × '+e.reps+' • '+e.rest_seconds+'s de descanso</small>'+catalogHelp(e.exercise_id);for(let j=0;j<e.sets;j++){const actual=(s.actual||pending||editing)?.sets.find(x=>x.exercise_index===i&&x.set_index===j);const row=document.createElement('div');row.className='row set-row';row.dataset.exercise=i;row.dataset.set=j;row.innerHTML='<div><label>Série '+(j+1)+' • kg</label><input class="weight" maxlength="16" inputmode="decimal" value="'+esc(actual?.weight_kg??'')+'" '+(s.state!=='active'?'disabled':'')+'></div><div><label>Repetições realizadas</label><input class="reps" type="number" value="'+esc(actual?.reps??'')+'" '+(s.state!=='active'?'disabled':'')+'></div>';box.append(row);}$('#sets').append(box);}
 if(s.state!=='active')return;
 const finishButton=$('#finish'), status=$('#saveState');
 function retryState(message){
   status.textContent=message;
   finishButton.textContent='Tentar confirmar novamente';
   document.querySelectorAll('.set-row input,#note').forEach(input=>input.disabled=true);
 }
 if(unreadable){status.textContent='O rascunho não pôde ser lido. Confira o histórico do servidor antes de preencher novamente.';}
 if(editing){
   $('#note').value=editing.note;
   status.textContent='Rascunho recuperado neste aparelho. Você pode continuar preenchendo.';
 }
 function saveEditing(){
   if(pending||!native)return;
   const sets=[];
   for(const row of document.querySelectorAll('.set-row')){
     const weight=row.querySelector('.weight').value,reps=row.querySelector('.reps').value;
     if(weight||reps)sets.push({exercise_index:Number(row.dataset.exercise),set_index:Number(row.dataset.set),weight_kg:weight,reps});
   }
   const note=$('#note').value;
   const saved=native.storeFinish(scope,sets.length||note?JSON.stringify({mode:'editing',sets,note}):'');
   status.textContent=saved?'Rascunho salvo neste aparelho.':'Não foi possível guardar o rascunho neste aparelho.';
 }
 $('#sets').addEventListener('input',saveEditing);
 $('#note').addEventListener('input',saveEditing);
 if(pending){$('#note').value=pending.note;retryState('Envio pendente. Os dados desta tentativa foram recuperados.');}
 button('finish',async()=>{
   if(!pending){
     const body=finishPayload();
     if(native?.storeFinish&&!native.storeFinish(scope,JSON.stringify(body)))throw Error('Não foi possível guardar a tentativa neste aparelho. Os campos continuam disponíveis.');
     pending=body;
   }
   retryState('Aguardando confirmação do servidor…');
   let result;
   try{result=await api('POST','/sessions/'+s.id+'/finish',pending);}
   catch(error){status.textContent='Gravação ainda não confirmada. Reconecte e tente novamente com os mesmos dados. Se o treino foi suspenso, consulte o histórico.';throw error;}
   native?.storeFinish?.(scope,'');
   if(me!==viewUser||!finishButton.isConnected)return;
   try{await history();}catch{sessionView(result);toast('Treino salvo. O histórico completo poderá ser atualizado depois.');}
 });
}
// Isolated offline walkthrough: never calls the server; all contents are fictional.
let demoPlans=[],demoTemplates=[],demoSessions=[],demoAlerts=[];
const sampleDay=()=>({title:'Treino demonstrativo',exercises:[{name:'Exercício ilustrativo A',sets:2,reps:10,rest_seconds:60,instructions:'Exemplo de interface. Não executar como prescrição.'},{name:'Exercício ilustrativo B',sets:2,reps:12,rest_seconds:60,instructions:'O treinador define exercícios e orientações reais.'}]});
function resetDemo(){demoTemplates=[{id:'sample-model',approved:true,data:{name:'Exemplo fictício • 1 dia',goal:'condicionamento',experience:'iniciante',equipment:'academia',minutes:30,min_age:18,max_age:65,days:[sampleDay()]}}];demoSessions=[];demoPlans=[{id:'demo-plan',student_name:'Ana Demo',version:1,state:'released',source:'demo',note:'Ficha fictícia para conhecer o aplicativo. Não executar.',profile:{age:30,goal:'condicionamento',experience:'iniciante',equipment:'academia',days:1,minutes:40,needs_review:false,limitations:'',consent:true},days:[sampleDay()]}];demoAlerts=[{id:'demo-alert',plan:'demo-plan',message:'Ficha completa de demonstração disponível.',seen:0}];}
async function demoApi(method,path,b){
 const parts=path.split('/').filter(Boolean),id=parts[1];
 if(path.startsWith('/history/page/')) {
   const rows=demoSessions.map(s=>({kind:'sessao',name:'Ana Demo',version:s.version,created:Date.now()/1000,payload:{day:s.snapshot,actual:s.actual,state:s.state}}));
   return rows.concat(demoPlans.map(p=>({kind:'plano',name:p.student_name,version:p.version,created:Date.now()/1000,payload:p.days}))).slice(Number(parts[2])*30,Number(parts[2])*30+30);
 }
 if(path==='/plans'&&method==='GET')return copy(demoPlans);
 if(path==='/plans'&&method==='POST'){
   const profile=b.profile;
   if(!Number.isInteger(profile.age)||profile.age<18||profile.age>100||!Number.isInteger(profile.days)||profile.days<1||profile.days>6||!Number.isInteger(profile.minutes)||profile.minutes<15||profile.minutes>120)throw Error('Confira idade (18–100), dias (1–6) e duração (15–120 minutos).');
   const model=demoTemplates.find(t=>t.approved && !profile.needs_review && !profile.limitations.trim()
     && ['goal','experience','equipment'].every(key=>t.data[key]===profile[key])
     && t.data.days.length===profile.days && t.data.minutes<=profile.minutes
     && t.data.min_age<=profile.age && profile.age<=t.data.max_age);
   const plan={id:uuid(),student_name:'Ana Demo',version:1,state:model?'released':'pending',
     note:model?'Simulação por regras. Ficha completa disponível para revisão.':'Avaliação individual pendente.',
     profile,days:model?copy(model.data.days):[]};
   demoPlans.unshift(plan);
   demoAlerts.unshift({id:uuid(),plan:plan.id,message:model?'Ficha completa de Ana Demo disponível.':'Avaliação aguardando atendimento.',seen:0});
   return copy(plan);
 }
 if(parts[0]==='plans'&&id){const p=demoPlans.find(x=>x.id===id);if(!p)throw Error('Ficha não encontrada.');if(method==='GET')return copy(p);if(parts[2]==='review'){if(b.note.trim().length<3)throw Error('Descreva sua revisão.');if(b.action==='edit'){if(!b.days.length||b.days.some(d=>!d.exercises.length))throw Error('Preencha os exercícios.');p.days=b.days;}if(b.action==='approve'&&!p.days.length)throw Error('Adicione exercícios antes de aprovar.');p.version++;p.state=b.action==='suspend'?'suspended':'reviewed';p.note=b.note;if(p.state==='suspended')demoSessions.filter(s=>s.plan===p.id&&s.state==='active').forEach(s=>s.state='suspended');return copy(p);}if(parts[2]==='sessions'){if(demoSessions.some(s=>s.state==='active'))throw Error('Já há um treino ativo no histórico.');const s={id:uuid(),plan:p.id,version:p.version,state:'active',snapshot:copy(p.days[b.day]),actual:null};demoSessions.unshift(s);return copy(s);}}
 if(path==='/templates'&&method==='GET')return copy(demoTemplates);
 if(path==='/templates'&&method==='POST'){if(!b.name||b.days.some(d=>!d.exercises.length))throw Error('Preencha nome e exercícios.');const t={id:uuid(),approved:false,data:b};demoTemplates.push(t);return t;}
 if(parts[0]==='templates'&&parts[2]==='approval'){demoTemplates.find(x=>x.id===id).approved=b.approved;return {};}
 if(path==='/notifications')return copy(demoAlerts);
 if(parts[0]==='notifications'){demoAlerts.find(x=>x.id===id).seen=1;return {};}
 if(path==='/students')return {access_code:'EXEMPLO-SEM-VALIDADE',expires_in_days:30};
 if(path==='/sessions')return copy(demoSessions);
 if(parts[0]==='sessions'&&parts[2]==='finish'){const s=demoSessions.find(x=>x.id===id);s.actual=b;s.state='finished';return copy(s);}
 throw Error('Ação indisponível na demonstração.');
}
$('#logout').onclick=login;login();
