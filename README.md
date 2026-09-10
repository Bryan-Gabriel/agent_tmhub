<div align="center">
  <img src="https://raw.githubusercontent.com/foxtec198/TMHub/main/public/brands/main_brand.svg" alt="TM Hub" width="260">

  # TM Hub · Agent

  Agente local de automação do ecossistema TM Hub. Executa comandos recebidos
  pela API, integra sistemas externos e informa o andamento de cada tarefa em tempo real.

  [![Python](https://img.shields.io/badge/Python-3.11+-3776AB?logo=python&logoColor=white)](https://www.python.org/)
  [![Socket.IO](https://img.shields.io/badge/Socket.IO-Tempo%20real-010101?logo=socketdotio&logoColor=white)](https://socket.io/)
  [![Playwright](https://img.shields.io/badge/Playwright-Automação%20web-2EAD33?logo=playwright&logoColor=white)](https://playwright.dev/python/)
  [![Windows](https://img.shields.io/badge/Windows-Automação%20legada-0078D4?logo=windows&logoColor=white)](https://www.microsoft.com/windows)

  [Frontend](https://github.com/foxtec198/TMHub) ·
  [API](https://github.com/foxtec198/TMHub_Api)
</div>

---

## Visão geral

O TM Hub Agent é executado na máquina que possui acesso aos sistemas externos.
Ele se conecta à API pelo Socket.IO, registra suas capacidades e aguarda
comandos. Quando uma automação é solicitada, o agente executa o fluxo local e
devolve eventos de progresso, conclusão ou falha para o TM Hub.

Atualmente, o projeto concentra dois módulos independentes:

| Módulo | Finalidade |
| --- | --- |
| **Ponto Mais** | Acessa o Ponto Mais, gera o relatório Auditoria/Jornadas, baixa o XLSX e o envia para importação na API. |
| **HK** | Mantém o fluxo legado de ajustes no SAR2G/HK por automação de desktop. |

O módulo HK é legado e usa imagem, foco de janela e coordenadas. O Ponto Mais
usa Playwright e seletores da página web. Os dois fluxos são mantidos
separados para que uma evolução não altere o comportamento do outro.

## Arquitetura

```text
TM Hub (frontend)
        │ solicita automação e acompanha o andamento
        ▼
TM Hub API + Socket.IO
        │ evento "command"
        ▼
TM Hub Agent
   ├── registra agente, categoria e capacidades
   ├── executa Ponto Mais com Playwright
   ├── executa HK com PyAutoGUI quando solicitado
   └── envia command_progress e command_done
        │
        ▼
Sistemas externos e API de importação
```

## Recursos atuais

- Conexão persistente com a API por Socket.IO.
- Identificação do agente pela interface de rede da máquina.
- Registro das capacidades disponíveis ao conectar.
- Execução assíncrona para não interromper o recebimento de comandos.
- Progresso por etapa para automações do Ponto Mais.
- Download validado de relatório XLSX e envio autenticado à API.
- Navegador Playwright em modo headless por padrão, com opção de diagnóstico visível.
- Automação HK preservada em módulo legado isolado.
- Conversor local de relatórios de faltas do HK para JSON.

## Execução local

### Pré-requisitos

Para executar todos os módulos, use Windows com:

- Python 3.11 ou superior.
- Acesso à API do TM Hub.
- Conta válida no Ponto Mais, quando utilizar a importação de Jornadas.
- Google Chromium instalado pelo Playwright.
- Microsoft Excel e `pywin32` apenas para o conversor legado de relatórios HK.
- HK/SAR2G e FortiClient instalados apenas quando utilizar as automações legadas.

```powershell
git clone https://github.com/foxtec198/agent_tmhub.git
cd agent_tmhub

python -m venv venv
.\venv\Scripts\Activate.ps1

python -m pip install --upgrade pip
python -m pip install -r requirements.txt
python -m playwright install chromium

Copy-Item .env.example .env
python configure_pontomais.py
python main.py
```

O comando `configure_pontomais.py` solicita login e senha no terminal e grava
somente as chaves do Ponto Mais no arquivo local `.env`.

Para interromper o agente, use `Ctrl+C` no terminal.

## Configuração

O arquivo `.env` é local e está ignorado pelo Git. Nunca use valores reais em
`.env.example`, código-fonte, logs ou commits.

### Variáveis do agente

| Variável | Uso | Obrigatória para |
| --- | --- | --- |
| `API_URL` | URL base da API que expõe o Socket.IO e recebe a importação. | Todas as automações |
| `PONTOMAIS_LOGIN` | Login ou CPF da conta Ponto Mais. | Ponto Mais |
| `PONTOMAIS_PASSWORD` | Senha da conta Ponto Mais. | Ponto Mais |
| `PONTOMAIS_HEADLESS` | `true` para navegador invisível; `false` para diagnóstico visual. | Ponto Mais |
| `UID` | Usuário usado pelos fluxos legados de VPN e HK. | HK |
| `VPN_PWD` | Senha usada no fluxo legado de VPN. | HK/VPN |
| `HK_PWD` | Senha usada pelo HK/SAR2G. | HK |
| `VPN_SHORTCUT` | Caminho do executável ou atalho do FortiClient. | HK/VPN |
| `HK_SHORTCUT` | Caminho do executável do HK/SAR2G. | HK |

Exemplo de configuração sem dados reais:

```env
API_URL=https://api.exemplo.com.br

PONTOMAIS_LOGIN=
PONTOMAIS_PASSWORD=
PONTOMAIS_HEADLESS=true

UID=
VPN_PWD=
HK_PWD=
VPN_SHORTCUT=C:\Caminho\Para\FortiClient.exe
HK_SHORTCUT=C:\Caminho\Para\SarClient.exe
```

A credencial de importação do TM Hub não é configurada no `.env`: ela é
recebida no comando emitido pela API e usada somente durante a importação.

## Comunicação com a API

Ao conectar, o agente emite `register` com seu identificador, categoria e
capacidades:

```json
{
  "agent_id": "identificador-da-maquina",
  "category": "Ponto Mais",
  "capabilities": [
    "HK_adjust",
    "pontomais_report_import"
  ]
}
```

A API envia automações pelo evento `command`. O agente encaminha o comando
para o handler correspondente:

| Tipo de comando | Handler | Comportamento |
| --- | --- | --- |
| `HK_adjust` | `_handle_hk_adjust` | Executa ajustes no fluxo legado do HK. |
| `pontomais_report_import` | `_handle_pontomais_report` | Gera e importa o relatório Jornadas do Ponto Mais. |

Durante a execução do Ponto Mais, o agente emite `command_progress`. Ao
final, emite `command_done` com um dos status abaixo:

| Status | Significado |
| --- | --- |
| `completed` | A automação e a importação terminaram com sucesso. |
| `failed` | O fluxo foi interrompido; a mensagem informa a etapa ou causa resumida. |

## Automação Ponto Mais

O módulo está em [models/pontomais.py](./models/pontomais.py). O fluxo atual:

1. Abre a página de login do Ponto Mais.
2. Preenche credenciais do arquivo local `.env`.
3. Confirma que a aplicação saiu da tela de login.
4. Acessa Relatórios.
5. Seleciona o tipo **Auditoria**.
6. Define a data de referência.
7. Seleciona o modelo **Jornadas**.
8. Baixa o arquivo XLS.
9. Valida a existência e o tamanho do arquivo.
10. Envia o arquivo para `/jornadas/importar` na API.
11. Atualiza o progresso até 100% e informa o resultado.

A automação usa Playwright com timeouts por etapa e sempre fecha contexto e
navegador no bloco `finally`.

### Diagnóstico visual

O navegador é invisível por padrão:

```env
PONTOMAIS_HEADLESS=true
```

Para acompanhar a automação durante uma investigação:

```env
PONTOMAIS_HEADLESS=false
```

Após a validação, volte para `true` para evitar interferência na operação da
máquina.

### Playwright

Se a execução informar que não encontrou o Chromium, execute novamente:

```powershell
.\venv\Scripts\python.exe -m playwright install chromium
```

## Automação HK

O módulo está em [models/models.py](./models/models.py) e é preservado como
fluxo legado. Ele depende de aplicativos instalados, foco da janela e imagens
em [assets](./assets).

Antes de executar um comando `HK_adjust`, confirme:

- HK/SAR2G está instalado no caminho configurado.
- A sessão do Windows está desbloqueada.
- A resolução e a escala da tela são compatíveis com as imagens do módulo.
- O usuário possui acesso ao HK.
- Nenhuma janela inesperada está sobrepondo o aplicativo.

Não misture a lógica do HK com a automação do Ponto Mais. Novas automações web
devem ter módulo próprio e seletores Playwright estáveis.

## Conversor de relatórios HK

O script [conv.py](./conv.py) lê um arquivo Excel de faltas e gera o JSON
consumido pela automação legada.

Instale a dependência adicional:

```powershell
python -m pip install pywin32
```

Uso:

```powershell
python conv.py --file "C:\Relatorios\faltas.xlsx"
```

Para definir a saída:

```powershell
python conv.py --file "C:\Relatorios\faltas.xlsx" --output "C:\Relatorios\faltas.json"
```

O arquivo de origem não é alterado.

## Estrutura do projeto

```text
agent_tmhub/
├── assets/                   imagens usadas pelo fluxo legado do HK
├── models/
│   ├── models.py             automações legadas de HK e VPN
│   └── pontomais.py          automação web e importação do Ponto Mais
├── main.py                   conexão Socket.IO e encaminhamento de comandos
├── configure_pontomais.py    configuração local das credenciais Ponto Mais
├── conv.py                   conversor de relatórios HK para JSON
├── requirements.txt          dependências Python
└── .env.example              referência de variáveis locais
```

## Desenvolvimento

Ao adicionar uma automação:

1. Crie um módulo específico para o sistema externo.
2. Defina um tipo de comando e um handler em `COMMAND_HANDLERS`.
3. Emita progresso somente em marcos reais do fluxo.
4. Valide o resultado final, não apenas o clique ou o download.
5. Feche browser, contexto ou recursos locais em `finally`.
6. Não registre senhas, tokens, CPFs ou arquivos sensíveis nos logs.
7. Mantenha os módulos legados isolados.
8. Atualize esta documentação com a nova capacidade e suas variáveis.

Antes de publicar alterações, valide ao menos:

```powershell
python -m py_compile main.py models\pontomais.py
git diff --check
```

Para alterações no Ponto Mais, também valide conexão, autenticação, seleção de
Auditoria/Jornadas, download e retorno da importação em ambiente autorizado.

## Projetos relacionados

- Interface web: [TMHub](https://github.com/foxtec198/TMHub)
- API e regras de negócio: [TMHub_Api](https://github.com/foxtec198/TMHub_Api)

## Licença e uso

Projeto proprietário de uso interno. Distribuição, cópia ou modificação externa
dependem de autorização.