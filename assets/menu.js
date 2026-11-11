// Mobile touch-menu toggle for static, single-language pages (no [data-en]/[data-it]
// content swap needed here — that's lang.js, used on pages that still serve both
// languages from one file via ?lang=). Split pages (/it/*.html and their EN siblings)
// include this instead.
(function () {
  document.addEventListener('DOMContentLoaded', function () {
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
