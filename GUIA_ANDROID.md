# Testar o TrackFit no Android

O APK de teste está em [downloads/TrackFit-Piloto.apk](downloads/TrackFit-Piloto.apk). Use Android 8 ou superior com WebView atualizado. O arquivo também funciona offline. No computador, baixe [TrackFit-Demo.html](downloads/TrackFit-Demo.html) e abra no navegador.

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
