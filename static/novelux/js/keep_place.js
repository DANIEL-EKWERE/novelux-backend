/* Keeps an editor's place in the SE / CE dashboards.
 *
 * Many actions (locking a chapter, approving an edit, reviewing KYC…) refresh
 * the page to show the new state. Without this, every refresh landed back on
 * the Dashboard section at the top. Now the open section, its sub-tab and the
 * scroll position are remembered for the browser tab and restored after any
 * refresh (an action's or the editor's own F5).
 */
(function () {
  var KEY = 'nux_place:' + location.pathname;
  var MAX_AGE = 30 * 60 * 1000;          // a place older than 30 min isn't restored

  function scroller() { return document.querySelector('.main'); }

  function save() {
    try {
      var active = document.querySelector('.page.active');
      var main = scroller();
      sessionStorage.setItem(KEY, JSON.stringify({
        page: active ? active.id.replace(/^page-/, '') : null,
        y: window.scrollY || document.documentElement.scrollTop || 0,
        my: main ? main.scrollTop : 0,
        t: Date.now()
      }));
    } catch (e) {}
  }
  window.addEventListener('beforeunload', save);
  window.addEventListener('pagehide', save);
  document.addEventListener('visibilitychange', function () { if (document.hidden) save(); });

  function restoreScroll(st, tries) {
    var main = scroller();
    window.scrollTo(0, st.y || 0);
    if (main && st.my) main.scrollTop = st.my;
    // Lists load after the page — keep trying until the page is tall enough
    var short = (window.scrollY + 2 < (st.y || 0)) || (main && st.my && main.scrollTop + 2 < st.my);
    if (short && tries > 0) setTimeout(function () { restoreScroll(st, tries - 1); }, 250);
  }

  function restore() {
    var st;
    try { st = JSON.parse(sessionStorage.getItem(KEY) || 'null'); } catch (e) { st = null; }
    if (!st || !st.page || Date.now() - st.t > MAX_AGE) return;
    if ('scrollRestoration' in history) history.scrollRestoration = 'manual';
    if (st.page !== 'dashboard' && document.getElementById('page-' + st.page)) {
      // Click the sidebar button so the section loads its data as usual
      var btn = document.querySelector('.nbtn[onclick*="gp(\'' + st.page + '\'"]');
      if (btn) btn.click();
      else if (typeof window.gp === 'function') window.gp(st.page, null);
    }
    restoreScroll(st, 12);              // up to ~3 seconds of retries
  }

  if (document.readyState === 'complete') restore();
  else window.addEventListener('load', restore);
})();
