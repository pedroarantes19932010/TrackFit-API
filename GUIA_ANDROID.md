# Testar o TrackFit no Android

O APK de teste está em [downloads/TrackFit-Piloto.apk](downloads/TrackFit-Piloto.apk). Use Android 8 ou superior com WebView atualizado. O arquivo também funciona offline. No computador, baixe [TrackFit-Demo.html](downloads/TrackFit-Demo.html) e abra no navegador.

1. Abra **Conhecer a demonstração**. A página inicial mostra as fichas que Pedro pode revisar.
2. Toque em **Ver como aluno**, depois em **Preencher avaliação**. Para o exemplo fictício, use 30 anos, condicionamento, iniciante, academia, 1 dia e 40 minutos. Responda “Não” à pergunta sobre limitações e marque a autorização para o exemplo.
3. Toque em **Solicitar ficha completa**. A ficha aparece com revisão pendente e já permite iniciar o treino. O teste usa um modelo fictício de um dia. Outros perfis podem precisar de revisão.
4. Registre uma série fictícia e salve. Em **Minhas fichas**, volte para **Ver como treinador**. Abra **Avisos**, escolha a nova ficha e edite um exercício. A revisão cria uma versão nova. O histórico guarda a versão da sessão realizada.

A demonstração roda em memória. Sair ou fechar apaga os exemplos. O servidor do piloto usa SQLite para guardar treinos entre sessões. O aviso de geração aparece quando a ficha fica completa. No Android conectado, o app consulta a caixa de avisos a cada 30 segundos enquanto está aberto. O envio em segundo plano ainda está pendente.

## Rodar o piloto conectado

O PR nº 8 contém a API /v1. Este piloto traz um serviço experimental separado em server/ com avaliação, modelos completos, revisões, avisos e sessões realizadas. Ele possui banco e códigos de acesso próprios. A consolidação com as identidades e fichas da API /v1 ainda precisa ser feita antes de atender alunos reais. Use exclusivamente dados fictícios no teste.

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

Execute python -m unittest discover -s tests -v na raiz após instalar as dependências. O APK foi compilado com SDK 35, assinado com chave de teste e verificado com apksigner. A instalação em aparelho físico, o envio com app fechado, o servidor público e a publicação na Play Store ainda estão pendentes.
