(function () {
  const SUPPORTED = ['en', 'it'];

  function getLang() {
    const p = new URLSearchParams(window.location.search).get('lang');
    if (p && SUPPORTED.includes(p)) return p;
    const s = localStorage.getItem('siteLang');
    if (s && SUPPORTED.includes(s)) return s;
    return 'en';
  }

  function applyLang(lang) {
    document.documentElement.lang = lang;

    // Swap translatable content
    document.querySelectorAll('[data-en]').forEach(el => {
      const val = el.dataset[lang];
      if (val !== undefined) el.innerHTML = val;
    });

    // Swap translatable alt text on images (data-alt-en / data-alt-it)
    const altKey = 'alt' + lang.charAt(0).toUpperCase() + lang.slice(1);
    document.querySelectorAll('[data-alt-en]').forEach(el => {
      const val = el.dataset[altKey];
      if (val !== undefined) el.alt = val;
    });

    // Show ONLY the opposite-language button (the one you can switch TO)
    document.querySelectorAll('.lang-btn').forEach(btn => {
      btn.style.display = btn.dataset.lang !== lang ? '' : 'none';
    });

    localStorage.setItem('siteLang', lang);

    // Keep HOME link language-aware (clean absolute paths, no ?lang= query
    // string: this page is noindex, so there is no SEO-crawlability reason
    // left to rewrite the URL, and a ?lang= link was still being
    // re-discovered by Google via this page's own hreflang tag).
    const homeLink = document.getElementById('home-link');
    if (homeLink) {
      homeLink.href = lang === 'en' ? '/en/' : '/';
    }
  }

  document.addEventListener('DOMContentLoaded', function () {
    applyLang(getLang());
    document.querySelectorAll('.lang-btn').forEach(btn => {
      btn.addEventListener('click', function () { applyLang(this.dataset.lang); });
    });

    // Topics menu: tap to open/close on touch screens (hover still works on desktop)
    const menu = document.querySelector('.menu-container');
    if (menu) {
      const trigger = menu.querySelector('.menu-trigger');
      trigger.addEventListener('click', function (e) {
        e.stopPropagation();
        menu.classList.toggle('open');
      });
      document.addEventListener('click', function (e) {
        if (!menu.contains(e.target)) menu.classList.remove('open');
      });
      document.addEventListener('keydown', function (e) {
        if (e.key === 'Escape') menu.classList.remove('open');
      });
    }
  });
})();
