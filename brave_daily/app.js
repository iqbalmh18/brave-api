/* ===================================================================
   Brave Daily — Application Logic
   Vanilla JS single-page app matching brave-api.svg design system.
   =================================================================== */

const state = { data: null, module: "pulse", theme: localStorage.getItem("theme") || "auto" };
const $ = (sel) => document.querySelector(sel);
const $$ = (sel) => document.querySelectorAll(sel);
const reducedMotion = window.matchMedia("(prefers-reduced-motion: reduce)").matches;

const MODULE_COLORS = {
  pulse: { accent: "var(--pulse)", soft: "var(--pulse-soft)", dim: "var(--pulse-dim)", line: "var(--pulse-line)" },
  trends: { accent: "var(--trends)", soft: "var(--trends-soft)", dim: "var(--trends-dim)", line: "var(--trends-line)" },
  threats: { accent: "var(--threats)", soft: "var(--threats-soft)", dim: "var(--threats-dim)", line: "var(--threats-line)" },
  market: { accent: "var(--market)", soft: "var(--market-soft)", dim: "var(--market-dim)", line: "var(--market-line)" },
  datalab: { accent: "var(--datalab)", soft: "var(--datalab-soft)", dim: "var(--datalab-dim)", line: "var(--datalab-line)" },
  playground: { accent: "var(--playground)", soft: "var(--playground-soft)", dim: "var(--playground-dim)", line: "var(--playground-line)" },
};

function esc(v) { return String(v ?? "").replace(/[&<>'"]/g, c => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", "'": "&#39;", '"': "&quot;" })[c]); }
function truncate(text, max = 120) { return text && text.length > max ? text.slice(0, max) + "…" : text || ""; }

function setModuleColors(mod) {
  const colors = MODULE_COLORS[mod] || MODULE_COLORS.pulse;
  const root = document.documentElement.style;
  root.setProperty("--accent", colors.accent);
  root.setProperty("--accent-soft", colors.soft);
  root.setProperty("--accent-dim", colors.dim);
  root.setProperty("--accent-line", colors.line);
}

function bindThemeToggle() {
  const btn = $("#theme-toggle");
  if (!btn) return;

  function applyTheme(theme) {
    if (theme === "light") {
      document.documentElement.setAttribute("data-theme", "light");
    } else if (theme === "dark") {
      document.documentElement.setAttribute("data-theme", "dark");
    } else {
      document.documentElement.removeAttribute("data-theme");
    }
  }

  applyTheme(state.theme);

  btn.addEventListener("click", () => {
    const current = document.documentElement.getAttribute("data-theme");
    const systemDark = window.matchMedia("(prefers-color-scheme: dark)").matches;
    let nextTheme = "light";
    if (current === "light") nextTheme = "dark";
    else if (current === "dark") nextTheme = "light";
    else nextTheme = systemDark ? "light" : "dark";

    state.theme = nextTheme;
    localStorage.setItem("theme", nextTheme);
    applyTheme(nextTheme);
  });
}

function bindAmbient() {
  if (reducedMotion) return;
  let frame = 0;
  window.addEventListener("pointermove", (e) => {
    if (frame) return;
    frame = requestAnimationFrame(() => {
      document.documentElement.style.setProperty("--pointer-x", `${e.clientX}px`);
      document.documentElement.style.setProperty("--pointer-y", `${e.clientY}px`);
      document.documentElement.style.setProperty("--pointer-x-ratio", `${e.clientX / window.innerWidth}`);
      document.documentElement.style.setProperty("--pointer-y-ratio", `${e.clientY / window.innerHeight}`);
      frame = 0;
    });
  }, { passive: true });
  window.addEventListener("scroll", () => {
    document.documentElement.style.setProperty("--scroll-y", `${window.scrollY}px`);
  }, { passive: true });
}

function bindReveal(selector = ".intel-card, .trend-card, .threat-item, .market-card, .download-card, .playground-card") {
  const els = $$(selector);
  if (reducedMotion || !("IntersectionObserver" in window)) {
    els.forEach(el => el.classList.add("is-visible"));
    return;
  }
  const observer = new IntersectionObserver((entries, obs) => {
    entries.forEach(entry => {
      if (!entry.isIntersecting) return;
      entry.target.classList.add("is-visible");
      obs.unobserve(entry.target);
    });
  }, { threshold: 0.08 });
  els.forEach((el, i) => {
    el.style.transitionDelay = `${i * 0.04}s`;
    observer.observe(el);
  });
}

function animateCounter(el, target, duration = 800) {
  if (!el) return;
  if (reducedMotion) { el.textContent = target.toLocaleString(); return; }
  const start = performance.now();
  function tick(now) {
    const progress = Math.min((now - start) / duration, 1);
    const eased = 1 - Math.pow(1 - progress, 3);
    el.textContent = Math.round(target * eased).toLocaleString();
    if (progress < 1) requestAnimationFrame(tick);
  }
  requestAnimationFrame(tick);
}

function renderStats() {
  const stats = state.data.stats || {};
  const date = new Date(state.data.generated_at);
  const dateStr = date.toLocaleDateString("en-US", { month: "short", day: "numeric", year: "numeric" });
  const timeStr = date.toLocaleTimeString("en-US", { hour: "2-digit", minute: "2-digit" });

  animateCounter($("#stat-articles .stat-value"), stats.total_articles || 0);
  animateCounter($("#stat-sources .stat-value"), stats.total_sources || 0);
  animateCounter($("#stat-threats .stat-value"), stats.total_threats || 0);
  animateCounter($("#stat-trends .stat-value"), stats.total_trends || 0);

  const genEl = $("#stat-generated .stat-value");
  if (genEl) {
    genEl.textContent = dateStr;
    genEl.title = `${dateStr} at ${timeStr}`;
  }
}

function renderPulse() {
  const pulse = state.data.pulse || {};
  const domains = pulse.domains || [];
  const brief = state.data.brief || "";
  const briefSource = state.data.brief_source || "";

  let html = `
    <div class="intel-brief">
      <div class="intel-brief-header">
        <span class="intel-brief-kicker">DAILY INTELLIGENCE BRIEF</span>
        <span class="intel-brief-source">via ${esc(briefSource)}</span>
      </div>
      <div class="intel-brief-text"><p>${esc(brief)}</p></div>
    </div>
    <div class="section-header"><h2>Intelligence Domains</h2><span>${domains.length} active domains</span></div>
    <div class="domain-slider" aria-label="Intelligence domains slider">
      <button class="slider-control slider-prev" type="button" data-slider-direction="prev" aria-label="Previous intelligence domain">‹</button>
      <div class="card-grid">
  `;

  for (const domain of domains) {
    const articles = domain.articles || [];
    const images = domain.images || [];
    html += `
      <article class="intel-card" data-domain="${esc(domain.id)}" tabindex="0" role="button"
               aria-label="Explore ${esc(domain.label)}">
        <div class="card-header">
          <span class="card-domain">
            ${esc(domain.label)}
            <span class="diversity-badge">${domain.diversity_score || 0} sources</span>
          </span>
        </div>
        <div class="card-summary">${esc(truncate(domain.summary, 160))}</div>
        <div class="card-articles">
    `;
    for (let i = 0; i < Math.min(articles.length, 4); i++) {
      const a = articles[i];
      html += `
        <div class="card-article">
          <span class="card-article-num">${String(i + 1).padStart(2, "0")}</span>
          <div>
            <div class="card-article-title">${esc(truncate(a.title, 90))}</div>
            <div class="card-article-meta">${esc(a.source)} · ${esc(a.age)}</div>
          </div>
        </div>
      `;
    }
    html += `</div><div class="card-footer">
      <button class="card-explore" data-domain="${esc(domain.id)}">
        <span>Open</span>
        <svg viewBox="0 0 16 16" width="12" height="12" fill="none" stroke="currentColor" stroke-width="2"><path d="M4 12L12 4M6 4h6v6" stroke-linecap="round" stroke-linejoin="round"/></svg>
      </button>
      <div class="card-images">`;
    for (const img of images.slice(0, 3)) {
      if (img.thumbnail) html += `<img src="${esc(img.thumbnail)}" alt="" loading="lazy" />`;
    }
    html += `</div></div></article>`;
  }
  html += `</div><button class="slider-control slider-next" type="button" data-slider-direction="next" aria-label="Next intelligence domain">›</button></div>`;
  return html;
}

function renderTrends() {
  const trends = state.data.trends || [];
  let html = `
    <div class="section-header"><h2>Trend Radar</h2><span>${trends.length} topics tracked</span></div>
    <p class="section-desc">Topic momentum tracked via Brave News article volume. Rising = 5+ articles, Stable = 2-4, Cooling = 0-1.</p>
    <div class="trend-grid">
  `;
  for (const t of trends) {
    const momentumSvg = t.momentum === "rising"
      ? `<svg viewBox="0 0 16 16" width="12" height="12" fill="none" stroke="currentColor" stroke-width="2"><path d="M12 10L8 6 4 10" stroke-linecap="round" stroke-linejoin="round"/></svg>`
      : t.momentum === "cooling"
        ? `<svg viewBox="0 0 16 16" width="12" height="12" fill="none" stroke="currentColor" stroke-width="2"><path d="M4 6l4 4 4-4" stroke-linecap="round" stroke-linejoin="round"/></svg>`
        : `<svg viewBox="0 0 16 16" width="12" height="12" fill="none" stroke="currentColor" stroke-width="2"><line x1="4" y1="8" x2="12" y2="8" stroke-linecap="round"/></svg>`;

    html += `
      <div class="trend-card" tabindex="0" role="button" data-topic="${esc(t.topic_id)}">
        <div>
          <div class="trend-label">${esc(t.label)}</div>
          <div class="trend-headline">${esc(truncate(t.top_headline, 80))}</div>
          <div class="trend-meta">
            <span class="trend-count">${t.article_count} articles</span>
            <span class="trend-momentum" data-momentum="${esc(t.momentum)}">${momentumSvg} ${esc(t.momentum)}</span>
          </div>
        </div>
        <div class="trend-spark">
          <div class="trend-bar-container" style="border-color: var(--${t.momentum})">
            <span class="trend-bar-value">${t.article_count}</span>
          </div>
        </div>
      </div>
    `;
  }
  html += `</div>`;
  return html;
}

function renderThreats() {
  const threats = state.data.threats || [];
  const severityCounts = { critical: 0, high: 0, medium: 0, low: 0 };
  threats.forEach(t => { severityCounts[t.severity] = (severityCounts[t.severity] || 0) + 1; });

  let html = `
    <div class="section-header"><h2>Threat Wire</h2><span>${threats.length} threats detected</span></div>
    <p class="section-desc">
      <span style="color:var(--sev-critical)">● ${severityCounts.critical} Critical</span> &nbsp;
      <span style="color:var(--sev-high)">● ${severityCounts.high} High</span> &nbsp;
      <span style="color:var(--sev-medium)">● ${severityCounts.medium} Medium</span> &nbsp;
      <span style="color:var(--sev-low)">● ${severityCounts.low} Low</span>
    </p>
    <div class="threat-list">
  `;
  for (const t of threats) {
    const indicators = (t.indicators || []).map(ioc => `<span class="ioc-tag">${esc(ioc)}</span>`).join("");
    html += `
      <div class="threat-item" tabindex="0" role="button" data-url="${esc(t.url)}">
        <div class="threat-severity">
          <span class="severity-badge" data-severity="${esc(t.severity)}">${esc(t.severity)}</span>
          <span class="threat-category">${esc(t.category)}</span>
        </div>
        <div class="threat-body">
          <div class="threat-title">${esc(t.title)}</div>
          <div class="threat-desc">${esc(truncate(t.description, 160))}</div>
          ${indicators ? `<div class="threat-indicators">${indicators}</div>` : ""}
        </div>
        <div class="threat-source">
          <span class="threat-source-name">${esc(t.source)}</span>
          <span class="threat-source-age">${esc(t.age)}</span>
        </div>
      </div>
    `;
  }
  html += `</div>`;
  return html;
}

function renderMarket() {
  const sectors = state.data.market || [];
  let html = `
    <div class="section-header"><h2>Market Scanner</h2><span>${sectors.length} sectors tracked</span></div>
    <p class="section-desc">Financial intelligence signals aggregated from Brave News with AI-generated sentiment analysis.</p>
    <div class="market-grid">
  `;
  for (const sector of sectors) {
    const articles = sector.articles || [];
    html += `
      <div class="market-card">
        <div class="market-header">
          <span class="market-label">${esc(sector.label)}</span>
          <span class="market-sentiment">${esc(sector.id)}</span>
        </div>
        <div class="market-summary">${esc(truncate(sector.sentiment, 200))}</div>
        <div class="market-articles">
    `;
    for (const a of articles.slice(0, 5)) {
      html += `
        <a class="market-article" href="${esc(a.url)}" target="_blank" rel="noopener">
          <div class="market-article-title">${esc(truncate(a.title, 100))}</div>
          <div class="market-article-meta">${esc(a.source)} · ${esc(a.age)}</div>
        </a>
      `;
    }
    html += `</div></div>`;
  }
  html += `</div>`;
  return html;
}

function renderDataLab() {
  const stats = state.data.stats || {};
  return `
    <div class="datalab-hero">
      <h2>Data Lab</h2>
      <p>Download today's complete intelligence dataset. ${stats.total_articles || 0} articles from ${stats.total_sources || 0} sources, ${stats.total_threats || 0} threat items, and ${stats.total_trends || 0} trending topics — all machine-readable.</p>
    </div>
    <div class="datalab-grid">
      <div class="download-card" id="dl-json">
        <div class="download-icon">
          <svg viewBox="0 0 24 24" width="24" height="24" fill="none" stroke="currentColor" stroke-width="2"><path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/><polyline points="14 2 14 8 20 8"/></svg>
        </div>
        <div class="download-title">Full Dataset (JSON)</div>
        <div class="download-desc">Complete intelligence harvest — all modules, articles, images, videos, and AI summaries in structured JSON.</div>
        <a class="download-btn" href="data/intel.json" download="brave-intel-hub.json">
          <svg viewBox="0 0 16 16" width="12" height="12" fill="none" stroke="currentColor" stroke-width="2"><path d="M8 2v9M4 7l4 4 4-4M2 13h12"/></svg>
          Download JSON
        </a>
      </div>
      <div class="download-card" id="dl-csv">
        <div class="download-icon">
          <svg viewBox="0 0 24 24" width="24" height="24" fill="none" stroke="currentColor" stroke-width="2"><line x1="18" y1="20" x2="18" y2="10"/><line x1="12" y1="20" x2="12" y2="4"/><line x1="6" y1="20" x2="6" y2="14"/></svg>
        </div>
        <div class="download-title">Tabular Export (CSV)</div>
        <div class="download-desc">Flattened spreadsheet-ready format. Import into Excel, Google Sheets, or any data tool for analysis.</div>
        <a class="download-btn" href="data/export.csv" download="brave-intel-hub.csv">
          <svg viewBox="0 0 16 16" width="12" height="12" fill="none" stroke="currentColor" stroke-width="2"><path d="M8 2v9M4 7l4 4 4-4M2 13h12"/></svg>
          Download CSV
        </a>
      </div>
      <div class="download-card" id="dl-threats">
        <div class="download-icon">
          <svg viewBox="0 0 24 24" width="24" height="24" fill="none" stroke="currentColor" stroke-width="2"><path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z"/></svg>
        </div>
        <div class="download-title">Threat Feed (JSON)</div>
        <div class="download-desc">STIX-lite structured threat intelligence feed. Ingestible by SIEM tools, threat platforms, and security scripts.</div>
        <a class="download-btn" href="data/threats.json" download="brave-threat-feed.json">
          <svg viewBox="0 0 16 16" width="12" height="12" fill="none" stroke="currentColor" stroke-width="2"><path d="M8 2v9M4 7l4 4 4-4M2 13h12"/></svg>
          Download Feed
        </a>
      </div>
      <div class="download-card" id="dl-report">
        <div class="download-icon">
          <svg viewBox="0 0 24 24" width="24" height="24" fill="none" stroke="currentColor" stroke-width="2"><path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/><line x1="16" y1="13" x2="8" y2="13"/><line x1="16" y1="17" x2="8" y2="17"/><polyline points="10 9 9 9 8 9"/></svg>
        </div>
        <div class="download-title">Daily Report (Markdown)</div>
        <div class="download-desc">Formatted intelligence report ready for sharing. Includes all modules, severity ratings, and trend analysis.</div>
        <a class="download-btn" href="data/report.md" download="brave-intel-report.md">
          <svg viewBox="0 0 16 16" width="12" height="12" fill="none" stroke="currentColor" stroke-width="2"><path d="M8 2v9M4 7l4 4 4-4M2 13h12"/></svg>
          Download Report
        </a>
      </div>
    </div>
  `;
}

function renderPlayground() {
  const demos = state.data.playground || [];
  let html = `
    <div class="section-header"><h2>Search Playground</h2><span>${demos.length} API demos</span></div>
    <p class="section-desc">Pre-built examples showcasing brave-api capabilities. Each card shows the Python code, query, and real results fetched today.</p>
    <div class="playground-grid">
  `;
  for (const demo of demos) {
    const codeHighlighted = esc(demo.python_code)
      .replace(/(await|async|for|in|print)/g, '<span class="kw">$1</span>')
      .replace(/(&quot;[^&]*&quot;)/g, '<span class="str">$1</span>')
      .replace(/(client\.\w+\(\))/g, '<span class="fn">$1</span>');

    html += `
      <div class="playground-card">
        <div class="playground-header">
          <span class="playground-method">${esc(demo.api_method)}</span>
          <span class="playground-count">${demo.result_count} results</span>
        </div>
        <div class="playground-query">
          <div class="playground-query-label">Query</div>
          <div class="playground-query-text">${esc(demo.query)}</div>
        </div>
        <div class="playground-code"><pre>${codeHighlighted}</pre></div>
        <div class="playground-results">
    `;

    if (demo.query_id === "image_demo") {
      const images = demo.results || [];
      if (images.length) {
        html += `<div class="playground-result-img">`;
        for (const img of images.slice(0, 6)) {
          if (img.thumbnail) html += `<img src="${esc(img.thumbnail)}" alt="${esc(img.title || "")}" loading="lazy" />`;
        }
        html += `</div>`;
      }
    } else if (demo.query_id === "ask_demo") {
      for (const r of demo.results || []) {
        html += `<div class="playground-result-item"><div class="playground-result-text">${esc(truncate(r.text, 300))}</div></div>`;
      }
    } else {
      for (const r of (demo.results || []).slice(0, 4)) {
        html += `
          <a class="playground-result-item" href="${esc(r.url || "#")}" target="_blank" rel="noopener">
            <div class="playground-result-title">${esc(truncate(r.title, 80))}</div>
            <div class="playground-result-meta">${esc(r.source || r.channel || "")} ${r.age ? "· " + esc(r.age) : ""} ${r.duration ? "· " + esc(r.duration) : ""}</div>
          </a>
        `;
      }
    }
    html += `</div></div>`;
  }
  html += `</div>`;
  return html;
}

const RENDERERS = {
  pulse: renderPulse,
  trends: renderTrends,
  threats: renderThreats,
  market: renderMarket,
  datalab: renderDataLab,
  playground: renderPlayground,
};

function renderModule(mod) {
  state.module = mod;
  setModuleColors(mod);
  const renderer = RENDERERS[mod];
  if (renderer && state.data) {
    $("#app").innerHTML = renderer();
    bindReveal();
    bindModuleInteractions(mod);
  }
  $$(".tab").forEach(tab => {
    tab.classList.toggle("active", tab.dataset.module === mod);
  });
}

function bindModuleInteractions(mod) {
  if (mod === "pulse") {
    const slider = $(".domain-slider .card-grid");
    const previousButton = $(".domain-slider .slider-prev");
    const nextButton = $(".domain-slider .slider-next");

    const updateSliderControls = () => {
      if (!slider || !previousButton || !nextButton) return;
      const maxScrollLeft = slider.scrollWidth - slider.clientWidth;
      previousButton.hidden = maxScrollLeft <= 1 || slider.scrollLeft <= 1;
      nextButton.hidden = maxScrollLeft <= 1 || slider.scrollLeft >= maxScrollLeft - 1;
    };

    $$(".domain-slider .slider-control").forEach(button => {
      button.addEventListener("click", () => {
        const direction = button.dataset.sliderDirection === "next" ? 1 : -1;
        slider?.scrollBy({ left: direction * (slider.clientWidth * 0.82), behavior: "smooth" });
      });
    });
    slider?.addEventListener("scroll", updateSliderControls, { passive: true });
    window.addEventListener("resize", updateSliderControls, { passive: true });
    updateSliderControls();

    $$(".intel-card").forEach(card => {
      const handler = () => openPulseDetail(card.dataset.domain);
      card.addEventListener("click", handler);
      card.addEventListener("keydown", e => { if (e.key === "Enter" || e.key === " ") { e.preventDefault(); handler(); } });
    });
  }
  if (mod === "trends") {
    $$(".trend-card").forEach(card => {
      card.addEventListener("click", () => {
        const topic = state.data.trends.find(t => t.topic_id === card.dataset.topic);
        if (topic && topic.top_url) window.open(topic.top_url, "_blank");
      });
    });
  }
  if (mod === "threats") {
    $$(".threat-item").forEach(item => {
      item.addEventListener("click", () => {
        if (item.dataset.url) window.open(item.dataset.url, "_blank");
      });
    });
  }
}

function openPulseDetail(domainId) {
  const domain = (state.data.pulse?.domains || []).find(d => d.id === domainId);
  if (!domain) return;
  const articles = domain.articles || [];
  const images = domain.images || [];

  let html = `
    <div class="detail-kicker">${esc(domain.label)}</div>
    <h2 class="detail-title">${esc(articles[0]?.title || domain.label)}</h2>
    <div class="detail-narrative"><p>${esc(domain.summary)}</p></div>
    <div class="detail-section-title">NEWS SOURCES (${articles.length})</div>
  `;
  for (const a of articles) {
    html += `<a class="detail-article" href="${esc(a.url)}" target="_blank" rel="noopener"><strong>${esc(a.title)}</strong><small>${esc(a.source)} · ${esc(a.age)}</small></a>`;
  }
  if (images.length) {
    html += `<div class="detail-section-title">VISUAL CONTEXT</div><div class="detail-images">`;
    for (const img of images.slice(0, 6)) {
      if (img.thumbnail) html += `<a href="${esc(img.url)}" target="_blank" rel="noopener"><img src="${esc(img.thumbnail)}" alt="${esc(img.title || "")}" loading="lazy" /></a>`;
    }
    html += `</div>`;
  }
  html += `<a class="detail-search-link" href="https://search.brave.com/search?q=${encodeURIComponent(domain.query)}" target="_blank" rel="noopener">Explore on Brave Search →</a>`;

  $("#detail-content").innerHTML = html;
  $("#detail-dialog").showModal();
}

function bindTabs() {
  $$(".tab").forEach(tab => {
    tab.addEventListener("click", () => renderModule(tab.dataset.module));
  });
}

function bindDialog() {
  $("#dialog-close").addEventListener("click", () => $("#detail-dialog").close());
  $("#detail-dialog").addEventListener("click", (e) => {
    if (e.target === $("#detail-dialog")) $("#detail-dialog").close();
  });
}

async function init() {
  try {
    const response = await fetch("data/intel.json");
    if (!response.ok) throw new Error(`HTTP ${response.status}`);
    state.data = await response.json();
    renderStats();
    renderModule("pulse");
  } catch (error) {
    $("#app").innerHTML = `<p class="error">Brave Daily data is temporarily unavailable. Deploy the generator first.</p>`;
    console.error("Init failed:", error);
  }
}

bindThemeToggle();
bindAmbient();
bindTabs();
bindDialog();
init();
