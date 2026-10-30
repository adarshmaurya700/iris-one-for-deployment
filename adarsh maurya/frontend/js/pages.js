/**
 * IRIS one — Separate pages for every sidebar item
 * Loads AFTER app.js. Adds real routes (#opportunities, #saved, #applications,
 * #ai, #settings) so each sidebar item opens its own page instead of
 * filtering the dashboard.
 */
(function () {
  'use strict';

  const S = window.irisState;
  const router = window.router;
  if (!S || !router) {
    console.warn('pages.js: app.js must expose irisState and router first.');
    return;
  }

  // ───────────────────────── Routes ─────────────────────────
  const SUB_PAGES = ['opportunities', 'saved', 'applications', 'ai', 'settings'];
  const NAV_FOR = {
    dashboard: 'home', profile: 'profile', opportunities: 'opportunities',
    saved: 'saved', applications: 'applications', ai: 'ai', settings: 'settings'
  };
  SUB_PAGES.forEach(r => { router.routes[r] = 'screen-dashboard'; });

  const $ = id => document.getElementById(id);
  const esc = s => String(s == null ? '' : s).replace(/[&<>"']/g, c =>
    ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]));

  function routeName() {
    const h = (window.location.hash || '').replace('#', '').trim();
    return NAV_FOR[h] ? h : 'dashboard';
  }

  // Opportunities page filter state
  const P = { cat: 'All', q: '', sort: 'match' };

  // ───────────────────────── Page container ─────────────────────────
  function ensurePageView() {
    let el = $('page-view');
    if (el) return el;
    const profile = $('profile-page');
    if (!profile) return null;
    el = document.createElement('div');
    el.id = 'page-view';
    el.className = 'view-hidden flex-1 min-w-0 flex flex-col overflow-hidden';
    el.style.backgroundColor = 'var(--bg-canvas)';
    profile.parentNode.insertBefore(el, profile);
    return el;
  }

  function shell(eyebrow, title, sub, body) {
    return `
      <header class="top-header-canvas flex items-center justify-between gap-4 px-10 py-5 flex-shrink-0">
        <div>
          <p class="text-[10px] font-bold tracking-widest uppercase text-[#B8962E] mb-1">${eyebrow}</p>
          <h1 class="text-xl sm:text-2xl font-extrabold tracking-tight text-[#181B28]">${title}</h1>
          ${sub ? `<p class="text-xs text-[#6B7280] mt-1">${sub}</p>` : ''}
        </div>
        <button onclick="router.navigate('dashboard')" class="px-3.5 py-2 rounded-full bg-white border border-[#E5E0D8] text-xs font-semibold text-[#181B28] hover:border-[#1E60D5] hover:bg-blue-50/70 shadow-xs transition-all cursor-pointer flex items-center gap-1.5">
          <span>←</span><span>Back to dashboard</span>
        </button>
      </header>
      <main class="flex-1 overflow-y-auto px-10 py-8">${body}</main>`;
  }

  function emptyState(icon, title, text, btnLabel, btnJs) {
    return `
      <div class="col-span-full p-10 rounded-2xl bg-white border border-dashed border-[#E5E0D8] text-center">
        <div class="w-12 h-12 rounded-full bg-amber-50 border border-amber-200 flex items-center justify-center mx-auto mb-3 text-xl">${icon}</div>
        <h4 class="text-sm font-bold text-[#181B28] mb-1">${title}</h4>
        <p class="text-xs text-[#6B7280] max-w-sm mx-auto mb-4">${text}</p>
        ${btnLabel ? `<button onclick="${btnJs}" class="btn-primary-blue text-xs py-2 px-4 rounded-full font-semibold cursor-pointer">${btnLabel}</button>` : ''}
      </div>`;
  }

  // ───────────────────────── Shared helpers ─────────────────────────
  function daysLeft(o) {
    const d = new Date(o.deadlineIso || o.deadline);
    if (isNaN(d)) return null;
    return Math.ceil((d - Date.now()) / 86400000);
  }

  function daysBadge(o) {
    const n = daysLeft(o);
    if (n === null) return `<span class="text-[10px] font-semibold px-2 py-0.5 rounded-full bg-gray-100 text-gray-600">${esc(o.deadline)}</span>`;
    if (n < 0) return '<span class="text-[10px] font-semibold px-2 py-0.5 rounded-full bg-gray-100 text-gray-600">Closed</span>';
    const cls = n <= 7 ? 'bg-red-100 text-red-700' : n <= 31 ? 'bg-amber-100 text-amber-800' : 'bg-blue-100 text-blue-800';
    return `<span class="text-[10px] font-semibold px-2 py-0.5 rounded-full ${cls}">${n} day${n === 1 ? '' : 's'} left</span>`;
  }

  function docsProgress(o) {
    const docs = (o.mandatory_documents && o.mandatory_documents.length)
      ? o.mandatory_documents
      : ['Student ID Card', 'Latest Marksheet / Transcript', 'Aadhaar / National ID'];
    let checked = [];
    try { checked = JSON.parse(localStorage.getItem('iris_docs_' + o.id) || '[]'); } catch (e) {}
    const done = checked.filter(d => docs.includes(d)).length;
    return { done, total: docs.length };
  }

  function oppCard(o) {
    const t = (o.type || '').toLowerCase();
    const c = (o.category || '').toLowerCase();
    let bg = 'card-pastel-peach', btn = 'btn-circle-red';
    if (t.includes('scholar') || c.includes('scholar')) {
      bg = 'card-pastel-mint';
    } else if (t.includes('intern') || t.includes('offer') || c.includes('intern') || c.includes('offer')) {
      bg = 'card-pastel-blue'; btn = 'btn-circle-navy';
    }
    const id = esc(o.id);
    const saved = S.savedOppIds.has(o.id);
    const applied = S.appliedOppIds.has(o.id);
    const logo = window.getBrandLogoMarkup ? window.getBrandLogoMarkup(o, 'w-10 h-10 rounded-xl') : '';

    return `
      <div class="${bg} group cursor-pointer" onclick="openDetailDrawer('${id}')" tabindex="0" role="button"
           onkeydown="if(event.key==='Enter'||event.key===' '){event.preventDefault();openDetailDrawer('${id}');}">
        <div class="flex items-center justify-between mb-3.5">
          <div class="flex items-center gap-1.5 flex-wrap">
            <span class="px-2.5 py-0.5 rounded-full text-[10px] font-semibold bg-[#111625] text-white">✦ ${esc(o.type || 'Opportunity')}</span>
            <span class="px-2 py-0.5 rounded-full text-[10px] font-semibold bg-white/70 text-[#065F46]">${esc(o.matchPct || '')}% match</span>
            ${applied ? '<span class="px-2 py-0.5 rounded-full text-[9px] font-bold bg-blue-100 text-[#1E60D5]">✓ Tracked</span>' : ''}
          </div>
          <button type="button" class="p-1.5 rounded-lg hover:bg-black/5 cursor-pointer ${saved ? 'text-[#D4AF37]' : 'text-[#6B7280] hover:text-[#181B28]'}"
                  onclick="event.stopPropagation(); toggleSaveOpportunity('${id}')"
                  title="${saved ? 'Remove from saved' : 'Save'}" aria-label="${saved ? 'Remove from saved' : 'Save'}">
            <svg width="17" height="17" viewBox="0 0 24 24" fill="${saved ? '#D4AF37' : 'none'}" stroke="currentColor" stroke-width="2"><path d="M19 21l-7-5-7 5V5a2 2 0 0 1 2-2h10a2 2 0 0 1 2 2z"/></svg>
          </button>
        </div>
        <div class="mb-2">
          ${logo}
          <h4 class="text-sm font-bold mt-2.5 mb-1 leading-snug line-clamp-2 text-[#181B28] group-hover:text-[#1E60D5] transition-colors">${esc(o.title)}</h4>
          <p class="text-[11px] text-[#4B5563] leading-relaxed line-clamp-1">${esc(o.provider)} · <span class="font-medium text-[#181B28]">${esc(o.amount)}</span> · ${esc(o.location)}</p>
        </div>
        <div class="flex items-center justify-between pt-3 mt-auto border-t border-black/5">
          <span class="text-[11px] text-[#6B7280] font-medium">Apply by ${esc(o.deadline)}</span>
          <div class="flex items-center gap-1.5">
            <button type="button" class="px-2.5 py-1 rounded-full text-[10px] font-bold bg-[#111625] text-white hover:bg-[#1E60D5] transition-all cursor-pointer"
                    onclick="event.stopPropagation(); openApplyOptionsModal('${id}')">Apply options ↗</button>
            <button type="button" class="${btn}" onclick="event.stopPropagation(); openApplyOptionsModal('${id}')" aria-label="View details">
              <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><line x1="5" y1="12" x2="19" y2="12"/><polyline points="12 5 19 12 12 19"/></svg>
            </button>
          </div>
        </div>
      </div>`;
  }

  // ───────────────────────── PAGE: Opportunities ─────────────────────────
  const CATS = ['All', 'Scholarships', 'Internships', 'Competitions', 'Student Offers', 'International'];

  function matchCat(o, cat) {
    if (cat === 'All') return true;
    const c = cat.toLowerCase();
    const type = (o.type || '').toLowerCase();
    const ocat = (o.category || '').toLowerCase();
    return ocat.includes(c) || type.includes(c) ||
      (c === 'scholarships' && type.includes('scholar')) ||
      (c === 'internships' && type.includes('intern')) ||
      (c === 'competitions' && (type.includes('compet') || type.includes('quiz') || type.includes('hack'))) ||
      (c === 'student offers' && (type.includes('offer') || ocat.includes('offer'))) ||
      (c === 'international' && (ocat.includes('internat') || (o.location || '').toLowerCase() === 'germany'));
  }

  function filteredOpps() {
    const q = P.q.toLowerCase().trim();
    let items = S.opportunities.filter(o => {
      if (!matchCat(o, P.cat)) return false;
      if (!q) return true;
      return [o.title, o.provider, o.type, o.category, (o.tags || []).join(' ')].join(' ').toLowerCase().includes(q);
    });
    const time = o => { const d = new Date(o.deadlineIso || o.deadline); return isNaN(d) ? 9e15 : d.getTime(); };
    if (P.sort === 'deadline') items.sort((a, b) => time(a) - time(b));
    else if (P.sort === 'title') items.sort((a, b) => a.title.localeCompare(b.title));
    else items.sort((a, b) => (b.matchPct || 0) - (a.matchPct || 0));
    return items;
  }

  function updateOppResults() {
    const res = $('opp-results');
    if (!res) return;
    const items = filteredOpps();
    res.innerHTML = items.length
      ? items.map(oppCard).join('')
      : emptyState('🔍', 'No opportunities found', 'Try a different category or clear your search.', 'Show everything', "IrisPages.reset()");

    const count = $('opp-count');
    if (count) count.textContent = `${items.length} of ${S.opportunities.length} opportunities`;

    const chips = $('opp-chips');
    if (chips) {
      chips.innerHTML = CATS.map(cat => {
        const n = S.opportunities.filter(o => matchCat(o, cat)).length;
        const on = cat === P.cat;
        return `<button type="button" onclick="IrisPages.setCat('${cat}')" class="px-3.5 py-1.5 rounded-full text-xs font-semibold cursor-pointer border transition-all ${on ? 'bg-[#111625] text-white border-[#111625]' : 'bg-white text-[#4B5563] border-[#E5E0D8] hover:border-[#D4AF37]'}">${cat} <span class="${on ? 'text-[#FDE047]' : 'text-[#9CA3AF]'}">${n}</span></button>`;
      }).join('');
    }
  }

  function renderOpportunities() {
    return shell('Browse', 'Opportunities', 'Every verified scholarship, internship, competition and offer in one place.', `
      <div class="flex flex-col lg:flex-row gap-3 mb-4">
        <div class="search-pill-input flex items-center gap-2.5 px-3.5 py-2 flex-1">
          <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="#9CA3AF" stroke-width="2"><circle cx="11" cy="11" r="8"/><line x1="21" y1="21" x2="16.65" y2="16.65"/></svg>
          <input id="opp-search" type="text" value="${esc(P.q)}" oninput="IrisPages.setQuery(this.value)"
                 placeholder="Search by title, provider, skill or tag" class="w-full bg-transparent text-sm text-[#181B28] placeholder-[#9CA3AF] outline-none" />
        </div>
        <select onchange="IrisPages.setSort(this.value)" class="iris-input !w-auto text-xs cursor-pointer" aria-label="Sort opportunities">
          <option value="match" ${P.sort === 'match' ? 'selected' : ''}>Best match first</option>
          <option value="deadline" ${P.sort === 'deadline' ? 'selected' : ''}>Closing soonest</option>
          <option value="title" ${P.sort === 'title' ? 'selected' : ''}>Title A–Z</option>
        </select>
      </div>
      <div id="opp-chips" class="flex flex-wrap gap-2 mb-3"></div>
      <p id="opp-count" class="text-[11px] text-[#6B7280] mb-5"></p>
      <div id="opp-results" class="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-6"></div>`);
  }

  // ───────────────────────── PAGE: Saved ─────────────────────────
  function renderSaved() {
    const items = S.opportunities.filter(o => S.savedOppIds.has(o.id));
    return shell('Your list', 'Saved', `${items.length} bookmarked ${items.length === 1 ? 'opportunity' : 'opportunities'}`, `
      <div class="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-6">
        ${items.length ? items.map(oppCard).join('')
          : emptyState('🔖', 'Nothing saved yet', 'Tap the bookmark on any opportunity to keep it here.', 'Browse opportunities', "router.navigate('opportunities')")}
      </div>`);
  }

  // ───────────────────────── PAGE: Applications ─────────────────────────
  function renderApplications() {
    const items = S.opportunities.filter(o => S.appliedOppIds.has(o.id));
    const dueSoon = items.filter(o => { const n = daysLeft(o); return n !== null && n >= 0 && n <= 31; }).length;
    const docTotals = items.reduce((a, o) => { const p = docsProgress(o); a.done += p.done; a.total += p.total; return a; }, { done: 0, total: 0 });

    const stat = (label, value) => `
      <div class="metric-stat-card">
        <p class="text-xs font-medium text-[#4B5563]">${label}</p>
        <p class="text-2xl font-bold text-[#181B28] mt-1">${value}</p>
      </div>`;

    const rows = items.map(o => {
      const p = docsProgress(o);
      const pct = p.total ? Math.round((p.done / p.total) * 100) : 0;
      const urls = window.getApplyUrls ? window.getApplyUrls(o) : { officialUrl: '#' };
      const id = esc(o.id);
      return `
        <div class="right-sidebar-card flex flex-col lg:flex-row lg:items-center gap-4">
          <div class="flex items-center gap-3 min-w-0 flex-1">
            ${window.getBrandLogoMarkup ? window.getBrandLogoMarkup(o, 'w-11 h-11 rounded-xl') : ''}
            <div class="min-w-0">
              <p class="text-sm font-bold text-[#181B28] truncate">${esc(o.title)}</p>
              <p class="text-[11px] text-[#6B7280] truncate">${esc(o.provider)} · Apply by ${esc(o.deadline)}</p>
            </div>
          </div>
          <div class="flex items-center gap-3">${daysBadge(o)}</div>
          <div class="w-full lg:w-48">
            <div class="flex justify-between text-[10px] text-[#6B7280] mb-1"><span>Documents ready</span><span class="font-semibold text-[#181B28]">${p.done}/${p.total}</span></div>
            <div class="w-full h-1.5 rounded-full bg-[#E5E7EB] overflow-hidden"><div class="h-full rounded-full bg-[#10B981]" style="width:${pct}%"></div></div>
          </div>
          <div class="flex items-center gap-2 flex-shrink-0">
            <button onclick="openDetailDrawer('${id}')" class="px-3 py-1.5 rounded-lg text-[11px] font-semibold bg-[#F3F4F6] hover:bg-[#E5E7EB] border border-[#E5E7EB] text-[#181B28] cursor-pointer">Details</button>
            <a href="${esc(urls.officialUrl)}" target="_blank" rel="noopener noreferrer" class="px-3 py-1.5 rounded-lg text-[11px] font-semibold bg-[#111625] text-white hover:bg-[#1E60D5] no-underline cursor-pointer">Open portal ↗</a>
            <button onclick="handleToggleTrackApplication('${id}')" class="px-3 py-1.5 rounded-lg text-[11px] font-semibold text-red-600 hover:bg-red-50 border border-red-200 cursor-pointer">Stop tracking</button>
          </div>
        </div>`;
    }).join('');

    return shell('Your progress', 'Applications', 'Track deadlines and document readiness for everything you have applied to.', `
      <div class="grid grid-cols-1 md:grid-cols-3 gap-6 mb-8">
        ${stat('Tracked applications', items.length)}
        ${stat('Closing within 31 days', dueSoon)}
        ${stat('Documents ready', `${docTotals.done}/${docTotals.total}`)}
      </div>
      <div class="space-y-4">
        ${items.length ? rows : `<div class="grid">${emptyState('📋', 'No applications tracked', 'Open any opportunity and choose “Track application in IRIS”.', 'Browse opportunities', "router.navigate('opportunities')")}</div>`}
      </div>`);
  }

  // ───────────────────────── PAGE: AI Assistant ─────────────────────────
  let aiCard = null, aiCardStyle = '';

  function renderAi() {
    return shell('Your co-pilot', 'AI Assistant', 'Ask about eligibility, policy conflicts, SOP drafts or scan the web for new opportunities.',
      '<div id="ai-page-host" class="max-w-4xl mx-auto"></div>');
  }

  function acquireAiCard() {
    const overlay = $('ai-modal-overlay');
    const host = $('ai-page-host');
    const card = aiCard || (overlay && overlay.firstElementChild);
    if (!card || !host) return;
    if (!aiCard) { aiCard = card; aiCardStyle = card.getAttribute('style') || ''; }
    host.appendChild(card);
    Object.assign(card.style, { maxWidth: 'none', width: '100%', height: 'calc(100vh - 180px)', maxHeight: 'none', minHeight: '520px' });
    const x = card.querySelector('button[title^="Close"]');
    if (x) x.style.display = 'none';
    window.openAiChatModal();            // refreshes banner + focuses input
    overlay.classList.add('hidden');
  }

  function releaseAiCard() {
    if (!aiCard) return;
    const overlay = $('ai-modal-overlay');
    if (aiCardStyle) aiCard.setAttribute('style', aiCardStyle); else aiCard.removeAttribute('style');
    const x = aiCard.querySelector('button[title^="Close"]');
    if (x) x.style.display = '';
    if (overlay) overlay.appendChild(aiCard);
    aiCard = null;
  }

  // ───────────────────────── PAGE: Settings ─────────────────────────
  const SETTINGS_KEY = 'iris_settings';
  const defaultPrefs = { reminders: true, matchAlerts: true, digest: false };
  function prefs() {
    try { return Object.assign({}, defaultPrefs, JSON.parse(localStorage.getItem(SETTINGS_KEY) || '{}')); }
    catch (e) { return Object.assign({}, defaultPrefs); }
  }

  function switchRow(label, desc, on, js) {
    return `
      <div class="flex items-center justify-between gap-4 py-3.5 border-b border-[#E8E2D8] last:border-0">
        <div><p class="text-xs font-semibold text-[#181B28]">${label}</p><p class="text-[11px] text-[#6B7280] mt-0.5">${desc}</p></div>
        <button type="button" role="switch" aria-checked="${on}" aria-label="${label}" onclick="${js}"
                class="relative w-10 h-5 rounded-full flex-shrink-0 cursor-pointer transition-colors ${on ? 'bg-[#1E60D5]' : 'bg-[#D1D5DB]'}">
          <span class="absolute top-0.5 ${on ? 'left-[22px]' : 'left-0.5'} w-4 h-4 rounded-full bg-white shadow transition-all"></span>
        </button>
      </div>`;
  }

  function actionRow(label, desc, btnLabel, js, danger) {
    return `
      <div class="flex items-center justify-between gap-4 py-3.5 border-b border-[#E8E2D8] last:border-0">
        <div><p class="text-xs font-semibold text-[#181B28]">${label}</p><p class="text-[11px] text-[#6B7280] mt-0.5">${desc}</p></div>
        <button type="button" onclick="${js}" class="px-3 py-1.5 rounded-lg text-[11px] font-semibold flex-shrink-0 cursor-pointer border ${danger ? 'text-red-600 border-red-200 hover:bg-red-50' : 'text-[#181B28] border-[#E5E7EB] bg-[#F3F4F6] hover:bg-[#E5E7EB]'}">${btnLabel}</button>
      </div>`;
  }

  function renderSettings() {
    const u = S.user || {};
    const p = prefs();
    const shrunk = localStorage.getItem('iris_sidebar_shrunk') === 'true';
    const card = (title, inner) => `
      <div class="right-sidebar-card" style="padding:1.25rem 1.5rem;">
        <h4 class="text-sm font-semibold text-[#181B28] mb-1">${title}</h4>${inner}
      </div>`;

    return shell('Preferences', 'Settings', 'Account, notifications and local data.', `
      <div class="max-w-3xl space-y-6">
        ${card('Account', `
          <div class="flex items-center gap-4 py-3.5 border-b border-[#E8E2D8]">
            <div class="w-12 h-12 rounded-full bg-[#1E60D5] flex items-center justify-center text-sm font-bold text-white flex-shrink-0">${esc((u.name || 'AM').split(' ').map(n => n[0]).join('').substring(0, 2).toUpperCase())}</div>
            <div class="min-w-0"><p class="text-sm font-bold text-[#181B28]">${esc(u.name || 'Student')}</p><p class="text-[11px] text-[#6B7280]">${esc(u.email || '')}</p></div>
          </div>
          ${actionRow('Profile and skills', 'Update your class, state and skills to improve matches.', 'Edit profile', "router.navigate('setup')")}
          ${actionRow('Log out', 'End this session on this device.', 'Log out', 'handleLogout()', true)}`)}

        ${card('Notifications', `
          ${switchRow('Deadline reminders', 'Show alerts when a saved or tracked opportunity is closing.', p.reminders, "IrisPages.togglePref('reminders')")}
          ${switchRow('New match alerts', 'Tell me when a new opportunity scores above 90%.', p.matchAlerts, "IrisPages.togglePref('matchAlerts')")}
          ${switchRow('Weekly email digest', 'A weekly summary of new and closing opportunities.', p.digest, "IrisPages.togglePref('digest')")}`)}

        ${card('Appearance', `
          ${switchRow('Collapse the profile sidebar', 'Give the dashboard the full width by default.', shrunk, 'IrisPages.toggleSidebar()')}
          ${actionRow('Banner theme and motto', 'Change the dashboard banner picture and your daily focus line.', 'Open Personal OS', "openBannerStudioModal()")}`)}

        ${card('Your data', `
          ${actionRow('Clear saved list', `${S.savedOppIds.size} saved on this device.`, 'Clear saved', 'IrisPages.clearSaved()', true)}
          ${actionRow('Clear tracked applications', `${S.appliedOppIds.size} tracked on this device.`, 'Clear tracked', 'IrisPages.clearApplied()', true)}
          ${actionRow('Reset everything', 'Remove saved items, tracked applications, document checks and preferences stored in this browser.', 'Reset all', 'IrisPages.resetAll()', true)}`)}
      </div>`);
  }

  // ───────────────────────── Rendering + routing ─────────────────────────
  function renderPage(r) {
    const pv = ensurePageView();
    if (!pv) return;
    releaseAiCard();                       // always put the chat card back before wiping the DOM
    const map = {
      opportunities: renderOpportunities, saved: renderSaved,
      applications: renderApplications, ai: renderAi, settings: renderSettings
    };
    pv.innerHTML = map[r] ? map[r]() : '';
    if (r === 'opportunities') updateOppResults();
    if (r === 'ai') acquireAiCard();
  }

  function applyRoute() {
    const r = routeName();
    const isSub = SUB_PAGES.includes(r);
    const pv = ensurePageView();
    if (isSub) {
      ['main-canvas', 'right-sidebar', 'profile-page'].forEach(id => { const el = $(id); if (el) el.classList.add('view-hidden'); });
    } else {
      releaseAiCard();
    }
    if (pv) pv.classList.toggle('view-hidden', !isSub);
    document.querySelectorAll('.dash-sidebar-item').forEach(i => i.classList.toggle('active', i.dataset.nav === NAV_FOR[r]));
    if (isSub) renderPage(r);
    window.scrollTo(0, 0);
  }

  const origShowScreen = router.showScreen.bind(router);
  router.showScreen = function (screenId) {
    origShowScreen(screenId);
    if (screenId === 'screen-dashboard') applyRoute();
  };

  function refresh() {
    const r = routeName();
    if (r === 'opportunities') updateOppResults();
    else if (['saved', 'applications', 'settings'].includes(r)) renderPage(r);
  }

  // ───────────────────────── Override global handlers ─────────────────────────
  // Sidebar clicks now navigate to real pages.
  window.handleNavClick = function (el, key) {
    router.navigate(key === 'home' ? 'dashboard' : key);
  };

  // Category cards / quick pills open the Opportunities page with that filter.
  window.filterByCategory = function (cat) {
    P.cat = CATS.includes(cat) ? cat : 'All';
    P.q = '';
    router.navigate('opportunities');
  };

  // "View all" links open the full Opportunities page.
  window.handleViewAllOpportunities = function () {
    P.cat = 'All'; P.q = '';
    router.navigate('opportunities');
  };

  // Keep the current page in sync after saving / tracking.
  const origSave = window.toggleSaveOpportunity;
  window.toggleSaveOpportunity = function (id) {
    return Promise.resolve(origSave(id)).then(r => { refresh(); return r; });
  };
  ['handleToggleTrackApplication', 'handleApplyOpportunity'].forEach(name => {
    const orig = window[name];
    if (typeof orig !== 'function') return;
    window[name] = function () {
      const r = orig.apply(this, arguments);
      return Promise.resolve(r).then(v => { refresh(); return v; });
    };
  });

  // AI chat: when the chat lives on the AI page, never show the popup overlay.
  const origOpenAi = window.openAiChatModal;
  window.openAiChatModal = function (id) {
    origOpenAi(id);
    if (aiCard) $('ai-modal-overlay').classList.add('hidden');
  };
  const origAsk = window.askIrisAboutOpportunity;
  window.askIrisAboutOpportunity = function (id) {
    if (aiCard) window.closeDetailDrawer();
    origAsk(id);
    if (aiCard) $('ai-modal-overlay').classList.add('hidden');
  };

  // ───────────────────────── Handlers used by page markup ─────────────────────────
  function persistSets() {
    localStorage.setItem('iris_saved_ids', JSON.stringify([...S.savedOppIds]));
    localStorage.setItem('iris_applied_ids', JSON.stringify([...S.appliedOppIds]));
    if (window.updateUserDisplay) window.updateUserDisplay();
  }

  window.IrisPages = {
    setCat(c) { P.cat = c; updateOppResults(); },
    setQuery(v) { P.q = v || ''; updateOppResults(); },
    setSort(v) { P.sort = v; updateOppResults(); },
    reset() {
      P.cat = 'All'; P.q = ''; P.sort = 'match';
      renderPage('opportunities');
    },
    togglePref(key) {
      const p = prefs(); p[key] = !p[key];
      localStorage.setItem(SETTINGS_KEY, JSON.stringify(p));
      renderPage('settings');
    },
    toggleSidebar() {
      const now = localStorage.getItem('iris_sidebar_shrunk') === 'true';
      window.toggleRightSidebarShrink(!now);
      renderPage('settings');
    },
    clearSaved() {
      S.savedOppIds.clear(); persistSets(); renderPage('settings');
      window.showToast('Saved list cleared', 'info');
    },
    clearApplied() {
      S.appliedOppIds.clear(); persistSets(); renderPage('settings');
      window.showToast('Tracked applications cleared', 'info');
    },
    resetAll() {
      if (!window.confirm('Remove all saved items, tracked applications and preferences from this browser?')) return;
      Object.keys(localStorage).forEach(k => {
        if (k.startsWith('iris_') && k !== 'iris_token') localStorage.removeItem(k);
      });
      window.location.reload();
    }
  };
})();
