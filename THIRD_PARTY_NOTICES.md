# Avisos de terceiros

## ad-pattern-lab (Artem Novitckii), licença MIT

O Jev Ad Pattern Lab adapta ideias e trechos do projeto aberto https://github.com/artemnovitckii/ad-pattern-lab
(consultado em 27/10/2026, commit `456fd37b86174e8f612f48b43d52b0079914770e`):

- as **sete dimensões de classificação** (formato, gancho, ângulo, oferta, prova, objeção e chamada para ação), seus valores e as descrições em inglês enviadas ao Jev (`taxonomy.py`);
- a lógica dos **achados** (grupo mínimo, fatia de 60+ dias contra a linha de base, comparador, facetas e exemplos distintos por família) e das **hipóteses de teste**, traduzidas para o português (`analytics.py`, `taxonomy.py`);
- a ideia da **quebra do texto** em abertura, corpo e chamada (`analytics.py`).
- a ideia da **reprodução animada** do arquivo, com parede, mapa e contadores num relógio único (`static/replay.js`); a implementação é própria.

Não foram copiados: conector Apify, provedor OpenAI Decisions, modo de demonstração com dados fictícios, páginas de gravação, transcrição de fala nem o gerador de briefs. O código aqui é Python e foi reescrito; o projeto original é Node.js.

O projeto original é independente da Meta, da Apify e da TypeSafe. Anúncios de terceiros continuam sendo propriedade de seus donos.

### Texto da licença original

MIT License

Copyright (c) 2026 Artem Novitckii

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.

## Componentes incluídos no repositório

- **Alpine.js** (Caleb Porzio e colaboradores), licença MIT, em `static/vendor/alpine.min.js`. Licença em `static/vendor/ALPINE-LICENSE.txt`.
- **Inter** (The Inter Project Authors), licença SIL Open Font License 1.1, em `static/vendor/fonts/`. Licença em `static/vendor/fonts/Inter-LICENSE.txt`.
- **Avatares da marca barral.pro** em `static/brand/`, de uso próprio do autor.
