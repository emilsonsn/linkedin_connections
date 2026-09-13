# LinkedIn Connections RPA

Automação em Python com Selenium para percorrer as sugestões de conexão do LinkedIn e enviar convites. A cada tentativa, registra em uma planilha XLSX o nome, a descrição, o link do perfil e o resultado da ação.

> O uso de automações no LinkedIn pode estar sujeito aos termos e políticas da plataforma. Use por sua conta e risco, respeitando os limites aplicáveis à sua conta.

## O que o projeto faz hoje

- Abre o Chrome com um perfil persistente e conecta o Selenium por depuração remota.
- Acessa `Minha rede` e a página de sugestões de conexões.
- Localiza botões **Conectar**, envia o convite (sem nota quando o modal oferece essa opção) e confirma a mudança para **Pendente**.
- Filtra as sugestões por área de interesse, comparando palavras-chave configuráveis com a descrição/cargo do card; quem não bate é apenas pulado (não conecta, não conta no limite, não vai para a planilha).
- Extrai nome, descrição e URL do perfil a partir do card renderizado.
- Aplica pausas aleatórias entre convites e uma pausa maior ao fim de cada lote.
- Rola a lista em busca de novas sugestões; depois de 12 rolagens sem resultado, pode reiniciar o Chrome, reabrir as sugestões e continuar do ponto em que estava.
- Salva uma linha na planilha para cada tentativa, inclusive no modo de simulação.
- Gera logs no terminal e em um arquivo por execução.

O limite padrão é de 10 convites por execução. Ele é um limite da execução, não uma contagem do total diário já enviado pela conta.

## Requisitos

- Python 3.
- Google Chrome instalado em `/usr/bin/google-chrome`, ou o caminho configurado em `CHROME_BINARY`.
- Uma sessão autenticada do LinkedIn no perfil do Chrome configurado.

As dependências Python estão em `requirements.txt`: Selenium, Beautiful Soup, OpenPyXL e python-dotenv. O Selenium resolve/usa um ChromeDriver compatível ao iniciar o navegador.

## Instalação e execução

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
python main.py
```

Edite `.env` antes da primeira execução para revisar os limites, pausas e caminhos. O arquivo contém configurações locais e não é versionado.

## Autenticação do LinkedIn

O bot executa o Chrome em modo **headless**; portanto, não é possível concluir o login interativamente durante `python main.py`. Antes de executar o bot pela primeira vez, abra o mesmo perfil do Chrome em uma janela normal, faça login e feche o Chrome:

```bash
google-chrome --user-data-dir="$HOME/.linkedin-selenium" https://www.linkedin.com/
```

Se `CHROME_USER_DATA_DIR` tiver outro valor no `.env`, use esse mesmo diretório no comando. A sessão fica armazenada fora do repositório por padrão, em `~/.linkedin-selenium`.

## Configuração

As variáveis em `.env` podem ser sobrescritas no ambiente:

```bash
DAILY_CONNECTION_LIMIT=3 DRY_RUN=true python main.py
```

| Variável | Padrão | Efeito |
| --- | ---: | --- |
| `DAILY_CONNECTION_LIMIT` | `10` | Máximo de convites confirmados (ou perfis simulados) na execução. |
| `WAIT_SECONDS` | `15` | Tempo máximo de espera por elementos e carregamento. |
| `SCROLL_PAUSE_SECONDS` | `1.0` | Pausa após rolar em busca de sugestões. |
| `MIN_INVITATION_PAUSE_SECONDS` / `MAX_INVITATION_PAUSE_SECONDS` | `3.0` / `8.0` | Intervalo aleatório entre convites. |
| `BATCH_SIZE` | `10` | Quantidade de convites antes da pausa de lote. |
| `MIN_BATCH_PAUSE_SECONDS` / `MAX_BATCH_PAUSE_SECONDS` | `30.0` / `60.0` | Intervalo aleatório da pausa de lote. |
| `MAX_BROWSER_RESTARTS_WITHOUT_SUGGESTIONS` | `1` | Reinícios permitidos após esgotar as sugestões. |
| `TARGET_KEYWORDS` | recrutadores (`recruiter`, `talent acquisition`, `sourcer`, `rh`...) + Python/back-end, React/front-end e DevOps (ver `.env.example`) | Lista separada por vírgula comparada (sem acento/caixa) com a descrição/cargo do card. Só conecta com quem bate em pelo menos uma palavra-chave. Vazio desativa o filtro. |
| `CHROME_BINARY` | `/usr/bin/google-chrome` | Executável do Chrome. |
| `CHROME_USER_DATA_DIR` | `~/.linkedin-selenium` | Diretório do perfil persistente. |
| `CHROME_DEBUGGER_ADDRESS` | `127.0.0.1:9222` | Endereço usado para anexar o Selenium ao Chrome. |
| `CHROMEDRIVER_LOG_PATH` | `logs/chromedriver.log` | Arquivo de log do ChromeDriver. |
| `OUTPUT_XLSX_PATH` | `~/Documentos/linkedin_connections.xlsx` | Planilha de resultados. |
| `LOG_DIR` / `LOG_LEVEL` | `logs` / `INFO` | Destino e nível dos logs da aplicação. |
| `DRY_RUN` | `false` | Quando `true`, encontra e registra os cards, mas não clica em **Conectar**. |
| `KEEP_BROWSER_OPEN` | `true` | Quando `true`, não chama `quit()` no driver ao final. |

O Chrome é iniciado com `--headless=new`, portanto não produz uma janela visível durante a automação.

### Escolhendo a área de interesse (`TARGET_KEYWORDS`)

O bot só envia convite para quem tem, na descrição/cargo exibido no card de sugestão, pelo menos uma das palavras-chave definidas em `TARGET_KEYWORDS` (no `.env`). Quem não bate em nenhuma é apenas pulado — não conta no limite diário, não vai para a planilha.

- Formato: lista separada por vírgula, sem espaço extra necessário (`termo1,termo2,termo3`).
- A comparação ignora maiúsculas/minúsculas e acentos, e é por substring (ex.: `react` bate em "Desenvolvedora React Native").
- Padrão atual (definido em `config/constants.py` e replicado no `.env`/`.env.example`): recrutadores/RH (`recruiter`, `tech recruiter`, `talent acquisition`, `sourcer`, `headhunter`, `rh`, etc.) e as áreas técnicas Python/back-end, React/front-end e DevOps — lista completa nesses arquivos.
- Para mudar o público-alvo, edite a variável `TARGET_KEYWORDS` no seu `.env` (não precisa mexer no código). Exemplo, focando só em recrutadores e Python:
  ```bash
  TARGET_KEYWORDS=recruiter,tech recruiter,talent acquisition,python,django,back-end,backend
  ```
- Para desativar o filtro e voltar a conectar com qualquer sugestão, deixe a variável vazia: `TARGET_KEYWORDS=`.
- Teste uma lista nova sem enviar convites de verdade: `DRY_RUN=true python main.py` e acompanhe o log — perfis fora do filtro aparecem como "Fora do filtro de area".

## Saídas

A planilha é criada no caminho de `OUTPUT_XLSX_PATH`, com a aba `conexoes` e as colunas:

- `data_hora`
- `nome`
- `descricao`
- `status` (`dry_run`, `pendente_confirmado` ou `nao_confirmado`)
- `perfil_linkedin`

Os logs ficam em `LOG_DIR`, com nomes como `linkedin_connections_2026-07-11_10-30-00.log`. O log do ChromeDriver é gravado separadamente no caminho de `CHROMEDRIVER_LOG_PATH`.

## Comportamentos e limitações atuais

- O processo gerencia e encerra apenas a instância de Chrome iniciada pelo próprio bot; feche manualmente qualquer Chrome que esteja usando o mesmo `CHROME_USER_DATA_DIR` antes de rodar a automação.
- O limite de reinícios evita um ciclo infinito quando o LinkedIn não oferecer mais sugestões. A variável antiga `MAX_PAGE_REFRESHES_WITHOUT_SUGGESTIONS` continua sendo aceita temporariamente como compatibilidade.
- O Chrome é iniciado headless e usa a porta definida em `CHROME_DEBUGGER_ADDRESS`.
- Se o login expirar, a execução termina com erro solicitando uma sessão autenticada; refaça a autenticação no perfil persistente.
- Não há comando `linkedinbot`, agendador ou interface gráfica. A entrada disponível é `python main.py`; os testes unitários podem ser executados com `python -m unittest discover -v`.
- A estrutura e os textos do LinkedIn podem mudar e afetar os seletores, a extração dos dados ou a confirmação do convite.

## Execução diária automática (systemd timer)

O bot pode ser agendado para rodar todo dia sem depender de cron. Diferente do cron puro, um systemd timer com `Persistent=true` recupera a execução perdida assim que o PC é ligado (mesmo que já tenha passado do horário), mas dispara **só uma vez** para o dia mais recente — não acumula uma execução por dia que ficou desligado.

Como isso não é usado em notebook e desktop ao mesmo tempo (as duas máquinas rodam de forma independente, sem sincronizar entre si), o script `linkedin_conn.sh` guarda localmente a data da última execução (`~/.local/state/linkedin-connections/last_run_date`) e recusa rodar de novo no mesmo dia naquela máquina — evita tanto um "catch-up" duplicado do systemd quanto qualquer disparo repetido no mesmo dia.

Arquivos de unit em `systemd/` (versionados). O `linkedin-connections.service` usa o placeholder `__REPO_DIR__` no lugar do caminho do repositório, então funciona em qualquer máquina/usuário independente de onde o repositório foi clonado — a instalação abaixo substitui o placeholder pelo diretório atual:

```bash
cd /caminho/onde/voce/clonou/linkedin_connections   # rode a partir da raiz do repositorio
REPO_DIR="$(pwd)"

mkdir -p ~/.config/systemd/user
sed "s#__REPO_DIR__#$REPO_DIR#g" systemd/linkedin-connections.service > ~/.config/systemd/user/linkedin-connections.service
cp systemd/linkedin-connections.timer ~/.config/systemd/user/

systemctl --user daemon-reload
systemctl --user enable --now linkedin-connections.timer
loginctl enable-linger "$(whoami)"   # permite rodar mesmo sem sessao grafica ativa apos o boot
```

Comandos úteis:

```bash
systemctl --user list-timers linkedin-connections.timer   # proxima execucao agendada
systemctl --user status linkedin-connections.service       # status/log da ultima execucao
journalctl --user -u linkedin-connections.service -f       # acompanhar em tempo real
systemctl --user disable --now linkedin-connections.timer  # desativar o agendamento
```

O horário é definido em `systemd/linkedin-connections.timer` (`OnCalendar`, padrão `11:00`); edite e rode `systemctl --user daemon-reload` para aplicar.

## Estrutura

```text
main.py                 # Ponto de entrada e tratamento do ciclo de execução
linkedin_conn.sh         # Wrapper de execucao diaria (trava de 1x/dia por maquina)
systemd/                 # Unit files do timer/service para agendamento diario
config/
├── constants.py        # URLs, rótulos e valores padrão
└── settings.py         # Leitura de .env e variáveis de ambiente
src/
├── bot.py              # Loop de convites, limites, pausas e reinícios
├── browser.py          # Inicialização do Chrome e conexão do Selenium
├── linkedin.py         # Navegação, leitura dos cards e envio de convites
├── logging_config.py   # Logs no terminal e em arquivo por execução
├── models.py           # Modelos de pessoa e estatísticas
└── storage.py          # Persistência da planilha XLSX
```
