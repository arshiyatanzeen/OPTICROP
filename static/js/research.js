/* Research dashboard — Chart.js visualizations */

(function () {
  'use strict';

  function themed() {
    const dark = document.documentElement.getAttribute('data-theme') === 'dark';
    return {
      grid:  dark ? 'rgba(255,255,255,.08)' : 'rgba(15,30,23,.08)',
      text:  dark ? '#cfe0d5' : '#0f1e17',
      brand: '#3d8361',
      accent:'#d4a24a',
    };
  }

  async function init() {
    if (!window.Chart) return setTimeout(init, 50);
    let data;
    try { data = await window.OptiFetch('/api/stats'); }
    catch (_) { return; }
    const t = themed();
    Chart.defaults.color = t.text;
    Chart.defaults.borderColor = t.grid;
    Chart.defaults.font.family = "Inter, system-ui, sans-serif";

    const impEl = document.getElementById('chartImportance');
    if (impEl && data.model.feature_importance) {
      const labels = Object.keys(data.model.feature_importance);
      const values = labels.map(k => data.model.feature_importance[k]);
      new Chart(impEl, {
        type: 'bar',
        data: { labels, datasets: [{ label: 'Importance', data: values,
                backgroundColor: t.brand, borderRadius: 8 }] },
        options: { plugins: { legend: { display: false } }, responsive: true,
                   scales: { y: { beginAtZero: true } } },
      });
    }

    const modelsEl = document.getElementById('chartModels');
    const scores = data.model.model_scores || {};
    if (modelsEl && Object.keys(scores).length) {
      new Chart(modelsEl, {
        type: 'bar',
        data: {
          labels: Object.keys(scores),
          datasets: [{ label: 'Accuracy', data: Object.values(scores).map(v => v * 100),
                       backgroundColor: t.accent, borderRadius: 8 }],
        },
        options: { plugins: { legend: { display: false } }, responsive: true,
                   scales: { y: { beginAtZero: true, max: 100, ticks: { callback: v => v + '%' } } } },
      });
    }

    const volEl = document.getElementById('chartVolume');
    const days = data.usage.by_day || [];
    if (volEl) {
      new Chart(volEl, {
        type: 'line',
        data: {
          labels: days.map(d => d.day),
          datasets: [{ label: 'Predictions', data: days.map(d => d.count),
                       borderColor: t.brand, backgroundColor: 'rgba(61,131,97,.18)',
                       fill: true, tension: .35, pointRadius: 3 }],
        },
        options: { plugins: { legend: { display: false } }, responsive: true,
                   scales: { y: { beginAtZero: true, ticks: { precision: 0 } } } },
      });
    }

    const topEl = document.getElementById('chartTop');
    const tops = data.usage.top_crops || [];
    if (topEl) {
      new Chart(topEl, {
        type: 'doughnut',
        data: {
          labels: tops.map(x => x.crop),
          datasets: [{ data: tops.map(x => x.count),
                       backgroundColor: ['#0f3d2e','#3d8361','#7cc4a0','#d4a24a','#b7791f',
                                         '#2f855a','#6b7280','#c0392b','#8b6f47','#6c3483'] }],
        },
        options: { plugins: { legend: { position: 'right' } }, responsive: true, cutout: '58%' },
      });
    }
  }

  document.addEventListener('DOMContentLoaded', init);
})();
