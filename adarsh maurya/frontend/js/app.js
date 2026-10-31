/* IRIS onE: one router, one data store, and explicit backend actions. */
(() => {
  "use strict";

  const API_BASE = window.IRIS_API_URL || "/api";
  const $ = (id) => document.getElementById(id);
  const esc = (value) =>
    String(value ?? "").replace(
      /[&<>"']/g,
      (char) =>
        ({
          "&": "&amp;",
          "<": "&lt;",
          ">": "&gt;",
          '"': "&quot;",
          "'": "&#39;",
        })[char],
    );
  const paths = {
    medal:
      '<path d="m7 3 5 7 5-7M5 3h4l3 5 3-5h4l-5 9H10Z"/><circle cx="12" cy="16" r="5"/><path d="m12 13 1 2 2 .3-1.5 1.5.4 2.2-1.9-1-1.9 1 .4-2.2L9 15.3l2-.3Z"/>',
    home: '<path d="m3 10 9-7 9 7v10a1 1 0 0 1-1 1h-5v-7H9v7H4a1 1 0 0 1-1-1Z"/>',
    compass:
      '<circle cx="12" cy="12" r="9"/><path d="m16 8-2.5 5.5L8 16l2.5-5.5Z"/>',
    bookmark: '<path d="M6 3h12v18l-6-4-6 4Z"/>',
    briefcase:
      '<rect x="3" y="7" width="18" height="14" rx="2"/><path d="M8 7V4h8v3M3 12a22 22 0 0 0 18 0M12 11v3"/>',
    user: '<circle cx="12" cy="7" r="4"/><path d="M4 21v-2a8 8 0 0 1 16 0v2"/>',
    settings:
      '<path d="m10 3-.6 2.4-2 .9L5 5.5 3 9l1.8 1.6v2.8L3 15l2 3.5 2.4-.8 2 .9L10 21h4l.6-2.4 2-.9 2.4.8 2-3.5-1.8-1.6v-2.8L21 9l-2-3.5-2.4.8-2-.9L14 3Z"/><circle cx="12" cy="12" r="3"/>',
    sparkle:
      '<path d="m12 3 2.6 6.4L21 12l-6.4 2.6L12 21l-2.6-6.4L3 12l6.4-2.6Z"/><path d="m20 2 .6 1.4L22 4l-1.4.6L20 6l-.6-1.4L18 4l1.4-.6Z"/>',
    search: '<circle cx="10.5" cy="10.5" r="6.5"/><path d="m16 16 4.5 4.5"/>',
    bell: '<path d="M18 8a6 6 0 0 0-12 0c0 7-3 7-3 9h18c0-2-3-2-3-9M10 21h4"/>',
    down: '<path d="m6 9 6 6 6-6"/>',
    right: '<path d="m9 5 7 7-7 7"/>',
    left: '<path d="m15 5-7 7 7 7"/>',
    arrow: '<path d="M4 12h16m-6-6 6 6-6 6"/>',
    external: '<path d="M14 3h7v7M21 3 10 14M10 3H4v17h17v-6"/>',
    close: '<path d="m6 6 12 12M6 18 18 6"/>',
    menu: '<path d="M4 6h16M4 12h16M4 18h16"/>',
    calendar:
      '<rect x="3" y="5" width="18" height="16" rx="2"/><path d="M7 2v6M17 2v6M3 11h18"/>',
    cap: '<path d="m2 9 10-5 10 5-10 5Z"/><path d="M6 11v6c4 3 8 3 12 0v-6M22 9v7"/>',
    globe:
      '<circle cx="12" cy="12" r="9"/><ellipse cx="12" cy="12" rx="4" ry="9"/><path d="M3 12h18"/>',
    code: '<path d="m7 6-6 6 6 6m10-12 6 6-6 6M14 3l-4 18"/>',
    trophy:
      '<path d="M7 3h10v5c0 5-2 7-5 7S7 13 7 8ZM7 5H3v3a4 4 0 0 0 5 4M17 5h4v3a4 4 0 0 1-5 4M12 15v5M7 21h10"/>',
    gift: '<rect x="3" y="8" width="18" height="4" rx="1"/><path d="M5 12v9h14v-9M12 8v13M12 8H7a3 3 0 1 1 3-3l2 3Zm0 0h5a3 3 0 1 0-3-3Z"/>',
    document: '<path d="M6 2h8l4 4v16H6ZM14 2v5h4M9 12h6M9 16h6"/>',
    shield:
      '<path d="m12 2 8 4v6c0 5-8 10-8 10S4 17 4 12V6Z"/><path d="m8 12 3 3 5-6"/>',
    check: '<path d="m5 12 4 4L20 5"/>',
    checkCircle: '<circle cx="12" cy="12" r="9"/><path d="m8 12 3 3 5-6"/>',
    info: '<circle cx="12" cy="12" r="9"/><path d="M12 11v6M12 7h.01"/>',
    location:
      '<path d="M19 10c0 5-7 12-7 12S5 15 5 10a7 7 0 0 1 14 0Z"/><circle cx="12" cy="10" r="2.5"/>',
    upload: '<path d="M12 16V3m-5 5 5-5 5 5M4 15v6h16v-6"/>',
    download: '<path d="M12 3v13m-5-5 5 5 5-5M4 16v5h16v-5"/>',
    star: '<path d="m12 3 2.8 5.7 6.2.9-4.5 4.4 1.1 6.2-5.6-3-5.6 3 1.1-6.2L3 9.6l6.2-.9Z"/>',
    chart: '<path d="M5 20v-5M12 20V9M19 20V3"/>',
    filter: '<path d="M4 6h16M7 12h10M10 18h4"/>',
    clock: '<circle cx="12" cy="12" r="9"/><path d="M12 6v6l4 2"/>',
    refresh:
      '<path d="M20 7a9 9 0 0 0-15-2L3 8m0-5v5h5M4 17a9 9 0 0 0 15 2l2-3m0 5v-5h-5"/>',
    lock: '<rect x="5" y="10" width="14" height="11" rx="2"/><path d="M8 10V6a4 4 0 0 1 8 0v4M12 14v3"/>',
    logout: '<path d="M9 3H4v18h5M10 12h11m-4-4 4 4-4 4"/>',
    send: '<path d="m22 2-7 20-4-9L2 9ZM22 2 11 13"/>',
    trash: '<path d="M3 6h18M9 6V3h6v3M6 6l1 15h10l1-15M10 10v7M14 10v7"/>',
    plus: '<path d="M12 4v16M4 12h16"/>',
    stop: '<rect x="6" y="6" width="12" height="12" rx="1"/>',
  };
  const icon = (name, classes = "") =>
    `<svg class="icon ${classes}" viewBox="0 0 24 24" aria-hidden="true">${paths[name] || paths.document}</svg>`;
  const parseJSON = (value, fallback = []) => {
    try {
      return typeof value === "string"
        ? (JSON.parse(value || "null") ?? fallback)
        : (value ?? fallback);
    } catch {
      return fallback;
    }
  };
  const safeURL = (value) => {
    try {
      const url = new URL(value);
      return ["https:", "http:"].includes(url.protocol) ? url.href : "";
    } catch {
      return "";
    }
  };
  const dateFormat = (
    value,
    options = { month: "short", day: "numeric", year: "numeric" },
  ) => {
    if (!value) return "Not confirmed";
    const date = new Date(
      String(value).length === 10 ? `${value}T12:00:00+05:30` : value,
    );
    return Number.isNaN(date.getTime())
      ? "Not confirmed"
      : new Intl.DateTimeFormat("en-IN", {
          timeZone: "Asia/Kolkata",
          ...options,
        }).format(date);
  };
  const todayISO = () =>
    new Intl.DateTimeFormat("en-CA", {
      timeZone: "Asia/Kolkata",
      year: "numeric",
      month: "2-digit",
      day: "2-digit",
    }).format(new Date());
  const currentCalendar = () => {
    const [year, month] = todayISO().split("-").map(Number);
    return { year, month: month - 1, selected: null };
  };
  const S = {
    token: localStorage.getItem("iris_token") || "",
    user: null,
    profile: null,
    opportunities: [],
    saved: [],
    applications: [],
    sync: null,
    config: null,
    ready: false,
    error: "",
    loading: false,
    loadVersion: 0,
    view: "home",
    detailId: null,
    detail: null,
    guides: new Map(),
    filter: {
      category: "All Opportunities",
      query: "",
      location: "",
      deadline: "",
      sort: "match",
    },
    applicationFilter: "All",
    calendar: currentCalendar(),
    wizard: null,
    wizardStep: 1,
    authMode: "login",
    chat: [],
    chatBusy: false,
    chatController: null,
    chatFocus: null,
    chatStatus: "",
    modalId: null,
    modalVersion: 0,
    documentDrafts: new Map(),
    documentTimer: null,
    documentQueue: Promise.resolve(),
  };
  class ApiError extends Error {
    constructor(message, status) {
      super(message);
      this.status = status;
    }
  }
  async function api(endpoint, options = {}) {
    const controller = new AbortController();
    const timer = setTimeout(
      () => controller.abort(),
      options.timeout || 25000,
    );
    const isForm = options.body instanceof FormData;
    try {
      const response = await fetch(`${API_BASE}${endpoint}`, {
        ...options,
        signal: options.signal || controller.signal,
        headers: {
          ...(isForm ? {} : { "Content-Type": "application/json" }),
          ...(S.token ? { Authorization: `Bearer ${S.token}` } : {}),
          ...options.headers,
        },
      });
      if (!response.ok) {
        const error = await response.json().catch(() => ({}));
        const detail = Array.isArray(error.detail)
          ? error.detail.map((item) => item.msg).join("; ")
          : error.detail;
        throw new ApiError(
          detail || `This request could not be completed (${response.status}).`,
          response.status,
        );
      }
      return options.raw ? response : await response.json();
    } catch (error) {
      if (error instanceof ApiError) throw error;
      if (error.name === "AbortError")
        throw new ApiError("The request took too long. Please try again.", 408);
      throw new ApiError(
        "We could not reach the IRIS server. Check your connection and try again.",
        0,
      );
    } finally {
      clearTimeout(timer);
    }
  }
  const post = (endpoint, body = {}, options = {}) =>
    api(endpoint, { method: "POST", body: JSON.stringify(body), ...options });
  const idOf = (opp) => String(opp.slug || opp.id);
  const initials = (name) =>
    String(name || "Student")
      .trim()
      .split(/\s+/)
      .map((word) => word[0])
      .slice(0, 2)
      .join("")
      .toUpperCase();
  const profileName = () => S.profile?.name || S.user?.name || "Student";
  const categories = [
    "All Opportunities",
    "Scholarships",
    "Internships",
    "Competitions",
    "Hackathons",
    "Student Offers",
    "Olympiads",
    "International",
  ];
  const categoryIcons = {
    "All Opportunities": "compass",
    Scholarships: "cap",
    Internships: "briefcase",
    Competitions: "trophy",
    Hackathons: "code",
    "Student Offers": "gift",
    Olympiads: "medal",
    International: "globe",
  };
  const categoryDescriptions = {
    Scholarships: "Tuition support and financial aid.",
    Internships: "Real experience. New possibilities.",
    Hackathons: "Build, collaborate, and make an impact.",
    Competitions: "Put your ideas and skills to the test.",
    "Student Offers": "Tools, credits, and a little extra support.",
    Olympiads: "Challenge yourself and celebrate what you know.",
    International: "Discover a world beyond your campus.",
  };
  function categoryOf(opp) {
    const value =
      `${opp.category || ""} ${opp.type || ""} ${opp.title || ""}`.toLowerCase();
    if (value.includes("olympiad")) return "Olympiads";
    if (value.includes("hackathon")) return "Hackathons";
    if (value.includes("scholar") || value.includes("grant"))
      return "Scholarships";
    if (value.includes("intern")) return "Internships";
    if (value.includes("offer") || value.includes("free_"))
      return "Student Offers";
    return "Competitions";
  }
  function isInternational(opp) {
    return /international|germany|europe|united states|united kingdom|canada|daad|global/i.test(
      `${opp.title || ""} ${opp.location || ""}`,
    );
  }
  function deadline(opp) {
    const iso = String(opp.deadline_iso || opp.deadline || "").slice(0, 10);
    if (!/^\d{4}-\d{2}-\d{2}$/.test(iso))
      return { iso: "", days: null, label: "Check official portal" };
    const days = Math.round(
      (Date.parse(`${iso}T00:00:00Z`) - Date.parse(`${todayISO()}T00:00:00Z`)) /
        86400000,
    );
    return {
      iso,
      days,
      label:
        days < 0
          ? "Past deadline"
          : days === 0
            ? "Due today"
            : `${days} days left`,
    };
  }
  function verification(status) {
    return (
      {
        VERIFIED_LIVE: ["Verified recently", "green"],
        PREVIOUSLY_VERIFIED: ["Previously verified", "gold"],
        VERIFICATION_PENDING: ["Verification pending", "neutral"],
        COULD_NOT_VERIFY: ["Could not verify", "gold"],
        ARCHIVED: ["Archived", "neutral"],
        SEEDED_CACHE: ["From the catalog", "neutral"],
        CACHE_ONLY: ["Cached information", "gold"],
        EXPIRED: ["Past deadline", "red"],
        CLOSED: ["Applications closed", "red"],
      }[status] || ["Cached information", "neutral"]
    );
  }
  const scoreOf = (opp) =>
    Math.round(opp.match_score ?? opp.match?.overall ?? 0);
  const findOpp = (id) =>
    [...S.opportunities, ...S.saved, ...S.applications].find(
      (opp) => idOf(opp) === String(id),
    ) ||
    (S.detail && idOf(S.detail.opportunity) === String(id)
      ? S.detail.opportunity
      : null);
  function mark(opp, large = false) {
    const name = String(
      opp.organization || opp.provider || opp.title || "",
    ).toLowerCase();
    let kind = "",
      content = esc(
        initials(opp.organization || opp.provider || opp.title).slice(0, 1),
      );
    if (name.includes("microsoft")) {
      kind = "microsoft";
      content = "<i></i><i></i><i></i><i></i>";
    } else if (name.includes("google")) {
      kind = "google";
      content = "G";
    } else if (name.includes("github")) {
      kind = "github";
      content = icon("code");
    } else if (name.includes("adobe")) {
      kind = "adobe";
      content = "A";
    } else if (name.includes("reliance")) content = icon("star");
    else if (name.includes("bharti") || name.includes("airtel")) {
      content = "a";
      kind = "adobe";
    }
    return `<span class="brand-mark ${kind} ${large ? "large" : ""}" aria-hidden="true">${content}</span>`;
  }
  function pill(text, color = "neutral", symbol = "") {
    return `<span class="pill ${color}">${symbol ? icon(symbol) : ""}${esc(text)}</span>`;
  }
  function empty(title, copy, action = "", label = "", symbol = "compass") {
    return `<div class="surface empty-state"><div class="empty-icon">${icon(symbol, "icon-lg")}</div><h3>${esc(title)}</h3><p>${esc(copy)}</p>${action ? `<button class="button primary" data-action="${esc(action)}">${esc(label)}${icon("arrow")}</button>` : ""}</div>`;
  }
  const heading = (view, eyebrow, title, copy, action = "") =>
    `<div class="page-heading"><div><span class="eyebrow">${esc(eyebrow)}</span><h1 id="${view}-heading">${esc(title)}</h1><p>${esc(copy)}</p></div>${action}</div>`;
  function toast(message, type = "success") {
    const el = document.createElement("div");
    el.className = `toast ${type === "error" ? "error" : ""}`;
    el.setAttribute("role", type === "error" ? "alert" : "status");
    el.innerHTML = `${icon(type === "error" ? "info" : "checkCircle")}<span>${esc(message)}</span><button class="icon-button" aria-label="Dismiss notification">${icon("close")}</button>`;
    el.querySelector("button").addEventListener("click", () => el.remove());
    $("toast-container").replaceChildren(el);
    setTimeout(() => el.remove(), type === "error" ? 8500 : 4500);
  }
  function updateShell() {
    document.body.classList.toggle("is-home", S.view === "home");
    const navigation = [
      ["home", "home", "Home"],
      ["opportunities", "compass", "Opportunities"],
      ["saved", "bookmark", "Saved"],
      ["applications", "briefcase", "Applications"],
      ["profile", "user", "Profile"],
      ["ai-assistant", "sparkle", "AI Assistant"],
      ["settings", "settings", "Settings"],
    ];
    $("primary-navigation").innerHTML = navigation
      .map(
        ([view, symbol, label]) =>
          `<a href="#${view}" class="nav-link ${S.view === view || (S.view === "detail" && view === "opportunities") || (S.view === "onboarding" && view === "profile") ? "active" : ""}" ${S.view === view ? 'aria-current="page"' : ""}>${icon(symbol)}<span>${label}</span>${view === "saved" && S.saved.length ? `<span class="nav-count">${S.saved.length}</span>` : ""}</a>`,
      )
      .join("");
    const firstName = profileName().split(" ")[0];
    $("sidebar-user-name").textContent = profileName();
    $("sidebar-user-detail").textContent =
      S.profile?.institution ||
      (S.user
        ? "Student workspace"
        : S.config?.is_simulated
          ? "Demo workspace"
          : "Private guest workspace");
    $("header-user-name").textContent = firstName;
    $("header-avatar").textContent = initials(profileName());
    $("sidebar-avatar").textContent = initials(profileName());
    $("header-location").textContent =
      {
        home: "Your overview",
        opportunities: "Discover your next step",
        saved: "Your shortlist",
        applications: "Your progress, together",
        profile: "Your personal space",
        detail: "Opportunity overview",
        "ai-assistant": "A little guidance goes a long way",
        settings: "Make IRIS your own",
        onboarding: "Let’s get to know you",
        login: "Welcome to IRIS onE",
      }[S.view] || "Your workspace";
    $("sidebar-sync-label").textContent = S.sync?.sync_running
      ? "Catalog sync in progress"
      : "Catalog refreshes every 12h";
    const prefs = S.profile?.preferences || {};
    document.body.classList.toggle("reduce-motion", !!prefs.reduce_motion);
    document.body.classList.toggle("compact-cards", !!prefs.compact_cards);
    $("account-popover").innerHTML =
      `<a href="#profile">${icon("user")}Your profile</a><a href="#onboarding/1">${icon("cap")}Edit your details</a><a href="#settings">${icon("settings")}Preferences</a>${S.token ? `<button data-action="logout">${icon("logout")}Sign out</button>` : `<a href="#login">${icon("lock")}Sign in / create account</a>`}`;
  }
  function card(opp) {
    const id = idOf(opp),
      category = categoryOf(opp),
      saved = S.saved.some((item) => idOf(item) === id);
    const due = deadline(opp),
      status = verification(opp.verification_status);
    const color =
      category === "Scholarships"
        ? "green"
        : category === "Student Offers" || category === "Internships"
          ? "blue"
          : "purple";
    return `<article class="surface opportunity-card" data-action="open-detail" data-id="${esc(id)}" tabindex="0" role="link" aria-label="View ${esc(opp.title)}">
      <div class="card-top">${mark(opp)}<button class="bookmark-button ${saved ? "saved" : ""}" data-action="save" data-id="${esc(id)}" aria-label="${saved ? "Unsave" : "Save"} ${esc(opp.title)}" aria-pressed="${saved}">${icon("bookmark")}</button></div>
      <div class="card-category">${pill(category === "Scholarships" ? "Scholarship" : category === "Internships" ? "Internship" : category, color, categoryIcons[category])}</div>
      <h3>${esc(opp.title)}</h3><p class="card-provider">${esc(opp.organization || opp.provider)} <span aria-hidden="true">·</span> ${esc(opp.location || opp.location_state || "Online")}</p>
      <p class="card-description">${esc(opp.description || "Explore the official program details and eligibility requirements.")}</p>
      <p class="card-benefit">${esc(opp.benefit_summary || opp.financial_value_label || opp.amount || "See program benefits")}</p>
      <div class="card-meta"><span>${icon("calendar")}${esc(due.iso ? dateFormat(due.iso, { month: "short", day: "numeric" }) : "Check portal")}</span><span class="match-value">${icon("chart")}${scoreOf(opp)}% match</span></div>
      <div class="card-footer"><a href="#detail/${encodeURIComponent(id)}">View opportunity ${icon("arrow")}</a>${S.profile?.preferences?.show_verification === false ? "" : `<span class="card-verified">${icon(opp.verification_status === "VERIFIED_LIVE" ? "shield" : "clock")}${esc(status[0])}</span>`}</div>
    </article>`;
  }
  function upcoming(items = S.applications) {
    return items
      .filter((opp) => deadline(opp).days !== null && deadline(opp).days >= 0)
      .sort((a, b) => deadline(a).days - deadline(b).days);
  }
  function metric(value, label, symbol, view) {
    return `<a href="#${view}" class="surface metric-card"><span class="metric-icon">${icon(symbol)}</span><span><span class="metric-value">${esc(value)}</span><span class="metric-caption" style="display:block">${esc(label)}</span></span></a>`;
  }
  function homeFeatureCard(opp) {
    const id = idOf(opp),
      due = deadline(opp);
    return `<article class="featured-opportunity" data-action="open-detail" data-id="${esc(id)}" tabindex="0" role="link" aria-label="View ${esc(opp.title)}">
      <div class="featured-head">${mark(opp)}<div class="featured-copy"><h3>${esc(opp.title)}</h3><p>${esc(opp.organization || opp.provider || "Official program")}</p></div><span class="featured-match" title="Profile compatibility, not selection probability">${icon("sparkle")}${scoreOf(opp)}% Match</span></div>
      <div class="featured-meta"><span>${icon("calendar")}${due.iso ? esc(dateFormat(due.iso)) : "Deadline not confirmed"}</span><span>${icon("location")}${esc(opp.mode || opp.location || opp.location_state || "See official portal")}</span><span class="featured-provenance">${esc(verification(opp.verification_status)[0])}</span></div>
    </article>`;
  }
  function renderHome() {
    const domains = S.profile?.domains || [];
    const interested = S.opportunities.filter(
      (opp) =>
        !domains.length ||
        domains.includes(categoryOf(opp)) ||
        (domains.includes("International") && isInternational(opp)),
    );
    const top = [...(interested.length ? interested : S.opportunities)]
      .sort((a, b) => scoreOf(b) - scoreOf(a))
      .slice(0, 2);
    const shortcuts = [
      ["Hackathons", "code"],
      ["Scholarships", "cap"],
      ["Internships", "briefcase"],
      ["Competitions", "trophy"],
      ["Student Offers", "gift"],
      ["Olympiads", "medal"],
      ["AI Assistant", "sparkle"],
    ];
    $("view-home").innerHTML =
      `<section class="home-hero" aria-labelledby="home-heading">
      <div class="home-hero-art" aria-hidden="true"><svg viewBox="668 76 365 257" preserveAspectRatio="xMidYMid slice" focusable="false"><image href="assets/homepage-reference.png" x="0" y="0" width="1046" height="690" /></svg></div>
      <div class="home-hero-copy"><span class="home-eyebrow">YOUR OPPORTUNITY COMPANION</span><h1 id="home-heading"><span>Discover. Apply.</span> <em>Grow.</em></h1><p>A personalized platform to discover scholarships, internships, hackathons and opportunities that fit you.</p>
      <form id="home-search-form" class="home-search" role="search"><label class="sr-only" for="home-search-input">Search opportunities, skills or organizations</label>${icon("search")}<input id="home-search-input" type="search" placeholder="Search opportunities, skills or organizations..." autocomplete="off" maxlength="200" /><button type="submit" aria-label="Search opportunities">${icon("search")}</button></form></div></section>
      <nav class="home-categories" aria-label="Opportunity categories">${shortcuts.map(([category, symbol], index) => `<button type="button" data-action="home-category" data-category="${category}" class="home-category category-tone-${index % 3}">${icon(symbol)}<span>${category}</span></button>`).join("")}</nav>
      <section class="home-featured" aria-labelledby="home-featured-heading"><div class="home-section-heading"><h2 id="home-featured-heading">Top opportunities for you</h2><a href="#opportunities">View all ${icon("arrow")}</a></div><div class="home-featured-grid">${top.map(homeFeatureCard).join("") || empty("Your next opportunity starts here", "Add your interests or explore the catalog to discover a possibility that fits you.", "explore", "Explore opportunities")}</div></section>`;
  }
  function filteredOpportunities() {
    const f = S.filter;
    const result = S.opportunities.filter((opp) => {
      if (
        f.category !== "All Opportunities" &&
        (f.category === "International"
          ? !isInternational(opp)
          : categoryOf(opp) !== f.category)
      )
        return false;
      if (
        f.query &&
        !`${opp.title} ${opp.organization || opp.provider} ${opp.description || ""} ${opp.tags || ""}`
          .toLowerCase()
          .includes(f.query.toLowerCase())
      )
        return false;
      if (
        f.location &&
        !`${opp.location || ""} ${opp.mode || ""} ${opp.location_state || ""}`
          .toLowerCase()
          .includes(f.location.toLowerCase())
      )
        return false;
      if (
        f.deadline &&
        (deadline(opp).days === null ||
          deadline(opp).days < 0 ||
          deadline(opp).days > Number(f.deadline))
      )
        return false;
      return true;
    });
    return result.sort((a, b) =>
      f.sort === "deadline"
        ? (deadline(a).days ?? 99999) - (deadline(b).days ?? 99999)
        : f.sort === "value"
          ? (b.amount_inr || b.estimated_value_inr || 0) -
            (a.amount_inr || a.estimated_value_inr || 0)
          : f.sort === "title"
            ? a.title.localeCompare(b.title)
            : scoreOf(b) - scoreOf(a),
    );
  }
  function renderResults() {
    if (!$("opportunity-results")) return;
    const items = filteredOpportunities();
    $("opportunity-results").innerHTML =
      items.map(card).join("") ||
      empty(
        "A fresh perspective might help",
        "Try another category, broaden your search, or clear a filter to see more opportunities.",
        "clear-filters",
        "Clear filters",
        "search",
      );
    $("opportunity-count").textContent =
      `${items.length} ${items.length === 1 ? "opportunity" : "opportunities"}`;
    document.querySelectorAll("[data-category]").forEach((button) => {
      const active = button.dataset.category === S.filter.category;
      button.classList.toggle("active", active);
      button.setAttribute("aria-pressed", String(active));
    });
    if ($("category-filter")) $("category-filter").value = S.filter.category;
  }
  function renderOpportunities() {
    $("view-opportunities").innerHTML =
      `${heading("opportunities", "EXPLORE & DISCOVER", "Your next opportunity is out there.", "Scholarships, internships, and experiences — thoughtfully gathered for where you want to go.")}
      <form id="opportunity-search-form" class="search-bar" role="search">${icon("search")}<input id="opportunity-search" type="search" value="${esc(S.filter.query)}" placeholder="Search opportunities, organizations, or a little inspiration…" aria-label="Search opportunities" autocomplete="off" /><button class="button primary" type="submit">Search ${icon("arrow")}</button></form>
      <div class="category-pills" aria-label="Opportunity categories">${categories.map((category) => `<button class="category-pill ${S.filter.category === category ? "active" : ""}" data-action="category" data-category="${esc(category)}" aria-pressed="${S.filter.category === category}">${icon(categoryIcons[category])}${category}</button>`).join("")}</div>
      <div class="filter-toolbar"><label class="select-wrap">${icon("filter")}<span class="sr-only">Category</span><select id="category-filter">${categories.map((category) => `<option value="${esc(category)}" ${category === S.filter.category ? "selected" : ""}>${category === "All Opportunities" ? "All categories" : category}</option>`).join("")}</select></label>
      <label class="select-wrap">${icon("location")}<span class="sr-only">Location</span><select id="location-filter"><option value="">All locations</option>${["Online", "Remote", "India", "Delhi", "Germany"].map((location) => `<option ${S.filter.location === location ? "selected" : ""}>${location}</option>`).join("")}</select></label>
      <label class="select-wrap">${icon("calendar")}<span class="sr-only">Deadline</span><select id="deadline-filter"><option value="">Any deadline</option>${[
        [7, "Within 7 days"],
        [30, "Within 30 days"],
        [90, "Within 90 days"],
      ]
        .map(
          ([value, label]) =>
            `<option value="${value}" ${S.filter.deadline === String(value) ? "selected" : ""}>${label}</option>`,
        )
        .join("")}</select></label>
      <label class="select-wrap">${icon("chart")}<span class="sr-only">Sort opportunities</span><select id="sort-filter">${[
        ["match", "Most relevant"],
        ["deadline", "Closing soon"],
        ["value", "Highest benefit"],
        ["title", "A to Z"],
      ]
        .map(
          ([value, label]) =>
            `<option value="${value}" ${S.filter.sort === value ? "selected" : ""}>${label}</option>`,
        )
        .join("")}</select></label>
      <button class="clear-filters" data-action="clear-filters">Reset</button><span id="opportunity-count" class="filter-count" aria-live="polite"></span></div><div id="opportunity-results" class="opportunity-grid"></div>`;
    renderResults();
  }
  function renderSaved() {
    $("view-saved").innerHTML =
      `${heading("saved", "A LITTLE LATER, A LITTLE CLOSER", "Good things, kept close.", "Your shortlist of possibilities. Come back when you’re ready to take the next step.", '<a href="#opportunities" class="button secondary">Explore more ' + icon("arrow") + "</a>")}
      <div class="results-heading"><span>${S.saved.length} saved ${S.saved.length === 1 ? "opportunity" : "opportunities"}</span><span>Saved to your IRIS profile</span></div><div class="opportunity-grid">${S.saved.map(card).join("") || empty("Keep a little possibility for later", "Tap the bookmark on any opportunity to add it to your shortlist.", "explore", "Find an opportunity", "bookmark")}</div>`;
  }

  function gateRows(opp, guide) {
    return (guide.eligibility_checklist || []).map((item) => [
      item.pass,
      item.detail,
    ]);
  }

  function policyMarkup(guide) {
    return `<div class="policy-banner ${guide.conflict_warning ? "conflict" : ""}"><strong>${icon("shield")}Policy Conflict Shield</strong>${esc(guide.conflict_warning || (guide.is_exclusive_tuition_grant ? "Exclusive tuition support. Check non-duplication rules before accepting another tuition award." : /offer|perk/i.test(guide.category || "") ? "Stackable non-tuition benefit in the cached policy. Confirm current offer terms and availability." : "No exclusive tuition restriction is recorded in the cache. Review the official terms before combining awards."))}</div>`;
  }
  function renderDetail() {
    const content = S.detail;
    if (!content || idOf(content.opportunity) !== S.detailId) {
      $("view-detail").innerHTML =
        '<div class="loading-state"><span class="spinner"></span>Getting to know this opportunity…</div>';
      return;
    }
    const { opportunity: opp, guide } = content;
    const category = categoryOf(opp),
      due = deadline(opp),
      status = verification(guide.verification_status),
      score = Number(guide.match_score) || 0;
    const factors = [
      ["academic", "Academic fit", 35],
      ["domicile", "Location fit", 25],
      ["skills", "Skills & interests", 25],
      ["gates", "Eligibility gates", 15],
    ];
    const trace = parseJSON(opp.verification_log_json);
    const traceRows = Array.isArray(trace) ? trace : [];
    $("view-detail").innerHTML =
      `<a href="#opportunities" class="detail-back">${icon("left")}Back to opportunities</a>
      <div class="detail-hero"><div>${pill(category === "Scholarships" ? "Scholarship" : category, category === "Scholarships" ? "green" : "blue", categoryIcons[category])}<h1 id="detail-heading">${esc(opp.title)}</h1><div class="detail-provider">${icon("cap", "icon-sm")}${esc(opp.organization || opp.provider)} <span>·</span> ${esc(opp.location || opp.location_state || "Online")}</div><p style="margin-top:15px">${esc(opp.description || guide.benefit_summary)}</p><div class="button-row"><button class="button primary" data-action="apply" data-id="${esc(idOf(opp))}">Apply Now ${icon("arrow")}</button><button class="button secondary" data-action="save" data-id="${esc(idOf(opp))}" aria-pressed="${S.saved.some((item) => idOf(item) === idOf(opp))}">${icon("bookmark")}${S.saved.some((item) => idOf(item) === idOf(opp)) ? "Saved to your shortlist" : "Save for later"}</button></div></div><div class="detail-art">${mark(opp, true)}</div></div>
      <div class="intelligence-grid"><section class="surface intelligence-card"><h3>${icon("chart")}A fit for your potential</h3><div class="match-ring-row"><div class="match-ring"><svg viewBox="0 0 100 100" aria-hidden="true"><circle cx="50" cy="50" r="43"/><circle class="ring-value" cx="50" cy="50" r="43" stroke-dasharray="270.177" stroke-dashoffset="${270.177 * (1 - Math.min(100, score) / 100)}"/></svg><span>${Math.round(score)}%<small>PROFILE MATCH</small></span></div><div class="match-summary"><strong>${score >= 85 ? "A promising match" : score >= 65 ? "Room to explore" : "Take a closer look"}</strong><p>Profile compatibility.<br />Not selection odds.</p></div></div>${factors.map(([key, label, max]) => `<div class="factor"><span>${label}</span><b>${guide.match_breakdown?.[key] ?? 0} / ${max}</b></div>`).join("")}</section>
      <section class="surface intelligence-card"><h3>${icon("checkCircle")}Eligibility, made clearer</h3>${pill({ confirmed_eligible: "Confirmed eligible", likely_eligible: "Likely eligible", requires_information: "Requires additional information", not_eligible: "Not eligible" }[guide.eligibility_status] || "Requires additional information", guide.eligible ? "green" : "gold")}${gateRows(
        opp,
        guide,
      )
        .map(
          ([pass, label]) =>
            `<div class="eligibility-row ${pass === true ? "" : pass === false ? "failed" : "unknown"}">${icon(pass === true ? "checkCircle" : "info")}<span>${esc(label)}</span></div>`,
        )
        .join("")}${policyMarkup(guide)}</section>
      <section class="surface intelligence-card"><h3>${icon("shield")}A little peace of mind</h3>${pill(status[0], status[1], guide.verification_status === "VERIFIED_LIVE" ? "shield" : "clock")}<p class="verification-copy">${guide.last_verified_at ? "A previous portal check is recorded. Use the badge and timestamp to judge its freshness." : "Program information is available in the catalog. A live application check has not been confirmed."}</p><p class="verification-date">${guide.last_verified_at ? `Last live check ${dateFormat(guide.last_verified_at, { day: "numeric", month: "short", hour: "numeric", minute: "2-digit" })}` : guide.last_checked_at ? `Cache checked ${dateFormat(guide.last_checked_at, { day: "numeric", month: "short" })}` : "Background catalog refresh · every 12 hours"}</p><button id="detail-verify-button" class="button secondary small" data-action="verify" data-id="${esc(idOf(opp))}">Verify now ${icon("external")}</button></section></div>
      <div class="detail-bottom"><section class="surface overview-card"><h2>A closer look</h2><p>${esc(opp.description || guide.benefit_summary)}</p><h3>What this could mean for you</h3><p>${esc(guide.benefit_summary || "See the current program benefits and conditions on the official portal.")}</p><h3>Your first few steps</h3>${(
        guide.how_to_apply_steps || []
      )
        .slice(0, 3)
        .map(
          (step) =>
            `<div class="step-preview"><span class="step-number">${esc(step.step)}</span><div><strong>${esc(step.title)}</strong><p>${esc(step.detail)}</p></div></div>`,
        )
        .join(
          "",
        )}<div class="button-row" style="margin-top:22px"><button class="button secondary small" data-action="apply" data-id="${esc(idOf(opp))}">See the full application guide ${icon("arrow")}</button><button class="text-link" style="border:0;background:none" data-action="ask-opportunity" data-id="${esc(idOf(opp))}">Ask IRIS about this ${icon("sparkle", "icon-sm")}</button></div></section>
      <aside class="surface key-details"><h2>The essentials</h2><dl>${[
        [
          "calendar",
          "Application deadline",
          due.iso ? dateFormat(due.iso) : "Confirm on the portal",
        ],
        [
          "gift",
          "Benefit",
          guide.benefit_summary || opp.amount || "See official terms",
        ],
        [
          "location",
          "Location",
          opp.location || opp.location_state || "Not specified",
        ],
        ["globe", "Mode", opp.mode || "See official portal"],
        ["cap", "Category", category],
        [
          "document",
          "Documents",
          `${guide.required_documents.length} items to prepare`,
        ],
      ]
        .map(
          ([symbol, label, value]) =>
            `<div class="detail-pair"><dt>${icon(symbol)}${label}</dt><dd>${esc(value)}</dd></div>`,
        )
        .join(
          "",
        )}</dl>${safeURL(guide.rules_pdf_url) ? `<div class="divider"></div><a href="${esc(safeURL(guide.rules_pdf_url))}" target="_blank" rel="noopener noreferrer" class="text-link">Read the official rules ${icon("external", "icon-sm")}</a>` : ""}<p class="text-small muted" style="font-size:12px;margin-top:20px;line-height:1.9">${esc(guide.verification_note)}</p></aside></div>`;
  }
  function renderProfile() {
    const p = S.profile || {},
      skills = p.skills || [],
      domains = p.domains || [];
    const field = (label, value) =>
      `<dl><dt>${label}</dt><dd>${esc(value || "Add your details")}</dd></dl>`;
    $("view-profile").innerHTML =
      `<div class="profile-container">${heading("profile", "YOUR PERSONAL SPACE", "Your space, your opportunities.", "A little about you helps us find a little more for you.")}
      <div class="surface profile-card"><div class="profile-summary"><span class="avatar">${esc(initials(p.name))}</span><div><h2>${esc(p.name || "Your profile")}</h2>${pill(p.institution || "Your academic journey", "blue", "cap")}</div><a href="#onboarding/1" class="button secondary">${icon("user")}Edit profile</a></div>
      <div class="profile-completion"><div class="completion-label"><span>Profile completeness</span><b>${p.profile_completeness || 0}%</b></div><div class="progress" role="progressbar" aria-label="Profile completeness" aria-valuenow="${p.profile_completeness || 0}" aria-valuemin="0" aria-valuemax="100"><span style="width:${p.profile_completeness || 0}%"></span></div></div>
      <section class="profile-section"><div class="profile-section-heading">${icon("cap")}<h3>Academic details</h3></div><div class="profile-data-grid">${field("Class / Degree", (p.academic_stage || "").split("•")[0].trim())}${field("University / Institution", p.institution)}${field("Graduation year", p.graduation_year)}${field("Age", p.age)}</div></section>
      <section class="profile-section"><div class="profile-section-heading">${icon("location")}<h3>A sense of place</h3></div><div class="profile-data-grid">${field("City / State", p.state_domicile)}${field("Country", p.country)}</div></section>
      <section class="profile-section"><div class="profile-section-heading">${icon("chart")}<h3>Skills & interests</h3></div><div class="skill-tags">${skills.length ? skills.map((skill) => `<span class="skill-tag">${esc(skill)}</span>`).join("") : '<span class="muted text-small">A blank canvas. Add what you’re good at.</span>'}</div>${domains.length ? `<div class="skill-tags" style="margin-top:13px">${domains.map((domain) => pill(domain, "gold")).join("")}</div>` : ""}</section>
      <section class="profile-section"><div class="profile-section-heading">${icon("document")}<h3>Your resume</h3></div><div class="resume-bar" data-dropzone>${icon("document", "resume-icon")}<div><strong>${esc(p.resume_filename || "A little more of your story")}</strong><small>${p.resume_filename ? `Added ${dateFormat(p.resume_uploaded_at)}` : "Drop a PDF, DOCX, or TXT file here · up to 5 MB"}</small></div><button class="button secondary small" data-action="upload-resume">${icon("upload")}${p.resume_filename ? "Replace resume" : "Upload resume"}</button></div>${S.config?.is_simulated ? `<div class="profile-details-actions"><button class="text-link" style="border:0;background:none" data-action="sample-resume">Try the simulated sample profile ${icon("arrow", "icon-sm")}</button></div>` : ""}</section></div><p class="profile-tip">Your story can change. <a href="#onboarding/1">Update your profile</a> whenever you need to.</p></div>`;
  }
  function applicationStatus(opp) {
    const value = String(opp.application_status || "Draft");
    return /^(in progress|draft)$/i.test(value)
      ? "Draft"
      : value.toLowerCase() === "applied"
        ? "Applied"
        : value;
  }
  function renderApplications() {
    const waiting = S.applications.filter((opp) =>
      ["Applied", "Under Review"].includes(applicationStatus(opp)),
    ).length;
    const soon = upcoming().filter((opp) => deadline(opp).days <= 30).length;
    $("view-applications").innerHTML =
      `${heading("applications", "SMALL STEPS, REAL PROGRESS", "Your possibilities, in progress.", "Every application is a step forward. Keep the important things together, and take it one at a time.", '<a href="#opportunities" class="button secondary">Find your next step ' + icon("plus") + "</a>")}
      <div class="metrics-grid application-metrics">${metric(S.applications.length, "Applications you’re tracking", "briefcase", "applications")}${metric(waiting, "Awaiting a little good news", "clock", "applications")}${metric(soon, "Deadlines in the next 30 days", "calendar", "applications")}</div>
      <div class="application-layout"><div class="application-list-panel"><div class="status-pills" aria-label="Filter application status">${["All", "Draft", "Applied", "Under Review", "Interview"].map((status) => `<button class="status-pill ${S.applicationFilter === status ? "active" : ""}" data-action="application-filter" data-status="${status}" aria-pressed="${S.applicationFilter === status}">${status}<span>${status === "All" ? S.applications.length : S.applications.filter((opp) => applicationStatus(opp) === status).length}</span></button>`).join("")}</div><div id="application-list"></div><p class="application-hint">${icon("lock")}Your application status is updated by you. IRIS keeps your progress in one place.</p></div>
      <aside class="application-aside"><section id="application-calendar" class="surface calendar-card" aria-label="Application deadlines calendar"></section><section class="surface upcoming-card"><h3>A few dates to keep close</h3>${
        upcoming()
          .slice(0, 4)
          .map(
            (opp) =>
              `<div class="upcoming-row"><a href="#detail/${encodeURIComponent(idOf(opp))}">${esc(opp.title)}</a><div><span>${dateFormat(deadline(opp).iso)}</span>${pill(deadline(opp).label, deadline(opp).days < 8 ? "gold" : "blue")}</div></div>`,
          )
          .join("") ||
        '<p class="text-small muted" style="font-size:12px;line-height:1.9">Your upcoming tracked deadlines will appear here.</p>'
      }<div style="margin-top:20px"><button class="button secondary small wide" data-action="calendar-all" ${upcoming().length ? "" : 'disabled title="Track an opportunity with a confirmed deadline first"'}>${icon("calendar")}Export your reminders</button></div></section></aside></div>`;
    renderApplicationList();
    renderCalendar();
  }
  function renderApplicationList() {
    const items = S.applications.filter(
      (opp) =>
        S.applicationFilter === "All" ||
        applicationStatus(opp) === S.applicationFilter,
    );
    $("application-list").innerHTML =
      items
        .map((opp) => {
          const id = idOf(opp),
            status = applicationStatus(opp),
            due = deadline(opp);
          return `<article class="surface application-row">${mark(opp)}<div class="application-main"><a href="#detail/${encodeURIComponent(id)}">${esc(opp.title)}</a><p>${esc(opp.organization || opp.provider)} · ${esc(categoryOf(opp))}</p><div class="application-meta"><span>${icon("calendar")}${due.iso ? dateFormat(due.iso) : "Deadline not confirmed"}</span><span>${icon("chart")}${scoreOf(opp)}% match</span>${pill(due.label, due.days !== null && due.days < 0 ? "red" : due.days !== null && due.days <= 7 ? "gold" : "neutral")}</div><div class="application-controls"><label><span class="sr-only">Application status for ${esc(opp.title)}</span><select class="status-select" data-application-status="${esc(id)}">${["Draft", "Applied", "Under Review", "Interview", "Offer", "Rejected"].map((item) => `<option ${item === status ? "selected" : ""}>${item}</option>`).join("")}</select></label><button class="button secondary small" data-action="apply" data-id="${esc(id)}">Application guide ${icon("arrow")}</button><button class="icon-button" data-action="untrack" data-id="${esc(id)}" aria-label="Stop tracking ${esc(opp.title)}">${icon("trash")}</button></div></div></article>`;
        })
        .join("") ||
      empty(
        S.applicationFilter === "All"
          ? "Every journey starts somewhere"
          : `No ${S.applicationFilter.toLowerCase()} applications yet`,
        S.applicationFilter === "All"
          ? "Find an opportunity that feels right and choose “Track Application in IRIS” in its application guide."
          : "Your applications will appear here as you update their status.",
        "explore",
        "Explore opportunities",
        "briefcase",
      );
  }
  function renderCalendar() {
    const { year, month, selected } = S.calendar;
    const first = new Date(Date.UTC(year, month, 1)),
      count = new Date(Date.UTC(year, month + 1, 0)).getUTCDate();
    const dates = new Map();
    S.applications.forEach((opp) => {
      const iso = deadline(opp).iso;
      if (iso) dates.set(iso, [...(dates.get(iso) || []), opp]);
    });
    const label = new Intl.DateTimeFormat("en-IN", {
      month: "long",
      year: "numeric",
      timeZone: "UTC",
    }).format(first);
    const cells = Array(first.getUTCDay()).fill("<span></span>");
    for (let day = 1; day <= count; day++) {
      const iso = `${year}-${String(month + 1).padStart(2, "0")}-${String(day).padStart(2, "0")}`;
      const events = dates.get(iso) || [];
      cells.push(
        `<button class="calendar-day ${iso === todayISO() ? "today" : ""} ${iso === selected ? "selected" : ""} ${events.length ? "has-event" : ""}" data-action="calendar-day" data-date="${iso}" aria-label="${dateFormat(iso)}${events.length ? `, ${events.length} application deadline` : ""}" aria-pressed="${iso === selected}" ${iso === todayISO() ? 'aria-current="date"' : ""}>${day}</button>`,
      );
    }
    $("application-calendar").innerHTML =
      `<div class="calendar-title"><h3>${esc(label)}</h3><div class="calendar-actions"><button class="icon-button" data-action="calendar-prev" aria-label="Previous month">${icon("left")}</button><button class="icon-button" data-action="calendar-next" aria-label="Next month">${icon("right")}</button></div></div><div class="calendar-weekdays">${["S", "M", "T", "W", "T", "F", "S"].map((day) => `<span>${day}</span>`).join("")}</div><div class="calendar-days">${cells.join("")}</div><div class="calendar-footer"><span><span class="status-dot" style="background:var(--gold);margin-right:4px"></span>Tracked deadline</span><button class="text-link" data-action="calendar-today">Today</button></div>${
        selected
          ? `<div class="calendar-selection">${dateFormat(selected)}${
              dates.has(selected)
                ? dates
                    .get(selected)
                    .map(
                      (opp) =>
                        `<a href="#detail/${encodeURIComponent(idOf(opp))}">${esc(opp.title)} ↗</a>`,
                    )
                    .join("")
                : '<p style="margin-top:5px">A little breathing room. No tracked deadlines.</p>'
            }</div>`
          : ""
      }`;
  }

  const starters = [
    ["cap", "Which scholarships fit my profile?"],
    ["document", "How do I apply for Bharti Airtel?"],
    ["shield", "Can I combine Airtel, Delhi MCM, and Google Gemini?"],
    ["sparkle", "Help me get my application documents ready."],
  ];
  function inlineMarkdown(value) {
    let text = esc(value);
    text = text.replace(/`([^`]+)`/g, "<code>$1</code>");
    text = text.replace(
      /\[([^\]]+)\]\((https?:\/\/[^\s)]+)\)/g,
      (all, label, url) => {
        const decoded = url
          .replace(/&amp;/g, "&")
          .replace(/&#39;/g, "'")
          .replace(/&quot;/g, '"');
        return safeURL(decoded)
          ? `<a href="${esc(safeURL(decoded))}" target="_blank" rel="noopener noreferrer">${label}</a>`
          : label;
      },
    );
    return text
      .replace(/\*\*([^*]+)\*\*/g, "<strong>$1</strong>")
      .replace(/(?<!\*)\*([^*]+)\*(?!\*)/g, "<em>$1</em>");
  }
  function markdown(value) {
    const lines = String(value || "")
      .replace(/\r\n/g, "\n")
      .split("\n");
    let output = "",
      list = "",
      paragraph = [],
      code = null;
    const flushParagraph = () => {
      if (paragraph.length) {
        output += `<p>${paragraph.map(inlineMarkdown).join("<br>")}</p>`;
        paragraph = [];
      }
    };
    const closeList = () => {
      if (list) {
        output += `</${list}>`;
        list = "";
      }
    };
    for (const line of lines) {
      if (/^\s*```/.test(line)) {
        flushParagraph();
        closeList();
        if (code !== null) {
          output += `<pre><code>${esc(code.join("\n"))}</code></pre>`;
          code = null;
        } else code = [];
        continue;
      }
      if (code !== null) {
        code.push(line);
        continue;
      }
      if (!line.trim()) {
        flushParagraph();
        closeList();
        continue;
      }
      const headingLine = line.match(/^(#{1,4})\s+(.+)$/);
      if (headingLine) {
        flushParagraph();
        closeList();
        output += `<h${Math.min(4, headingLine[1].length + 1)}>${inlineMarkdown(headingLine[2])}</h${Math.min(4, headingLine[1].length + 1)}>`;
        continue;
      }
      const bullet = line.match(/^\s*[-*]\s+(.+)$/),
        ordered = line.match(/^\s*\d+[.)]\s+(.+)$/);
      if (bullet || ordered) {
        flushParagraph();
        const tag = bullet ? "ul" : "ol";
        if (list !== tag) {
          closeList();
          output += `<${tag}>`;
          list = tag;
        }
        output += `<li>${inlineMarkdown((bullet || ordered)[1])}</li>`;
        continue;
      }
      if (/^>\s?/.test(line)) {
        flushParagraph();
        closeList();
        output += `<blockquote>${inlineMarkdown(line.replace(/^>\s?/, ""))}</blockquote>`;
        continue;
      }
      if (/^---+$/.test(line)) {
        flushParagraph();
        closeList();
        output += "<hr>";
        continue;
      }
      closeList();
      paragraph.push(line);
    }
    flushParagraph();
    closeList();
    if (code !== null)
      output += `<pre><code>${esc(code.join("\n"))}</code></pre>`;
    return output;
  }
  function chatMessage(message) {
    const sources = (message.sources || []).slice(0, 3);
    return `<article class="chat-message ${message.role}" data-message-id="${esc(message.id)}"><span class="message-avatar">${message.role === "user" ? esc(initials(profileName())) : icon("sparkle")}</span><div class="message-content"><div class="message-label">${message.role === "user" ? "You" : "IRIS"}</div>${message.role === "user" ? `<p>${esc(message.text)}</p>` : `<div class="markdown">${markdown(message.text)}</div>`}${sources.length ? `<div class="message-sources">${sources.map((opp) => `<button class="source-card" data-action="open-detail" data-id="${esc(idOf(opp))}">${mark(opp)}<span><strong>${esc(opp.title)}</strong><small>${scoreOf(opp)}% profile match</small></span>${icon("arrow")}</button>`).join("")}</div>` : ""}${message.pending ? `<div class="stream-status"><span class="spinner"></span>${esc(S.chatStatus || "Finding a little clarity…")}</div>` : message.error ? `<p class="stream-status">${esc(message.error)} <button class="text-link" style="border:0;background:none" data-action="retry-chat" data-query="${esc(message.query || "")}">Try again</button></p>` : ""}</div></article>`;
  }
  function renderChatMessages() {
    const container = $("ai-chat-messages");
    if (!container) return;
    const nearBottom =
      container.scrollHeight - container.scrollTop - container.clientHeight <
      130;
    container.innerHTML = S.chat.length
      ? S.chat.map(chatMessage).join("")
      : `<div class="chat-welcome"><span class="iris-symbol">${icon("sparkle")}</span><h2>A little guidance.<br />A clearer next step.</h2><p>Your opportunities, your profile, and a helping hand to bring it all together.</p><div class="starter-prompts">${starters.map(([symbol, prompt]) => `<button class="starter-prompt" data-action="chat-prompt" data-query="${esc(prompt)}">${icon(symbol)}<span>${esc(prompt)}</span></button>`).join("")}</div></div>`;
    if (nearBottom || S.chat.length <= 2)
      container.scrollTop = container.scrollHeight;
    const send = $("ai-chat-send-btn");
    if (send) {
      send.dataset.action = S.chatBusy ? "stop-chat" : "send-chat";
      send.type = S.chatBusy ? "button" : "submit";
      send.innerHTML = `${icon(S.chatBusy ? "stop" : "send")}<span>${S.chatBusy ? "Stop" : "Send"}</span>`;
      send.setAttribute(
        "aria-label",
        S.chatBusy ? "Stop response" : "Send message",
      );
    }
  }
  function renderAIContext() {
    const el = $("ai-context");
    if (!el) return;
    const p = S.profile || {},
      focus = S.chatFocus
        ? findOpp(S.chatFocus)
        : [...S.opportunities].sort((a, b) => scoreOf(b) - scoreOf(a))[0];
    const latest = [...S.chat]
      .reverse()
      .find((message) => message.role === "assistant" && !message.pending);
    el.innerHTML = `<span class="eyebrow">A LITTLE CONTEXT</span><div class="context-profile"><span class="avatar small">${esc(initials(p.name))}</span><span><strong>${esc(p.name || "Your profile")}</strong><small>${esc(p.academic_stage || "Your next chapter")}</small></span></div><div class="context-fields"><div><span>Your campus</span><b>${esc(p.institution || "Add your institution")}</b></div><div><span>Home base</span><b>${esc(p.state_domicile || "Not added yet")}</b></div><div><span>Profile strength</span><b>${p.profile_completeness || 0}%</b></div></div><div class="skill-tags">${(
      p.skills || []
    )
      .slice(0, 5)
      .map(
        (skill) =>
          `<span class="skill-tag" style="font-size:10px;padding:4px 8px">${esc(skill)}</span>`,
      )
      .join(
        "",
      )}</div><a href="#profile" class="text-link" style="font-size:11px;margin-top:18px">Keep your profile current ${icon("arrow", "icon-sm")}</a>${focus ? `<h3>${S.chatFocus ? "Your current focus" : "A promising possibility"}</h3><div class="context-focus">${mark(focus)}<strong>${esc(focus.title)}</strong><p>${esc(focus.organization || focus.provider)} · ${scoreOf(focus)}% match</p><a href="#detail/${encodeURIComponent(idOf(focus))}" class="text-link" style="font-size:11px">Take a closer look ${icon("arrow", "icon-sm")}</a>${S.chatFocus ? '<button class="clear-filters" style="padding:9px 0 0;display:block" data-action="clear-focus">Clear focus</button>' : ""}</div>` : ""}${latest?.conflicts?.length ? `<h3>Policy Conflict Shield</h3><div class="policy-banner conflict">${esc(latest.conflicts[0].warning)}</div>` : ""}<div class="context-note">${icon("shield")}Answers begin with your stored profile and the local catalog. Check current deadlines and terms on each official portal.${latest?.model ? `<p style="margin-top:12px">Response source: ${esc(latest.model === "deterministic-local-rag" ? "Local catalog synthesis" : latest.model)}</p>` : ""}</div>`;
  }
  function renderAI() {
    $("view-ai-assistant").innerHTML =
      `${heading("ai", "YOUR OPPORTUNITY COMPANION", "A little help from IRIS.", "From “where do I start?” to “I’m ready to apply.”", '<button class="button secondary small" data-action="new-chat">' + icon("plus") + "New conversation</button>")}
      <div class="surface ai-workspace"><div class="chat-panel"><div class="chat-toolbar"><span>${icon("shield")}Grounded in your profile & catalog</span>${pill("Ask IRIS", "gold", "sparkle")}</div><div id="ai-chat-messages" class="chat-messages" aria-live="polite" aria-relevant="additions text" aria-label="Conversation with IRIS"></div><div class="chat-composer-wrap"><form id="ai-chat-form" class="chat-composer"><label for="ai-chat-input" class="sr-only">Your message to IRIS</label><textarea id="ai-chat-input" rows="1" maxlength="4000" placeholder="What’s on your mind? Ask IRIS…"></textarea><button id="ai-chat-send-btn" class="button primary" type="submit" aria-label="Send message">${icon("send")}<span>Send</span></button></form><p class="composer-note">A little guidance, not a guarantee. Always confirm current details with the official program.</p></div></div><aside id="ai-context" class="ai-context" aria-label="Your conversation context"></aside></div>`;
    $("view-ai-assistant")
      .querySelector(".page-heading")
      .classList.add("ai-heading");
    renderChatMessages();
    renderAIContext();
  }
  function renderSettings() {
    const sync = S.sync || {},
      config = S.config || {},
      prefs = S.profile?.preferences || {};
    const seconds = Math.max(0, sync.seconds_until_next_run || 0),
      countdown = `${Math.floor(seconds / 3600)}h ${Math.floor((seconds % 3600) / 60)}m`;
    $("view-settings").innerHTML =
      `${heading("settings", "MAKE YOURSELF AT HOME", "A workspace that feels like you.", "A few thoughtful preferences, and a clear view of what keeps your catalog fresh.")}
      <div class="settings-layout"><div><section class="surface settings-card"><h2>Fresh possibilities, twice a day.</h2><p>IRIS checks the shared catalog every 12 hours so your browsing stays quick and your next steps stay clear.</p><div class="sync-hero">${icon("refresh")}<div><strong id="catalog-sync-status">${sync.sync_running ? "A little refresh is in progress…" : sync.last_sync_iso ? "Your last catalog check completed" : "Your first refresh is ready"}</strong><p>${sync.sync_running ? "You can keep exploring while it runs." : sync.last_sync_iso ? `Next scheduled check in ${countdown}` : "Run a catalog check whenever you’re ready."}</p></div></div><div class="settings-rows"><div><span>Last completed refresh</span><b>${sync.last_sync_iso ? dateFormat(sync.last_sync_iso, { day: "numeric", month: "short", hour: "numeric", minute: "2-digit" }) : "Not run yet"}</b></div><div><span>Last confirmed live check</span><b>${sync.last_verified_at ? dateFormat(sync.last_verified_at, { day: "numeric", month: "short" }) : "Not recorded"}</b></div><div><span>Catalog records</span><b>${config.catalog_count ?? S.opportunities.length} opportunities</b></div><div><span>Refresh interval</span><b>Every 12 hours</b></div></div><div class="button-row" style="margin-top:22px"><button id="sync-now-button" class="button primary" data-action="sync" ${sync.sync_running ? "disabled" : ""}>${icon("refresh")}${sync.sync_running ? "Refreshing…" : "Refresh the catalog"}</button><span class="text-small muted" style="font-size:11px">${config.live_verification_configured ? "Live portal checks are configured" : "Cache checks available · live verification unavailable"}</span></div></section>
      <section class="surface settings-card"><h2>Found a possibility somewhere else?</h2><p>Bring an official program link or a specific opportunity name to the verification pipeline.</p><form id="scan-form" class="scan-form"><label class="sr-only" for="scanner-query-input">Official portal URL or program name</label><input id="scanner-query-input" class="input" placeholder="Official portal link or program name" required maxlength="400" /><button id="scanner-verify-btn" class="button secondary" type="submit">Scan & verify ${icon("arrow")}</button></form><div id="scan-result" class="scan-result" role="status"></div></section></div>
      <div><section class="surface settings-card"><h2>Your little preferences</h2><p>Make this space a little more comfortable. Your choices stay with your profile.</p>${[
        [
          "reduce_motion",
          "A quieter experience",
          "Reduce motion and animated transitions.",
        ],
        [
          "compact_cards",
          "A little more at a glance",
          "Use a compact opportunity card layout.",
        ],
        [
          "show_verification",
          "Keep source labels visible",
          "Show catalog and live-check labels on cards.",
        ],
      ]
        .map(
          ([key, label, description]) =>
            `<label class="setting-toggle-row"><span><strong>${label}</strong><p>${description}</p></span><input type="checkbox" class="toggle" data-preference="${key}" ${key === "show_verification" ? (prefs[key] !== false ? "checked" : "") : prefs[key] ? "checked" : ""} aria-label="${label}" /></label>`,
        )
        .join("")}</section>
      <section class="surface settings-card"><h2>Behind your workspace</h2><p>A clear view of how your opportunities and answers are served.</p><div class="settings-rows"><div><span>Data store</span><b>${esc(config.database || "Local catalog")}</b></div><div><span>Assistant</span><b>${esc((config.assistant_providers || ["Local retrieval"]).join(", "))}</b></div><div><span>Live verification</span><b>${config.live_verification_configured ? "Configured" : "Not configured"}</b></div><div><span>Your workspace</span><b>${S.user ? "Personal account" : "Private guest workspace"}</b></div></div><div class="privacy-note" style="margin-top:18px">${icon("lock")} ${S.user ? "Your profile, saved opportunities and applications are scoped to your signed-in account." : "This guest workspace is private to this browser. Sign in to keep your progress linked to an account."}</div>${S.user ? `<button class="button ghost small" style="margin-top:19px" data-action="logout">${icon("logout")}Sign out</button>` : '<a class="button secondary small" style="margin-top:19px" href="#login">Create your own space</a>'}</section><section class="surface settings-card"><h2>Your data, in your hands</h2><p>Download your profile, shortlist and application tracker. Removing a resume clears its stored text and file details; your edited profile stays available.</p><div class="button-row"><button class="button secondary small" data-action="export-data">${icon("download")}Export my workspace</button><button class="button ghost small" data-action="remove-resume" ${S.profile?.resume_filename ? "" : "disabled"}>Remove stored resume</button></div></section></div></div>`;
  }
  function startWizard(reset = false) {
    if (S.wizard && !reset) return;
    const p = S.profile || {};
    S.wizard = {
      name: p.name || "",
      age: p.age || "",
      state_domicile: p.state_domicile || "",
      country: p.country || "India",
      academic_stage: (p.academic_stage || "").split("•")[0].trim(),
      institution: p.institution || "",
      graduation_year: p.graduation_year || "",
      class_12_pct: p.class_12_pct ?? "",
      family_income_inr: p.family_income_inr ?? "",
      nirf_top_50: p.nirf_top_50 == null ? "" : String(Boolean(p.nirf_top_50)),
      skills: [...(p.skills || [])],
      domains: new Set(p.domains || []),
      areas_of_interest: p.areas_of_interest || "",
    };
  }
  function captureWizard() {
    if (!S.wizard) return;
    const pendingSkill = $("setup-skills");
    if (pendingSkill?.value.trim()) {
      S.wizard.skills = [
        ...new Set([
          ...S.wizard.skills,
          ...pendingSkill.value
            .split(",")
            .map((value) => value.trim())
            .filter(Boolean),
        ]),
      ].slice(0, 40);
      pendingSkill.value = "";
    }
    const form = $("onboarding-form");
    if (form)
      for (const [key, value] of new FormData(form))
        if (key in S.wizard && !["skills", "domains"].includes(key))
          S.wizard[key] = value;
    const interests = $("areas-of-interest");
    if (interests) S.wizard.areas_of_interest = interests.value;
  }
  function skillTagsEditable() {
    return S.wizard.skills
      .map(
        (skill, index) =>
          `<span class="skill-tag">${esc(skill)}<button type="button" data-action="remove-skill" data-index="${index}" aria-label="Remove ${esc(skill)}">${icon("close")}</button></span>`,
      )
      .join("");
  }
  function renderWizard() {
    startWizard();
    const w = S.wizard,
      step = S.wizardStep;
    const countryOptions = [
      ...new Set(
        [
          "India",
          "United States",
          "United Kingdom",
          "Canada",
          "Australia",
          "Germany",
          "Singapore",
          "United Arab Emirates",
          w.country,
        ].filter(Boolean),
      ),
    ];
    const nowYear = Number(todayISO().slice(0, 4));
    const years = [
      ...new Set(
        [
          w.graduation_year ? Number(w.graduation_year) : 0,
          ...Array.from({ length: 11 }, (_, index) => nowYear - 2 + index),
        ].filter(Boolean),
      ),
    ].sort((a, b) => a - b);
    const meta = `<div class="wizard-meta"><div class="wizard-progress"><span class="wizard-step-label">Step ${step} of 2</span><div class="progress" role="progressbar" aria-label="Onboarding progress" aria-valuenow="${step * 50}" aria-valuemin="0" aria-valuemax="100"><span style="width:${step * 50}%"></span></div></div><button class="text-link" style="border:0;background:none;font-size:12px" data-action="wizard-exit">Save and exit</button></div>`;
    if (step === 1) {
      $("view-onboarding").innerHTML =
        `<div class="onboarding-container">${meta}${heading("onboarding", "A LITTLE ABOUT YOU", "Tell us about yourself.", "Let’s make this space feel more like you — and your opportunities a little more relevant.")}
        <div class="wizard-grid"><form id="onboarding-form" class="surface wizard-card"><h2>${icon("user")}Personal information</h2><p class="section-copy">The basics, so we can put you first.</p><div class="form-grid"><div class="form-field full"><label for="setup-name">Full name</label><input id="setup-name" class="input" name="name" value="${esc(w.name)}" required maxlength="120" autocomplete="name" /></div><div class="form-field"><label for="setup-age">Age</label><input id="setup-age" class="input" name="age" type="number" min="10" max="100" value="${esc(w.age)}" required /></div><div class="form-field"><label for="setup-country">Country</label><select id="setup-country" class="input" name="country">${countryOptions.map((country) => `<option ${country === w.country ? "selected" : ""}>${esc(country)}</option>`).join("")}</select></div><div class="form-field full"><label for="setup-state">City / State</label><input id="setup-state" class="input" name="state_domicile" list="state-options" value="${esc(w.state_domicile)}" required maxlength="100" autocomplete="address-level1" /><datalist id="state-options">${["Delhi", "Uttar Pradesh", "Maharashtra", "Karnataka", "Tamil Nadu", "Gujarat", "Rajasthan", "West Bengal", "Bihar", "Telangana", "Kerala", "Punjab", "Haryana"].map((state) => `<option value="${state}"></option>`).join("")}</datalist></div></div>
        <div class="divider"></div><h2>${icon("cap")}Education details</h2><p class="section-copy">Where you are in your academic journey.</p><div class="form-grid"><div class="form-field"><label for="setup-degree">Degree / Class</label><input id="setup-degree" class="input" name="academic_stage" list="degree-options" value="${esc(w.academic_stage)}" required maxlength="120" /><datalist id="degree-options">${["Class 11", "Class 12", "B.Tech (1st Year)", "B.Tech (2nd Year)", "B.Tech (3rd Year)", "B.Tech (4th Year)", "Undergraduate", "Postgraduate", "PhD"].map((degree) => `<option value="${degree}"></option>`).join("")}</datalist></div><div class="form-field"><label for="setup-university">University / Institution</label><input id="setup-university" class="input" name="institution" value="${esc(w.institution)}" maxlength="200" required placeholder="Your college or school" /></div><div class="form-field full"><label for="setup-graduation">Expected graduation year</label><select id="setup-graduation" class="input" name="graduation_year" required><option value="">Choose a year</option>${years.map((year) => `<option value="${year}" ${Number(w.graduation_year) === year ? "selected" : ""}>${year}</option>`).join("")}</select></div></div>
        <div class="divider"></div><h2>${icon("shield")}Eligibility details</h2><p class="section-copy">Optional. Leave unknown details blank; IRIS will ask you to confirm them rather than assume eligibility.</p><div class="form-grid"><div class="form-field"><label for="setup-marks">Class 12 marks (%)</label><input id="setup-marks" class="input" name="class_12_pct" type="number" min="0" max="100" step="0.01" value="${esc(w.class_12_pct)}" /></div><div class="form-field"><label for="setup-income">Annual family income (INR)</label><input id="setup-income" class="input" name="family_income_inr" type="number" min="0" step="1" value="${esc(w.family_income_inr)}" /></div><div class="form-field full"><label for="setup-ranking">Is your engineering institution in the NIRF top 50?</label><select id="setup-ranking" class="input" name="nirf_top_50"><option value="" ${w.nirf_top_50 === "" ? "selected" : ""}>Not confirmed</option><option value="true" ${w.nirf_top_50 === "true" ? "selected" : ""}>Yes, I have checked the current ranking</option><option value="false" ${w.nirf_top_50 === "false" ? "selected" : ""}>No</option></select></div></div>
        <div class="divider"></div><h2>${icon("chart")}A few things you’re good at</h2><p class="section-copy">Skills are optional. Curiosity counts, too.</p><div class="skill-input-wrap">${icon("search")}<input id="setup-skills" class="input" placeholder="Add a skill and press Enter (e.g. Python, Design)" aria-label="Add a skill" maxlength="60" /></div><div id="editable-skill-tags" class="skill-tags">${skillTagsEditable()}</div>
        <div class="wizard-resume" data-dropzone>${icon("document")}<div><strong>${esc(S.profile?.resume_filename || "Bring a little more of your story")}</strong><small>${S.profile?.resume_filename ? "Your resume is saved to your profile." : "Optional · PDF, DOCX, or TXT · up to 5 MB"}</small></div><button class="button secondary small" data-action="upload-resume" type="button">${icon("upload")}${S.profile?.resume_filename ? "Replace" : "Upload"}</button></div><p id="wizard-form-error" class="form-message" role="alert" hidden></p><div class="wizard-actions"><small>Your information helps personalize your own workspace.</small><button id="wizard-continue" class="button primary" type="submit">Save and continue ${icon("arrow")}</button></div></form>
        </div></div>`;
    } else {
      $("view-onboarding").innerHTML =
        `<div class="onboarding-container wizard-step-two">${meta}${heading("onboarding", "FOLLOW YOUR CURIOSITY", "What are you looking forward to?", "Choose the possibilities that interest you. You can pick more than one — and change your mind later.")}
      <div class="surface wizard-card"><h2>${icon("compass")}What opportunities are you interested in?</h2><p class="section-copy">A direction is all we need. We’ll help you explore the rest.</p><div class="interest-grid">${categories
        .slice(1)
        .map(
          (category) =>
            `<button class="interest-card ${w.domains.has(category) ? "selected" : ""}" data-action="interest" data-domain="${esc(category)}" aria-pressed="${w.domains.has(category)}"><span class="interest-check">${w.domains.has(category) ? icon("check") : ""}</span>${icon(categoryIcons[category])}<strong>${category}</strong><p>${categoryDescriptions[category]}</p></button>`,
        )
        .join(
          "",
        )}</div><div class="divider"></div><div class="form-field"><label for="areas-of-interest">Anything else that sparks your curiosity? <span class="muted">(optional)</span></label><input id="areas-of-interest" class="input" value="${esc(w.areas_of_interest)}" maxlength="400" placeholder="Machine learning, climate change, open source…" /></div><div class="privacy-note">${icon("lock")}You’re always in control. Your interests help shape your recommendations and can be changed in your profile.</div><p id="wizard-form-error" class="form-message" role="alert" hidden></p><div class="wizard-actions"><button class="button secondary" data-action="wizard-back">${icon("left")}Back</button><button id="wizard-finish" class="button primary" data-action="wizard-finish">Find my opportunities ${icon("arrow")}</button></div></div></div>`;
    }
  }
  function renderLogin() {
    const signup = S.authMode === "signup";
    $("view-login").innerHTML =
      `<div class="login-layout"><div class="login-art"><span class="eyebrow" style="color:#C9AF72;margin-bottom:20px">A WORLD OF POSSIBILITY</span><h2>Better opportunities.<br /><span>A brighter you.</span></h2><p>Scholarships, experiences, and a little direction for the person you’re becoming.</p></div><div class="login-panel"><div class="brand" style="padding:0;color:var(--ink)"><img src="assets/iris-bird-logo@2x.png" alt="" /><span>IRIS <span class="brand-light" style="color:#B99C55">onE</span></span></div><span class="eyebrow">YOUR NEXT CHAPTER</span><h1 id="login-heading">${signup ? "A fresh start, together." : "Welcome back."}</h1><p>${signup ? "Make a little space for your next big possibility." : "Your possibilities are right where you left them."}</p><form id="auth-form">${signup ? '<div class="form-field"><label for="auth-name">Full name</label><input id="auth-name" name="name" class="input" autocomplete="name" required maxlength="120" placeholder="Your name" /></div>' : ""}<div class="form-field"><label for="auth-email">Email address</label><input id="auth-email" type="email" class="input" name="email" autocomplete="email" required placeholder="you@university.edu" /></div><div class="form-field"><label for="auth-password">Password</label><input id="auth-password" type="password" class="input" name="password" autocomplete="${signup ? "new-password" : "current-password"}" minlength="${signup ? 8 : 1}" maxlength="72" required placeholder="${signup ? "At least 8 characters" : "Your password"}" /></div><p id="auth-error" class="form-message" role="alert" hidden></p><button id="auth-submit" class="button primary wide" type="submit">${signup ? "Create your space" : "Sign in to your space"} ${icon("arrow")}</button></form><div class="auth-switch">${signup ? "Already part of IRIS?" : "A new chapter?"} <button data-action="auth-switch">${signup ? "Sign in" : "Create an account"}</button></div><div class="login-demo">Just taking a look? <a href="#home">Explore the guest workspace →</a></div></div></div>`;
  }

  async function loadWorkspace({ render = true } = {}) {
    const version = ++S.loadVersion;
    S.loading = true;
    // Establish the signed workspace cookie before parallel requests on first visit.
    const profileResult = await api("/profile").then(
      (value) => ({ status: "fulfilled", value }),
      (reason) => ({ status: "rejected", reason }),
    );
    const results = [
      profileResult,
      ...(await Promise.allSettled(
        [
          "/opportunities",
          "/opportunities/saved",
          "/applications/overview",
          "/sync/status",
          "/platform/config",
        ].map((endpoint) => api(endpoint)),
      )),
    ];
    if (version !== S.loadVersion) return;
    const [profile, opportunities, saved, applications, sync, config] = results;
    const critical = [profile, opportunities].find(
      (result) => result.status === "rejected",
    );
    S.error = critical ? critical.reason.message : "";
    if (profile.status === "fulfilled") S.profile = profile.value;
    if (opportunities.status === "fulfilled")
      S.opportunities = opportunities.value;
    if (saved.status === "fulfilled") S.saved = saved.value;
    if (applications.status === "fulfilled")
      S.applications = applications.value.applications;
    if (sync.status === "fulfilled") S.sync = sync.value;
    if (config.status === "fulfilled") S.config = config.value;
    let banner = $("runtime-banner");
    if (!banner) {
      banner = document.createElement("div");
      banner.id = "runtime-banner";
      banner.className = "runtime-banner";
      banner.setAttribute("role", "status");
      $("main-content").prepend(banner);
    }
    banner.hidden = false;
    banner.textContent = S.config?.is_simulated
      ? "DEMO MODE · Sample catalog and profile. External services are disabled; no live verification is simulated."
      : "LIVE MODE · Program availability is confirmed only by a recent live verification badge. Cached records may be unconfirmed.";
    const noncritical = [saved, applications, sync, config].filter(
      (result) => result.status === "rejected",
    );
    if (noncritical.length && !critical)
      toast(
        "Some workspace information could not be refreshed. Please try again.",
        "error",
      );
    S.loading = false;
    S.ready = true;
    updateShell();
    if (render) renderActive();
  }
  function routeFromHash() {
    const raw = location.hash.replace(/^#\/?/, "");
    const [part = "home", value] = raw.split("/");
    const aliases = {
      dashboard: "home",
      ai: "ai-assistant",
      setup: "onboarding",
      "": "home",
    };
    const view = aliases[part] || part;
    let id = null;
    try {
      id = value ? decodeURIComponent(value) : null;
    } catch {}
    return { view, id };
  }
  function navigate(view, id) {
    const hash = `#${view}${id != null ? "/" + encodeURIComponent(id) : ""}`;
    if (location.hash === hash) handleRoute();
    else location.hash = hash;
  }
  function closeNavigation() {
    $("sidebar").classList.remove("is-open");
    $("sidebar-backdrop").hidden = true;
    $("menu-toggle").setAttribute("aria-expanded", "false");
  }
  function switchView(viewId, options = {}) {
    let view = String(viewId || "home")
      .replace(/^#?view-/, "")
      .replace(/^#/, "");
    view =
      { dashboard: "home", ai: "ai-assistant", setup: "onboarding" }[view] ||
      view;
    const el = $(`view-${view}`);
    if (!el) {
      navigate("home");
      return;
    }
    const wizardStep = options.id === "2" && S.wizard ? 2 : 1;
    const changed =
      S.view !== view ||
      (view === "detail" && options.id !== S.detailId) ||
      (view === "onboarding" && S.wizardStep !== wizardStep);
    S.view = view;
    if (view === "detail") S.detailId = options.id || S.detailId;
    if (view === "onboarding") S.wizardStep = wizardStep;
    document.querySelectorAll("[data-view]").forEach((section) => {
      section.hidden = section !== el;
      section.classList.toggle("is-active", section === el);
    });
    closeNavigation();
    $("account-popover").hidden = true;
    $("notifications-popover").hidden = true;
    $("account-trigger").setAttribute("aria-expanded", "false");
    $("notifications-trigger").setAttribute("aria-expanded", "false");
    if ($("apply-options-modal").open) $("apply-options-modal").close();
    updateShell();
    renderActive();
    document.title = `${{ home: "Your overview", opportunities: "Explore opportunities", saved: "Saved for later", applications: "Your applications", detail: "Opportunity details", profile: "Your profile", "ai-assistant": "Ask IRIS", settings: "Settings", onboarding: "A little about you", login: "Your next chapter" }[view]} — IRIS onE`;
    $("route-announcer").textContent = `${view.replace(/-/g, " ")} view opened`;
    if (changed) {
      $("toast-container").replaceChildren();
      window.scrollTo({ top: 0, behavior: "instant" });
      $("main-content").focus({ preventScroll: true });
    }
    if (view === "detail" && S.ready) loadDetail(S.detailId);
  }
  function handleRoute() {
    const route = routeFromHash();
    switchView(route.view, { id: route.id });
  }
  function renderActive() {
    if (!S.ready && !["login"].includes(S.view)) {
      $(`view-${S.view}`).innerHTML =
        '<div class="loading-state"><span class="spinner"></span>A little possibility is on its way…</div>';
      return;
    }
    if (S.error && S.view !== "login") {
      $(`view-${S.view}`).innerHTML = empty(
        "Let’s reconnect to your possibilities.",
        S.error,
        "reload",
        "Try again",
        "refresh",
      );
      return;
    }
    const renders = {
      home: renderHome,
      opportunities: renderOpportunities,
      saved: renderSaved,
      applications: renderApplications,
      profile: renderProfile,
      detail: renderDetail,
      "ai-assistant": renderAI,
      settings: renderSettings,
      onboarding: renderWizard,
      login: renderLogin,
    };
    renders[S.view]?.();
  }
  let detailVersion = 0;
  async function loadDetail(id, force = false) {
    if (!id) {
      navigate("opportunities");
      return;
    }
    if (!force && S.detail && idOf(S.detail.opportunity) === id) {
      renderDetail();
      return;
    }
    const version = ++detailVersion;
    try {
      const [opportunity, guide] = await Promise.all([
        api(`/opportunities/${encodeURIComponent(id)}`),
        api(`/opportunities/${encodeURIComponent(id)}/how-to-apply`),
      ]);
      S.guides.set(String(id), guide);
      if (version !== detailVersion || S.view !== "detail" || S.detailId !== id)
        return;
      S.detail = { opportunity, guide };
      renderDetail();
    } catch (error) {
      if (S.view === "detail" && S.detailId === id)
        $("view-detail").innerHTML = empty(
          "This possibility is a little out of reach.",
          error.message,
          "explore",
          "Back to opportunities",
          "info",
        );
    }
  }
  async function toggleSave(id, button) {
    const saved = S.saved.some((item) => idOf(item) === id);
    if (button) button.disabled = true;
    try {
      await api(`/opportunities/${encodeURIComponent(id)}/save`, {
        method: saved ? "DELETE" : "POST",
      });
      S.saved = await api("/opportunities/saved");
      updateShell();
      if (S.view === "opportunities") renderResults();
      else if (S.view !== "onboarding") renderActive();
      toast(
        saved
          ? "A little space made in your shortlist."
          : "Saved for whenever you’re ready.",
      );
    } finally {
      if (button?.isConnected) button.disabled = false;
    }
  }
  async function openApplyOptionsModal(id) {
    const version = ++S.modalVersion;
    S.modalId = String(id);
    const dialog = $("apply-options-modal");
    $("apply-options-modal-body").innerHTML =
      '<div class="loading-state" style="padding:70px 15px"><span class="spinner"></span>Preparing your next steps…</div>';
    if (!dialog.open) dialog.showModal();
    try {
      const guide = await api(
        `/opportunities/${encodeURIComponent(id)}/how-to-apply`,
      );
      S.guides.set(String(id), guide);
      if (S.modalVersion !== version || !dialog.open) return;
      renderApplicationGuide(guide);
    } catch (error) {
      if (dialog.open && S.modalVersion === version)
        $("apply-options-modal-body").innerHTML = empty(
          "Your guide couldn’t be loaded.",
          error.message,
          "retry-guide",
          "Try again",
          "document",
        );
    }
  }
  function renderApplicationGuide(guide) {
    const id = guide.opportunity_id,
      draft = S.documentDrafts.get(id);
    const checked = draft || guide.checked_documents || [];
    const isTracked =
      guide.tracking_status && guide.tracking_status !== "Saved";
    const channels = (guide.application_channels || []).filter((channel) =>
      safeURL(channel.url),
    );
    const status = verification(guide.verification_status);
    $("apply-options-modal-body").innerHTML =
      `<div class="dialog-summary"><h3>${esc(guide.title)}</h3><div class="button-row">${pill(`${Math.round(guide.match_score)}% profile match`, "blue")}${pill(status[0], status[1])}</div><p>${esc(guide.provider)} · ${esc(guide.benefit_summary)}</p><small>${guide.last_verified_at ? `Last live check: ${dateFormat(guide.last_verified_at)}` : "Live application status has not been confirmed. Check the current cycle on the official portal."}</small></div>
      <section class="dialog-section"><h3>${icon("external")}Your application channels</h3>${channels.map((channel, index) => `<a class="channel-link" href="${esc(safeURL(channel.url))}" target="_blank" rel="noopener noreferrer"><div><span class="channel-number">${index + 1}</span><span><strong>${esc(channel.name)}</strong><small>${esc(new URL(channel.url).hostname)}</small></span></div><span>${guide.verification_status === "VERIFIED_LIVE" && channel.verified ? "Apply Live" : "Open"} ↗</span></a>`).join("") || '<p class="text-small muted">A current application channel hasn’t been confirmed yet.</p>'}${safeURL(guide.rules_pdf_url) ? `<a class="text-link" style="font-size:12px;margin-top:9px" href="${esc(safeURL(guide.rules_pdf_url))}" target="_blank" rel="noopener noreferrer">Official PDF / program rules ${icon("external", "icon-sm")}</a>` : ""}</section>
      <section class="dialog-section"><h3>${icon("document")}A clearer path, step by step</h3><ol class="guide-steps">${(guide.how_to_apply_steps || []).map((step) => `<li><span class="step-number">${esc(step.step)}</span><div><strong>${esc(step.title)}</strong><p>${esc(step.detail)}</p></div></li>`).join("")}</ol></section>
      <section class="dialog-section"><h3>${icon("checkCircle")}A few things to have ready</h3>${(guide.required_documents || []).map((document, index) => `<label class="document-label"><input type="checkbox" data-guide-document="${index}" ${checked.includes(document) ? "checked" : ""} /><span>${esc(document)}</span></label>`).join("")}<div id="guide-document-status" class="document-status" role="status">${checked.length ? `${checked.length} of ${guide.required_documents.length} documents ready` : "Your checklist is saved to your IRIS profile."}</div></section>${policyMarkup(guide)}${guide.gate_warnings?.length ? `<p class="text-small muted" style="font-size:12px;line-height:1.8;margin-top:17px">${guide.gate_warnings.map(esc).join("<br>")}</p>` : ""}<div class="dialog-actions"><button id="guide-track-button" class="button primary" data-action="track" data-id="${esc(id)}">${icon("check")}${isTracked ? "Tracked in IRIS" : "Track Application in IRIS"}</button><button id="guide-calendar-button" class="button gold" data-action="calendar" data-id="${esc(id)}" ${guide.deadline_iso ? "" : 'disabled title="A confirmed deadline is needed for a calendar reminder"'}>${icon("calendar")}Sync to Calendar</button></div><p class="muted" style="font-size:11px;line-height:1.8;margin-top:16px">${esc(guide.verification_note)}</p>`;
  }
  async function persistDocuments(id) {
    const selection = S.documentDrafts.get(id);
    if (!selection) return;
    const status = $("guide-document-status");
    if (S.modalId === id && status) {
      status.classList.remove("error");
      status.textContent = "Saving your checklist…";
    }
    try {
      const guide = S.guides.get(id);
      const result = await post("/applications/track", {
        opportunity_id: id,
        status: guide?.tracking_status || "Saved",
        checked_documents: selection,
      });
      S.guides.set(id, result);
      if (S.documentDrafts.get(id) === selection) S.documentDrafts.delete(id);
      if (S.modalId === id && $("guide-document-status")) {
        $("guide-document-status").classList.remove("error");
        $("guide-document-status").textContent = "Checklist saved to IRIS.";
      }
    } catch (error) {
      if (S.modalId === id && $("guide-document-status")) {
        $("guide-document-status").classList.add("error");
        $("guide-document-status").innerHTML =
          `Your changes haven’t been saved. <button data-action="retry-documents">Try again</button>`;
      }
      throw error;
    }
  }
  function queueDocuments(id) {
    S.documentQueue = S.documentQueue
      .catch(() => {})
      .then(() => persistDocuments(id));
    return S.documentQueue;
  }
  async function trackApplication(id, button) {
    if (button) button.disabled = true;
    clearTimeout(S.documentTimer);
    try {
      await S.documentQueue.catch(() => {});
      const guide = S.guides.get(id),
        docs = S.documentDrafts.get(id) || guide?.checked_documents || [];
      const result = await post("/applications/track", {
        opportunity_id: id,
        status:
          guide?.tracking_status && guide.tracking_status !== "Saved"
            ? guide.tracking_status
            : "Draft",
        checked_documents: docs,
      });
      S.guides.set(id, result);
      S.documentDrafts.delete(id);
      S.applications = (await api("/applications/overview")).applications;
      if (S.detail && idOf(S.detail.opportunity) === id)
        S.detail.guide = result;
      updateShell();
      renderActive();
      if ($("apply-options-modal").open && S.modalId === id)
        renderApplicationGuide(result);
      toast("Your next step is tracked in IRIS.");
    } finally {
      if (button?.isConnected) button.disabled = false;
    }
  }
  async function downloadCalendar(id = null) {
    const response = await fetch(
      `${API_BASE}${id ? `/opportunities/${encodeURIComponent(id)}/calendar.ics` : "/applications/calendar.ics"}`,
      { headers: S.token ? { Authorization: `Bearer ${S.token}` } : {} },
    );
    if (!response.ok) {
      const data = await response.json().catch(() => ({}));
      throw new ApiError(
        data.detail ||
          "The calendar could not be downloaded. Please try again.",
        response.status,
      );
    }
    const blob = await response.blob(),
      url = URL.createObjectURL(blob),
      link = document.createElement("a");
    link.href = url;
    link.download = id
      ? `iris-${id}-deadline.ics`
      : "iris-application-reminders.ics";
    document.body.appendChild(link);
    link.click();
    link.remove();
    setTimeout(() => URL.revokeObjectURL(url), 1000);
    toast("Calendar downloaded with 72-hour and 24-hour reminders.");
  }
  async function verifyOpportunity(id, button) {
    const original = button?.innerHTML;
    if (button) {
      button.disabled = true;
      button.innerHTML = '<span class="spinner"></span>Checking the portal…';
    }
    try {
      const result = await post(
        "/verify-opportunity",
        { opportunity_id: id, live_agent: true },
        { timeout: 240000 },
      );
      toast(
        result.is_verified
          ? "The live portal check passed. Your guide is updated."
          : result.message ||
              "The live check could not be confirmed. Cached guidance is still available.",
        result.is_verified ? "success" : "info",
      );
      await loadWorkspace({ render: false });
      if (S.view === "detail" && S.detailId === id) await loadDetail(id, true);
    } finally {
      if (button?.isConnected) {
        button.disabled = false;
        button.innerHTML = original;
      }
    }
  }

  async function sendChat(query, focus = S.chatFocus) {
    query = String(query || "").trim();
    if (!query || S.chatBusy) return;
    if (query.length > 4000) {
      toast(
        "A little shorter, please — messages can be up to 4,000 characters.",
        "error",
      );
      return;
    }
    if (S.view !== "ai-assistant") navigate("ai-assistant");
    S.chatBusy = true;
    S.chatStatus = "Reading your profile and local catalog…";
    const controller = new AbortController();
    S.chatController = controller;
    const user = { id: `user-${Date.now()}`, role: "user", text: query };
    const assistant = {
      id: `iris-${Date.now()}`,
      role: "assistant",
      text: "",
      pending: true,
      query,
    };
    S.chat.push(user, assistant);
    if ($("ai-chat-input")) {
      $("ai-chat-input").value = "";
      $("ai-chat-input").style.height = "auto";
    }
    renderChatMessages();
    let frame;
    const renderSoon = () => {
      if (!frame)
        frame = requestAnimationFrame(() => {
          frame = null;
          renderChatMessages();
        });
    };
    let complete = false;
    const consume = (event) => {
      const lines = event.split("\n"),
        kind = lines
          .find((line) => line.startsWith("event:"))
          ?.slice(6)
          .trim();
      const data = lines
        .filter((line) => line.startsWith("data:"))
        .map((line) => line.slice(5).trimStart())
        .join("\n");
      if (!data) return;
      const payload = parseJSON(data, {});
      if (kind === "status") {
        S.chatStatus = payload.message || "Finding your next step…";
        renderSoon();
      } else if (kind === "delta") {
        assistant.text += payload.text || "";
        renderSoon();
      } else if (kind === "complete") {
        complete = true;
        assistant.text = payload.answer || assistant.text;
        assistant.sources = payload.matched_opportunities || [];
        assistant.conflicts = payload.policy_conflicts || [];
        assistant.model = payload.model_used;
        assistant.lastSync = payload.last_sync;
      } else if (kind === "error")
        throw new ApiError(
          payload.message ||
            "This answer could not be completed. Please try again.",
          500,
        );
    };
    const timeout = setTimeout(() => controller.abort("timeout"), 60000);
    try {
      const response = await fetch(`${API_BASE}/assistant/ask`, {
        method: "POST",
        signal: controller.signal,
        headers: {
          "Content-Type": "application/json",
          Accept: "text/event-stream",
          ...(S.token ? { Authorization: `Bearer ${S.token}` } : {}),
        },
        body: JSON.stringify({
          query,
          opportunity_id: focus || null,
          stream: true,
        }),
      });
      if (!response.ok) {
        const error = await response.json().catch(() => ({}));
        throw new ApiError(
          error.detail ||
            "IRIS could not complete your answer. Please try again.",
          response.status,
        );
      }
      if (
        response.headers.get("content-type")?.includes("text/event-stream") &&
        response.body
      ) {
        const reader = response.body.getReader(),
          decoder = new TextDecoder();
        let buffer = "";
        while (true) {
          const { done, value } = await reader.read();
          if (done) {
            buffer += decoder.decode();
            break;
          }
          buffer += decoder
            .decode(value, { stream: true })
            .replace(/\r\n/g, "\n");
          let separator;
          while ((separator = buffer.indexOf("\n\n")) >= 0) {
            const event = buffer.slice(0, separator);
            buffer = buffer.slice(separator + 2);
            consume(event);
          }
        }
        if (buffer.trim()) consume(buffer);
        if (!complete)
          throw new ApiError(
            "The response was interrupted. You can try your question again.",
            0,
          );
      } else {
        const payload = await response.json();
        assistant.text = payload.answer || "";
        assistant.sources = payload.matched_opportunities || [];
        assistant.conflicts = payload.policy_conflicts || [];
        assistant.model = payload.model_used;
        complete = true;
      }
    } catch (error) {
      if (controller.signal.aborted)
        assistant.error =
          controller.signal.reason === "timeout"
            ? "The response took too long. Please try again."
            : "Response paused.";
      else
        assistant.error =
          error instanceof ApiError
            ? error.message
            : "Your connection was interrupted. Please try again.";
    } finally {
      clearTimeout(timeout);
      if (frame) cancelAnimationFrame(frame);
      assistant.pending = false;
      S.chatBusy = false;
      S.chatController = null;
      renderChatMessages();
      renderAIContext();
    }
  }
  async function saveWizard(complete = false) {
    captureWizard();
    const w = S.wizard;
    const values = {
      skills: w.skills,
      domains: [...w.domains],
      areas_of_interest: w.areas_of_interest || "",
    };
    for (const key of [
      "name",
      "state_domicile",
      "country",
      "academic_stage",
      "institution",
    ])
      if (String(w[key] || "").trim()) values[key] = String(w[key]).trim();
    if (w.age) values.age = Number(w.age);
    if (w.graduation_year) values.graduation_year = Number(w.graduation_year);
    for (const key of ["class_12_pct", "family_income_inr"])
      values[key] = w[key] === "" ? null : Number(w[key]);
    values.nirf_top_50 = w.nirf_top_50 === "" ? null : w.nirf_top_50 === "true";
    if (complete) values.onboarding_complete = true;
    S.profile = await post("/profile/update", values);
    updateShell();
  }
  async function nextWizard() {
    const form = $("onboarding-form");
    if (!form.reportValidity()) return;
    const button = $("wizard-continue");
    button.disabled = true;
    try {
      await saveWizard();
      navigate("onboarding", "2");
    } catch (error) {
      const el = $("wizard-form-error");
      el.hidden = false;
      el.textContent = error.message;
    } finally {
      if (button?.isConnected) button.disabled = false;
    }
  }
  async function finishWizard(button) {
    captureWizard();
    if (!S.wizard.domains.size) {
      const el = $("wizard-form-error");
      el.hidden = false;
      el.textContent = "Pick at least one possibility that interests you.";
      return;
    }
    button.disabled = true;
    try {
      await saveWizard(true);
      S.wizard = null;
      await loadWorkspace({ render: false });
      S.filter.category = "All Opportunities";
      navigate("opportunities");
      toast("Your space is ready. Let’s find what’s next.");
    } catch (error) {
      const el = $("wizard-form-error");
      el.hidden = false;
      el.textContent = error.message;
    } finally {
      if (button?.isConnected) button.disabled = false;
    }
  }
  async function uploadResume(file = null, sample = false) {
    if (!sample && !file) return;
    if (
      file &&
      (!/\.(pdf|docx|txt)$/i.test(file.name) || file.size > 5 * 1024 * 1024)
    ) {
      toast(
        file.size > 5 * 1024 * 1024
          ? "Choose a resume smaller than 5 MB."
          : "Choose a PDF, DOCX, or TXT resume.",
        "error",
      );
      return;
    }
    captureWizard();
    document
      .querySelectorAll(
        '[data-action="upload-resume"], [data-action="sample-resume"]',
      )
      .forEach((button) => {
        button.disabled = true;
        button.dataset.originalLabel = button.innerHTML;
        button.innerHTML = '<span class="spinner"></span>Reading your resume…';
      });
    try {
      let response;
      if (sample)
        response = await post(
          "/resume/analyze",
          { use_sample: true },
          { timeout: 60000 },
        );
      else {
        const body = new FormData();
        body.append("file", file);
        response = await api("/resume/analyze", {
          method: "POST",
          body,
          timeout: 60000,
        });
      }
      if (!response.success)
        throw new ApiError(
          "Your resume could not be analyzed. Please try another file.",
          400,
        );
      S.profile = await api("/profile");
      if (S.wizard) {
        S.wizard.skills = [...(S.profile.skills || [])];
        for (const key of [
          "academic_stage",
          "institution",
          "state_domicile",
          "country",
          "age",
        ])
          if (!S.wizard[key] && S.profile[key]) S.wizard[key] = S.profile[key];
      }
      updateShell();
      renderActive();
      S.opportunities = await api("/opportunities");
      if (["home", "opportunities"].includes(S.view)) renderActive();
      toast(
        sample
          ? "Sample resume analyzed. Your profile and matches are updated."
          : "A little more of your story, added. Your profile and matches are updated.",
      );
    } finally {
      document
        .querySelectorAll(
          '[data-action="upload-resume"], [data-action="sample-resume"]',
        )
        .forEach((button) => {
          button.disabled = false;
          if (button.dataset.originalLabel) {
            button.innerHTML = button.dataset.originalLabel;
            delete button.dataset.originalLabel;
          }
        });
      $("resume-upload").value = "";
    }
  }
  async function submitAuth(form) {
    const data = Object.fromEntries(new FormData(form)),
      signup = S.authMode === "signup";
    const button = $("auth-submit"),
      error = $("auth-error");
    error.hidden = true;
    if (new TextEncoder().encode(data.password).length > 72) {
      error.hidden = false;
      error.textContent = "Use a password with at most 72 UTF-8 bytes.";
      return;
    }
    button.disabled = true;
    try {
      const result = await post(`/auth/${signup ? "signup" : "login"}`, data);
      if (!result.token)
        throw new ApiError(
          "Your sign-in could not be completed. Please try again.",
          401,
        );
      S.token = result.token;
      S.user = result.user;
      localStorage.setItem("iris_token", result.token);
      S.wizard = null;
      S.chat = [];
      S.detail = null;
      await loadWorkspace({ render: false });
      navigate(
        signup || !S.profile?.onboarding_complete ? "onboarding" : "home",
        signup || !S.profile?.onboarding_complete ? "1" : null,
      );
      toast(
        signup ? "Welcome to your next chapter." : "Good to have you back.",
      );
    } catch (problem) {
      error.hidden = false;
      error.textContent = problem.message;
    } finally {
      if (button?.isConnected) button.disabled = false;
    }
  }
  async function signOut() {
    S.chatController?.abort();
    S.token = "";
    S.user = null;
    S.profile = null;
    S.saved = [];
    S.applications = [];
    S.chat = [];
    S.wizard = null;
    S.detail = null;
    S.chatFocus = null;
    S.guides.clear();
    S.documentDrafts.clear();
    localStorage.removeItem("iris_token");
    localStorage.removeItem("iris_user_data");
    await loadWorkspace({ render: false });
    navigate("login");
    toast("You’re signed out. Your progress is saved to your account.");
  }
  async function refreshSync({ notify = false } = {}) {
    const wasRunning = S.sync?.sync_running;
    S.sync = await api("/sync/status");
    updateShell();
    if ($("catalog-sync-status"))
      $("catalog-sync-status").textContent = S.sync.sync_running
        ? "A little refresh is in progress…"
        : S.sync.last_sync_iso
          ? "Your catalog refresh is complete"
          : "Your first refresh is ready";
    const syncDescription = document.querySelector(
      "#view-settings .sync-hero p",
    );
    if (syncDescription) {
      const seconds = Math.max(0, S.sync.seconds_until_next_run || 0);
      syncDescription.textContent = S.sync.sync_running
        ? "You can keep exploring while it runs."
        : S.sync.last_sync_iso
          ? `Next scheduled check in ${Math.floor(seconds / 3600)}h ${Math.floor((seconds % 3600) / 60)}m`
          : "Run a catalog check whenever you’re ready.";
    }
    if ($("sync-now-button")) {
      $("sync-now-button").disabled = S.sync.sync_running;
      $("sync-now-button").innerHTML =
        `${icon("refresh")}${S.sync.sync_running ? "Refreshing…" : "Refresh the catalog"}`;
    }
    if (wasRunning && !S.sync.sync_running) {
      await loadWorkspace({ render: false });
      if (["home", "opportunities", "saved", "applications"].includes(S.view))
        renderActive();
      if (notify) toast("Your catalog refresh is complete.");
    }
    return S.sync;
  }
  async function triggerSync(button) {
    button.disabled = true;
    try {
      const result = await post("/sync/trigger", { live: true });
      toast(
        result.status === "already_running"
          ? "A refresh is already in progress. You can keep exploring."
          : "Your catalog refresh is queued. You can keep exploring.",
      );
      await refreshSync();
      let checks = 0;
      const poll = async () => {
        try {
          const status = await refreshSync({ notify: true });
          if (status.sync_running && ++checks < 120) setTimeout(poll, 3000);
        } catch {
          /* The existing catalog remains available while the server reconnects. */
        }
      };
      setTimeout(poll, 1000);
    } finally {
      if (button?.isConnected) button.disabled = !!S.sync?.sync_running;
    }
  }
  async function scanPortal(form) {
    const input = $("scanner-query-input"),
      button = $("scanner-verify-btn"),
      result = $("scan-result");
    button.disabled = true;
    result.textContent =
      "Checking discovery, portal rendering, application status, and program rules…";
    try {
      const data = await post(
        "/opportunities/discover-and-verify",
        { query_or_url: input.value.trim(), live_agent: true },
        { timeout: 240000 },
      );
      result.textContent = data.message || "The portal check is complete.";
      if (data.is_verified && data.opportunity) {
        const link = document.createElement("a");
        link.href = `#detail/${encodeURIComponent(idOf(data.opportunity))}`;
        link.textContent = " Open the verified opportunity ↗";
        link.className = "text-link";
        result.appendChild(link);
        await loadWorkspace({ render: false });
      }
    } catch (error) {
      result.textContent = error.message;
    } finally {
      button.disabled = false;
    }
  }
  function showNotifications() {
    const el = $("notifications-popover"),
      opening = el.hidden;
    $("account-popover").hidden = true;
    $("account-trigger").setAttribute("aria-expanded", "false");
    el.innerHTML = `<h4>A few dates to keep close</h4>${
      upcoming()
        .slice(0, 4)
        .map(
          (opp) =>
            `<a href="#detail/${encodeURIComponent(idOf(opp))}">${icon("calendar", "icon-sm")}<span>${esc(opp.title)}<small>${dateFormat(deadline(opp).iso)} · ${deadline(opp).label}</small></span></a>`,
        )
        .join("") ||
      "<p>No upcoming tracked deadlines. A little breathing room.</p>"
    }<a href="#applications" style="margin-top:10px;color:var(--blue)">Your application space ${icon("arrow", "icon-sm")}</a>`;
    el.hidden = !opening;
    $("notifications-trigger").setAttribute("aria-expanded", String(opening));
  }
  const resetFilters = () => {
    S.filter = {
      category: "All Opportunities",
      query: "",
      location: "",
      deadline: "",
      sort: "match",
    };
    renderOpportunities();
  };
  async function action(name, el) {
    const id = el.dataset.id;
    switch (name) {
      case "export-data": {
        const response = await api("/profile/export", { raw: true });
        const blob = await response.blob();
        const link = document.createElement("a");
        link.href = URL.createObjectURL(blob);
        link.download = "iris-workspace.json";
        link.click();
        setTimeout(() => URL.revokeObjectURL(link.href), 1000);
        toast("Your workspace export is ready.");
        break;
      }
      case "remove-resume":
        el.disabled = true;
        try {
          S.profile = await api("/profile/resume", { method: "DELETE" });
          renderSettings();
          updateShell();
          toast("Stored resume text and file details removed.");
        } finally {
          if (el.isConnected) el.disabled = false;
        }
        break;
      case "open-detail":
        navigate("detail", id);
        break;
      case "explore":
        navigate("opportunities");
        break;
      case "reload":
        await loadWorkspace();
        if (S.view === "detail") await loadDetail(S.detailId, true);
        break;
      case "home-category":
        if (el.dataset.category === "AI Assistant") navigate("ai-assistant");
        else {
          S.filter = {
            category: el.dataset.category,
            query: "",
            location: "",
            deadline: "",
            sort: "match",
          };
          navigate("opportunities");
        }
        break;
      case "category":
        S.filter.category = el.dataset.category;
        renderResults();
        break;
      case "clear-filters":
        resetFilters();
        break;
      case "save":
        await toggleSave(id, el);
        break;
      case "apply":
        await openApplyOptionsModal(id);
        break;
      case "retry-guide":
        await openApplyOptionsModal(S.modalId);
        break;
      case "close-modal":
        $("apply-options-modal").close();
        break;
      case "track":
        await trackApplication(id, el);
        break;
      case "retry-documents":
        await queueDocuments(S.modalId);
        break;
      case "calendar":
        await downloadCalendar(id);
        break;
      case "calendar-all":
        await downloadCalendar();
        break;
      case "verify":
        await verifyOpportunity(id, el);
        break;
      case "application-filter":
        S.applicationFilter = el.dataset.status;
        renderApplications();
        break;
      case "untrack": {
        el.disabled = true;
        try {
          await api(`/applications/tracked/${encodeURIComponent(id)}`, {
            method: "DELETE",
          });
          S.applications = (await api("/applications/overview")).applications;
          S.guides.delete(id);
          if (S.detail && idOf(S.detail.opportunity) === id) S.detail = null;
          renderActive();
          updateShell();
          toast("Application removed from your tracker.");
        } finally {
          if (el.isConnected) el.disabled = false;
        }
        break;
      }
      case "calendar-prev":
      case "calendar-next": {
        const month = new Date(
          Date.UTC(
            S.calendar.year,
            S.calendar.month + (name === "calendar-prev" ? -1 : 1),
            1,
          ),
        );
        S.calendar.year = month.getUTCFullYear();
        S.calendar.month = month.getUTCMonth();
        S.calendar.selected = null;
        renderCalendar();
        break;
      }
      case "calendar-day":
        S.calendar.selected = el.dataset.date;
        renderCalendar();
        break;
      case "calendar-today":
        S.calendar = { ...currentCalendar(), selected: todayISO() };
        renderCalendar();
        break;
      case "ask-opportunity": {
        S.chatFocus = id;
        navigate("ai-assistant");
        await sendChat(
          `Help me understand my eligibility and how to apply for ${findOpp(id)?.title || "this opportunity"}.`,
          id,
        );
        break;
      }
      case "chat-prompt":
      case "retry-chat":
        await sendChat(el.dataset.query);
        break;
      case "send-chat":
        await sendChat($("ai-chat-input")?.value);
        break;
      case "stop-chat":
        S.chatController?.abort();
        break;
      case "new-chat":
        S.chatController?.abort();
        S.chat = [];
        S.chatBusy = false;
        renderChatMessages();
        renderAIContext();
        $("ai-chat-input")?.focus();
        break;
      case "clear-focus":
        S.chatFocus = null;
        renderAIContext();
        break;
      case "upload-resume":
        $("resume-upload").click();
        break;
      case "sample-resume":
        await uploadResume(null, true);
        break;
      case "remove-skill":
        captureWizard();
        S.wizard.skills.splice(Number(el.dataset.index), 1);
        $("editable-skill-tags").innerHTML = skillTagsEditable();
        break;
      case "interest": {
        captureWizard();
        const domain = el.dataset.domain;
        if (S.wizard.domains.has(domain)) S.wizard.domains.delete(domain);
        else S.wizard.domains.add(domain);
        const selected = S.wizard.domains.has(domain);
        el.classList.toggle("selected", selected);
        el.setAttribute("aria-pressed", String(selected));
        el.querySelector(".interest-check").innerHTML = selected
          ? icon("check")
          : "";
        break;
      }
      case "wizard-back":
        captureWizard();
        navigate("onboarding", "1");
        break;
      case "wizard-finish":
        await finishWizard(el);
        break;
      case "wizard-exit":
        el.disabled = true;
        try {
          await saveWizard();
          S.wizard = null;
          navigate("profile");
          toast("Your details are saved. Come back whenever you’re ready.");
        } finally {
          if (el.isConnected) el.disabled = false;
        }
        break;
      case "auth-switch":
        S.authMode = S.authMode === "login" ? "signup" : "login";
        renderLogin();
        break;
      case "logout":
        await signOut();
        break;
      case "sync":
        await triggerSync(el);
        break;
    }
  }
  document.addEventListener("click", (event) => {
    if (!event.target.closest("#account-popover, #account-trigger")) {
      $("account-popover").hidden = true;
      $("account-trigger").setAttribute("aria-expanded", "false");
    }
    if (
      !event.target.closest("#notifications-popover, #notifications-trigger")
    ) {
      $("notifications-popover").hidden = true;
      $("notifications-trigger").setAttribute("aria-expanded", "false");
    }
    if (event.ctrlKey || event.metaKey || event.button > 0) return;
    const el = event.target.closest("[data-action]");
    if (!el || el.disabled) return;
    event.preventDefault();
    Promise.resolve(action(el.dataset.action, el)).catch((error) =>
      toast(
        error.message ||
          "This action could not be completed. Please try again.",
        "error",
      ),
    );
  });
  document.addEventListener("submit", (event) => {
    const form = event.target;
    const handler = {
      "home-search-form": () => {
        S.filter = {
          category: "All Opportunities",
          query: $("home-search-input").value.trim(),
          location: "",
          deadline: "",
          sort: "match",
        };
        navigate("opportunities");
      },
      "opportunity-search-form": () => {
        S.filter.query = $("opportunity-search").value.trim();
        renderResults();
      },
      "onboarding-form": nextWizard,
      "auth-form": () => submitAuth(form),
      "ai-chat-form": () => sendChat($("ai-chat-input").value),
      "scan-form": () => scanPortal(form),
    }[form.id];
    if (handler) {
      event.preventDefault();
      Promise.resolve(handler()).catch((error) =>
        toast(error.message, "error"),
      );
    }
  });
  document.addEventListener("input", (event) => {
    if (event.target.id === "opportunity-search") {
      S.filter.query = event.target.value;
      renderResults();
    }
    if (event.target.id === "ai-chat-input") {
      event.target.style.height = "auto";
      event.target.style.height = `${Math.min(135, event.target.scrollHeight)}px`;
    }
  });
  document.addEventListener("change", (event) => {
    const el = event.target;
    const filters = {
      "category-filter": "category",
      "location-filter": "location",
      "deadline-filter": "deadline",
      "sort-filter": "sort",
    };
    if (filters[el.id]) {
      S.filter[filters[el.id]] = el.value;
      renderResults();
    }
    if (el.id === "resume-upload")
      uploadResume(el.files[0]).catch((error) => toast(error.message, "error"));
    if (el.dataset.guideDocument != null && S.modalId) {
      const id = S.modalId,
        guide = S.guides.get(id);
      const selected = [
        ...$("apply-options-modal-body").querySelectorAll(
          "[data-guide-document]:checked",
        ),
      ].map(
        (input) =>
          guide.required_documents[Number(input.dataset.guideDocument)],
      );
      S.documentDrafts.set(id, selected);
      clearTimeout(S.documentTimer);
      S.documentTimer = setTimeout(
        () => queueDocuments(id).catch(() => {}),
        250,
      );
    }
    if (el.dataset.applicationStatus) {
      el.disabled = true;
      post("/applications/track", {
        opportunity_id: el.dataset.applicationStatus,
        status: el.value,
      })
        .then(async () => {
          S.applications = (await api("/applications/overview")).applications;
          S.guides.delete(el.dataset.applicationStatus);
          renderApplications();
          toast("Your application progress is updated.");
        })
        .catch((error) => {
          toast(error.message, "error");
          renderApplicationList();
        })
        .finally(() => {
          if (el.isConnected) el.disabled = false;
        });
    }
    if (el.dataset.preference) {
      const previous = !el.checked;
      el.disabled = true;
      post("/profile/update", {
        preferences: { [el.dataset.preference]: el.checked },
      })
        .then((profile) => {
          S.profile = profile;
          updateShell();
          toast("A little more like you. Preference saved.");
        })
        .catch((error) => {
          el.checked = previous;
          toast(error.message, "error");
        })
        .finally(() => {
          el.disabled = false;
        });
    }
  });
  document.addEventListener("keydown", (event) => {
    if ((event.metaKey || event.ctrlKey) && event.key.toLowerCase() === "k") {
      event.preventDefault();
      focusSearch();
    }
    if (event.key === "Escape") {
      closeNavigation();
      $("notifications-popover").hidden = true;
      $("account-popover").hidden = true;
    }
    if (
      event.target.id === "ai-chat-input" &&
      event.key === "Enter" &&
      !event.shiftKey &&
      !event.isComposing
    ) {
      event.preventDefault();
      sendChat(event.target.value).catch((error) =>
        toast(error.message, "error"),
      );
    }
    if (
      event.target.id === "setup-skills" &&
      ["Enter", ","].includes(event.key)
    ) {
      event.preventDefault();
      const values = event.target.value
        .split(",")
        .map((value) => value.trim())
        .filter(Boolean);
      S.wizard.skills = [...new Set([...S.wizard.skills, ...values])].slice(
        0,
        40,
      );
      event.target.value = "";
      $("editable-skill-tags").innerHTML = skillTagsEditable();
    }
    if (
      event.key === "Enter" &&
      event.target.matches(".opportunity-card, .featured-opportunity")
    ) {
      event.preventDefault();
      navigate("detail", event.target.dataset.id);
    }
  });
  document.addEventListener("dragover", (event) => {
    if (event.target.closest("[data-dropzone]")) {
      event.preventDefault();
      event.dataTransfer.dropEffect = "copy";
    }
  });
  document.addEventListener("drop", (event) => {
    if (event.target.closest("[data-dropzone]")) {
      event.preventDefault();
      uploadResume(event.dataTransfer.files[0]).catch((error) =>
        toast(error.message, "error"),
      );
    }
  });
  function focusSearch() {
    if (S.view !== "opportunities") navigate("opportunities");
    setTimeout(() => $("opportunity-search")?.focus(), 50);
  }
  $("menu-toggle").innerHTML = icon("menu");
  $("global-search-icon").innerHTML = icon("search");
  $("notifications-trigger").innerHTML = icon("bell");
  $("account-chevron").innerHTML = icon("down");
  $("apply-options-modal").querySelector(
    '[data-action="close-modal"]',
  ).innerHTML = icon("close");
  $("menu-toggle").addEventListener("click", () => {
    const opening = !$("sidebar").classList.contains("is-open");
    $("sidebar").classList.toggle("is-open", opening);
    $("sidebar-backdrop").hidden = !opening;
    $("menu-toggle").setAttribute("aria-expanded", String(opening));
  });
  $("sidebar-backdrop").addEventListener("click", closeNavigation);
  $("global-search-trigger").addEventListener("click", focusSearch);
  $("notifications-trigger").addEventListener("click", showNotifications);
  $("account-trigger").addEventListener("click", () => {
    const opening = $("account-popover").hidden;
    $("account-popover").hidden = !opening;
    $("notifications-popover").hidden = true;
    $("notifications-trigger").setAttribute("aria-expanded", "false");
    $("account-trigger").setAttribute("aria-expanded", String(opening));
  });
  $("apply-options-modal").addEventListener("close", () => {
    S.modalId = null;
    S.modalVersion += 1;
  });
  $("apply-options-modal").addEventListener("click", (event) => {
    if (event.target === $("apply-options-modal")) {
      const r = event.target.getBoundingClientRect();
      if (
        event.clientX < r.left ||
        event.clientX > r.right ||
        event.clientY < r.top ||
        event.clientY > r.bottom
      )
        event.target.close();
    }
  });
  window.addEventListener("hashchange", handleRoute);
  window.switchView = switchView;
  window.openApplyOptionsModal = openApplyOptionsModal;
  window.closeApplyOptionsModal = () => $("apply-options-modal").close();
  window.irisState = S;
  async function initialize() {
    handleRoute();
    if (S.token) {
      try {
        S.user = await api("/auth/me");
      } catch (error) {
        if (error.status === 401) {
          S.token = "";
          localStorage.removeItem("iris_token");
        }
      }
    }
    await loadWorkspace();
    if (S.view === "detail") await loadDetail(S.detailId);
    setInterval(() => {
      if (document.visibilityState === "visible" && S.ready && !S.error)
        refreshSync().catch(() => {});
    }, 30000);
  }
  initialize().catch((error) => {
    S.ready = true;
    S.error = error.message;
    renderActive();
  });
})();
