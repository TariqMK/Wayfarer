// The three poster styles, and turning a poster into PNG or paged JPEG images for export.
"use strict";

const POSTER_STYLES = [["route", "Route line"], ["survey", "Survey sheet"], ["tickets", "Ticket stack"]];
const DEFAULT_POSTER = "route";
const A4_RATIO = 297 / 210;

function firstType(day, fromSlot = 0) {
  for (const [slot] of SLOTS.slice(fromSlot)) {
    const list = (day.slots || {})[slot] || [];
    if (list.length) return list[0].type || "note";
  }
  return "note";
}
const slotEntries = (day, slot) => ((day.slots || {})[slot] || []);

// Route line ---------------------------------------------------------------------------
function posterRoute(trip, scope) {
  const days = trip.days || [];
  const bg = cssVar(scope, "--page");
  const colour = t => cssVar(scope, `--${LINE[t] ? t : "note"}`);
  const used = new Set();
  let rows = "";
  days.forEach((day, i) => {
    const t0 = firstType(day);
    rows += `<div class="rw dayh" data-break style="margin-top:${i ? 8 : 32}px"><div class="rail">${railSvg(t0, colour(t0), bg)}<span class="num">${i + 1}</span></div><div><span class="when">${esc(fmtFull(day.date) || "No date set")}</span><h2>${esc(day.label || `Day ${i + 1}`)}</h2></div></div>`;
    SLOTS.forEach(([slot, slotLabel]) => slotEntries(day, slot).forEach(e => {
      const t = e.type || "note";
      used.add(t);
      const isNote = t === "note";
      const mode = isNote ? slotLabel : [TYPE_LABELS[t] || t, fmtDuration(e)].filter(Boolean).join(" · ");
      const night = overnightLabel(e);
      rows += `<div class="rw" data-break><div class="rail">${railSvg(t, colour(t), bg)}<span class="stop"></span></div><div class="pe">${icon(t)}<div><b>${esc(entryTitle(e) || TYPE_LABELS[t])}</b>${!isNote && e.note ? `<p>${esc(e.note)}</p>` : ""}</div><span class="mode">${esc(mode)}${night ? `<br><span class="tag">${esc(night)}</span>` : ""}</span></div></div>`;
    }));
  });
  const key = [...used].filter(t => t !== "note").map(t => `<span>${keySvg(t, colour(t), bg)}${esc(TYPE_LABELS[t])}</span>`).join("");
  return `<div class="poster route">
    <div class="p-title">${esc(trip.title || "Untitled trip")}</div>
    ${trip.subtitle ? `<div class="p-sub">${esc(trip.subtitle)}</div>` : ""}
    <div class="p-meta">${esc([tripRange(days), tripSummary(days)].filter(Boolean).join(" · "))}</div>
    ${trip.notes ? `<div class="p-notes">${esc(trip.notes)}</div>` : ""}
    ${days.length ? rows : `<div class="p-empty">Add days in the Editor to see the itinerary</div>`}
    ${key ? `<div class="key" data-break>${key}</div>` : ""}
    <div class="wm">Wayfarer</div></div>`;
}

// Survey sheet --------------------------------------------------------------------------
function seedFrom(text) { let s = 42; for (const c of String(text)) s = (s * 31 + c.codePointAt(0)) % 2147483647; return s || 42; }

// A contour map generated from the title, so each trip's map is its own and stays the same on every export.
function contourMap(trip, scope) {
  let s = seedFrom(trip.title);
  const rng = () => (s = (s * 16807) % 2147483647) / 2147483647;
  const v = n => cssVar(scope, n);
  const blob = (cx, cy, r, ph) => {
    let d = "";
    for (let a = 0; a <= 48; a++) {
      const t = a / 48 * Math.PI * 2, k = r * (1 + .16 * Math.sin(3 * t + ph) + .09 * Math.sin(5 * t + ph * 2));
      d += `${a ? "L" : "M"}${(cx + k * 1.6 * Math.cos(t)).toFixed(1)} ${(cy + k * Math.sin(t)).toFixed(1)}`;
    }
    return d + "Z";
  };
  let lines = "";
  for (let hill = 0; hill < 3; hill++) {
    const x = 120 + rng() * 620, y = 30 + rng() * 180, ph = rng() * 6;
    for (let r = 14; r < 190; r += 15 + rng() * 5) lines += `<path d="${blob(x, y, r, ph + r * .006)}" fill="none" stroke="${v("--contour")}" stroke-width="${Math.round(r) % 4 === 0 ? 1.2 : .7}" opacity=".75"/>`;
  }
  const wood = Array.from({ length: 46 }, () => `<circle cx="${(560 + rng() * 260).toFixed(0)}" cy="${(rng() * 110).toFixed(0)}" r="1.6" fill="${v("--wood")}"/>`).join("");
  const riverY = 90 + rng() * 60;
  const river = `<path d="M-10 ${riverY}C120 ${riverY - 30} 190 ${riverY + 30} 300 ${riverY + 10}S470 ${riverY - 60} 590 ${riverY - 10} 730 ${riverY + 50} 840 ${riverY}" fill="none" stroke="${v("--water")}" stroke-width="3"/>`;
  const stops = Math.max(2, Math.min(8, (trip.days || []).length + 1));
  // Stops on the left stay above the title box, so none is hidden behind it.
  const pts = Array.from({ length: stops }, (_, i) => {
    const x = 40 + i * (740 / (stops - 1));
    return [x, 32 + rng() * (x < 440 ? 56 : 168)];
  });
  const accent = v("--poster-accent");
  const page = v("--page");
  const route = `<polyline points="${pts.map(p => p.map(n => n.toFixed(0)).join(",")).join(" ")}" fill="none" stroke="${accent}" stroke-width="2" stroke-dasharray="6 4"/>` + pts.map(([x, y]) => `<circle cx="${x.toFixed(0)}" cy="${y.toFixed(0)}" r="4" fill="${page}" stroke="${accent}" stroke-width="2"/>`).join("");
  return `<svg width="820" height="240" viewBox="0 0 820 240" aria-hidden="true">${lines}${wood}${river}${route}</svg>`;
}

function posterSurvey(trip, scope) {
  const days = trip.days || [];
  const cell = (day, i) => {
    let r = "";
    SLOTS.forEach(([slot]) => slotEntries(day, slot).forEach(e => {
      const t = e.type || "note";
      const night = overnightLabel(e);
      r += `<div class="pe2">${icon(t)}<div><div>${esc(entryTitle(e) || TYPE_LABELS[t])}</div>${t !== "note" && e.note ? `<p>${esc(e.note)}</p>` : ""}${night ? `<span class="tag">${esc(night)}</span>` : ""}</div><span class="num">${esc(fmtDuration(e))}</span></div>`;
    }));
    return `<div class="pd"><div class="sh"><span class="sq">${i + 1}</span><div><h2>${esc(day.label || `Day ${i + 1}`)}</h2><small>${esc(fmtFull(day.date) || "No date set")}</small></div></div>${r}</div>`;
  };
  let pairs = "";
  for (let i = 0; i < days.length; i += 2) pairs += `<div class="pair" data-break>${cell(days[i], i)}${days[i + 1] ? cell(days[i + 1], i + 1) : "<div></div>"}</div>`;
  return `<div class="poster survey">
    <div class="map">${contourMap(trip, scope)}<div class="ttl"><div class="p-title">${esc(trip.title || "Untitled trip")}</div>${trip.subtitle ? `<div class="p-sub">${esc(trip.subtitle)}</div>` : ""}</div></div>
    ${trip.notes ? `<div class="notes-band">${esc(trip.notes)}</div>` : ""}
    ${days.length ? pairs : `<div class="p-empty">Add days in the Editor to see the itinerary</div>`}
    <div class="foot" data-break><span>${esc([tripRange(days), tripSummary(days)].filter(Boolean).join(" · "))}</span><span>Wayfarer</span></div></div>`;
}

// Ticket stack --------------------------------------------------------------------------
function posterTickets(trip) {
  const days = trip.days || [];
  const body = days.map((day, i) => {
    let r = "";
    SLOTS.forEach(([slot, slotLabel]) => slotEntries(day, slot).forEach(e => {
      const t = e.type || "note";
      if (t === "note") {
        r += `<div class="tk" data-break><div class="l"><div class="mode">${icon("note")}${esc(slotLabel)}</div><div class="plain">${esc(e.note || TYPE_LABELS.note)}</div></div></div>`;
        return;
      }
      const night = overnightLabel(e);
      const points = [e.from, e.to].filter(Boolean).map(esc).join('<i>→</i>') || esc(TYPE_LABELS[t]);
      r += `<div class="tk" data-break><div class="l"><div class="mode">${icon(t)}${esc(TYPE_LABELS[t] || t)} · ${esc(slotLabel)}</div><div class="pts">${points}</div>${e.note ? `<p>${esc(e.note)}</p>` : ""}${night ? `<span class="stamp">${esc(night)}</span>` : ""}</div><div class="r"><span>${esc(fmtShort(day.date))}</span><span>${esc(fmtDuration(e))}</span></div></div>`;
    }));
    return `<div class="ph3" data-break>${esc(day.label || `Day ${i + 1}`)}<small>Day ${i + 1}${day.date ? ` · ${esc(fmtFull(day.date))}` : ""}</small></div>${r}`;
  }).join("");
  return `<div class="poster tickets"><div class="hd">
    <div class="p-title">${esc(trip.title || "Untitled trip")}</div>
    ${trip.subtitle ? `<div class="p-sub">${esc(trip.subtitle)}</div>` : ""}
    <div class="p-meta">${esc([tripRange(days), tripSummary(days)].filter(Boolean).join(" · "))}</div>
    ${trip.notes ? `<div class="p-notes">${esc(trip.notes)}</div>` : ""}</div>
    ${days.length ? body : `<div class="p-empty">Add days in the Editor to see the itinerary</div>`}
    <div class="wm" data-break>Wayfarer</div></div>`;
}

// `scope` must already carry the chosen appearance, because SVG lines use literal colours read from it.
function renderPoster(trip, style, scope) {
  // The accents are scoped under .survey and .tickets, so read them from a probe of that class.
  const probe = document.createElement("div");
  probe.className = `poster ${style}`;
  probe.style.cssText = "position:absolute;visibility:hidden;width:0;height:0;padding:0;overflow:hidden";
  scope.appendChild(probe);
  let html;
  if (style === "survey") html = posterSurvey(trip, probe);
  else if (style === "tickets") html = posterTickets(trip);
  else html = posterRoute(trip, probe);
  probe.remove();
  return html;
}

// Choose page cuts at row boundaries. Offsets are in CSS pixels from the poster's top.
// Returns [start, end] pairs, each no taller than pageHeight. A row taller than a page is cut where it must be.
function pageSlices(total, pageHeight, breaks, topPad = 0) {
  const cuts = [...new Set(breaks)].filter(b => b > 0 && b < total).sort((a, b) => a - b);
  const slices = [];
  let start = 0;
  while (total - start > (slices.length ? pageHeight - topPad : pageHeight)) {
    const room = slices.length ? pageHeight - topPad : pageHeight;
    const limit = start + room;
    let end = limit;
    for (const c of cuts) if (c > start && c <= limit) end = c;
    slices.push([start, end]);
    start = end;
  }
  slices.push([start, total]);
  return slices;
}

async function capturePoster(trip, style, appearance, scale) {
  const host = document.getElementById("export-host");
  host.dataset.theme = appearance;
  host.className = "export-render";
  host.innerHTML = renderPoster(trip, style, host);
  try {
    await document.fonts.ready;
    await Promise.all([...new Set([...host.querySelectorAll("*")].slice(0, 400).map(el => getComputedStyle(el).font))].map(f => document.fonts.load(f).catch(() => null)));
    const el = host.querySelector(".poster");
    const top = el.getBoundingClientRect().top;
    const breaks = [...el.querySelectorAll("[data-break]")].map(n => n.getBoundingClientRect().top - top);
    const background = getComputedStyle(el).backgroundColor;
    const canvas = await html2canvas(el, { backgroundColor: background, scale, logging: false, useCORS: false, windowWidth: 1400 });
    return { canvas, breaks, background, cssWidth: el.offsetWidth, cssHeight: el.offsetHeight };
  } finally {
    host.innerHTML = "";
  }
}

const canvasBase64 = (canvas, type, quality) => canvas.toDataURL(type, quality).split(",")[1];

async function posterToPng(trip, style, appearance) {
  const { canvas } = await capturePoster(trip, style, appearance, 2);
  return canvasBase64(canvas, "image/png");
}

// Returns one base64 JPEG per A4 page. Pages after the first start with a small top margin.
async function posterToPdfPages(trip, style, appearance) {
  const scale = 2.5;
  const { canvas, breaks, background, cssWidth, cssHeight } = await capturePoster(trip, style, appearance, scale);
  const pageCss = cssWidth * A4_RATIO;
  const topPad = 32;
  return pageSlices(cssHeight, pageCss, breaks, topPad).map(([start, end], i) => {
    const page = document.createElement("canvas");
    page.width = Math.round(cssWidth * scale);
    page.height = Math.round(pageCss * scale);
    const ctx = page.getContext("2d");
    ctx.fillStyle = background;
    ctx.fillRect(0, 0, page.width, page.height);
    const offset = i ? topPad * scale : 0;
    const srcY = Math.round(start * scale);
    const srcH = Math.min(Math.round((end - start) * scale), canvas.height - srcY);
    ctx.drawImage(canvas, 0, srcY, canvas.width, srcH, 0, offset, page.width, srcH * (page.width / canvas.width));
    return canvasBase64(page, "image/jpeg", 0.92);
  });
}
