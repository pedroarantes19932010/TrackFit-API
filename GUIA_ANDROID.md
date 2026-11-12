# Testar o TrackFit no Android

Abra o [PR do piloto](https://github.com/pedroarantes19932010/TrackFit-API/pull/9/checks), selecione a última execução bem-sucedida de **Android piloto** e baixe **TrackFit-Android-debug** na seção **Artifacts**. Extraia o APK do ZIP. O arquivo APK na pasta downloads é de uma versão anterior. Use Android 8 ou superior com WebView atualizado. O arquivo também funciona offline. No computador, baixe [TrackFit-Demo.html](downloads/TrackFit-Demo.html) e abra no navegador.

1. Abra **Conhecer a demonstração**. A página inicial mostra as fichas que Pedro pode revisar.
2. Toque em **Ver como aluno**, depois em **Preencher avaliação**. Para o exemplo fictício, use 30 anos, condicionamento, iniciante, academia, 1 dia e 40 minutos. Responda “Não” à pergunta sobre limitações e marque a autorização para o exemplo.
3. Toque em **Solicitar ficha completa**. A ficha aparece com revisão pendente e já permite iniciar o treino. O teste usa um modelo fictício de um dia. Outros perfis podem precisar de revisão.
4. Registre uma série fictícia e salve. Em **Minhas fichas**, volte para **Ver como treinador**. Abra **Avisos**, escolha a nova ficha e edite um exercício. A revisão cria uma versão nova. O histórico guarda a versão da sessão realizada.

A demonstração roda em memória. Sair ou fechar apaga os exemplos. O servidor do piloto usa SQLite para guardar treinos entre sessões. O aviso de geração aparece quando a ficha fica completa. No Android conectado, o app consulta a caixa de avisos a cada 30 segundos enquanto está aberto. Com Firebase configurado no APK e no servidor, ative os avisos em **Avisos** para recebê-los em segundo plano.

## Rodar o piloto conectado

O serviço iniciado abaixo atende o Android, /v1/auth e /v1/workouts usando o mesmo cadastro, vínculo e sessão de acesso. Um aluno cadastrado pelo treinador já pode ser identificado pela API v1. O piloto mantém as fichas de vários dias em /plans e os treinos simples da API anterior em /v1/workouts. A tela **Consultar histórico completo** reúne versões dos dois formatos e sessões realizadas, preservando a origem.

O serviço usa TRACKFIT_DB_PATH ou TRACKFIT_DB. Se ambas estiverem configuradas, devem apontar para o mesmo arquivo. Um banco antigo do piloto é convertido em uma transação na inicialização. Códigos, vencimentos e sessões de treino são preservados. Antes de atualizar uma instalação, pare os processos e faça backup do banco. Se já existirem dois arquivos distintos com dados, mantenha ambos: a atualização não combina contas de arquivos separados. No piloto Android o aluno precisa ter um único treinador responsável. Use dados fictícios nos testes.

No PowerShell, a partir da raiz desta branch:

~~~powershell
python -m venv .venv
.\.venv\Scripts\python -m pip install -r server/requirements.txt
.\.venv\Scripts\python -m server.bootstrap --name Pedro
.\.venv\Scripts\python -m uvicorn server.app:create_app --factory --host 127.0.0.1 --port 8000
~~~

Guarde o código de treinador exibido na criação. O APK disponibilizado usa HTTPS para conexões reais. Para o emulador local, abra android/ no Android Studio e execute a variante debug, que admite http://10.0.2.2:8000. Use **Cadastrar aluno** para obter um código de aluno. Em **Modelos**, informe o perfil, os dias e exercícios, salve e aprove o modelo. O banco começa sem modelos aprovados. Entre com o código do aluno para fazer a avaliação.

Por padrão o servidor seleciona modelos por regras. Para experimentar a integração externa, configure no ambiente do servidor TRACKFIT_PROVIDER=openai, OPENAI_MODEL e OPENAI_API_KEY. O serviço solicita à IA a escolha de uma ficha entre os modelos elegíveis e valida o identificador devolvido. Não envia o nome nem as respostas livres do aluno. A chave fica no servidor. A validação deste piloto usou dados fictícios, sem chamada paga.

## Verificação

Execute python -m unittest discover -s tests -v na raiz após instalar as dependências. O APK foi compilado com SDK 35, assinado com chave de teste e verificado com apksigner. Para hospedagem, backup, ativação da IA e notificações em aparelhos reais, consulte [o guia do piloto conectado](deploy/README.md). A entrega real pelo Firebase, o teste físico, o servidor público e a publicação na Play Store dependem de configuração externa.

## Quando o sinal cai ao salvar

Ao tocar em **Salvar treino realizado**, o Android conectado guarda uma tentativa criptografada no aparelho. Enquanto faltar a confirmação do servidor, os dados dessa tentativa ficam disponíveis para reenvio. Depois de reabrir o app, entre com a mesma conta no mesmo servidor e consulte **Histórico**. Se a sessão estiver em andamento, abra-a para confirmar o envio. Se estiver concluída, abra o registro salvo. Esta proteção começa ao tocar em salvar.

O [rascunho da primeira ficha](RASCUNHO_FICHA.md) fica disponível para revisão do treinador.

## Catálogo e suporte no piloto conectado

Ao criar ou editar um modelo, adicione um exercício e selecione a referência do catálogo. Você também pode manter um exercício personalizado. O vínculo acompanha a ficha gerada e a sessão gravada. No detalhe da ficha, **Consultar catálogo** mostra as orientações cadastradas. Os seis itens iniciais vêm do catálogo do PR nº 11; nenhum vídeo foi selecionado por padrão.

O aluno abre **Conversa sobre esta ficha** e envia a dúvida. Em **Conversas sobre fichas**, o treinador vê quem escreveu por último, abre a conversa, responde e pode voltar para editar a ficha. Cada mensagem guarda a versão existente no momento do envio. Em **Avisos**, aluno e treinador podem abrir diretamente a conversa que recebeu uma mensagem. Abrir a conversa marca seus avisos como lidos. Para receber avisos com o aplicativo fechado, use uma compilação vinculada ao Firebase e ative essa opção no aparelho.

No piloto conectado, abra **Vídeos**, escolha o exercício, cole o link do YouTube e informe o canal e a categoria. Após salvar, o aluno encontra o vídeo em **Consultar catálogo** na ficha ou durante o treino. Se a incorporação estiver indisponível, o player oferece **Abrir no YouTube**. O treinador pode atualizar um vídeo salvando o mesmo link ou removê-lo do exercício.

## Usar o treino na academia sem sinal

1. Entre com o código do aluno enquanto houver internet. Abra a ficha liberada, escolha o dia e toque em **Iniciar treino**. Aguarde **Treino baixado neste aparelho** antes de desconectar.
2. Se fechar o app, abra-o, informe o mesmo código e toque em **Abrir treino baixado**. O endereço do último servidor fica preenchido. A sessão do dia aceita cargas, repetições e observações. A opção **Consultar ficha baixada** mostra também os demais dias baixados. Apenas o dia iniciado aceita registros.
3. Toque em **Salvar treino realizado**. Sem conexão, o registro permanece no aparelho. Com a tela offline aberta e um envio pendente, o app tenta enviar quando o Android informa que a rede voltou. Você também pode tocar em **Tentar confirmar novamente**. Aguarde a confirmação do servidor.
4. Revisões e suspensões feitas pelo treinador só chegam com internet. O servidor confere o estado da sessão ao receber o registro. O download da sessão é removido após a confirmação. Mensagens, vídeos do YouTube e novas sessões precisam de conexão.

## Avaliar as escolhas da IA

O arquivo examples/avaliacoes_ficticias.json contém dois casos fictícios para entender o processo. Os rótulos são exemplos de preferência, sem validação profissional. Na raiz do projeto, execute:

```sh
python -m server.evaluate_selector examples/avaliacoes_ficticias.json
```

O modo demo seleciona o primeiro candidato. Para preparar a sua avaliação, use perfis fictícios, ofereça somente fichas elegíveis e preencha expected com o ID da ficha que escolheria. Inclua escolhas difíceis com duas ou mais fichas e varie a ordem dos candidatos. Mantenha alguns casos separados para testar mudanças futuras. Compare as divergências antes e depois de mudar as instruções de seleção.

Com as credenciais de API configuradas no ambiente, a opção `--provider openai` consulta o modelo uma vez por caso e pode gerar cobrança. Esse comando mede a concordância com os rótulos do treinador. Ele não atualiza os pesos do modelo nem altera as fichas do aplicativo.

## Agenda semanal do piloto conectado

Na ficha liberada do aluno, o treinador escolhe **Data do treino** e toca em **Agendar treino**. O mesmo agendamento pode ser retirado na **Agenda semanal**. A agenda usa a semana de segunda a domingo no horário de Brasília (UTC−3). O aluno vê as próprias datas e pode abrir a ficha. O treinador também vê as conversas cuja última mensagem veio do aluno.

O painel conta as sessões concluídas pela data em que foram iniciadas e só recebe o registro depois da sincronização. Assim, um treino que voltar da academia sem sinal pode aparecer mais tarde na semana original. Uma ficha agendada aparece como concluída quando há uma sessão concluída daquela ficha iniciada naquela data.
