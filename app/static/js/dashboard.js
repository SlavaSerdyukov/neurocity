const state = {
  socket: null,
  snapshot: null,
  selectedDistrictId: 0,
  charts: {},
  pixi: null,
  pixiReady: false,
  pixiInitPromise: null,
  pixiRenderVersion: 0,
  pendingSnapshot: null,
  renderScheduled: false,
  policyEditing: new Set(),
  interventionSeverity: 0.55,
};

const fmt = {
  pct: (value) => `${Math.round((value || 0) * 100)}%`,
  money: (value) => `${Math.round(value || 0).toLocaleString()}`,
  compactMoney: (value) => `${((value || 0) / 1_000_000).toFixed(1)}M`,
  number: (value, digits = 2) => Number(value || 0).toFixed(digits),
};

function byId(id) {
  return document.getElementById(id);
}

function commandLabel(message) {
  const labels = {
    start: "Simulation started",
    pause: "Simulation paused",
    reset: "City reset",
    tick: "Advanced one tick",
    speed: `Speed set to ${message.speed}x`,
    intervention: "Intervention queued",
    policy: "Policy updated",
  };
  return labels[message.action] || "Command sent";
}

function setCommandStatus(text, tone = "neutral") {
  const topStatus = byId("command-state");
  const feedback = byId("observer-feedback");
  [topStatus, feedback].forEach((element) => {
    if (!element) return;
    element.textContent = text;
    element.classList.toggle("good", tone === "good");
    element.classList.toggle("error", tone === "error");
  });
  if (topStatus) topStatus.title = text;
}

async function readJson(response) {
  const text = await response.text();
  if (!text) return null;
  try {
    return JSON.parse(text);
  } catch {
    return { detail: text.slice(0, 160) };
  }
}

async function command(message) {
  const label = commandLabel(message);
  if (state.socket && state.socket.readyState === WebSocket.OPEN) {
    state.socket.send(JSON.stringify(message));
    setCommandStatus(label, "good");
    return;
  }
  const jsonHeaders = { "Content-Type": "application/json" };
  const fallback = {
    start: () => fetch("/simulation/start", { method: "POST", headers: jsonHeaders, body: JSON.stringify({ speed: 1 }) }),
    pause: () => fetch("/simulation/pause", { method: "POST" }),
    reset: () => fetch("/simulation/reset", { method: "POST", headers: jsonHeaders, body: JSON.stringify({}) }),
    speed: () => fetch("/simulation/speed", { method: "POST", headers: jsonHeaders, body: JSON.stringify({ speed: message.speed }) }),
    tick: () => fetch(`/simulation/tick?steps=${message.steps || 1}`, { method: "POST" }),
    intervention: () =>
      fetch("/intervention", {
        method: "POST",
        headers: jsonHeaders,
        body: JSON.stringify({
          kind: message.kind,
          severity: message.severity,
          target_district_id: message.target_district_id ?? null,
        }),
      }),
    policy: () =>
      fetch("/policy", {
        method: "POST",
        headers: jsonHeaders,
        body: JSON.stringify({ parameter: message.parameter, value: message.value }),
      }),
  };
  if (!fallback[message.action]) {
    setCommandStatus("Unknown command", "error");
    return;
  }
  try {
    const response = await fallback[message.action]();
    const payload = await readJson(response);
    if (!response.ok) {
      const detail = payload?.detail || response.statusText || "Command failed";
      throw new Error(detail);
    }
    if (payload) scheduleDashboardUpdate(payload);
    setCommandStatus(label, "good");
  } catch (error) {
    setCommandStatus(error.message || "Command failed", "error");
  }
}

function scheduleDashboardUpdate(snapshot) {
  state.pendingSnapshot = snapshot;
  if (state.renderScheduled) return;
  state.renderScheduled = true;
  window.requestAnimationFrame(() => {
    state.renderScheduled = false;
    if (!state.pendingSnapshot) return;
    const nextSnapshot = state.pendingSnapshot;
    state.pendingSnapshot = null;
    updateDashboard(nextSnapshot);
  });
}

function wireControls() {
  document.querySelectorAll("[data-action]").forEach((button) => {
    button.addEventListener("click", async () => {
      const action = button.dataset.action;
      if (action === "save") {
        try {
          const response = await fetch("/save", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ name: "autosave" }),
          });
          if (!response.ok) throw new Error(response.statusText || "Save failed");
          setCommandStatus("Saved autosave", "good");
        } catch (error) {
          setCommandStatus(error.message || "Save failed", "error");
        }
        return;
      }
      if (action === "load") {
        try {
          const response = await fetch("/load", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ name: "autosave" }),
          });
          const payload = await readJson(response);
          if (!response.ok) throw new Error(payload?.detail || response.statusText || "Load failed");
          if (payload) scheduleDashboardUpdate(payload);
          const loaded = payload?.load_status?.loaded !== false;
          setCommandStatus(loaded ? "Loaded autosave" : "No autosave found", loaded ? "good" : "neutral");
        } catch (error) {
          setCommandStatus(error.message || "Load failed", "error");
        }
        return;
      }
      if (action === "reset") {
        command({ action: "reset" });
        return;
      }
      if (action === "tick") {
        command({ action: "tick", steps: 1 });
        return;
      }
      command({ action });
    });
  });

  document.querySelectorAll("[data-speed]").forEach((button) => {
    button.addEventListener("click", () => command({ action: "speed", speed: Number(button.dataset.speed) }));
  });

  const severityInput = byId("intervention-severity");
  severityInput.addEventListener("input", () => {
    state.interventionSeverity = Number(severityInput.value) / 100;
    byId("intervention-severity-value").textContent = fmt.pct(state.interventionSeverity);
  });

  document.querySelectorAll("[data-intervention]").forEach((button) => {
    button.addEventListener("click", () => {
      command({
        action: "intervention",
        kind: button.dataset.intervention,
        severity: state.interventionSeverity,
        target_district_id: state.selectedDistrictId,
      });
    });
  });

  wirePolicySlider("corruption");
  wirePolicySlider("crime");
}

function connectSocket() {
  const protocol = window.location.protocol === "https:" ? "wss" : "ws";
  const socket = new WebSocket(`${protocol}://${window.location.host}/ws/simulation`);
  state.socket = socket;
  socket.onopen = () => {
    byId("connection-state").textContent = "online";
    byId("connection-state").classList.add("online");
    setCommandStatus("ready");
  };
  socket.onmessage = (event) => scheduleDashboardUpdate(JSON.parse(event.data));
  socket.onclose = () => {
    byId("connection-state").textContent = "offline";
    byId("connection-state").classList.remove("online");
    setCommandStatus("reconnecting");
    setTimeout(connectSocket, 1200);
  };
}

function updateDashboard(snapshot) {
  state.snapshot = snapshot;
  const metrics = snapshot.metrics || {};
  byId("day-value").textContent = snapshot.day;
  byId("tick-value").textContent = snapshot.tick;
  byId("speed-value").textContent = `${snapshot.speed || 0}x`;

  byId("kpi-gdp").textContent = fmt.compactMoney(metrics.gdp);
  byId("kpi-unemployment").textContent = fmt.pct(metrics.unemployment);
  byId("kpi-inflation").textContent = fmt.pct(metrics.inflation);
  byId("kpi-productivity").textContent = fmt.number(metrics.productivity);
  byId("kpi-happiness").textContent = fmt.pct(metrics.happiness);
  byId("kpi-stress").textContent = fmt.pct(metrics.stress);
  byId("kpi-polarization").textContent = fmt.pct(metrics.polarization);
  byId("kpi-crime").textContent = fmt.pct(metrics.crime);
  byId("kpi-energy").textContent = fmt.pct(metrics.energy_margin);
  byId("kpi-housing").textContent = fmt.pct(metrics.housing_pressure);
  byId("kpi-transport").textContent = `${Math.round(metrics.commute_time || 0)} min`;
  byId("kpi-pollution").textContent = fmt.pct(metrics.pollution);
  if (snapshot.engine_error) {
    setCommandStatus(`Paused: ${snapshot.engine_error}`, "error");
  }

  renderMap(snapshot);
  renderInspector(snapshot);
  renderInterventions(snapshot);
  renderEvents(snapshot.events || []);
  renderNewspaper(snapshot.newspaper || []);
  renderCharts(snapshot.history || []);
}

function districtColor(district) {
  const crime = district.crime || 0;
  const wealth = district.wealth || 0;
  const pollution = district.pollution || 0;
  return d3.interpolateRgbBasis(["#15342d", "#3e624b", "#ad7840", "#ba3745"])(crime * 0.46 + pollution * 0.28 + (1 - wealth) * 0.2);
}

function renderMap(snapshot) {
  const svg = d3.select("#city-map");
  const districts = snapshot.districts || [];
  const roads = snapshot.roads || [];
  const districtById = new Map(districts.map((district) => [district.id, district]));
  svg.attr("viewBox", "0 0 100 100").attr("preserveAspectRatio", "xMidYMid meet");
  svg.selectAll("*").remove();

  svg
    .append("g")
    .selectAll("line")
    .data(roads)
    .join("line")
    .attr("class", "road")
    .attr("x1", (road) => districtById.get(road.source).x)
    .attr("y1", (road) => districtById.get(road.source).y)
    .attr("x2", (road) => districtById.get(road.target).x)
    .attr("y2", (road) => districtById.get(road.target).y)
    .attr("stroke-width", (road) => 0.15 + road.congestion * 0.9)
    .attr("opacity", (road) => 0.32 + road.congestion * 0.5);

  const transit = svg.append("g");
  (snapshot.transit_lines || []).forEach((line) => {
    const points = line.stops.map((id) => districtById.get(id)).filter(Boolean);
    transit
      .append("path")
      .datum(points)
      .attr("class", "transit-line")
      .attr("d", d3.line().x((district) => district.x).y((district) => district.y).curve(d3.curveCatmullRom.alpha(0.5)));
  });

  svg
    .append("g")
    .selectAll("polygon")
    .data(districts)
    .join("polygon")
    .attr("class", (district) => `district ${district.id === state.selectedDistrictId ? "selected" : ""}`)
    .attr("points", (district) => district.polygon.map((point) => point.join(",")).join(" "))
    .attr("fill", districtColor)
    .attr("fill-opacity", (district) => 0.48 + (district.happiness || 0) * 0.18)
    .on("click", (_, district) => {
      state.selectedDistrictId = district.id;
      renderMap(state.snapshot);
      renderInspector(state.snapshot);
    });

  svg
    .append("g")
    .selectAll("text")
    .data(districts)
    .join("text")
    .attr("class", "district-label")
    .attr("x", (district) => district.x)
    .attr("y", (district) => district.y)
    .attr("text-anchor", "middle")
    .text((district) => district.name.split(" ")[0]);

  renderPixiHeat(districts);
}

async function ensurePixi() {
  if (state.pixiReady && state.pixi) return state.pixi;
  if (state.pixiInitPromise) return state.pixiInitPromise;
  if (!window.PIXI) return null;
  const host = byId("pixi-layer");
  state.pixiInitPromise = (async () => {
    const app = new PIXI.Application();
    await app.init({
      resizeTo: host,
      backgroundAlpha: 0,
      antialias: true,
      autoDensity: true,
      resolution: window.devicePixelRatio || 1,
    });
    host.replaceChildren();
    host.appendChild(app.canvas);
    state.pixi = app;
    state.pixiReady = true;
    return app;
  })();
  try {
    return await state.pixiInitPromise;
  } catch {
    state.pixiInitPromise = null;
    state.pixiReady = false;
    state.pixi = null;
    return null;
  }
}

function renderPixiHeat(districts) {
  const renderVersion = ++state.pixiRenderVersion;
  ensurePixi().then((app) => {
    if (!app || renderVersion !== state.pixiRenderVersion) return;
    const host = byId("pixi-layer");
    const bounds = host.getBoundingClientRect();
    if (!bounds.width || !bounds.height) return;
    app.renderer.resize(bounds.width, bounds.height);
    app.stage.removeChildren();
    districts.forEach((district) => {
      const heat = Math.max(district.crime || 0, district.pollution || 0, district.congestion || 0);
      if (heat < 0.08) return;
      const g = new PIXI.Graphics();
      const color = district.crime > district.congestion ? 0xff5f68 : 0xf5b84b;
      g.circle((district.x / 100) * bounds.width, (district.y / 100) * bounds.height, 18 + heat * 58);
      g.fill({ color, alpha: 0.08 + heat * 0.16 });
      app.stage.addChild(g);
    });
  });
}

function renderInspector(snapshot) {
  const districts = snapshot.districts || [];
  const district = districts.find((item) => item.id === state.selectedDistrictId) || districts[0];
  if (!district) return;
  state.selectedDistrictId = district.id;
  byId("district-name").textContent = district.name;
  byId("district-type").textContent = district.archetype;
  byId("observer-target").textContent = district.name;
  byId("district-wealth").textContent = fmt.pct(district.wealth);
  byId("district-density").textContent = fmt.pct(district.density);
  byId("district-crime").textContent = fmt.pct(district.crime);
  byId("district-transit").textContent = fmt.pct(district.transit_access);
  byId("district-rent").textContent = fmt.money(district.average_rent);
  byId("district-jobs").textContent = fmt.pct(district.business_activity);
}

function renderInterventions(snapshot) {
  const government = snapshot.government || {};
  syncPolicySlider("corruption", government.corruption || 0);
  syncPolicySlider("crime", (snapshot.metrics || {}).crime || 0);

  const list = byId("active-interventions");
  list.innerHTML = "";
  const interventions = snapshot.interventions || [];
  if (!interventions.length) {
    const empty = document.createElement("span");
    empty.className = "intervention-empty";
    empty.textContent = "No active interventions";
    list.appendChild(empty);
    return;
  }
  interventions.slice(-6).forEach((intervention) => {
    const chip = document.createElement("span");
    chip.className = "intervention-chip";
    const remaining = Math.max(0, (intervention.expires_tick || 0) - (snapshot.tick || 0));
    chip.textContent = `${intervention.name} ${fmt.pct(intervention.severity)} · ${remaining}d`;
    list.appendChild(chip);
  });
}

function wirePolicySlider(parameter) {
  const input = byId(`policy-${parameter}`);
  if (!input) return;
  input.addEventListener("pointerdown", () => {
    state.policyEditing.add(parameter);
  });
  input.addEventListener("input", () => {
    byId(`policy-${parameter}-value`).textContent = `${input.value}%`;
  });
  input.addEventListener("change", () => {
    state.policyEditing.delete(parameter);
    command({ action: "policy", parameter, value: Number(input.value) / 100 });
  });
}

function syncPolicySlider(parameter, value) {
  const input = byId(`policy-${parameter}`);
  if (!input || state.policyEditing.has(parameter)) return;
  const percent = Math.round((value || 0) * 100);
  input.value = percent;
  byId(`policy-${parameter}-value`).textContent = `${percent}%`;
}

function renderEvents(events) {
  const list = byId("event-list");
  const wasReadingOlderEvents = list.scrollTop > 8;
  const previousScrollTop = list.scrollTop;
  list.innerHTML = "";
  events
    .slice()
    .reverse()
    .forEach((event) => {
      const row = document.createElement("div");
      row.className = `event-row ${event.category}`;
      const title = document.createElement("strong");
      title.textContent = event.title;
      const meta = document.createElement("span");
      meta.textContent = `Day ${event.day} · ${event.category} · severity ${fmt.pct(event.severity)}`;
      const description = document.createElement("p");
      description.textContent = event.description;
      row.append(title, meta, description);
      list.appendChild(row);
    });
  if (wasReadingOlderEvents) {
    list.scrollTop = previousScrollTop;
  }
}

function renderNewspaper(headlines) {
  const list = byId("newspaper-list");
  const wasReadingOlderHeadlines = list.scrollTop > 8;
  const previousScrollTop = list.scrollTop;
  list.innerHTML = "";
  headlines.slice(1).forEach((headline) => {
    const item = document.createElement("li");
    item.textContent = headline;
    list.appendChild(item);
  });
  if (wasReadingOlderHeadlines) {
    list.scrollTop = previousScrollTop;
  }
}

function chartOptions() {
  return {
    responsive: true,
    maintainAspectRatio: false,
    animation: false,
    interaction: { intersect: false, mode: "index" },
    plugins: {
      legend: { labels: { color: "#8fa49a", boxWidth: 10, font: { size: 10 } } },
    },
    scales: {
      x: { display: false },
      y: {
        ticks: { color: "#8fa49a", font: { size: 10 }, maxTicksLimit: 4 },
        grid: { color: "rgba(143, 164, 154, 0.12)" },
      },
    },
  };
}

function makeChart(id, datasets) {
  const context = byId(id).getContext("2d");
  return new Chart(context, {
    type: "line",
    data: { labels: [], datasets },
    options: chartOptions(),
  });
}

function initCharts() {
  state.charts.economy = makeChart("economy-chart", [
    { label: "GDP", borderColor: "#4fe3ff", data: [], tension: 0.25, pointRadius: 1.4 },
    { label: "Unemployment", borderColor: "#ff5f68", data: [], tension: 0.25, pointRadius: 1.4 },
    { label: "Inflation", borderColor: "#f5b84b", data: [], tension: 0.25, pointRadius: 1.4 },
  ]);
  state.charts.society = makeChart("society-chart", [
    { label: "Happiness", borderColor: "#6df0a5", data: [], tension: 0.25, pointRadius: 1.4 },
    { label: "Stress", borderColor: "#f5b84b", data: [], tension: 0.25, pointRadius: 1.4 },
    { label: "Polarization", borderColor: "#b68cff", data: [], tension: 0.25, pointRadius: 1.4 },
    { label: "Crime", borderColor: "#ff5f68", data: [], tension: 0.25, pointRadius: 1.4 },
  ]);
  state.charts.infrastructure = makeChart("infrastructure-chart", [
    { label: "Energy", borderColor: "#4fe3ff", data: [], tension: 0.25, pointRadius: 1.4 },
    { label: "Housing", borderColor: "#ff5f68", data: [], tension: 0.25, pointRadius: 1.4 },
    { label: "Congestion", borderColor: "#f5b84b", data: [], tension: 0.25, pointRadius: 1.4 },
  ]);
}

function updateChart(chart, labels, series) {
  chart.data.labels = labels;
  chart.data.datasets.forEach((dataset, index) => {
    dataset.data = series[index] || [];
  });
  chart.update("none");
}

function renderCharts(history) {
  if (!state.charts.economy) return;
  const metrics = state.snapshot?.metrics || {};
  const rows = history.length
    ? history.slice(-90)
    : [
        {
          tick: state.snapshot?.tick || 0,
          gdp: metrics.gdp || 0,
          unemployment: metrics.unemployment || 0,
          inflation: metrics.inflation || 0,
          happiness: metrics.happiness || 0,
          stress: metrics.stress || 0,
          polarization: metrics.polarization || 0,
          crime: metrics.crime || 0,
          energy_margin: metrics.energy_margin || 0,
          housing_pressure: metrics.housing_pressure || 0,
          congestion: metrics.congestion || 0,
        },
      ];
  const labels = rows.map((row) => row.tick);
  const gdpMax = Math.max(1, ...rows.map((row) => row.gdp || 0));
  updateChart(state.charts.economy, labels, [
    rows.map((row) => (row.gdp || 0) / gdpMax),
    rows.map((row) => row.unemployment || 0),
    rows.map((row) => row.inflation || 0),
  ]);
  updateChart(state.charts.society, labels, [
    rows.map((row) => row.happiness || 0),
    rows.map((row) => row.stress || 0),
    rows.map((row) => row.polarization || 0),
    rows.map((row) => row.crime || 0),
  ]);
  updateChart(state.charts.infrastructure, labels, [
    rows.map((row) => row.energy_margin || 0),
    rows.map((row) => row.housing_pressure || 0),
    rows.map((row) => row.congestion || 0),
  ]);
}

async function hydrate() {
  wireControls();
  initCharts();
  const response = await fetch("/city");
  scheduleDashboardUpdate(await response.json());
  connectSocket();
}

hydrate();
