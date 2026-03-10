const form = document.getElementById("form");
const btn = document.getElementById("btn");
const statusEl = document.getElementById("status");
const metaEl = document.getElementById("meta");
const anglesEl = document.getElementById("angles");
const healthEl = document.getElementById("health");
const natalGridEl = document.getElementById("kundli-grid");
const progressGridEl = document.getElementById("progress-grid");
const chartYearEl = document.getElementById("chart-year");
const yearDecEl = document.getElementById("year-dec");
const yearIncEl = document.getElementById("year-inc");
const progressMetaEl = document.getElementById("progress-meta");
const transitGridEl = document.getElementById("transit-grid");
const transitMetaEl = document.getElementById("transit-meta");
const placeInput = document.getElementById("place");
const searchResults = document.getElementById("search-results");

let localPlaces = [];
let lastPayload = null;
let progressListenerBound = false;
async function loadLocalPlaces() {
  try {
    const res = await fetch("/places.min.json", { headers: { Accept: "application/json" } });
    const data = await res.json();
    if (Array.isArray(data)) localPlaces = data;
  } catch {
    localPlaces = [];
  }
}

function showStatus(msg, isError = false) {
  statusEl.textContent = msg;
  statusEl.style.color = isError ? '#ef4444' : 'var(--primary)';
  if (isError) {
    statusEl.classList.add('shake');
    setTimeout(() => statusEl.classList.remove('shake'), 400);
  }
}

function fmtDeg(v) {
  if (v === null || v === undefined) return "";
  const n = Number(v);
  if (!Number.isFinite(n)) return "";
  return n.toFixed(6);
}

function fmtDms(v) {
  const n = Number(v);
  if (!Number.isFinite(n)) return "";
  const sign = n < 0 ? "-" : "";
  const a = Math.abs(n);
  const d = Math.floor(a);
  const mFloat = (a - d) * 60;
  const m = Math.floor(mFloat);
  const s = (mFloat - m) * 60;
  const pad2 = (x) => String(x).padStart(2, "0");
  return `${sign}${d}°${pad2(m)}'${pad2(Math.round(s))}"`;
}

function clearTables() {
  // Frontend is chart-first now; tables are no longer used.
}

function row(cells) {
  const tr = document.createElement("tr");
  for (const c of cells) {
    const td = document.createElement("td");
    td.textContent = c;
    tr.appendChild(td);
  }
  return tr;
}

async function generate(payload) {
  const res = await fetch("/api/kundli", {
    method: "POST",
    headers: { "content-type": "application/json" },
    body: JSON.stringify(payload),
  });
  const data = await res.json();
  if (!res.ok) {
    const msg = data?.detail || "Request failed";
    throw new Error(msg);
  }
  return data;
}

function fill(data) {
  clearTables();

  const meta = data.meta || {};
  const ep = meta.ephe_files || {};
  const pFile = ep.planets ? String(ep.planets).split(/[\\/]/).slice(-1)[0] : "?";
  const mFile = ep.moon ? String(ep.moon).split(/[\\/]/).slice(-1)[0] : "?";
  metaEl.textContent = `Mode: ${meta.zodiac || "sidereal"} ${meta.ayanamsa || ""} | Rahu: ${meta.node || ""} | Houses: ${meta.house_system || ""} | Files: ${pFile}, ${mFile}`;

  const asc = data.angles?.ascendant;
  const mc = data.angles?.mc;
  const ascDeg = Number(asc?.deg_in_sign);
  const mcDeg = Number(mc?.deg_in_sign);
  anglesEl.textContent = `Asc: ${asc?.sign || ""} ${Number.isFinite(ascDeg) ? ascDeg.toFixed(1) : ""}° | MC: ${mc?.sign || ""} ${Number.isFinite(mcDeg) ? mcDeg.toFixed(1) : ""}°`;

  renderChart(data, { gridEl: natalGridEl, idPrefix: "natal", centerTitle: "RASHI" });
  setupDerivedChartsUI();
}

function renderChart(data, { gridEl, idPrefix, centerTitle }) {
  if (!gridEl) return;
  const prefix = String(idPrefix || "chart");

  const SIGN_NAMES = [
    "Aries",
    "Taurus",
    "Gemini",
    "Cancer",
    "Leo",
    "Virgo",
    "Libra",
    "Scorpio",
    "Sagittarius",
    "Capricorn",
    "Aquarius",
    "Pisces",
  ];

  const SOUTH_LAYOUT = [
    "Pisces",
    "Aries",
    "Taurus",
    "Gemini",
    "Aquarius",
    "EMPTY",
    "EMPTY",
    "Cancer",
    "Capricorn",
    "EMPTY",
    "EMPTY",
    "Leo",
    "Sagittarius",
    "Scorpio",
    "Libra",
    "Virgo",
  ];

  const PLANET_ABBR = {
    Sun: "Su",
    Moon: "Mo",
    Mars: "Ma",
    Mercury: "Me",
    Jupiter: "Ju",
    Venus: "Ve",
    Saturn: "Sa",
    Uranus: "Ur",
    Neptune: "Ne",
    Pluto: "Pl",
    Rahu: "Ra",
    Ketu: "Ke",
  };

  const shortPlanet = (name) => PLANET_ABBR[name] || String(name || "").slice(0, 2);
  const signIndexFrom = (maybeIndex, maybeName) => {
    const n = Number(maybeIndex);
    if (Number.isFinite(n) && n >= 0 && n < 12) return n;
    const s = String(maybeName || "");
    const idx = SIGN_NAMES.indexOf(s);
    return idx >= 0 ? idx : NaN;
  };

  const initBlankChart = () => {
    gridEl.innerHTML = "";
    SOUTH_LAYOUT.forEach((signName, index) => {
      if (signName === "EMPTY") {
        if (index === 5) {
          const center = document.createElement("div");
          center.className = "center-box";
          center.id = `${prefix}-center-box`;
          gridEl.appendChild(center);
        }
        return;
      }

      const signIdx = SIGN_NAMES.indexOf(signName);
      const box = document.createElement("div");
      box.className = "house";
      box.id = `${prefix}-box-${signIdx}`;
      box.innerHTML = `<div class=\"house-ids\" id=\"${prefix}-hid-${signIdx}\"></div><span class=\"sign-id\">${signName
        .substring(0, 3)
        .toUpperCase()}</span><div class=\"planet-list\" id=\"${prefix}-list-${signIdx}\"></div>`;
      gridEl.appendChild(box);
    });
  };

  initBlankChart();

  const asc = data?.angles?.ascendant;
  const ascSignIdx = signIndexFrom(asc?.sign_index, asc?.sign);
  const ascDeg = asc?.deg_in_sign;

  const ROMAN = ["I", "II", "III", "IV", "V", "VI", "VII", "VIII", "IX", "X", "XI", "XII"];
  const houses = Array.isArray(data?.houses) ? data.houses : [];

  // Place each house cusp label into the sign box where that cusp actually falls.
  houses.forEach((h) => {
    const houseNum = Number(h.house);
    if (!Number.isFinite(houseNum) || houseNum < 1 || houseNum > 12) return;
    const signIdx = signIndexFrom(h.sign_index, h.sign);
    if (!Number.isFinite(signIdx)) return;
    const hid = document.getElementById(`${prefix}-hid-${signIdx}`);
    if (!hid) return;
    const deg = Number(h.deg_in_sign);
    const line = document.createElement("div");
    line.textContent = `${ROMAN[houseNum - 1]} ${Number.isFinite(deg) ? deg.toFixed(1) : ""}°`;
    hid.appendChild(line);
  });

  if (Number.isFinite(ascSignIdx)) {
    const lagnaBox = document.getElementById(`${prefix}-box-${ascSignIdx}`);
    const lagnaList = document.getElementById(`${prefix}-list-${ascSignIdx}`);
    if (lagnaBox && lagnaList) {
      const line = document.createElement("div");
      line.className = "lagna-line";
      lagnaBox.appendChild(line);
      const lbl = document.createElement("div");
      lbl.className = "lagna-label";
      const ld = Number(ascDeg);
      lbl.textContent = `LAGNA ${Number.isFinite(ld) ? ld.toFixed(1) : ""}`;
      lagnaList.appendChild(lbl);
    }
  }




  const planets = Array.isArray(data?.planets) ? data.planets : [];
  planets.forEach((p) => {
    const idx = signIndexFrom(p.sign_index, p.sign);
    if (!Number.isFinite(idx)) return;
    const list = document.getElementById(`${prefix}-list-${idx}`);
    if (!list) return;
    const item = document.createElement("div");
    item.className = "planet-item";
    const left = document.createElement("span");
    left.textContent = shortPlanet(p.name);
    if (p.retrograde) {
      const r = document.createElement("span");
      r.className = "retro";
      r.textContent = "R";
      left.appendChild(r);
    }
    const right = document.createElement("span");
    right.className = "deg";
    const pd = Number(p.deg_in_sign);
    right.textContent = `${Number.isFinite(pd) ? pd.toFixed(1) : ""}`;
    item.appendChild(left);
    item.appendChild(right);
    list.appendChild(item);
  });
}

function addDaysToDateStr(dateStr, days) {
  const parts = String(dateStr || "").split("-").map((x) => Number(x));
  if (parts.length !== 3) return "";
  const [y, m, d] = parts;
  if (!Number.isFinite(y) || !Number.isFinite(m) || !Number.isFinite(d)) return "";
  const dt = new Date(Date.UTC(y, m - 1, d));
  if (!Number.isFinite(dt.getTime())) return "";
  dt.setUTCDate(dt.getUTCDate() + Number(days || 0));
  const pad2 = (n) => String(n).padStart(2, "0");
  return `${dt.getUTCFullYear()}-${pad2(dt.getUTCMonth() + 1)}-${pad2(dt.getUTCDate())}`;
}

function fmtDateDMY(dateStr) {
  const parts = String(dateStr || "").split("-");
  if (parts.length !== 3) return String(dateStr || "");
  const [y, m, d] = parts;
  if (!y || !m || !d) return String(dateStr || "");
  return `${d}/${m}/${y}`;
}

function setupDerivedChartsUI() {
  if (!chartYearEl) return;

  if (!lastPayload?.date) {
    chartYearEl.value = "";
    chartYearEl.disabled = true;
    if (yearDecEl) yearDecEl.disabled = true;
    if (yearIncEl) yearIncEl.disabled = true;
    if (progressMetaEl) progressMetaEl.textContent = "";
    if (transitMetaEl) transitMetaEl.textContent = "";
    return;
  }

  const birthYear = Number(String(lastPayload.date).slice(0, 4));
  if (!Number.isFinite(birthYear)) return;

  const currentYear = new Date().getFullYear();
  const defaultYear = Math.max(currentYear, birthYear);

  chartYearEl.min = String(birthYear);
  chartYearEl.max = String(birthYear + 150);
  chartYearEl.value = String(defaultYear);
  chartYearEl.disabled = false;
  if (yearDecEl) yearDecEl.disabled = false;
  if (yearIncEl) yearIncEl.disabled = false;

  if (!progressListenerBound) {
    progressListenerBound = true;

    // Manual typing — debounce so we don't fire on every keystroke
    let typeTimer = null;
    chartYearEl.addEventListener("input", () => {
      if (typeTimer) clearTimeout(typeTimer);
      typeTimer = setTimeout(() => {
        const y = Number(chartYearEl.value);
        if (Number.isFinite(y) && y >= 1800 && y <= 2300) refreshDerivedCharts();
      }, 600);
    });

    // ± buttons
    yearDecEl?.addEventListener("click", () => {
      const y = Number(chartYearEl.value) - 1;
      const min = Number(chartYearEl.min) || 1800;
      if (y >= min) {
        chartYearEl.value = String(y);
        refreshDerivedCharts();
      }
    });
    yearIncEl?.addEventListener("click", () => {
      const y = Number(chartYearEl.value) + 1;
      const max = Number(chartYearEl.max) || 2300;
      if (y <= max) {
        chartYearEl.value = String(y);
        refreshDerivedCharts();
      }
    });
  }

  refreshDerivedCharts();
}

async function refreshDerivedCharts() {
  if (!chartYearEl || !lastPayload?.date) return;
  chartYearEl.disabled = true;
  try {
    // Run sequentially or with a slight staggered delay if sequential is too slow.
    // Sequential is safer to avoid net::ERR_CONNECTION_RESET if server has concurrency limits.
    await refreshProgressionChart();
    await new Promise(r => setTimeout(r, 100)); // Tiny breather
    await refreshTransitChart();
  } catch (err) {
    console.error("Derived charts refresh failed:", err);
  } finally {
    chartYearEl.disabled = false;
  }
}

async function refreshProgressionChart() {
  if (!chartYearEl || !progressGridEl || !lastPayload?.date) return;

  const birthYear = Number(String(lastPayload.date).slice(0, 4));
  const targetYear = Number(chartYearEl.value);
  if (!Number.isFinite(birthYear) || !Number.isFinite(targetYear)) return;

  const ageYears = targetYear - birthYear;
  const progressedDate = addDaysToDateStr(lastPayload.date, ageYears);
  if (!progressedDate) return;

  const progressedPayload = { ...lastPayload, date: progressedDate };

  if (progressMetaEl) {
    progressMetaEl.style.color = "var(--text-muted)";
    progressMetaEl.textContent = `Loading...`;
  }

  try {
    const data = await generate(progressedPayload);
    if (progressMetaEl) {
      progressMetaEl.style.color = "var(--text-muted)";
      progressMetaEl.textContent = `DATE - ${fmtDateDMY(progressedDate)} ${String(lastPayload.time || "")}  AGE - ${ageYears}`;
    }
    renderChart(data, { gridEl: progressGridEl, idPrefix: "progress", centerTitle: "PROGRESSION" });
  } catch (err) {
    if (progressMetaEl) {
      progressMetaEl.style.color = "#ef4444";
      progressMetaEl.textContent = `Progression Error: ${err?.message || String(err)}`;
    }
  }
}

function isLeapYear(y) {
  return (y % 4 === 0 && y % 100 !== 0) || y % 400 === 0;
}

function dateWithYear(dateStr, targetYear) {
  const parts = String(dateStr || "").split("-").map((x) => Number(x));
  if (parts.length !== 3) return "";
  const [, m, d] = parts;
  if (!Number.isFinite(m) || !Number.isFinite(d) || !Number.isFinite(targetYear)) return "";
  const pad2 = (n) => String(n).padStart(2, "0");
  let day = d;
  if (m === 2 && d === 29 && !isLeapYear(targetYear)) day = 28;
  return `${targetYear}-${pad2(m)}-${pad2(day)}`;
}

async function refreshTransitChart() {
  if (!chartYearEl || !transitGridEl || !lastPayload?.date) return;

  const targetYear = Number(chartYearEl.value);
  if (!Number.isFinite(targetYear)) return;

  const transitDate = dateWithYear(lastPayload.date, targetYear);
  if (!transitDate) return;

  const transitPayload = { ...lastPayload, date: transitDate };

  if (transitMetaEl) {
    transitMetaEl.style.color = "var(--text-muted)";
    transitMetaEl.textContent = `Loading...`;
  }

  try {
    const data = await generate(transitPayload);
    if (transitMetaEl) {
      transitMetaEl.style.color = "var(--text-muted)";
      transitMetaEl.textContent = `DATE - ${fmtDateDMY(transitDate)} ${String(lastPayload.time || "")}`;
    }
    renderChart(data, { gridEl: transitGridEl, idPrefix: "transit", centerTitle: "TRANSIT" });
  } catch (err) {
    if (transitMetaEl) {
      transitMetaEl.style.color = "#ef4444";
      transitMetaEl.textContent = `Transit Error: ${err?.message || String(err)}`;
    }
  }
}

function initDefaults() {
  // Set a reasonable default to let you click "Generate" immediately.
  const now = new Date();
  const pad = (n) => String(n).padStart(2, "0");
  const yyyy = now.getFullYear();
  const mm = pad(now.getMonth() + 1);
  const dd = pad(now.getDate());
  const hh = pad(now.getHours());
  const mi = pad(now.getMinutes());

  form.elements.date.value = `${yyyy}-${mm}-${dd}`;
  form.elements.time.value = `${hh}:${mi}`;

  // Browser offset is opposite sign (minutes behind UTC). Convert to "+HH:MM" style.
  const offMin = -now.getTimezoneOffset();
  const sign = offMin >= 0 ? "+" : "-";
  const abs = Math.abs(offMin);
  const oh = pad(Math.floor(abs / 60));
  const om = pad(abs % 60);
  form.elements.tz_offset.value = `${sign}${oh}:${om}`;

  // Default coordinates: Mumbai-ish.
  form.elements.lat.value = "17.9689";
  form.elements.lon.value = "79.5941";
  if (form.elements.house_system) form.elements.house_system.value = "P";

  // Initialize empty South Indian chart.
  renderChart(
    { angles: { ascendant: { sign_index: 0, deg_in_sign: 0 } }, planets: [], houses: [] },
    { gridEl: natalGridEl, idPrefix: "natal", centerTitle: "RASHI" }
  );
  renderChart(
    { angles: { ascendant: { sign_index: 0, deg_in_sign: 0 } }, planets: [], houses: [] },
    { gridEl: progressGridEl, idPrefix: "progress", centerTitle: "PROGRESSION" }
  );
  renderChart(
    { angles: { ascendant: { sign_index: 0, deg_in_sign: 0 } }, planets: [], houses: [] },
    { gridEl: transitGridEl, idPrefix: "transit", centerTitle: "TRANSIT" }
  );
  setupDerivedChartsUI();
}

form.addEventListener("submit", async (e) => {
  e.preventDefault();
  showStatus("");
  btn.disabled = true;
  btn.textContent = "Calculating...";
  try {
    const payload = Object.fromEntries(new FormData(form).entries());
    payload.lat = Number(payload.lat);
    payload.lon = Number(payload.lon);
    lastPayload = { ...payload };
    const data = await generate(payload);
    fill(data);
    showStatus(`JD(UT): ${data.meta?.jd_ut ?? ""}`);
  } catch (err) {
    showStatus(err?.message || String(err), true);
  } finally {
    btn.disabled = false;
    btn.textContent = "Generate Kundli";
  }
});

initDefaults();

async function refreshHealth() {
  if (!healthEl) return;
  try {
    const res = await fetch("/health");
    const h = await res.json();
    if (!res.ok) throw new Error("health failed");
    healthEl.innerHTML = `Server: <code>${h.mode || "?"}</code> <code>v${h.version || "?"}</code>`;
  } catch {
    healthEl.innerHTML = `Server: <code>unreachable</code>`;
  }
}

refreshHealth();
loadLocalPlaces();

let placeTimer = null;
placeInput?.addEventListener("input", (e) => {
  const q = String(e.target.value || "").trim();
  if (placeTimer) clearTimeout(placeTimer);
  placeTimer = setTimeout(() => placeSearch(q), 220);
});

async function placeSearch(q) {
  if (!searchResults) return;
  if (!q || q.length < 3) {
    searchResults.style.display = "none";
    searchResults.innerHTML = "";
    return;
  }

  try {
    // 1. Offline-first suggestions.
    const needle = q.toLowerCase();
    const offline = (localPlaces || [])
      .filter((p) => String(p.name || "").toLowerCase().includes(needle))
      .slice(0, 6)
      .map((p) => ({
        display_name: `${p.name}${p.region ? ", " + p.region : ""}${p.country ? ", " + p.country : ""}`,
        lat: p.lat,
        lon: p.lon,
      }));

    let items = [...offline];

    // 2. Optional online lookup for broader coverage.
    // We wrap this in a separate try/catch so online failure doesn't kill offline results.
    if (items.length < 3) {
      try {
        const url = `https://nominatim.openstreetmap.org/search?format=jsonv2&limit=5&q=${encodeURIComponent(q)}`;
        const res = await fetch(url, {
          headers: { "Accept": "application/json" },
          signal: AbortSignal.timeout(3000) // Don't hang forever
        });
        if (res.ok) {
          const online = await res.json();
          if (Array.isArray(online)) {
            // Deduplicate by simple fuzzy match or coordinate check if needed, 
            // but for now just append unique-ish names.
            const existingNames = new Set(items.map(i => i.display_name.toLowerCase()));
            online.forEach(p => {
              const name = p.display_name;
              if (!existingNames.has(name.toLowerCase())) {
                items.push({
                  display_name: name,
                  lat: p.lat,
                  lon: p.lon
                });
              }
            });
          }
        }
      } catch (e) {
        console.warn("Online geocode backup failed:", e);
      }
    }

    searchResults.innerHTML = "";
    if (items.length === 0) {
      searchResults.style.display = "none";
      // Only show error if we have nothing at all.
      return;
    }

    searchResults.style.display = "block";
    items.slice(0, 5).forEach((place) => {
      const div = document.createElement("div");
      div.className = "result-item";
      div.textContent = place.display_name || q;
      div.onclick = () => {
        form.elements.lat.value = Number(place.lat).toFixed(4);
        form.elements.lon.value = Number(place.lon).toFixed(4);
        placeInput.value = String(place.display_name || q).split(",")[0];
        searchResults.style.display = "none";
        showStatus("Place selected.");
      };
      searchResults.appendChild(div);
    });
  } catch (err) {
    console.error("placeSearch error:", err);
    searchResults.style.display = "none";
  }
}

window.addEventListener("click", (e) => {
  if (!searchResults) return;
  if (e.target !== placeInput) searchResults.style.display = "none";
});
