/* OptiCrop — global app JS: theme, sidebar, icons, toasts, helpers */

(function () {
  'use strict';

  // ---- Theme ----
  const THEME_KEY = 'opticrop.theme';
  const root = document.documentElement;
  const saved = localStorage.getItem(THEME_KEY);
  if (saved === 'light' || saved === 'dark') root.setAttribute('data-theme', saved);

  document.addEventListener('click', (e) => {
    const btn = e.target.closest('#themeBtn');
    if (!btn) return;
    const next = root.getAttribute('data-theme') === 'dark' ? 'light' : 'dark';
    root.setAttribute('data-theme', next);
    localStorage.setItem(THEME_KEY, next);
    if (window.lucide) window.lucide.createIcons();
  });

  // ---- Mobile sidebar ----
  const MOBILE_BP = 768;
  const isMobile = () => window.innerWidth <= MOBILE_BP;
  const getSidebar = () => document.querySelector('.sidebar');
  const getOverlay = () => document.getElementById('sidebarOverlay');
  const openSidebar = () => {
    getSidebar()?.classList.add('open', 'is-open');
    getOverlay()?.classList.add('is-visible');
  };
  const closeSidebar = () => {
    getSidebar()?.classList.remove('open', 'is-open');
    getOverlay()?.classList.remove('is-visible');
  };

  // ---- Sidebar toggle (works on desktop AND mobile) ----
  document.addEventListener('click', (e) => {
    if (!isMobile()) return;
    const toggle = e.target.closest('.sidebar-toggle, #menuBtn');
    if (toggle) {
      e.stopPropagation();
      const sb = getSidebar();
      if (sb?.classList.contains('open')) closeSidebar(); else openSidebar();
      return;
    }
    // Link inside sidebar → close
    if (e.target.closest('#sidebar a')) {
      closeSidebar();
      return;
    }
    // Click outside sidebar → close
    if (!e.target.closest('#sidebar')) {
      closeSidebar();
    }
  });

  window.addEventListener('resize', () => {
    if (!isMobile()) closeSidebar();
  });

  // ---- Lucide icons (idempotent) ----
  const renderIcons = () => window.lucide && window.lucide.createIcons();
  document.addEventListener('DOMContentLoaded', renderIcons);
  window.addEventListener('load', renderIcons);

  // ---- Toasts ----
  window.OptiToast = function (opts) {
    const host = document.getElementById('toastHost');
    if (!host) return;
    const el = document.createElement('div');
    el.className = 'toast is-' + (opts.type || 'info');
    el.innerHTML =
      '<div style="flex:1"><div class="toast__title">' + (opts.title || 'Notice') + '</div>' +
      '<div class="toast__msg">' + (opts.message || '') + '</div></div>';
    host.appendChild(el);
    setTimeout(() => {
      el.style.opacity = '0';
      el.style.transform = 'translateY(6px)';
      el.style.transition = 'opacity .3s ease, transform .3s ease';
      setTimeout(() => el.remove(), 320);
    }, opts.duration || 4200);
  };

  // ---- Fetch helper ----
  window.OptiFetch = async function (url, opts) {
    const r = await fetch(url, Object.assign({
      headers: { 'Content-Type': 'application/json' },
    }, opts || {}));
    let data = null;
    try { data = await r.json(); } catch (_) { /* non-JSON */ }
    if (!r.ok || (data && data.ok === false)) {
      const msg = (data && data.error) || ('HTTP ' + r.status);
      const details = (data && data.details) ? data.details.join(' · ') : '';
      window.OptiToast({ type: 'error', title: 'Request failed',
                         message: details || msg });
      throw new Error(msg);
    }
    return data;
  };
})();
