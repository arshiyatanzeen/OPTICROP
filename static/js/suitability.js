/* Suitability page */

(function () {
  'use strict';
  const SAMPLE = { N: 90, P: 42, K: 43, temperature: 24, humidity: 82, ph: 6.5, rainfall: 210 };
  const form = document.getElementById('suitForm');
  const emptyEl = document.getElementById('suitEmpty');
  const bodyEl  = document.getElementById('suitBody');

  document.getElementById('sampleBtn').addEventListener('click', () => {
    for (const k in SAMPLE) {
      const input = form.querySelector('[name="' + k + '"]');
      if (input) input.value = SAMPLE[k];
    }
    if (!form.crop.value) form.crop.value = 'rice';
  });

  form.addEventListener('submit', async (e) => {
    e.preventDefault();
    const btn = form.querySelector('button[type=submit]');
    const original = btn.innerHTML;
    btn.disabled = true;
    btn.innerHTML = '<span class="spinner"></span> Scoring…';
    try {
      const payload = Object.fromEntries(new FormData(form).entries());
      const data = await window.OptiFetch('/api/suitability', {
        method: 'POST', body: JSON.stringify(payload),
      });
      render(data.report);
    } catch (_) { /* toast shown */ }
    finally { btn.disabled = false; btn.innerHTML = original;
             if (window.lucide) window.lucide.createIcons(); }
  });

  function render(r) {
    const m = r.meta || {};
    const bg = m.color ? ('linear-gradient(135deg,' + m.color + ',#0f3d2e)') : '';
    const html = `
      <div class="result">
        <div class="result__thumb" style="${bg ? 'background:' + bg : ''}">${m.emoji || '🌱'}</div>
        <div>
          <div class="result__title">
            <h4>${r.crop}</h4>
            <span class="status-badge status-${r.overall_status}">${r.overall_status}</span>
            <span class="result__confidence">${r.overall_score.toFixed(1)} / 100</span>
          </div>
          <div class="result__desc">${m.description || ''}</div>
        </div>
      </div>
      <div style="margin-top:14px">
        ${r.parameters.map(p => `
          <div class="progress">
            <div class="progress__head">
              <div class="progress__label">${p.label}
                <span class="status-badge status-${p.status}" style="margin-left:6px">${p.status}</span>
              </div>
              <div class="progress__value">${p.value} ${p.unit} · ideal ${p.ideal_low}–${p.ideal_high}</div>
            </div>
            <div class="progress__bar"><div class="progress__fill" style="width:${p.score}%"></div></div>
            <div class="progress__hint">${p.suggestion}</div>
          </div>`).join('')}
      </div>
    `;
    bodyEl.innerHTML = html;
    bodyEl.hidden = false;
    emptyEl.hidden = true;
    if (window.lucide) window.lucide.createIcons();
  }
})();
