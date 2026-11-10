# Registro de treinos — Treino_v6.py

Programa de terminal para registrar o que o aluno realizou. Não prescreve treinos, não avalia condições de saúde e não decide progressão de carga.

## Executar

Requer Python 3.10 ou superior. Não precisa instalar bibliotecas adicionais.

```powershell
python .\Treino_v6.py
```

Pode ser chamado por caminho absoluto a partir de outra pasta. O histórico é sempre o `historico_treinos.json` ao lado do script. Se você tem duas cópias do projeto, elas têm históricos separados. O programa mostra o caminho utilizado no início.

1. Informe o aluno e a quantidade de exercícios.
2. Para cada exercício, informe nome e quantidade de séries.
3. Escolha se todas as séries têm a mesma carga e repetições. Se não, informe cada uma separadamente.
4. Confira o total e confirme o salvamento com `s`.

Nomes vazios ou só com espaços são recusados. O programa não verifica se o nome pertence a um catálogo: `abc` ainda é texto válido. O nome do aluno é uma etiqueta, não uma conta autenticada nem uma identificação única de pessoa.

Cargas aceitam vírgula ou ponto decimal, com até três casas, sem separadores de milhar. Séries, repetições e quantidade de exercícios exigem inteiros positivos. Letras, números negativos, notação científica, NaN e infinito são rejeitados. Os limites de 100 exercícios, 100 séries, 10.000 repetições e 10.000 kg são limites técnicos para conter erros de entrada, não recomendações de treinamento. Ajuste as constantes se um caso legítimo exigir outros limites.

Carga zero significa ausência de carga externa. Um exercício com peso corporal pode ter volume externo zero e ainda exigir esforço elevado. A métrica carga × repetições não mede trabalho mecânico, intensidade relativa ou qualidade do estímulo; não compare exercícios distintos apenas pelo total. Defina uma convenção consistente para halteres, máquinas e exercícios unilaterais.

## O que foi corrigido

- Todas as perguntas e o armazenamento do exercício permanecem dentro da repetição correta.
- O registro tem nome do aluno, identificador UUID da sessão e instante de registro com o fuso configurado no computador.
- A quantidade de exercícios deixou de ser fixa em três.
- O cálculo utiliza Decimal antes da conversão para números JSON.
- Cada exercício guarda `series_detalhes`, `series` e `volume_total`. Quando todas as séries são iguais, guarda também os campos resumidos `peso_kg` e `repeticoes`. Para séries diferentes, consulte `series_detalhes`.
- Sessões anteriores são lidas e preservadas antes de acrescentar a nova.
- A gravação usa temporário na mesma pasta, flush/fsync e substituição do destino. Uma falha antes da substituição não trunca o arquivo original.
- Antes de atualizar um histórico existente válido, uma cópia exata da versão anterior é gravada em `historico_treinos.json.bak`.
- Um lock do sistema operacional protege leitura, backup e escrita contra outras instâncias deste programa. O lock é liberado ao encerrar o processo. O arquivo `.lock` fica no disco de propósito; não o apague enquanto houver programas abertos.
- Repetir o salvamento da mesma sessão não a duplica. Falha de gravação permite tentar novamente com os dados ainda em memória.
- Histórico vazio, JSON inválido, chaves duplicadas, números não finitos ou estrutura incompatível geram erro sem substituir o original.
- Importar o módulo para testes não pede entradas nem salva dados.

## Históricos existentes

O formato usado durante a aula (`[{"aluno": "...", "exercicios": [...]}]`) é aceito e preservado. Os dados antigos não ganham datas inventadas e nomes antigos vazios não são alterados silenciosamente. A validação do histórico legado é estrutural; não confirma a exatidão de cada registro antigo.

O `banco_de_dados.json` da primeira versão NÃO é alterado nem importado automaticamente: ele não contém aluno e data suficientes para atribuir corretamente a sessão. A migração precisa ser feita separadamente, com identificação explícita dos dados desconhecidos.

Se um arquivo estiver corrompido, o programa não o troca por uma lista vazia. Feche as instâncias do programa, preserve uma cópia do arquivo com problema e confira a cópia `.bak` antes de qualquer recuperação. O backup contém apenas a versão imediatamente anterior, não todas as versões. Não use os dados de testes como registros reais de alunos.

## Testar

Na pasta do projeto:

```powershell
python -m unittest discover -s tests -v
```

Os testes usam pastas temporárias e não modificam o histórico real. Cobrem conversões, cálculo, nomes vazios, séries diferentes, compatibilidade, corrupção, falhas de disco e substituição, concorrência, liberação de lock após término de processo, cancelamento e execução completa em uma cópia isolada.

Validação local executada em Linux. O código possui caminho específico de lock para Windows (`msvcrt`), mas essa plataforma precisa ser testada no ambiente de destino.

## Limites desta versão

É um aplicativo local de terminal, não uma API ou serviço para múltiplos usuários. O lock protege instâncias cooperantes no mesmo computador; não garante segurança em pastas de rede, editores externos ou sincronização por nuvem. O arquivo tem limite de 20 MiB: para crescer, migrar para um banco transacional.

Backup local e gravação por substituição não garantem recuperação em toda queda de energia, falha física de disco ou exclusão manual. Ctrl+C antes de salvar descarta o que foi digitado; durante a gravação, confira o histórico, pois a substituição pode já ter ocorrido. Não há recuperação automática de sessão ainda não salva após desligamento.

Os arquivos de histórico são texto simples, sem criptografia ou controle de acesso. Não são adequados, por si só, para hospedar dados reais de clientes em um serviço público. A regra `.gitignore` evita incluir novos históricos, backups e temporários acidentalmente no Git; arquivos que já estavam versionados continuam versionados.

## Para estudar o código

1. `validar_texto`, `converter_inteiro`, `converter_peso`: regras de entrada.
2. `perguntar`: repetição e tratamento de erros.
3. `calcular_volume`: função de cálculo independente do terminal.
4. `coletar_exercicio`, `coletar_sessao`: listas e dicionários.
5. `ler_historico`, `salvar_sessao`: persistência e compatibilidade.
6. `bloquear_historico`, `escrever_atomicamente`: proteção de gravação.
7. `main` e `if __name__ == "__main__"`: início do programa e cancelamento.
