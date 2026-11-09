// Shared display data and drawing: entry types, their icons, and the line style each type gets on a route.
"use strict";

const ICON_ATTRS = 'viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round" width="16" height="16" class="ic" aria-hidden="true"';
// Icon paths are from Lucide (ISC licence).
const ICON_PATHS = {
  plane: '<path d="M17.8 19.2 16 11l3.5-3.5C21 6 21.5 4 21 3c-1-.5-3 0-4.5 1.5L13 8 4.8 6.2c-.5-.1-.9.1-1.1.5l-.3.5c-.2.5-.1 1 .3 1.3L9 12l-2 3H4l-1 1 3 2 2 3 1-1v-3l3-2 3.5 5.3c.3.4.8.5 1.3.3l.5-.2c.4-.3.6-.7.5-1.2z"/>',
  car: '<path d="M19 17h2c.6 0 1-.4 1-1v-3c0-.9-.7-1.7-1.5-1.9C18.7 10.6 16 10 16 10s-1.3-1.4-2.2-2.3c-.5-.4-1.1-.7-1.8-.7H5c-.6 0-1.1.4-1.4.9l-1.4 2.9A3.7 3.7 0 0 0 2 12v4c0 .6.4 1 1 1h2"/><circle cx="7" cy="17" r="2"/><path d="M9 17h6"/><circle cx="17" cy="17" r="2"/>',
  train: '<path d="M8 3.1V7a4 4 0 0 0 8 0V3.1"/><path d="m9 15-1-1"/><path d="m15 15 1-1"/><path d="M9 19c-2.8 0-5-2.2-5-5v-4a8 8 0 0 1 16 0v4c0 2.8-2.2 5-5 5Z"/><path d="m8 19-2 3"/><path d="m16 19 2 3"/>',
  bus: '<path d="M8 6v6"/><path d="M15 6v6"/><path d="M2 12h19.6"/><path d="M18 18h3s.5-1.7.8-2.8c.1-.4.2-.8.2-1.2 0-.4-.1-.8-.2-1.2l-1.4-5C20.1 6.8 19.1 6 18 6H4a2 2 0 0 0-2 2v10h3"/><circle cx="7" cy="18" r="2"/><path d="M9 18h5"/><circle cx="17" cy="18" r="2"/>',
  cycle: '<circle cx="18.5" cy="17.5" r="3.5"/><circle cx="5.5" cy="17.5" r="3.5"/><circle cx="15" cy="5" r="1"/><path d="M12 17.5V14l-3-3 4-3 2 3h2"/>',
  bike: '<path d="m18 14-1-3"/><path d="m3 9 6 2a2 2 0 0 1 2-2h2a2 2 0 0 1 1.99 1.81"/><path d="M8 17h3a1 1 0 0 0 1-1 6 6 0 0 1 6-6 1 1 0 0 0 1-1v-.75A5 5 0 0 0 17 5"/><circle cx="19" cy="17" r="3"/><circle cx="5" cy="17" r="3"/>',
  boat: '<path d="M12 10.189V14"/><path d="M12 2v3"/><path d="M19 13V7a2 2 0 0 0-2-2H7a2 2 0 0 0-2 2v6"/><path d="M19.38 20A11.6 11.6 0 0 0 21 14l-8.188-3.639a2 2 0 0 0-1.624 0L3 14a11.6 11.6 0 0 0 2.81 7.76"/><path d="M2 21c.6.5 1.2 1 2.5 1 2.5 0 2.5-2 5-2 1.3 0 1.9.5 2.5 1s1.2 1 2.5 1c2.5 0 2.5-2 5-2 1.3 0 1.9.5 2.5 1"/>',
  walk: '<path d="M4 16v-2.38C4 11.5 2.97 10.5 3 8c.03-2.72 1.49-6 4.5-6C9.37 2 10 3.8 10 5.5c0 3.11-2 5.66-2 8.68V16a2 2 0 1 1-4 0Z"/><path d="M20 20v-2.38c0-2.12 1.03-3.12 1-5.62-.03-2.72-1.49-6-4.5-6C14.63 6 14 7.8 14 9.5c0 3.11 2 5.66 2 8.68V20a2 2 0 1 0 4 0Z"/><path d="M16 17h4"/><path d="M4 13h4"/>',
  taxi: '<path d="M19 17h2c.6 0 1-.4 1-1v-3c0-.9-.7-1.7-1.5-1.9C18.7 10.6 16 10 16 10s-1.3-1.4-2.2-2.3c-.5-.4-1.1-.7-1.8-.7H5c-.6 0-1.1.4-1.4.9l-1.4 2.9A3.7 3.7 0 0 0 2 12v4c0 .6.4 1 1 1h2"/><circle cx="7" cy="17" r="2"/><path d="M9 17h6"/><circle cx="17" cy="17" r="2"/><path d="M9 9V8"/><path d="M15 9V8"/><path d="M11 8h2"/>',
  hike: '<path d="m15 10.42 4.8-5.07"/><path d="M19 18h3"/><path d="M9.5 22 21.414 9.415A2 2 0 0 0 21.2 6.4l-5.61-4.208A1 1 0 0 0 14 3v2a2 2 0 0 1-1.394 1.906L8.677 8.053A1 1 0 0 0 8 9c-.155 6.393-2.082 9-4 9a2 2 0 0 0 0 4h14"/>',
  note: '<path d="M20 10c0 4.993-5.539 10.193-7.399 11.799a1 1 0 0 1-1.202 0C9.539 20.193 4 14.993 4 10a8 8 0 0 1 16 0"/><circle cx="12" cy="10" r="3"/>',
  grip: '<circle cx="9" cy="5" r="1"/><circle cx="9" cy="12" r="1"/><circle cx="9" cy="19" r="1"/><circle cx="15" cy="5" r="1"/><circle cx="15" cy="12" r="1"/><circle cx="15" cy="19" r="1"/>',
  up: '<path d="m18 15-6-6-6 6"/>',
  down: '<path d="m6 9 6 6 6-6"/>',
  right: '<path d="m9 18 6-6-6-6"/>',
  trash: '<path d="M3 6h18"/><path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6"/><path d="M8 6V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"/>',
};
const icon = name => `<svg ${ICON_ATTRS}>${ICON_PATHS[name] || ICON_PATHS.note}</svg>`;

const TYPE_LABELS = { plane: "Flight", car: "Drive", train: "Train", bus: "Bus", cycle: "Cycle", bike: "Motorbike", boat: "Boat", walk: "Walk", taxi: "Taxi", hike: "Hike", note: "Stop or note" };
const SLOTS = [["morning", "Morning"], ["afternoon", "Afternoon"], ["evening", "Evening"]];

const esc = s => String(s == null ? "" : s).replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;").replace(/"/g, "&quot;").replace(/'/g, "&#39;");

function parseDate(d) {
  const m = /^(\d{4})-(\d{2})-(\d{2})$/.exec(d || "");
  return m ? new Date(Number(m[1]), Number(m[2]) - 1, Number(m[3])) : null;
}
const toISO = dt => `${dt.getFullYear()}-${String(dt.getMonth() + 1).padStart(2, "0")}-${String(dt.getDate()).padStart(2, "0")}`;
function addDays(d, n) { const dt = parseDate(d); if (!dt) return ""; dt.setDate(dt.getDate() + n); return toISO(dt); }
function weekday(d) { const dt = parseDate(d); return dt ? dt.toLocaleDateString("en-GB", { weekday: "long" }) : ""; }
function fmtFull(d) { const dt = parseDate(d); return dt ? dt.toLocaleDateString("en-GB", { weekday: "long", day: "numeric", month: "long", year: "numeric" }).replace(",", "") : ""; }
function fmtShort(d) { const dt = parseDate(d); return dt ? dt.toLocaleDateString("en-GB", { weekday: "short", day: "numeric", month: "short" }).replace(",", "") : ""; }
function fmtDuration(e) {
  const v = String(e.duration == null ? "" : e.duration).trim();
  if (!v) return "";
  return /^\d+([.,]\d+)?$/.test(v) ? v + ({ mins: "m", hrs: "h", days: "d" }[e.unit] || "") : v;
}
function overnightLabel(e) {
  if (!e.overnight) return "";
  const n = String(e.spansNights || 1);
  return n === "1" ? "Overnight" : `${n} nights`;
}
function entryTitle(e) {
  if ((e.type || "note") === "note") return e.note || "";
  return [e.from, e.to].filter(Boolean).join(" → ");
}
function tripSummary(days) {
  const dated = days.map(d => d.date).filter(d => parseDate(d)).sort();
  const nights = dated.length >= 2 ? Math.round((parseDate(dated[dated.length - 1]) - parseDate(dated[0])) / 86400000) : 0;
  const parts = [`${days.length} day${days.length === 1 ? "" : "s"}`];
  if (nights > 0) parts.push(`${nights} night${nights === 1 ? "" : "s"}`);
  return parts.join(", ");
}
function tripRange(days) {
  const dated = days.map(d => d.date).filter(d => parseDate(d)).sort();
  if (!dated.length) return "";
  return dated.length === 1 ? fmtShort(dated[0]) : `${fmtShort(dated[0])} to ${fmtShort(dated[dated.length - 1])}`;
}

// The line style for each type. Lines are SVG with literal colours so html2canvas draws them the same in exports.
const LINE = {
  plane: { width: 2, dash: "8 6" },
  train: { width: 4, inner: "5 5" },
  car: { width: 3 },
  taxi: { width: 3 },
  bus: { width: 2 },
  walk: { width: 3, dash: "0.1 7", round: true },
  hike: { width: 4, dash: "0.1 10", round: true },
  cycle: { width: 2, dash: "4 4" },
  bike: { width: 2, dash: "10 3 2 3" },
  boat: { width: 1.5, wave: true },
  note: { width: 1, faint: true },
};

function cssVar(el, name) { return getComputedStyle(el).getPropertyValue(name).trim(); }

// Draw a line of one type between two points on a straight axis, as SVG shapes.
function lineShapes(type, length, axis, colour, background) {
  const s = LINE[type] || LINE.note;
  const pos = axis.cross;
  const seg = (attrs, width) => axis.vertical
    ? `<line x1="${pos}" y1="0" x2="${pos}" y2="${length}" stroke-width="${width}" ${attrs}/>`
    : `<line x1="0" y1="${pos}" x2="${length}" y2="${pos}" stroke-width="${width}" ${attrs}/>`;
  if (s.wave) {
    let d = axis.vertical ? `M${pos} 0` : `M0 ${pos}`;
    for (let i = 0; i < length; i += 12) {
      d += axis.vertical
        ? `C${pos + 4} ${i + 3} ${pos + 4} ${i + 3} ${pos} ${i + 6}S${pos - 4} ${i + 9} ${pos} ${i + 12}`
        : `C${i + 3} ${pos + 4} ${i + 3} ${pos + 4} ${i + 6} ${pos}S${i + 9} ${pos - 4} ${i + 12} ${pos}`;
    }
    return `<path d="${d}" fill="none" stroke="${colour}" stroke-width="${s.width}"/>`;
  }
  let out = seg(`stroke="${colour}"${s.dash ? ` stroke-dasharray="${s.dash}"` : ""}${s.round ? ' stroke-linecap="round"' : ""}${s.faint ? ' opacity=".6"' : ""}`, s.width);
  if (s.inner) out += seg(`stroke="${background}" stroke-dasharray="${s.inner}"`, s.width - 2);
  return out;
}

// A tall vertical line. Its .rail parent clips it to the row, so rows of any height need no measuring.
function railSvg(type, colour, background) {
  const h = 1200;
  return `<svg width="32" height="${h}" viewBox="0 0 32 ${h}" aria-hidden="true">${lineShapes(type, h, { vertical: true, cross: 16 }, colour, background)}</svg>`;
}

function keySvg(type, colour, background) {
  return `<svg width="32" height="12" viewBox="0 0 32 12" aria-hidden="true">${lineShapes(type, 32, { vertical: false, cross: 6 }, colour, background)}</svg>`;
}

// A small horizontal picture of a whole trip, one segment per entry.
function routeStrip(modes, colour, background, width = 200) {
  const list = modes.length ? modes : ["note"];
  const seg = width / list.length;
  const parts = list.map((m, i) => `<g transform="translate(${(i * seg).toFixed(1)} 0)"><svg width="${seg.toFixed(1)}" height="12" viewBox="0 0 ${seg.toFixed(1)} 12">${lineShapes(m, seg, { vertical: false, cross: 6 }, colour, background)}</svg></g>`).join("");
  return `<svg class="strip" width="${width}" height="12" viewBox="0 0 ${width} 12" aria-hidden="true">${parts}</svg>`;
}
