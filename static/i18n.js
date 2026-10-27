/* Brazilian Portuguese display layer. The API keeps stable machine codes (e.g. incomplete_scroll_cap);
   this file only decides how they are SHOWN. Numbers, dates and money follow pt-BR. */
(function () {
  var STATUS = {
    complete: 'completa', complete_zero_ads: 'completa, sem anúncios ativos', partial: 'parcial', failed: 'falhou',
    incomplete: 'incompleta', incomplete_collecting: 'incompleta: coletando', incomplete_scroll_cap: 'incompleta: limite de rolagem',
    incomplete_stalled: 'incompleta: coleta parada', incomplete_timed_out: 'incompleta: tempo esgotado',
    incomplete_challenge: 'incompleta: verificação da Meta', incomplete_parse_errors: 'incompleta: erros de leitura',
    page_selection_required: 'seleção da página necessária', not_collected: 'não capturada', not_analyzed: 'não analisada',
    skipped_empty: 'ignorada (vazia)', queued: 'na fila', running: 'em execução'
  };
  var JOB = { queued: 'na fila', running: 'em execução', complete: 'concluída', failed: 'falhou', partial: 'parcial', incomplete: 'incompleta' };
  var STAGE = { queued: 'na fila', collect: 'captura', analyze: 'classificação' };
  var AVAILABILITY = { available: 'disponível', unavailable: 'indisponível', checking: 'verificando' };
  var VISUAL = { still_only: 'somente imagem estática' };
  var FORMAT_FALLBACK = {
    'Talking head': 'Pessoa falando', Graphic: 'Gráfico ou texto', Mixed: 'Formato misto', UGC: 'Conteúdo de usuário (UGC)', 'B-roll': 'Cenas de apoio (B-roll)',
    Frustration: 'Frustração', Curiosity: 'Curiosidade', Direct: 'Direto', 'Proof / numbers': 'Prova ou números', Comparison: 'Comparação',
    'Free resource': 'Recurso gratuito', Workshop: 'Workshop', 'Low-ticket': 'Oferta de baixo valor', 'High-ticket': 'Oferta de alto valor', 'Direct sale': 'Venda direta'
  };

  function humanize(code) { return String(code).replace(/_/g, ' '); }
  function pick(map, code, fallback) { return map[code] || (code === null || code === undefined || code === '' ? fallback : humanize(code)); }
  function number(value, digits) {
    var n = Number(value);
    if (value === null || value === undefined || value === '' || !Number.isFinite(n)) return 'desconhecido';
    return n.toLocaleString('pt-BR', digits === undefined ? { maximumFractionDigits: 2 } : { minimumFractionDigits: digits, maximumFractionDigits: digits });
  }
  // decimal strings from the API (Decimal) keep their precision: only the separator changes
  function usd(value) {
    if (value === null || value === undefined || value === '') return 'US$ 0';
    return 'US$ ' + String(value).replace('.', ',');
  }
  function date(value) {
    var m = /^(\d{4})-(\d{2})-(\d{2})/.exec(value || '');
    return m ? m[3] + '/' + m[2] + '/' + m[1] : 'desconhecida';
  }

  window.BarralI18n = {
    status: function (c) { return pick(STATUS, c, 'desconhecido'); },
    job: function (c) { return pick(JOB, c, 'desconhecido'); },
    stage: function (c) { return pick(STAGE, c, 'desconhecida'); },
    availability: function (c) { return pick(AVAILABILITY, c, 'desconhecido'); },
    visual: function (c) { return pick(VISUAL, c, 'não analisada'); },
    fallbackLabel: function (v) { return FORMAT_FALLBACK[v] || v; },
    number: number, usd: usd, date: date,
    percent: function (v) { return v === null || v === undefined ? 'desconhecido' : number(v * 100, 1) + '%'; }
  };
})();
