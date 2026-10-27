# Jev Ad Pattern Lab

Ferramenta local para estudar os anúncios ativos de um anunciante na Biblioteca de Anúncios da Meta. Ela captura os anúncios públicos, classifica cada criativo com o modelo Jev (TypeSafe) e mostra, em um painel no navegador, quais padrões aparecem entre os anúncios que ficam mais tempo no ar.

Tudo roda na sua máquina. O painel abre em `http://127.0.0.1:5194`, em português do Brasil, e nunca vem com anúncios de exemplo.

## O que ela faz

1. **Captura** os anúncios ativos de uma página da Meta, informando o ID da página. Guarda texto, datas, miniatura estática e agrupa criativos idênticos.
2. **Classifica** cada criativo com o Jev em sete dimensões: formato, gancho, ângulo, oferta, prova, objeção e chamada para ação. A leitura do texto que aparece na imagem (OCR) é feita localmente.
3. **Calcula** quais grupos concentram mais anúncios ativos há 60 dias ou mais e sugere hipóteses de teste.
4. **Mostra** tudo no painel, com filtros, mapa de similaridade entre textos, inspetor de cada anúncio e uma reprodução animada do arquivo.

## Leia antes de usar

- **60 dias ou mais no ar é um indicador de longevidade, não prova de resultado.** Ele não informa gasto, lucro, conversão nem eficácia.
- **A classificação com o Jev é paga.** O teto é de US$ 0,4999 por execução e só roda com sua autorização explícita. O custo exibido é uma estimativa feita a partir do uso informado pela API, não a fatura do provedor.
- **A captura depende da Meta.** Se a Meta mudar o formato da página, pedir verificação ou bloquear o navegador automatizado, a captura fica marcada como incompleta. Não há tentativa de contornar bloqueios.
- Anúncios de terceiros continuam sendo propriedade de seus donos. A pasta `data/`, que guarda o que você coleta, não é versionada.

## Requisitos

- Python 3.14 (testado no Windows; outros sistemas não foram verificados)
- Chromium instalado pelo Playwright, para a captura
- Chave de API da TypeSafe, para a classificação
- Tesseract OCR, opcional. Sem ele, o texto da imagem aparece como indisponível, nunca inventado.

## Instalação

Os comandos abaixo usam o Git Bash no Windows.

```bash
git clone <endereço-do-repositório>
cd jev-ad-pattern-lab

python -m venv .venv
.venv/Scripts/python.exe -m pip install -r requirements.txt
.venv/Scripts/python.exe -m playwright install chromium
```

## Configuração

Copie `.env.example` para `.env` e preencha a chave:

```bash
cp .env.example .env
```

```text
TYPESAFE_API_KEY=sua-chave
```

O arquivo `.env` está no `.gitignore`. A chave nunca é exibida no painel, em logs ou em argumentos de linha de comando. Se a variável já existir no ambiente, ela tem prioridade sobre o arquivo.

Confira o ambiente, sem custo e sem chamadas pagas:

```bash
.venv/Scripts/python.exe scripts/lab.py doctor
```

## Uso pelo painel

```bash
.venv/Scripts/python.exe scripts/lab.py serve
```

Abra `http://127.0.0.1:5194`. No topo, informe o ID da página (1 a 30 dígitos) e escolha uma ação:

| Ação | O que faz | Custo |
|---|---|---|
| Capturar | Salva os anúncios ativos públicos da página. | Nenhum |
| Classificar com Jev | Classifica só os anúncios já salvos daquela página. | Pago, exige autorização |
| Capturar + classificar | Captura e, somente se a captura for completa, classifica. | Pago, exige autorização |

Regras que o painel aplica:

- Uma execução por vez. Enquanto uma roda, os botões ficam desativados e o arquivo continua consultável.
- Se a captura terminar incompleta, a ação combinada não chama o Jev.
- Criativos que já têm classificação em cache não geram nova cobrança.
- Fechar a aba não cancela a execução. Ao reabrir, o painel retoma o acompanhamento.

### Abas

- **Parede de miniaturas:** todos os anúncios, com filtros por texto, anunciante, as sete dimensões, revisão necessária e 60 dias ou mais.
- **Mapa:** mostra quais criativos dizem a mesma coisa (explicação abaixo).
- **Padrões:** achados por dimensão, cada um com uma hipótese para testar, e a tabela de padrões com o comparador.
- **Reprodução:** a parede, o mapa e os contadores avançam juntos num relógio único, do anúncio mais antigo ao mais novo. É só visual, não faz chamadas pagas e a velocidade não representa a do Jev.

### Como ler o mapa

Cada bolinha é um criativo. Bolinhas próximas têm textos parecidos; bolinhas distantes têm textos diferentes. O número dentro da bolinha é o grupo: textos quase iguais, em geral variações da mesma mensagem. Criativos com texto idêntico ficam numa bolinha maior, marcada com o total (por exemplo, x72).

O mapa não compara a imagem do anúncio nem indica desempenho. A posição exata não tem significado, apenas quem fica perto de quem. Tecnicamente, os grupos vêm da similaridade de cosseno TF-IDF entre os textos, com limiar de 0,65, e a posição é uma projeção 2D determinística.

## Uso pela linha de comando

```bash
# Captura (use o ID exato da página)
.venv/Scripts/python.exe scripts/lab.py collect --page-id 123456789 --max-scrolls 100 --timeout 120

# Classificação com teto de custo
.venv/Scripts/python.exe scripts/lab.py analyze --page-id 123456789 --budget 0.4999

# Importar anúncios já normalizados em JSON
.venv/Scripts/python.exe scripts/lab.py import-json anuncios.json --page-id 123456789
```

Busca por nome serve apenas para descoberta: devolve `page_selection_required` com as páginas candidatas. Escolha o ID exato antes de capturar. O parâmetro global `--data-dir` vem antes do subcomando.

## Como funciona

**Captura.** O Playwright abre a Biblioteca de Anúncios com os filtros de anúncios ativos e lê o que a própria página carrega: o HTML do documento (que traz a primeira página de resultados) e as respostas GraphQL das páginas seguintes. A captura só é marcada como completa quando a paginação informa o fim. Teto de rolagem, desafio da Meta, erros de leitura, tempo esgotado ou paginação travada resultam em captura incompleta. Vídeos não são baixados; só a miniatura estática.

**Identidade do criativo.** Criativos são agrupados por texto normalizado mais o identificador da mídia ou o caminho do arquivo da imagem. Hosts e parâmetros assinados da URL são ignorados, porque mudam a cada captura.

**Classificação.** O Jev recebe a imagem e o texto por um endpoint nativo, em lotes, com perguntas de escolha única. A confiança e a distribuição completa de probabilidades são guardadas como vieram. Confiança abaixo de 0,65, falta de evidência visual ou classificação só pelo texto marcam o item para revisão. Uma miniatura não comprova a estrutura de um vídeo nem a origem de um conteúdo feito por usuário.

**Controle de custo.** Antes de cada chamada, o sistema reserva 65.536 tokens de entrada (US$ 0,002752512, a US$ 0,042 por milhão). O valor reportado pela API substitui a reserva. Timeout, erro ou ausência de uso confiável mantêm a reserva máxima e interrompem o agendamento de novas chamadas. Execuções concorrentes com o mesmo identificador não ultrapassam o teto. Uma conta grande pode não terminar dentro do teto; nesse caso o resultado parcial é salvo.

**Cache.** Os rótulos ficam guardados por criativo, modelo, versão da rubrica e modo de imagem. Repetir a execução pula o que já foi classificado.

## Segurança e privacidade

- O servidor escuta apenas em `127.0.0.1:5194`, com Host e Origin restritos ao próprio computador.
- Ações que gravam dados exigem token CSRF e, para o Jev, consentimento explícito de cobrança. As rotas de consulta são somente leitura.
- Textos de anúncio e do OCR são exibidos como texto, nunca como HTML.
- Miniaturas só são baixadas de domínios aprovados da Meta, por HTTPS, com checagem de DNS e rejeição de redirecionamentos e endereços privados.
- Nenhuma fonte, script ou estilo é carregado de servidores externos em execução.

## Testes

```bash
.venv/Scripts/python.exe -m unittest discover -s tests
```

A suíte tem 149 testes: captura, classificação, custo, segurança, interface em navegador real, tradução, padrão de design e reprodução. Os testes usam dados sintéticos e bancos temporários, nunca o painel padrão. Alguns testes de interface precisam do servidor ligado (`scripts/lab.py serve`) e são ignorados quando ele não está.

## Estrutura

```text
scripts/lab.py     Linha de comando: doctor, collect, analyze, serve, import-json
collector.py       Captura pelo Playwright e leitura do HTML e do GraphQL
labcore.py         Banco SQLite, identidade dos criativos
inference.py       Chamadas ao Jev, orçamento e cache
media.py           Miniaturas seguras e OCR local
analytics.py       Estatísticas, achados, mapa de similaridade
taxonomy.py        Dimensões, valores e rótulos em português
webapp.py          Servidor FastAPI e rotas da API
webjobs.py         Execuções em segundo plano pelo painel
settings.json      Modelo, preços e limites
static/            Painel (HTML, CSS, Alpine.js, tema, tradução, reprodução)
tests/             Suíte de testes
data/              Dados coletados (não versionado)
```

## Limitações

- Testado em Windows com Python 3.14.
- A classificação por imagem usa um recurso experimental da TypeSafe.
- Uma captura completa de hoje pode não bater com a de amanhã, pois os anúncios mudam.
- O arquivo de configurações trava endpoint e preço; alterações fora dos limites aceitos são rejeitadas.

## Créditos e licença

### Repositório original

Este projeto é uma adaptação do **ad-pattern-lab**, de Artem Novitckii.

- Repositório: https://github.com/artemnovitckii/ad-pattern-lab
- Autor: Artem Novitckii (https://novitckii.com)
- Licença: MIT
- Versão consultada: commit `456fd37b86174e8f612f48b43d52b0079914770e`, em 27/10/2026

O que foi adaptado do original:

- as sete dimensões de classificação (formato, gancho, ângulo, oferta, prova, objeção e chamada para ação), seus valores e as descrições enviadas ao Jev;
- a lógica dos achados (grupo mínimo, fatia de 60 dias ou mais contra a linha de base, comparador, facetas e exemplos) e das hipóteses de teste, traduzidas para o português;
- a ideia de dividir o texto do anúncio em abertura, corpo e chamada;
- a ideia da reprodução animada, em que parede, mapa e contadores seguem um relógio único. A implementação aqui é própria.

O original é em Node.js; o código deste repositório foi reescrito em Python. Não foram copiados o conector Apify, o provedor OpenAI Decisions, a demonstração com dados fictícios, as páginas de gravação, a transcrição de fala nem o gerador de briefs. O texto completo da licença original está em `THIRD_PARTY_NOTICES.md`.

Também fazem parte do repositório o Alpine.js (MIT) e a fonte Inter (SIL OFL 1.1), com as licenças em `static/vendor/`.

O projeto é independente da Meta e da TypeSafe.

O código deste repositório é distribuído sob a licença MIT (arquivo `LICENSE`): você pode usar, copiar, modificar e redistribuir, desde que mantenha o aviso de copyright e a licença. O software é oferecido sem garantia de qualquer tipo. Os componentes de terceiros citados acima mantêm as suas próprias licenças.

Autor: Filipe Barral, barral.pro.
