/* Replay of the saved archive on ONE shared clock (wall, map and counters).
   Pure helpers live on window.BarralReplay so they can be tested without the UI.
   Read-only: uses GET /api/ads only. No paid calls, no writes. Order = oldest start date first. */
(function () {
  var DURATION = 20;       // seconds for the whole timeline at 1x
  var SCRUB_STEPS = 1000;  // resolution of the range input
  var loopActive = false;

  function clamp(n, a, b) { return Math.max(a, Math.min(b, n)); }

  // completed = how many creatives are revealed; phase = progress through the current one
  function frame(total, elapsed, duration) {
    duration = duration || DURATION;
    if (!Number.isFinite(total) || total <= 0) return { duration: duration, completed: 0, active: null, phase: 1 };
    var position = clamp(elapsed, 0, duration) / duration * total;
    var completed = Math.min(total, Math.floor(position + 1e-9));
    return { duration: duration, completed: completed, active: completed < total ? completed : null, phase: completed < total ? position - completed : 1 };
  }
  function advance(elapsed, dtMs, speed, duration) {
    duration = duration || DURATION;
    return Math.min(duration, elapsed + Math.max(0, dtMs) / 1000 * (speed || 1));
  }
  // oldest first; same date -> by id; unknown dates last (by id)
  function order(items) {
    return items.slice().sort(function (a, b) {
      var au = !a.start, bu = !b.start;
      if (au !== bu) return au ? 1 : -1;
      if (!au && a.start !== b.start) return a.start < b.start ? -1 : 1;
      return String(a.id) < String(b.id) ? -1 : String(a.id) > String(b.id) ? 1 : 0;
    });
  }

  // The map projection puts creatives with near-identical copy on the exact same coordinate.
  // Display only: spread them on a golden-angle spiral around that spot (first one stays in the center).
  var SPREAD_STEP = 2.4;   // percent of the map per sqrt(rank); dot is ~3% wide, so neighbours never touch
  function spread(items) {
    var groups = {};
    items.forEach(function (it) { var k = it.px.toFixed(3) + ',' + it.py.toFixed(3); (groups[k] = groups[k] || []).push(it); });
    var out = [];
    items.forEach(function (it) {
      var g = groups[it.px.toFixed(3) + ',' + it.py.toFixed(3)], k = g.indexOf(it);
      var r = g.length > 1 ? SPREAD_STEP * Math.sqrt(k) : 0, a = k * 2.399963229728653;
      out.push(Object.assign({}, it, { sx: clamp(it.px + r * Math.cos(a), 2, 98), sy: clamp(it.py + r * Math.sin(a), 2, 98) }));
    });
    return out;
  }

  window.BarralReplay = { DURATION: DURATION, frame: frame, advance: advance, order: order, spread: spread, running: function () { return loopActive; } };

  function typing(target) {
    return target && target.closest && target.closest('input,select,textarea,button,a,[contenteditable]');
  }

  document.addEventListener('alpine:init', function () {
    Alpine.data('replayStage', function () {
      var raf = 0, last = 0, elapsed = 0, onKey = null;
      return {
        items: [], loading: true, failed: '', playing: false, speed: 1, completed: 0, scrub: 0, clock: '0,0',
        revealedAds: 0, revealed60: 0, duration: DURATION, scrubMax: SCRUB_STEPS,

        async load(pageId, points) {
          try {
            var ads = [], offset = 0, more = true;
            while (more) {
              var url = '/api/ads?' + new URLSearchParams({ page_id: pageId || '', offset: offset, limit: 500 });
              var r = await fetch(url, { cache: 'no-store' });
              if (!r.ok) throw new Error('Falha ao carregar anúncios (' + r.status + ').');
              var data = await r.json();
              ads = ads.concat(data.ads || []); offset = ads.length; more = !!data.has_more && (data.ads || []).length > 0;
            }
            var byFp = {};
            ads.forEach(function (a) { (byFp[a.fingerprint] = byFp[a.fingerprint] || []).push(a); });
            var built = [];
            (points || []).forEach(function (p) {
              var group = byFp[p.fingerprint]; if (!group || !group.length) return;
              var dated = group.filter(function (a) { return a.start_date; }).sort(function (a, b) { return a.start_date < b.start_date ? -1 : 1; });
              var rep = dated[0] || group[0];
              var days = group.map(function (a) { return a.days_active; }).filter(function (d) { return d !== null && d !== undefined; });
              built.push({ id: rep.ad_id, start: rep.start_date || null, days: days.length ? Math.max.apply(null, days) : null,
                           px: p.px, py: p.py, cluster: p.cluster, adCount: p.ad_count || group.length, thumb: rep.thumbnail_src || null });
            });
            this.items = spread(order(built));
            this.loading = false;
            this.bindKeys();
            if (!this.items.length) return;
            var reduce = window.matchMedia('(prefers-reduced-motion: reduce)').matches;
            if (reduce) { elapsed = DURATION; this.sync(); }   // calm by default: finished, user steps with the slider
            else { this.sync(); this.play(); }
          } catch (e) { this.loading = false; this.failed = e.message; }
        },

        sync() {
          var f = frame(this.items.length, elapsed, DURATION);
          this.completed = f.completed;
          this.scrub = Math.round(elapsed / DURATION * SCRUB_STEPS);
          this.clock = elapsed.toFixed(1).replace('.', ',');
          var ads = 0, long = 0;
          for (var i = 0; i < f.completed; i++) { ads += this.items[i].adCount; if (this.items[i].days !== null && this.items[i].days >= 60) long++; }
          this.revealedAds = ads; this.revealed60 = long;
        },

        tick(ts) {
          if (!this.$root || !this.$root.isConnected) { this.halt(); return; }
          if (!last) last = ts;
          elapsed = advance(elapsed, ts - last, this.speed, DURATION); last = ts;
          this.sync();
          if (elapsed >= DURATION) { this.pause(); return; }
          raf = requestAnimationFrame(this.tick.bind(this));
        },
        play() {
          if (!this.items.length) return;
          if (elapsed >= DURATION) elapsed = 0;
          this.playing = true; last = 0; loopActive = true;
          cancelAnimationFrame(raf); raf = requestAnimationFrame(this.tick.bind(this));
        },
        pause() { this.playing = false; this.halt(); },
        halt() { cancelAnimationFrame(raf); raf = 0; last = 0; loopActive = false; this.playing = false; },
        toggle() { this.playing ? this.pause() : this.play(); },
        restart() { elapsed = 0; this.sync(); this.play(); },
        seek(value) { elapsed = clamp(Number(value) / SCRUB_STEPS, 0, 1) * DURATION; last = 0; this.sync(); if (elapsed >= DURATION && this.playing) this.pause(); },

        bindKeys() {
          var self = this;
          onKey = function (e) {
            if (e.ctrlKey || e.metaKey || e.altKey || typing(e.target)) return;
            if (e.code === 'Space') { e.preventDefault(); self.toggle(); }
            else if (e.key === 'r' || e.key === 'R') { self.restart(); }
          };
          document.addEventListener('keydown', onKey);
        },
        destroy() { this.halt(); if (onKey) document.removeEventListener('keydown', onKey); }
      };
    });
  });
})();
