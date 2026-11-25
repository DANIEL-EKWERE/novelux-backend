/* "Author benefits" share window, used by every dashboard.
 *   openBenefitsShare()                 → plain link
 *   openBenefitsShare({code: 'AB12CD'}) → a senior editor's link: authors who
 *     sign up from it are linked to that editor.
 */
(function () {
  function esc(v) { return String(v || '').replace(/[&<>"']/g, function (c) { return { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]; }); }
  window.openBenefitsShare = function (opts) {
    opts = opts || {};
    var url = location.origin + '/author-benefits/' + (opts.code ? '?ref=' + encodeURIComponent(opts.code) : '');
    var msg = opts.code
      ? 'Write on HuxNovel with me as your editor — 50% revenue share and up to $170 in bonuses. See the author benefits: '
      : 'Write on HuxNovel — 50% revenue share and up to $170 in bonuses for authors. See the benefits: ';
    var enc = encodeURIComponent, full = enc(msg + url);
    var old = document.getElementById('nxShare'); if (old) old.remove();
    var bg = document.createElement('div');
    bg.id = 'nxShare';
    bg.style.cssText = 'position:fixed;inset:0;background:rgba(0,0,0,.5);z-index:9999;display:flex;align-items:center;justify-content:center;padding:16px;font-family:inherit;';
    var btn = 'display:flex;align-items:center;justify-content:center;gap:6px;padding:10px;border-radius:10px;border:1px solid #e8d9ce;background:#fff;color:#3b2418;font-weight:600;font-size:13px;text-decoration:none;cursor:pointer;';
    bg.innerHTML = '<div style="background:#fff;color:#3b2418;border-radius:16px;width:min(440px,100%);padding:20px;box-shadow:0 20px 60px rgba(0,0,0,.3);">'
      + '<div style="display:flex;align-items:center;gap:10px;margin-bottom:6px;"><b style="font-size:16px;flex:1;">Share the author benefits</b>'
      + '<button id="nxClose" style="border:none;background:none;font-size:20px;cursor:pointer;color:#8a6f60;">✕</button></div>'
      + '<p style="font-size:13px;color:#8a6f60;margin:0 0 12px;">' + (opts.code
          ? 'Your link carries your editor code <b style="color:#b4501b;font-family:monospace;">' + esc(opts.code) + '</b> — authors who sign up from it are linked to you.'
          : 'Send writers the page with HuxNovel\'s author benefits and the sign-up link.') + '</p>'
      + '<div style="display:flex;gap:6px;"><input id="nxUrl" readonly value="' + esc(url) + '" style="flex:1;min-width:0;padding:10px;border:1px solid #e8d9ce;border-radius:10px;font-size:13px;background:#fff7f0;color:#3b2418;">'
      + '<button id="nxCopy" style="' + btn + 'background:#b4501b;color:#fff;border-color:#b4501b;">Copy</button></div>'
      + '<div style="display:grid;grid-template-columns:repeat(3,1fr);gap:8px;margin-top:12px;">'
      + '<a style="' + btn + '" target="_blank" href="https://wa.me/?text=' + full + '">WhatsApp</a>'
      + '<a style="' + btn + '" target="_blank" href="https://www.facebook.com/sharer/sharer.php?u=' + enc(url) + '">Facebook</a>'
      + '<a style="' + btn + '" target="_blank" href="https://twitter.com/intent/tweet?text=' + enc(msg) + '&url=' + enc(url) + '">X</a>'
      + '<a style="' + btn + '" target="_blank" href="https://t.me/share/url?url=' + enc(url) + '&text=' + enc(msg) + '">Telegram</a>'
      + '<a style="' + btn + '" href="mailto:?subject=' + enc('Write on HuxNovel') + '&body=' + full + '">Email</a>'
      + '<a style="' + btn + '" target="_blank" href="' + esc(url) + '">Open page ↗</a></div>'
      + (navigator.share ? '<button id="nxNative" style="' + btn + 'width:100%;margin-top:8px;">More options…</button>' : '')
      + '</div>';
    document.body.appendChild(bg);
    bg.addEventListener('click', function (e) { if (e.target === bg) bg.remove(); });
    document.getElementById('nxClose').onclick = function () { bg.remove(); };
    document.getElementById('nxCopy').onclick = function () {
      var b = this;
      (navigator.clipboard ? navigator.clipboard.writeText(url) : Promise.reject()).catch(function () {
        var i = document.getElementById('nxUrl'); i.select(); document.execCommand('copy');
      }).then(function () { b.textContent = 'Copied ✓'; setTimeout(function () { b.textContent = 'Copy'; }, 1800); });
    };
    var nat = document.getElementById('nxNative');
    if (nat) nat.onclick = function () { navigator.share({ title: 'HuxNovel Author Benefits', text: msg, url: url }).catch(function () {}); };
  };
})();
