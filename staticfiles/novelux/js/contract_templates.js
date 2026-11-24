/* Contract templates + "Send contract" — shared by the SE and CE dashboards.
 *
 * Needs the page to provide:
 *   window.NUX   — API helper with get(), post(), call()
 *   window.toast — toast(message)
 * Optional:
 *   #tplList            — container for the templates table
 *   window.onContractSent(slug) — called after a contract is sent (default: reload)
 *
 * Builds its own modals and styles (ct-* classes) so it looks the same on
 * either dashboard. Uses the dashboards' shared colour variables.
 */
(function () {
  'use strict';

  const css = `
.ct-bg{position:fixed;inset:0;background:rgba(0,0,0,.5);z-index:300;display:flex;align-items:center;justify-content:center;padding:16px;opacity:0;pointer-events:none;transition:opacity .2s;}
.ct-bg.open{opacity:1;pointer-events:all;}
.ct-modal{background:var(--bg);color:var(--fg);border:1px solid var(--border);border-radius:10px;width:100%;max-width:860px;max-height:92vh;display:flex;flex-direction:column;}
.ct-top{padding:16px 20px;border-bottom:1px solid var(--border);display:flex;align-items:center;justify-content:space-between;gap:10px;}
.ct-top h3{font-size:15px;font-weight:600;}
.ct-x{background:none;border:none;color:var(--muted-fg);font-size:22px;line-height:1;cursor:pointer;}
.ct-body{padding:18px 20px;overflow-y:auto;flex:1;font-size:13px;line-height:1.5;}
.ct-foot{padding:14px 20px;border-top:1px solid var(--border);display:flex;justify-content:flex-end;gap:8px;}
.ct-form{display:grid;grid-template-columns:1fr 1fr;gap:10px;margin-bottom:10px;}
.ct-form .full{grid-column:1/-1;}
.ct-form label,.ct-lbl{font-size:11px;color:var(--muted-fg);display:block;margin-bottom:4px;}
.ct-form input,.ct-form select{width:100%;padding:8px 10px;border:1px solid var(--border);border-radius:6px;background:var(--bg);color:var(--fg);font:inherit;font-size:13px;}
@media(max-width:640px){.ct-form{grid-template-columns:1fr;}}
.ct-doc{border:1px solid var(--border);border-radius:8px;background:var(--card);padding:16px 20px;font-size:13px;line-height:1.7;max-height:46vh;overflow-y:auto;}
.ct-doc h2,.ct-doc h3,.ct-doc h4{font-size:14px;margin:14px 0 4px;}
.ct-doc p{margin-bottom:8px;}
.ct-doc ul,.ct-doc ol{padding-left:20px;margin-bottom:8px;}
.ct-editor{min-height:260px;outline:none;}
.ct-editor:focus{border-color:var(--role);}
.ct-tools{display:flex;flex-wrap:wrap;gap:4px;align-items:center;margin-bottom:8px;}
.ct-tools button{border:1px solid var(--border);background:var(--bg);color:var(--fg);border-radius:5px;padding:4px 8px;font-size:12px;cursor:pointer;font-family:inherit;}
.ct-tools button:hover{background:var(--muted);}
.ct-tools .sep{width:1px;height:18px;background:var(--border);margin:0 4px;}
.ct-btn{display:inline-flex;align-items:center;gap:6px;padding:7px 14px;font-size:13px;font-weight:500;border-radius:6px;cursor:pointer;font-family:inherit;border:1px solid var(--border);background:none;color:var(--fg);}
.ct-btn:hover{background:var(--muted);}
.ct-btn.primary{background:var(--role);border-color:var(--role);color:#fff;}
.ct-btn.primary:hover{opacity:.9;background:var(--role);}
.ct-btn:disabled{opacity:.5;cursor:default;}
.ct-tbl{width:100%;border-collapse:collapse;}
.ct-tbl th,.ct-tbl td{padding:11px 14px;text-align:left;font-size:13px;border-bottom:1px solid var(--border);}
.ct-tbl th{font-size:10px;text-transform:uppercase;letter-spacing:.08em;color:var(--muted-fg);}
.ct-tbl tr:last-child td{border-bottom:none;}
.ct-card{border:1px solid var(--border);border-radius:8px;background:var(--card);overflow-x:auto;}
.ct-badge{display:inline-block;padding:2px 7px;font-size:11px;border-radius:4px;background:color-mix(in srgb,var(--role) 14%,transparent);color:var(--role);margin-left:6px;}
.ct-empty{text-align:center;padding:40px 20px;color:var(--muted-fg);}
.ct-empty h3{font-size:15px;color:var(--fg);margin-bottom:4px;}
code.ct{font-size:12px;background:var(--muted);padding:1px 5px;border-radius:4px;}`;

  const markup = `
<div class="ct-bg" id="ctSend">
  <div class="ct-modal">
    <div class="ct-top"><h3 id="ctSendTitle">Send contract</h3><button class="ct-x" data-close>×</button></div>
    <div class="ct-body">
      <div class="ct-form">
        <div><label>Template</label><select id="ctTemplate"></select></div>
        <div><label>Contract type</label>
          <select id="ctType"><option value="non_exclusive">Non-Exclusive</option><option value="exclusive">Exclusive</option></select>
        </div>
        <div class="full"><label>Note to the author (optional)</label><input id="ctNote" maxlength="500" placeholder="e.g. Congratulations — we love this story!"></div>
      </div>
      <span class="ct-lbl" style="margin-top:6px;">Preview — exactly what the author will sign</span>
      <div id="ctPreview" class="ct-doc">Loading…</div>
    </div>
    <div class="ct-foot">
      <button class="ct-btn" data-close>Cancel</button>
      <button class="ct-btn primary" id="ctSendBtn">Send contract</button>
    </div>
  </div>
</div>
<div class="ct-bg" id="ctEdit">
  <div class="ct-modal">
    <div class="ct-top"><h3 id="ctEditTitle">New template</h3><button class="ct-x" data-close>×</button></div>
    <div class="ct-body">
      <div class="ct-form">
        <div><label>Template name</label><input id="ctName" maxlength="150" placeholder="e.g. Exclusive — 2 years"></div>
        <div><label>Default contract type</label>
          <select id="ctEditType"><option value="non_exclusive">Non-Exclusive</option><option value="exclusive">Exclusive</option></select>
        </div>
      </div>
      <div class="ct-tools" id="ctTools">
        <button type="button" data-cmd="bold"><b>B</b></button>
        <button type="button" data-cmd="italic"><i>I</i></button>
        <button type="button" data-cmd="formatBlock" data-val="h3">Heading</button>
        <button type="button" data-cmd="formatBlock" data-val="p">Paragraph</button>
        <button type="button" data-cmd="insertUnorderedList">• List</button>
        <span class="sep"></span>
        <span style="font-size:11px;color:var(--muted-fg);">Insert:</span>
        <button type="button" data-field="author_name">Author name</button>
        <button type="button" data-field="pen_name">Pen name</button>
        <button type="button" data-field="book_title">Book title</button>
        <button type="button" data-field="contract_type">Contract type</button>
        <button type="button" data-field="date">Date</button>
        <button type="button" data-field="licence_clause">Licence clause</button>
      </div>
      <div id="ctEditor" class="ct-doc ct-editor" contenteditable="true"></div>
      <p style="font-size:11px;color:var(--muted-fg);margin-top:8px;">Fields in curly brackets, like <code class="ct">{book_title}</code>, are filled in automatically for each author. <code class="ct">{licence_clause}</code> becomes the standard exclusive / non-exclusive grant of rights. Only basic formatting is kept.</p>
    </div>
    <div class="ct-foot">
      <button class="ct-btn" id="ctDelete" style="margin-right:auto;display:none;">Remove</button>
      <button class="ct-btn" data-close>Cancel</button>
      <button class="ct-btn primary" id="ctSave">Save template</button>
    </div>
  </div>
</div>`;

  const $ = id => document.getElementById(id);
  const esc = v => String(v ?? '').replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
  const fmtDate = iso => iso ? new Date(iso).toLocaleDateString(undefined, {day:'numeric', month:'short', year:'numeric'}) : '—';
  const say = m => (window.toast ? window.toast(m) : alert(m));
  const open = id => $(id).classList.add('open');
  const close = id => $(id).classList.remove('open');

  let templates = [];
  let editing = null;
  let sendSlug = null;
  let previewTimer = null;

  // ── Templates ────────────────────────────────────────────────────────────
  async function loadTemplates() {
    try { templates = (await NUX.get('/editorial/contract-templates/')).templates; }
    catch (e) { templates = []; }
    const list = $('tplList');
    if (!list) return templates;
    if (!templates.length) {
      list.innerHTML = '<div class="ct-empty"><h3>No templates yet</h3><p>Create one or import a Word file.</p></div>';
      return templates;
    }
    list.innerHTML = '<div class="ct-card"><table class="ct-tbl"><thead><tr><th>Template</th><th>Default type</th><th>Created by</th><th>Used</th><th>Updated</th><th></th></tr></thead><tbody>'
      + templates.map(t => `<tr>
          <td style="font-weight:500;">${esc(t.name)}${t.is_default ? '<span class="ct-badge">Default</span>' : ''}</td>
          <td>${t.default_contract_type === 'exclusive' ? 'Exclusive' : 'Non-Exclusive'}</td>
          <td style="color:var(--muted-fg);">${esc(t.created_by)}</td>
          <td>${Number(t.times_used || 0).toLocaleString()} contract${t.times_used === 1 ? '' : 's'}</td>
          <td style="color:var(--muted-fg);font-size:12px;">${fmtDate(t.updated_at)}</td>
          <td style="text-align:right;"><button class="ct-btn" onclick="openTemplateEditor(${t.id})">${t.can_edit ? 'Edit' : 'View'}</button></td>
        </tr>`).join('')
      + '</tbody></table></div>';
    return templates;
  }

  const STARTER = '<h3>1. Parties</h3><p>This agreement is between <strong>HuxNovel</strong> ("Platform") and <strong>{author_name}</strong>, writing as <strong>{pen_name}</strong> ("Author"), for the work <strong>{book_title}</strong>, dated {date}.</p><h3>2. Grant of Rights</h3><p>{licence_clause}</p>';

  function openTemplateEditor(id, preset) {
    const t = id ? templates.find(x => x.id === id) : null;
    editing = t;
    const canEdit = !t || t.can_edit;
    $('ctEditTitle').textContent = t ? (canEdit ? 'Edit template' : 'View template') : 'New template';
    $('ctName').value = t ? t.name : (preset?.name || '');
    $('ctEditType').value = t ? t.default_contract_type : 'non_exclusive';
    $('ctEditor').innerHTML = t ? t.body : (preset?.body || STARTER);
    $('ctEditor').contentEditable = canEdit ? 'true' : 'false';
    $('ctName').disabled = $('ctEditType').disabled = !canEdit;
    $('ctTools').style.display = canEdit ? '' : 'none';
    $('ctSave').style.display = canEdit ? '' : 'none';
    $('ctDelete').style.display = (t && canEdit && !t.is_default) ? '' : 'none';
    open('ctEdit');
  }

  async function saveTemplate() {
    const btn = $('ctSave');
    const payload = { name: $('ctName').value, body: $('ctEditor').innerHTML, default_contract_type: $('ctEditType').value };
    btn.disabled = true;
    try {
      if (editing) await NUX.call('/editorial/contract-templates/' + editing.id + '/', { method: 'PATCH', body: JSON.stringify(payload) });
      else await NUX.post('/editorial/contract-templates/', payload);
      close('ctEdit'); say('Template saved'); loadTemplates();
    } catch (e) { say(e.detail || 'Could not save the template'); }
    finally { btn.disabled = false; }
  }

  async function removeTemplate() {
    if (!editing || !confirm(`Remove "${editing.name}"? Contracts already sent with it are not affected.`)) return;
    try {
      // 204 has no body, so NUX's r.json() rejects without a .detail — that's success.
      await NUX.call('/editorial/contract-templates/' + editing.id + '/', { method: 'DELETE' })
        .catch(e => { if (e && e.detail) throw e; });
      close('ctEdit'); say('Template removed'); loadTemplates();
    } catch (e) { say(e.detail || 'Could not remove the template'); }
  }

  let mammothLoading = null;
  function loadMammoth() {
    if (window.mammoth) return Promise.resolve();
    return mammothLoading ||= new Promise((ok, fail) => {
      const sc = document.createElement('script');
      sc.src = 'https://cdnjs.cloudflare.com/ajax/libs/mammoth/1.6.0/mammoth.browser.min.js';
      sc.onload = ok;
      sc.onerror = () => { mammothLoading = null; fail(new Error('Could not load the Word reader')); };
      document.head.appendChild(sc);
    });
  }

  async function importTemplate(file) {
    if (!file) return;
    const ext = file.name.split('.').pop().toLowerCase();
    try {
      let body;
      if (ext === 'docx') {
        await loadMammoth();
        body = (await mammoth.convertToHtml({ arrayBuffer: await file.arrayBuffer() })).value;
      } else if (ext === 'txt' || ext === 'md') {
        const text = (await file.text()).replace(/\r\n?/g, '\n').trim();
        body = text.split(/\n\s*\n/).map(b => '<p>' + esc(b.trim()).replace(/\n/g, '<br>') + '</p>').join('');
      } else { say('Use a Word (.docx) or text (.txt) file'); return; }
      if (!templates.length) await loadTemplates();
      openTemplateEditor(null, { name: file.name.replace(/\.[^.]+$/, ''), body });
      say('Imported — review the text, add fields like {book_title}, then save');
    } catch (e) { say("Couldn't read that file"); }
  }

  // ── Send contract ────────────────────────────────────────────────────────
  async function openSendContract(slug, title) {
    sendSlug = slug;
    $('ctSendTitle').textContent = 'Send contract — ' + title;
    $('ctNote').value = '';
    $('ctTemplate').innerHTML = '<option>Loading…</option>';
    $('ctPreview').textContent = 'Loading…';
    open('ctSend');
    await loadTemplates();
    $('ctTemplate').innerHTML = templates.map(t => `<option value="${t.id}" ${t.is_default ? 'selected' : ''}>${esc(t.name)}</option>`).join('');
    templateChanged();
  }

  function templateChanged() {
    const t = templates.find(x => String(x.id) === $('ctTemplate').value);
    if (t) $('ctType').value = t.default_contract_type;
    refreshPreview();
  }

  function refreshPreview() {
    clearTimeout(previewTimer);
    previewTimer = setTimeout(async () => {
      try {
        const r = await NUX.post('/editorial/contracts/preview/', {
          story_slug: sendSlug, template_id: $('ctTemplate').value, contract_type: $('ctType').value,
        });
        $('ctPreview').innerHTML = r.html || '<p style="color:var(--muted-fg);">This template is empty.</p>';
      } catch (e) { $('ctPreview').textContent = e.detail || 'Could not build the preview.'; }
    }, 150);
  }

  async function sendContract() {
    const type = $('ctType');
    const label = type.options[type.selectedIndex].text;
    if (!confirm(`Send this ${label} contract to the author now? They will be emailed a link to sign it.`)) return;
    const btn = $('ctSendBtn');
    btn.disabled = true;
    try {
      await NUX.post('/editorial/stories/' + sendSlug + '/send-contract/', {
        template_id: $('ctTemplate').value, contract_type: type.value, note: $('ctNote').value,
      });
      close('ctSend');
      say('Contract sent to the author');
      if (typeof window.onContractSent === 'function') window.onContractSent(sendSlug);
      else setTimeout(() => location.reload(), 900);
    } catch (e) { say(e.detail || 'Could not send the contract'); }
    finally { btn.disabled = false; }
  }

  // ── Wire up ──────────────────────────────────────────────────────────────
  function init() {
    const style = document.createElement('style');
    style.textContent = css;
    document.head.appendChild(style);
    const wrap = document.createElement('div');
    wrap.innerHTML = markup;
    document.body.appendChild(wrap);

    document.querySelectorAll('.ct-bg').forEach(bg => {
      bg.addEventListener('click', e => { if (e.target === bg || e.target.hasAttribute('data-close')) bg.classList.remove('open'); });
    });
    $('ctTemplate').addEventListener('change', templateChanged);
    $('ctType').addEventListener('change', refreshPreview);
    $('ctSendBtn').addEventListener('click', sendContract);
    $('ctSave').addEventListener('click', saveTemplate);
    $('ctDelete').addEventListener('click', removeTemplate);
    $('ctTools').addEventListener('click', e => {
      const b = e.target.closest('button');
      if (!b) return;
      $('ctEditor').focus();
      if (b.dataset.field) document.execCommand('insertText', false, '{' + b.dataset.field + '}');
      else document.execCommand(b.dataset.cmd, false, b.dataset.val || null);
    });
  }

  window.loadTemplates      = loadTemplates;
  window.openTemplateEditor = openTemplateEditor;
  window.importTemplate     = importTemplate;
  window.openSendContract   = openSendContract;

  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', init);
  else init();
})();
