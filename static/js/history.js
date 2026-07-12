/* Prediction history — live search */

(function () {
  'use strict';
  const tbody = document.querySelector('#historyTable tbody');
  const search = document.getElementById('historySearch');
  let cache = [];

  function render(rows) {
    if (!rows.length) {
      tbody.innerHTML = '<tr><td colspan="11" class="muted">No predictions match.</td></tr>';
      return;
    }
    tbody.innerHTML = rows.map(r => `
      <tr>
        <td>#${r.id}</td>
        <td>${r.created_at}</td>
        <td><span class="pill">${r.predicted_crop}</span></td>
        <td>${r.confidence.toFixed(1)}%</td>
        <td>${r.N}</td><td>${r.P}</td><td>${r.K}</td>
        <td>${r.temperature}</td><td>${r.humidity}</td>
        <td>${r.ph}</td><td>${r.rainfall}</td>
      </tr>`).join('');
    if (window.lucide) window.lucide.createIcons();
  }

  async function load() {
    try {
      const data = await window.OptiFetch('/api/history?limit=500');
      cache = data.rows || [];
      apply();
    } catch (_) { /* toast shown */ }
  }
  function apply() {
    const q = (search.value || '').trim().toLowerCase();
    const rows = !q ? cache : cache.filter(r => r.predicted_crop.toLowerCase().includes(q));
    render(rows);

    // Keep "Export CSV" in sync with the current search — exporting the
    // same crop(s) currently shown in the table, not the entire history.
    const exportBtn = document.getElementById('exportCsvBtn');
    if (exportBtn) {
      exportBtn.href = q
        ? '/api/history.csv?q=' + encodeURIComponent(q)
        : '/api/history.csv';
    }
  }

  search.addEventListener('input', apply);
  document.addEventListener('DOMContentLoaded', load);
})();