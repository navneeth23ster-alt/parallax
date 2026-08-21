/* Parallax UI — vanilla JS, hash routing (#/story/<id>) */
const $ = (sel, el = document) => el.querySelector(sel);
const feedEl = $("#feed"), detailEl = $("#detail"), searchEl = $("#search");
const CATS = ["alarmist", "delegitimizing", "sympathetic", "minimizing", "militarized"];

const esc = (s) =>
  String(s).replace(/[&<>"']/g, (c) =>
    ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));

const when = (iso) => (iso ? iso.slice(0, 16).replace("T", " ") : "—");

/* Highlight loaded terms inside an (escaped) headline.
   Terms come from the API per category, so marks are data, not guesses. */
function markTerms(title, loadedTerms) {
  let html = esc(title);
  for (const [cat, terms] of Object.entries(loadedTerms || {})) {
    for (const t of [...terms].sort((a, b) => b.length - a.length)) {
      const re = new RegExp(`\\b(${esc(t).replace(/[.*+?^${}()|[\]\\]/g, "\\$&")})\\b`, "gi");
      html = html.replace(re, `<mark class="${cat}">$1</mark>`);
    }
  }
  return html;
}

async function api(path) {
  const r = await fetch(path);
  if (!r.ok) throw new Error(`${r.status} on ${path}`);
  return r.json();
}

/* ---------- feed ---------- */
let stories = [];
async function loadFeed(q = "") {
  const r = await api(`/api/stories${q ? `?q=${encodeURIComponent(q)}` : ""}`);
  stories = r.stories;
  renderFeed();
}
function renderFeed() {
  const current = location.hash.split("/")[2] || "";
  feedEl.innerHTML = stories.length
    ? stories.map((s) => `
      <a href="#/story/${s.id}" class="${s.id === current ? "active" : ""}">
        <h3>${esc(s.label)}</h3>
        <div class="row">
          <span>${s.outlet_count} outlets</span>
          <span>div ${s.divergence.toFixed(2)}</span>
          ${s.discrepancies ? `<span class="badge disc">${s.discrepancies} discrepancy</span>` : ""}
          ${s.consequence_kinds.map((k) => `<span class="badge conseq">${esc(k)}</span>`).join("")}
        </div>
      </a>`).join("")
    : `<p style="padding:18px;color:var(--dim)">No stories yet — run
       <code>python -m parallax run</code> first.</p>`;
}

/* ---------- detail ---------- */
function legendHtml() {
  return `<div class="legend">${CATS.map(
    (c) => `<span><i style="background:var(--${c})"></i>${c}</span>`).join("")}</div>`;
}

function coverageHtml(cov) {
  return cov.map((c) => `
    <article class="cov">
      <div class="who"><b>${esc(c.outlet)}</b><span>${esc(c.placement)}</span>
        <span>${when(c.published)}</span></div>
      <p class="headline">${
        c.link
          ? `<a href="${esc(c.link)}" target="_blank" rel="noopener">${markTerms(c.title, c.loaded_terms)}</a>`
          : markTerms(c.title, c.loaded_terms)
      }</p>
      ${c.passive_voice ? `<p class="passive">agentless passive voice in headline</p>` : ""}
    </article>`).join("");
}

function factsHtml(facts, numeric) {
  const rows = facts.map((f) => `
    <div class="fact">
      <span class="tier ${f.tier}">${f.tier}</span>
      <span class="when">${when(f.first_seen)}</span>
      <span>${esc(f.text)} <span class="src">(${esc(f.outlets.join(", "))})</span></span>
    </div>`);
  for (const n of numeric.filter((n) => !n.agreement)) {
    const vals = Object.entries(n.values).map(([o, v]) => `${o}: ${v}`).join(", ");
    rows.push(`
      <div class="fact">
        <span class="tier discrepancy">discrepancy</span>
        <span class="when">&nbsp;</span>
        <span>number near “…${esc(n.context)}” — ${esc(vals)}</span>
      </div>`);
  }
  return rows.join("") || `<p class="note">No multi-outlet facts yet.</p>`;
}

function consequencesHtml(items) {
  if (!items.length) return `<p class="note">No reported consequence events yet.</p>`;
  return items.map((c) => `
    <div class="conseq-item">
      <span class="kind">${esc(c.type)}</span>
      <span><span class="desc">${esc(c.description)}</span><br>
        <span class="src">first seen ${when(c.first_seen)} · ${esc(c.outlets.join(", "))}</span></span>
    </div>`).join("");
}

async function showStory(id) {
  const s = await api(`/api/stories/${id}`);
  document.body.classList.add("viewing");
  detailEl.classList.remove("fade");
  void detailEl.offsetWidth; // restart animation
  detailEl.classList.add("fade");
  detailEl.innerHTML = `
    <a class="back" href="#/">&larr; all stories</a>
    <h1>${esc(s.label)}</h1>
    <p class="meta"><b>${s.outlet_count}</b> outlets ·
      divergence <b>${s.divergence.toFixed(2)}</b> ·
      tracked since ${when(s.tracked_since)}</p>
    ${s.divergent_labels.length ? `
      <section><h2>Same actors, different labels</h2>
        ${s.divergent_labels.map((g) => `<div class="pills">${
          g.map((t) => `<span class="pill">${esc(t)}</span>`).join(`<span class="vs">vs</span>`)
        }</div>`).join("<br>")}
      </section>` : ""}
    <section><h2>Coverage — evaluative language marked in place</h2>
      ${coverageHtml(s.coverage)}${legendHtml()}
    </section>
    <section><h2>Factual record — corroboration-tiered</h2>
      ${factsHtml(s.facts, s.numeric_claims)}
      <p class="note">${esc(s.caveat || "")}</p>
    </section>
    <section><h2>Consequences — what started, as reported</h2>
      ${consequencesHtml(s.consequences)}
      <p class="note">An entry means outlets reported it happened —
        nothing here claims who arranged it or why.</p>
    </section>
    ${velocityHtml(s.velocity)}
    <section class="report">
      <button id="reportBtn" type="button">Report an issue with this story</button>
      <div id="reportForm" hidden>
        <select id="reportCategory">
          <option value="wrong-loaded-term">Loaded-term flag looks wrong</option>
          <option value="bad-cluster">Headlines don't belong together</option>
          <option value="wrong-tier">Fact tier looks wrong</option>
          <option value="broken-link">Broken link</option>
          <option value="other">Other</option>
        </select>
        <textarea id="reportMessage" maxlength="2000" placeholder="What's wrong?"></textarea>
        <button id="reportSubmit" type="button">Submit</button>
        <span id="reportStatus" class="src"></span>
      </div>
    </section>`;
  renderFeed();
  wireReportForm(id);
}

function wireReportForm(storyId) {
  const btn = $("#reportBtn"), form = $("#reportForm"), status = $("#reportStatus");
  if (!btn) return;
  btn.addEventListener("click", () => { form.hidden = !form.hidden; });
  $("#reportSubmit").addEventListener("click", async () => {
    const message = $("#reportMessage").value.trim();
    if (!message) { status.textContent = "Say a bit about the issue first."; return; }
    status.textContent = "Sending…";
    try {
      const res = await fetch("/api/feedback", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          category: $("#reportCategory").value,
          message, story_id: storyId,
        }),
      });
      status.textContent = res.ok ? "Thanks — received." : "Couldn't send, try again.";
      if (res.ok) $("#reportMessage").value = "";
    } catch {
      status.textContent = "Couldn't send, try again.";
    }
  });
}

function velocityHtml(v) {
  if (!v || (!v.reactions.length && !v.bursts.length)) return "";
  const rows = v.reactions.map((r) => `
    <div class="fact">
      <span class="tier conseqchip">${esc(r.type)}</span>
      <span class="when">${r.latency_hours === null ? "?" : "+" + r.latency_hours + "h"}</span>
      <span>${r.outlets.length} outlet${r.outlets.length === 1 ? "" : "s"} —
        ${r.outlets_within_24h} within 24h of first sighting, spread ${r.spread_hours}h
        <span class="src">(${esc(r.outlets.join(", "))})</span></span>
    </div>`);
  const bursts = v.bursts.map((b) => `
    <div class="fact">
      <span class="tier discrepancy">burst</span>
      <span class="when">${esc(b.date)}</span>
      <span>${b.headlines} headlines vs median ${b.median_other_days} on other days</span>
    </div>`);
  return `<section><h2>Velocity — observable timing</h2>
    <p class="note">First coverage ${when(v.first_coverage)}; latency = hours after first coverage.</p>
    ${rows.join("")}${bursts.join("")}
    <p class="note">${esc(v.note)}</p></section>`;
}

/* ---------- query view ---------- */
async function showQuery(q) {
  const r = await api(`/api/query?q=${encodeURIComponent(q)}`);
  document.body.classList.add("viewing");
  detailEl.classList.remove("fade"); void detailEl.offsetWidth;
  detailEl.classList.add("fade");
  if (!r.stories.length) {
    detailEl.innerHTML = `<a class="back" href="#/">&larr; all stories</a>
      <div class="empty"><h2>No tracked coverage matches “${esc(q)}”</h2></div>`;
    return;
  }
  const total = r.volume.reduce((a, v) => a + v.headlines, 0);
  const span = r.volume.length
    ? `${r.volume[0].date} → ${r.volume[r.volume.length - 1].date}` : "";
  const maxV = Math.max(...r.volume.map((v) => v.headlines), 1);
  detailEl.innerHTML = `
    <a class="back" href="#/">&larr; all stories</a>
    <h1>“${esc(q)}”</h1>
    <p class="meta"><b>${r.stories.length}</b> stories ·
      <b>${total}</b> headlines · ${esc(span)}</p>

    <section><h2>Coverage volume</h2>
      <div class="vol">${r.volume.map((v) => `
        <div class="vbar" title="${v.date}: ${v.headlines}">
          <i style="height:${Math.round((v.headlines / maxV) * 64)}px"></i>
          <span>${esc(v.date.slice(5))}</span></div>`).join("")}
      </div>
    </section>

    <section><h2>Chronological record — facts &amp; consequences, as reported</h2>
      ${r.record.map((item) => `
        <div class="fact">
          <span class="tier ${item.kind === "fact" ? item.tier : "conseqchip"}">${esc(item.tier)}</span>
          <span class="when">${when(item.when)}</span>
          <span>${esc(item.text)}
            <span class="src">(${esc(item.outlets.join(", "))})</span></span>
        </div>`).join("")}
    </section>

    ${r.discrepancies.length ? `
    <section><h2>Unresolved numeric discrepancies</h2>
      ${r.discrepancies.map((d) => `
        <div class="fact"><span class="tier discrepancy">discrepancy</span>
          <span>“…${esc(d.context)}” — ${esc(Object.entries(d.values)
            .map(([o, v]) => `${o}: ${v}`).join(", "))}</span></div>`).join("")}
    </section>` : ""}

    <section><h2>Framing profile — observed counts / headlines analyzed</h2>
      <table class="profile"><thead><tr><th>Outlet</th><th>Headlines</th>
        <th>Loaded terms by category</th><th>Passive voice</th></tr></thead>
      <tbody>${r.outlets.map((o) => `
        <tr><td><b>${esc(o.outlet)}</b> <span class="src">${esc(o.placement)}</span></td>
          <td>${o.headlines}</td>
          <td>${Object.entries(o.loaded).sort()
            .map(([c, n]) => `<mark class="${c}">${esc(c)} ×${n}</mark>`)
            .join(" ") || "—"}</td>
          <td>${o.passive || "—"}</td></tr>`).join("")}
      </tbody></table>
      <p class="note">${esc(r.note)}</p>
    </section>

    ${r.labels.length ? `
    <section><h2>Label choices</h2>
      ${r.labels.map((l) => `<div class="pills"><span class="pill">${esc(l.term)}</span>
        <span class="src">${esc(l.outlets.join(", "))}</span></div>`).join("")}
    </section>` : ""}

    <section><h2>Matched stories</h2>
      ${r.stories.map((st) => `<p><a href="#/story/${st.id}">${esc(st.label)}</a>
        <span class="src">tracked since ${when(st.tracked_since)}</span></p>`).join("")}
    </section>`;
}

/* ---------- routing ---------- */
function route() {
  const parts = location.hash.split("/");
  if (parts[1] === "query" && parts[2]) {
    showQuery(decodeURIComponent(parts.slice(2).join("/"))).catch(() => {
      detailEl.innerHTML = `<div class="empty"><h2>Query failed</h2></div>`;
    });
    return;
  }
  if (parts[1] === "story" && parts[2]) {
    showStory(parts[2]).catch(() => {
      detailEl.innerHTML = `<div class="empty"><h2>Story not found</h2></div>`;
    });
  } else {
    document.body.classList.remove("viewing");
    renderFeed();
  }
}
window.addEventListener("hashchange", route);

let t;
searchEl.addEventListener("input", () => {
  clearTimeout(t);
  t = setTimeout(() => loadFeed(searchEl.value.trim()), 200);
});
searchEl.addEventListener("keydown", (e) => {
  const v = searchEl.value.trim();
  if (e.key === "Enter" && v) location.hash = `#/query/${encodeURIComponent(v)}`;
});

(async function init() {
  const meta = await api("/api/meta");
  $("#caveat").textContent = meta.caveat;
  await loadFeed();
  route();
})();
