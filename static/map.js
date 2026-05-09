// PSEUDOCODE:
// 1. Init Leaflet centered on Trondheim sentrum
// 2. Add OSM tiles + a markercluster layer
// 3. Fetch /kart/markers, render coloured circle markers per listing
// 4. On filter form change, debounced refetch and rebuild the layer
// 5. Marker click → Leaflet popup with key info + link to detail page

(function () {
  const map = L.map("map").setView([63.4305, 10.3951], 12);
  L.tileLayer("https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png", {
    attribution: '© <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a>',
    maxZoom: 19,
  }).addTo(map);

  const cluster = L.markerClusterGroup();
  map.addLayer(cluster);

  // ── Colour scale ────────────────────────────────────────────────────────────
  // 5-step green→red ramp based on the dataset's P10/P30/P50/P70/P90 of kvm_pris.
  const RAMP = ["#16a34a", "#84cc16", "#facc15", "#fb923c", "#dc2626"];
  const NEUTRAL = "#94a3b8";

  function percentiles(values) {
    const sorted = values.slice().sort((a, b) => a - b);
    const at = (p) => sorted[Math.min(sorted.length - 1, Math.floor(p * sorted.length))];
    return [at(0.1), at(0.3), at(0.5), at(0.7), at(0.9)];
  }

  function bucketColour(kvm, ps) {
    if (kvm == null) return NEUTRAL;
    if (kvm <= ps[0]) return RAMP[0];
    if (kvm <= ps[1]) return RAMP[1];
    if (kvm <= ps[2]) return RAMP[2];
    if (kvm <= ps[3]) return RAMP[3];
    return RAMP[4];
  }

  // ── Format helpers ──────────────────────────────────────────────────────────
  function fmtKr(n) {
    if (n == null) return "—";
    return Math.round(n).toLocaleString("nb-NO").replace(/,/g, " ") + " kr";
  }

  function flagBadges(flagg) {
    if (!flagg) return "";
    return flagg.split(" | ").map((f) => {
      let cls = "badge";
      if (f === "Prisnedsatt") cls += " badge-prisnedsatt";
      else if (f.includes("14+")) cls += " badge-dager";
      else if (f.includes("visninger")) cls += " badge-visninger";
      else if (f.includes("fellesgjeld")) cls += " badge-fellesgjeld";
      else if (f.includes("Lav kr/m²")) cls += " badge-lavkvm";
      else return "";
      return `<span class="${cls}">${f}</span>`;
    }).join(" ");
  }

  function buildPopup(l) {
    return `
      <div class="map-popup">
        <strong>${l.adresse || l.finnkode}</strong><br>
        <span style="color:#64748b;">${l.omrade || ""}</span><br>
        <div style="margin:6px 0;">
          ${l.prisantydning ? "Pris: <strong>" + fmtKr(l.prisantydning) + "</strong><br>" : ""}
          ${l.totalpris && l.totalpris !== l.prisantydning ? "Totalt: " + fmtKr(l.totalpris) + "<br>" : ""}
          ${l.kvm_pris ? "kr/m²: <strong>" + fmtKr(l.kvm_pris) + "</strong><br>" : ""}
          ${l.bra ? "BRA: " + l.bra + "<br>" : ""}
          ${l.rom ? "Rom: " + l.rom + "<br>" : ""}
        </div>
        <div style="margin-bottom:6px;">${flagBadges(l.flagg)}</div>
        <a href="/annonse/${l.finnkode}">Se detaljer →</a>
      </div>`;
  }

  // ── Marker rendering ────────────────────────────────────────────────────────
  function renderMarkers(listings) {
    cluster.clearLayers();
    const stats = document.getElementById("map-stats");

    const kvmValues = listings.map((l) => l.kvm_pris).filter((v) => v != null);
    const ps = kvmValues.length >= 5 ? percentiles(kvmValues) : null;

    listings.forEach((l) => {
      if (l.lat == null || l.lon == null) return;
      const colour = ps ? bucketColour(l.kvm_pris, ps) : NEUTRAL;
      const marker = L.circleMarker([l.lat, l.lon], {
        radius: 6,
        fillColor: colour,
        color: "#fff",
        weight: 1,
        opacity: 1,
        fillOpacity: 0.9,
      });
      marker.bindPopup(buildPopup(l));
      cluster.addLayer(marker);
    });

    if (stats) {
      stats.textContent = `Viser ${listings.length} boliger`;
    }
  }

  // ── Filter wiring ───────────────────────────────────────────────────────────
  let refreshTimer = null;
  async function fetchMarkers() {
    const form = document.getElementById("filter-form");
    const fd = new FormData(form);
    const r = await fetch("/kart/markers", { method: "POST", body: fd });
    if (!r.ok) {
      console.error("Failed to load markers", r.status);
      return;
    }
    renderMarkers(await r.json());
  }

  // Exposed globally for the inline handlers in kart.html (resetFilters, toggle*…)
  window.refreshMarkers = function () {
    clearTimeout(refreshTimer);
    refreshTimer = setTimeout(fetchMarkers, 200);
  };

  // Debounced reaction to filter form changes
  document.getElementById("filter-form").addEventListener("input", () => {
    clearTimeout(refreshTimer);
    refreshTimer = setTimeout(fetchMarkers, 400);
  });
  document.getElementById("filter-form").addEventListener("change", fetchMarkers);

  // Initial load
  fetchMarkers();
})();
