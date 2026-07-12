/* Smart Recommendation page */

(function () {
  'use strict';

  const SAMPLE = { N: 90, P: 42, K: 43, temperature: 24, humidity: 82, ph: 6.5, rainfall: 210 };

  const form = document.getElementById('recForm');
  const emptyEl = document.getElementById('resultEmpty');
  const bodyEl  = document.getElementById('resultBody');

  document.getElementById('sampleBtn').addEventListener('click', () => {
    for (const k in SAMPLE) {
      const input = form.querySelector('[name="' + k + '"]');
      if (input) input.value = SAMPLE[k];
    }
  });

  form.addEventListener('submit', async (e) => {
    e.preventDefault();
    const btn = form.querySelector('button[type=submit]');
    const original = btn.innerHTML;
    btn.disabled = true;
    btn.innerHTML = '<span class="spinner"></span> Analysing…';
    try {
      const payload = Object.fromEntries(new FormData(form).entries());
      const data = await window.OptiFetch('/api/predict', {
        method: 'POST', body: JSON.stringify(payload),
      });
      renderResult(data);
      window.OptiToast({
        type: 'success', title: 'Recommendation ready',
        message: data.prediction.crop + ' · ' + data.prediction.confidence + '%',
      });
    } catch (_) { /* toast already shown */ }
    finally { btn.disabled = false; btn.innerHTML = original;
             if (window.lucide) window.lucide.createIcons(); }
  });

  function renderResult(data) {
    const p = data.prediction;
    const m = p.meta || {};
    const bg = m.color ? ('linear-gradient(135deg,' + m.color + ',#0f3d2e)') : '';
    const html = `
      <div class="result">
        <div class="result__thumb" style="${bg ? 'background:' + bg : ''}">
          ${m.emoji || '🌱'}
        </div>
        <div>
          <div class="result__title">
            <h4>${p.crop}</h4>
            <span class="pill">${m.category || 'Recommended'}</span>
            <span class="result__confidence">${p.confidence.toFixed(1)}%</span>
          </div>
          <div class="result__desc">${m.description || ''}</div>
        </div>
      </div>

      <div class="top3">
        ${data.top3.map(t => `
          <div class="top-item"><b>${t.crop}</b><span class="muted">${t.confidence.toFixed(1)}%</span></div>`).join('')}
      </div>

      <dl class="meta-grid">
        <div><dt>Category</dt><dd>${m.category || '—'}</dd></div>
        <div><dt>Growing season</dt><dd>${m.season || '—'}</dd></div>
        <div><dt>Ideal temperature</dt><dd>${m.ideal_temperature || '—'}</dd></div>
        <div><dt>Suitable pH</dt><dd>${m.ph_range || '—'}</dd></div>
        <div><dt>Rainfall</dt><dd>${m.rainfall_range || '—'}</dd></div>
        <div><dt>Water requirement</dt><dd>${m.water || '—'}</dd></div>
        <div><dt>Suitable soil</dt><dd>${m.soil || '—'}</dd></div>
        <div><dt>Fertilizer</dt><dd>${m.fertilizer || '—'}</dd></div>
        <div><dt>Expected yield</dt><dd>${m.expected_yield || '—'}</dd></div>
        <div><dt>Benefits</dt><dd>${(m.benefits || []).join(', ') || '—'}</dd></div>
      </dl>

      <div class="form-actions">
        <a class="btn btn--ghost" href="/api/history/${data.id}/report.pdf" download="opticrop_report_${data.id}.pdf">
          <i data-lucide="file-down"></i> Download PDF report
        </a>
        <a class="btn btn--primary" href="/suitability">
          <i data-lucide="gauge"></i> Deep-dive suitability
        </a>
      </div>
    `;
    bodyEl.innerHTML = html;
    bodyEl.hidden = false;
    emptyEl.hidden = true;
    if (window.lucide) window.lucide.createIcons();
  }
})();