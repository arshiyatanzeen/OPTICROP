/* Crop library — search + category filter */

(function () {
  'use strict';
  const grid = document.getElementById('cropGrid');
  const search = document.getElementById('cropSearch');
  const chipsHost = document.getElementById('catChips');

  const cards = Array.from(grid.querySelectorAll('.crop-card'));
  const categories = Array.from(new Set(cards.map(c => c.dataset.category))).sort();

  const chipHtml = ['<button data-cat="all" class="is-active">All</button>']
    .concat(categories.map(c => `<button data-cat="${c}">${c.replace(/\b\w/g, m => m.toUpperCase())}</button>`))
    .join('');
  chipsHost.innerHTML = chipHtml;

  let activeCat = 'all';
  function apply() {
    const q = (search.value || '').trim().toLowerCase();
    cards.forEach(card => {
      const matchCat = activeCat === 'all' || card.dataset.category === activeCat;
      const matchTxt = !q || card.dataset.name.includes(q) || card.dataset.category.includes(q)
                       || card.textContent.toLowerCase().includes(q);
      card.style.display = (matchCat && matchTxt) ? '' : 'none';
    });
  }

  chipsHost.addEventListener('click', (e) => {
    const b = e.target.closest('button[data-cat]');
    if (!b) return;
    activeCat = b.dataset.cat;
    chipsHost.querySelectorAll('button').forEach(x => x.classList.toggle('is-active', x === b));
    apply();
  });
  search.addEventListener('input', apply);
})();
