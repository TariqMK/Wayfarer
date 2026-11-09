// Product page behaviour: the live editor preview, the poster switcher, the line legend and the download links.
"use strict";

const REPO = "TariqMK/Wayfarer";
const ASSET = { windows: /windows-x64\.exe$/i, macos: /macos-arm64\.zip$/i, linux: /linux-x64\.tar\.gz$/i };
const OS_NAME = { windows: "Windows", macos: "macOS", linux: "Linux" };
const reduced = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
const $ = sel => document.querySelector(sel);

// Editor preview -------------------------------------------------------------------------
// Mirrors the editor markup in wayfarer/ui/app.js, with the sample trip. It plays a short story:
// a walk to dinner is added to day 1, then the trip is saved.
const ED = { trip: null, selected: null, state: "Saved", version: "", focus: "", pressed: false };
const NEW_ENTRY = { id: "story", type: "walk", from: "Hotel", to: "Omoide Yokocho", duration: "20", unit: "mins", note: "Dinner" };

function setupTrip() {
  const trip = JSON.parse(JSON.stringify(SAMPLE_TRIP));
  trip.days.forEach((d, i) => { d.id = `d${i}`; SLOTS.forEach(([s]) => (d.slots[s] || []).forEach((e, j) => { e.id = `${d.id}${s}${j}`; })); });
  trip.days[0].slots.evening = [];
  return trip;
}

function edHeader() {
  return `<div class="bar"><div class="left"><span class="btn q">← Trips</span><span class="brand">Wayfarer</span><span class="ver">${esc(ED.version)}</span></div>
    <div class="seg"><button aria-pressed="true" tabindex="-1">Editor</button><button aria-pressed="false" tabindex="-1">Preview</button></div>
    <div class="right"><span class="state">${ED.state}</span><span class="btn" data-hide-sm>Export</span><span class="btn p${ED.pressed ? " pressed" : ""}">Save</span></div></div>`;
}

function edSide() {
  const t = ED.trip;
  return `<aside class="side">
    <label class="f"><span>Trip title</span><input class="in" tabindex="-1" readonly value="${esc(t.title)}"></label>
    <label class="f"><span>Subtitle</span><input class="in" tabindex="-1" readonly value="${esc(t.subtitle)}"></label>
    <label class="f" style="margin-bottom:0"><span>Trip notes</span><textarea class="in" rows="3" tabindex="-1" readonly>${esc(t.notes)}</textarea></label>
    <h3>Days <i>${t.days.length}</i></h3>
    ${t.days.map((d, i) => `<div class="dayjump"><span>${esc(d.label || `Day ${i + 1}`)}</span><em>${esc(fmtShort(d.date))}</em></div>`).join("")}
    <span class="btn" style="width:100%;margin-top:8px">Add day</span></aside>`;
}

function edRow(e, c) {
  const t = e.type || "note";
  const title = entryTitle(e);
  return `<div class="rw ent"><div class="rail">${railSvg(t, c.line, c.bg)}<span class="stop"></span></div>
    <div class="box">${icon(t)}<span class="what">${esc(title || TYPE_LABELS[t])}</span><span class="sub">${t !== "note" && e.note ? esc(e.note) : ""}</span><span class="dur">${esc(fmtDuration(e))}</span></div></div>`;
}

function edCard(e, c) {
  const field = (name, label, cls = "") => `<label class="${cls}"><span>${label}</span><input class="in${ED.focus === name ? " is-focus" : ""}" tabindex="-1" readonly value="${esc(e[name])}"></label>`;
  const units = { mins: "m", hrs: "h", days: "d" };
  return `<div class="rw ent sel"><div class="rail">${railSvg(e.type, c.line, c.bg)}<span class="stop"></span></div>
    <div class="card"><div class="grid">
      <label><span>Type</span><select class="in" tabindex="-1"><option>${TYPE_LABELS[e.type]}</option></select></label>
      ${field("from", "From")}${field("to", "To")}
      <label><span>Duration</span><span class="dur-pair"><input class="in${ED.focus === "duration" ? " is-focus" : ""}" tabindex="-1" readonly value="${esc(e.duration)}"><select class="in" tabindex="-1"><option>${units[e.unit]}</option></select></span></label>
      ${field("note", "Notes", "wide")}
    </div><div class="foot"><label><input type="checkbox" tabindex="-1"> Overnight</label><span class="grow"></span>
      <span class="btn q">Move up</span><span class="btn q">Move down</span><span class="btn q d">Delete entry</span><span class="btn">Done</span></div></div></div>`;
}

function edDays(c) {
  return ED.trip.days.map((day, i) => {
    let h = `<div class="rw dayh"><div class="rail">${railSvg(firstType(day), c.line, c.bg)}<span class="num">${i + 1}</span></div>
      <div class="title"><div class="daywhen"><span>${esc(weekday(day.date))}</span><span>${esc(day.date.split("-").reverse().join("/"))}</span></div><div class="lbl-static">${esc(day.label)}</div></div></div>`;
    SLOTS.forEach(([slot, label], si) => {
      h += `<div class="rw slot"><div class="rail">${railSvg(firstType(day, si), c.line, c.bg)}</div><span>${label}</span><span class="add">Add entry</span></div>`;
      day.slots[slot].forEach(e => { h += e.id === ED.selected ? edCard(e, c) : edRow(e, c); });
    });
    return h;
  }).join("");
}

function renderEditor() {
  const root = $("#editor");
  const c = { line: cssVar(root, "--t3"), bg: cssVar(root, "--page") };
  root.innerHTML = edHeader() + `<div class="body">${edSide()}<div class="scroll"><div class="d1main">${edDays(c)}</div></div></div>`;
}

// The story, as steps. Each step changes the state and says how long to wait before the next.
function storySteps() {
  const steps = [];
  const evening = () => ED.trip.days[0].slots.evening;
  let entry;
  steps.push(() => { ED.trip = setupTrip(); ED.selected = null; ED.state = "Saved"; ED.focus = ""; return 1400; });
  steps.push(() => {
    entry = { ...NEW_ENTRY, from: "", to: "", duration: "", note: "", unit: "hrs" };
    evening().push(entry); ED.selected = entry.id; ED.state = "Unsaved changes"; return 700;
  });
  for (const name of ["from", "to", "duration", "note"]) {
    const text = NEW_ENTRY[name];
    for (let i = 1; i <= text.length; i++) {
      steps.push(() => { ED.focus = name; entry[name] = text.slice(0, i); if (name === "duration") entry.unit = "mins"; return 70; });
    }
    steps.push(() => 260);
  }
  steps.push(() => { ED.focus = ""; return 600; });
  steps.push(() => { ED.selected = null; return 1300; });
  steps.push(() => { ED.pressed = true; return 160; });
  steps.push(() => { ED.pressed = false; ED.state = "Saved"; return 3600; });
  return steps;
}

function playStory() {
  const steps = storySteps();
  let i = 0, timer = null;
  const tick = () => {
    if (document.hidden) { timer = null; return; }
    const wait = steps[i]();
    renderEditor();
    i = (i + 1) % steps.length;
    timer = setTimeout(tick, wait);
  };
  document.addEventListener("visibilitychange", () => { if (!document.hidden && !timer) tick(); });
  tick();
}

function staticEditor() {
  // One still frame for reduced motion: the new entry open and filled in.
  ED.trip = setupTrip();
  const entry = { ...NEW_ENTRY };
  ED.trip.days[0].slots.evening.push(entry);
  ED.selected = entry.id; ED.state = "Unsaved changes";
  renderEditor();
}

// Poster switcher ------------------------------------------------------------------------
const POSTER = { style: "route", theme: "light" };

function renderPosterPanel() {
  const holder = $("#poster-scale");
  holder.dataset.theme = POSTER.theme;
  holder.style.transform = "none";
  holder.innerHTML = renderPoster(SAMPLE_TRIP, POSTER.style, holder);
  fitPoster();
}

function fitPoster() {
  const holder = $("#poster-scale");
  const poster = holder.firstElementChild;
  if (!poster) return;
  const stage = $("#poster-stage");
  const width = poster.offsetWidth;
  const room = stage.clientWidth - 32;
  // On narrow screens a scaled poster has unreadable text, so show it at full size and let it scroll sideways.
  const pan = room / width < 0.7;
  const scale = pan ? 1 : Math.min(1, room / width);
  stage.classList.toggle("pan", pan);
  holder.style.width = `${width}px`;
  holder.style.marginLeft = pan ? "16px" : `calc(50% - ${width / 2}px)`;
  holder.style.transform = `scale(${scale})`;
}

function setupSeg(id, attr, apply) {
  const seg = $(id);
  seg.addEventListener("click", e => {
    const b = e.target.closest("button");
    if (!b) return;
    seg.querySelectorAll("button").forEach(x => x.setAttribute("aria-pressed", String(x === b)));
    apply(b.getAttribute(attr));
    renderPosterPanel();
  });
}

// Legend, text export and section lines ---------------------------------------------------
function renderLegend() {
  const el = $("#legend");
  const bg = cssVar(el, "--page");
  el.innerHTML = Object.entries(TYPE_LABELS).filter(([t]) => t !== "note")
    .concat([["note", TYPE_LABELS.note]])
    .map(([t, label]) => `<span>${keySvg(t, cssVar(el, `--${t}`), bg)}${esc(label)}</span>`).join("");
}

function renderEyebrows() {
  document.querySelectorAll(".eyebrow[data-line]").forEach(el => {
    el.insertAdjacentHTML("afterbegin", keySvg(el.dataset.line, "#8c8c92", "#0f0f10"));
  });
}

// Downloads ------------------------------------------------------------------------------
function detectOS() {
  const ua = navigator.userAgent;
  if (/Android|iPhone|iPad|iPod/i.test(ua)) return null;
  const platform = (navigator.userAgentData && navigator.userAgentData.platform) || navigator.platform || ua;
  if (/win/i.test(platform)) return "windows";
  if (/mac/i.test(platform)) return "macos";
  if (/linux|x11/i.test(platform)) return "linux";
  return null;
}

async function wireDownloads() {
  const os = detectOS();
  const hero = $("#hero-download");
  if (os) {
    hero.textContent = `Download for ${OS_NAME[os]}`;
    document.querySelector(`.dl[data-os="${os}"]`).classList.add("mine");
  }
  try {
    const r = await fetch(`https://api.github.com/repos/${REPO}/releases/latest`, { headers: { Accept: "application/vnd.github+json" } });
    if (!r.ok) return;
    const rel = await r.json();
    for (const asset of rel.assets || []) {
      for (const [key, pattern] of Object.entries(ASSET)) {
        if (!pattern.test(asset.name)) continue;
        const card = document.querySelector(`.dl[data-os="${key}"]`);
        card.href = asset.browser_download_url;
        card.querySelector(".size").textContent = `${(asset.size / 1048576).toFixed(1)} MB`;
        if (key === os) hero.href = asset.browser_download_url;
      }
    }
    const date = new Date(rel.published_at).toLocaleDateString("en-GB", { day: "numeric", month: "long", year: "numeric" });
    $("#hero-version").textContent = rel.tag_name;
    $("#download-title").textContent = `Download Wayfarer ${rel.tag_name}`;
    $("#download-sub").textContent = `Released ${date}. Free. One file per computer. Put it in a folder you can change, for example in Documents.`;
    ED.version = rel.tag_name;
    if (reduced) renderEditor();
  } catch {
    // Offline, rate limited or no release yet: every link already points to the Releases page.
  }
}

// Start ----------------------------------------------------------------------------------
$("#textout").textContent = SAMPLE_TEXT;
renderEyebrows();
renderLegend();
setupSeg("#style-seg", "data-style", v => { POSTER.style = v; });
setupSeg("#theme-seg", "data-theme-value", v => { POSTER.theme = v; });
document.fonts.ready.then(renderPosterPanel);
renderPosterPanel();
window.addEventListener("resize", fitPoster);
if (reduced) staticEditor(); else playStory();
wireDownloads();
