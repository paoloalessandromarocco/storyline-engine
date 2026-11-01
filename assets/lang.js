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

    // Show ONLY the opposite-language button (the one you can switch TO)
    document.querySelectorAll('.lang-btn').forEach(btn => {
      btn.style.display = btn.dataset.lang !== lang ? '' : 'none';
    });

    // Update URL for SEO crawlability
    const url = new URL(window.location.href);
    lang === 'en' ? url.searchParams.delete('lang')
                  : url.searchParams.set('lang', lang);
    history.replaceState({}, '', url.toString());

    localStorage.setItem('siteLang', lang);

    // Keep HOME link language-aware
    const homeLink = document.getElementById('home-link');
    if (homeLink) {
      homeLink.href = lang === 'en' ? 'index.html' : 'index.html?lang=' + lang;
    }
  }

  document.addEventListener('DOMContentLoaded', function () {
    applyLang(getLang());
    document.querySelectorAll('.lang-btn').forEach(btn => {
      btn.addEventListener('click', function () { applyLang(this.dataset.lang); });
    });
  });
})();
