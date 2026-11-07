const TABS = [
  ["overview", "Overview"],
  ["states", "States"],
  ["hospitals", "Hospitals"],
  ["urgency", "Urgency"],
  ["actions", "What to do"],
];

const COLOURS = {
  ink: "#1c241f",
  muted: "#5c675f",
  teal: "#0e6b62",
  ochre: "#b86112",
  clay: "#9c2f2a",
  good: "#1d7a46",
  blue: "#1f4e79",
};

const URGENCY_COLOURS = [COLOURS.clay, COLOURS.ochre, COLOURS.teal];
const charts = [];

function money(n) {
  return Number(n).toLocaleString("en-AU");
}

function pct(n) {
  return `${Number(n).toLocaleString("en-AU", { minimumFractionDigits: 1, maximumFractionDigits: 1 })}%`;
}

function baseText() {
  return { fontFamily: "Avenir Next, Segoe UI, sans-serif", color: COLOURS.ink };
}

function axisCommon() {
  return {
    axisLine: { lineStyle: { color: "#e3d9c6" } },
    axisTick: { show: false },
    axisLabel: { color: COLOURS.ink, fontSize: 12 },
    splitLine: { lineStyle: { color: "#efe7d8" } },
  };
}

function mount(el, option) {
  const chart = echarts.init(el, null, { renderer: "canvas" });
  chart.setOption(option);
  charts.push(chart);
  return chart;
}

function hbar(el, rows, colour, suffix) {
  const labels = rows.map((row) => row.label).reverse();
  const values = rows.map((row) => row.value).reverse();
  mount(el, {
    textStyle: baseText(),
    grid: { left: 8, right: 72, top: 12, bottom: 8, containLabel: true },
    tooltip: { trigger: "axis", axisPointer: { type: "shadow" } },
    xAxis: { type: "value", ...axisCommon(), axisLabel: { show: false }, splitLine: { show: false } },
    yAxis: { type: "category", data: labels, ...axisCommon() },
    series: [{
      type: "bar",
      data: values,
      barMaxWidth: 22,
      itemStyle: { color: colour, borderRadius: [0, 6, 6, 0] },
      label: {
        show: true,
        position: "right",
        color: COLOURS.ink,
        formatter: (point) => `${point.value.toLocaleString("en-AU")}${suffix}`,
      },
    }],
  });
}

function signedBars(el, rows) {
  const labels = rows.map((row) => row.short || row.label).reverse();
  const values = rows.map((row) => row.value).reverse();
  mount(el, {
    textStyle: baseText(),
    grid: { left: 8, right: 56, top: 12, bottom: 8, containLabel: true },
    tooltip: { trigger: "axis", axisPointer: { type: "shadow" } },
    xAxis: { type: "value", ...axisCommon() },
    yAxis: { type: "category", data: labels, ...axisCommon() },
    series: [{
      type: "bar",
      data: values.map((value) => ({
        value,
        itemStyle: { color: value > 0 ? COLOURS.clay : COLOURS.teal, borderRadius: 4 },
      })),
      barMaxWidth: 18,
      label: {
        show: true,
        position: "right",
        color: COLOURS.ink,
        formatter: (point) => `${point.value > 0 ? "+" : ""}${point.value.toFixed(1)}`,
      },
    }],
  });
}

function grouped(el, rows, categories, colours) {
  mount(el, {
    textStyle: baseText(),
    legend: { top: 0, textStyle: { color: COLOURS.ink } },
    grid: { left: 8, right: 16, top: 36, bottom: 8, containLabel: true },
    tooltip: { trigger: "axis" },
    xAxis: { type: "category", data: rows.map((row) => row.short || row.label), ...axisCommon() },
    yAxis: {
      type: "value",
      ...axisCommon(),
      axisLabel: { formatter: "{value}%", color: COLOURS.ink },
    },
    series: categories.map((name, index) => ({
      name,
      type: "bar",
      data: rows.map((row) => row.values[index]),
      itemStyle: { color: colours[index], borderRadius: [4, 4, 0, 0] },
      label: {
        show: true,
        position: "top",
        fontSize: 10,
        color: COLOURS.ink,
        formatter: (point) => point.value.toFixed(0),
      },
    })),
  });
}

function line(el, rows) {
  mount(el, {
    textStyle: baseText(),
    grid: { left: 8, right: 16, top: 16, bottom: 8, containLabel: true },
    tooltip: { trigger: "axis" },
    xAxis: { type: "category", data: rows.map((row) => row.label), ...axisCommon() },
    yAxis: {
      type: "value",
      ...axisCommon(),
      axisLabel: { formatter: "{value}%", color: COLOURS.ink },
    },
    series: [{
      type: "line",
      data: rows.map((row) => row.value),
      smooth: false,
      symbol: "circle",
      symbolSize: 8,
      lineStyle: { width: 3, color: COLOURS.teal },
      itemStyle: { color: COLOURS.tealDark || COLOURS.teal },
      label: {
        show: true,
        position: "top",
        fontSize: 11,
        color: COLOURS.ink,
        formatter: (point) => point.value.toFixed(1),
      },
    }],
  });
}

function multiLine(el, rows, categories) {
  mount(el, {
    textStyle: baseText(),
    legend: { top: 0, textStyle: { color: COLOURS.ink } },
    grid: { left: 8, right: 16, top: 36, bottom: 8, containLabel: true },
    tooltip: { trigger: "axis" },
    xAxis: { type: "category", data: rows.map((row) => row.label), ...axisCommon() },
    yAxis: {
      type: "value",
      ...axisCommon(),
      axisLabel: { formatter: "{value}%", color: COLOURS.ink },
    },
    series: categories.map((name, index) => ({
      name,
      type: "line",
      data: rows.map((row) => row.values[index]),
      symbol: "circle",
      symbolSize: 6,
      lineStyle: { width: 2.5, color: URGENCY_COLOURS[index] },
      itemStyle: { color: URGENCY_COLOURS[index] },
    })),
  });
}

function card(title, insight, plotClass) {
  const section = document.createElement("section");
  section.className = "chart-card";
  const heading = document.createElement("h2");
  heading.textContent = title;
  const note = document.createElement("p");
  note.className = "insight";
  note.textContent = insight;
  const plot = document.createElement("div");
  plot.className = `plot ${plotClass || ""}`;
  section.append(heading, note, plot);
  return { section, plot };
}

function meansBox(text) {
  const box = document.createElement("section");
  box.className = "means";
  const heading = document.createElement("h2");
  heading.textContent = "What this means";
  const paragraph = document.createElement("p");
  paragraph.textContent = text;
  box.append(heading, paragraph);
  return box;
}

function render(data) {
  document.getElementById("kicker").textContent = data.banner.kicker;
  document.getElementById("title").textContent = data.banner.title;
  document.getElementById("dek").textContent = data.banner.dek;
  const when = new Intl.DateTimeFormat("en-AU", {
    timeZone: "Australia/Melbourne",
    dateStyle: "long",
    timeStyle: "short",
  }).format(new Date(data.generated_at));
  document.getElementById("asof").textContent = `Figures prepared ${when} (Melbourne) · ${data.latest_year}`;

  const tabs = document.getElementById("tabs");
  const panels = document.getElementById("panels");
  const built = {};

  TABS.forEach(([id, label], index) => {
    const button = document.createElement("button");
    button.type = "button";
    button.role = "tab";
    button.id = `tab-${id}`;
    button.setAttribute("aria-controls", `panel-${id}`);
    button.setAttribute("aria-selected", index === 0 ? "true" : "false");
    button.tabIndex = index === 0 ? 0 : -1;
    button.textContent = label;
    button.addEventListener("click", () => select(id, true));
    tabs.append(button);

    const panel = document.createElement("section");
    panel.className = `panel${index === 0 ? " active" : ""}`;
    panel.id = `panel-${id}`;
    panel.role = "tabpanel";
    panel.setAttribute("aria-labelledby", button.id);
    panels.append(panel);
    built[id] = panel;
  });

  const kpis = document.createElement("div");
  kpis.className = "kpis";
  data.kpis.forEach((item) => {
    const cardEl = document.createElement("article");
    cardEl.className = `kpi ${item.status}`;
    cardEl.innerHTML = `<p class="value"></p><p class="label"></p><p class="detail"></p>`;
    cardEl.querySelector(".value").textContent = item.value;
    cardEl.querySelector(".label").textContent = item.label;
    cardEl.querySelector(".detail").textContent = item.detail;
    kpis.append(cardEl);
  });
  built.overview.append(kpis);

  const hero = card(data.hero.title, data.hero.insight, "short");
  hero.section.classList.add("hero");
  built.overview.append(hero.section);
  hbar(hero.plot, data.hero.rows, COLOURS.clay, "%");

  const overviewGrid = document.createElement("div");
  overviewGrid.className = "chart-grid";
  const trend = card(data.overview.trend.title, data.overview.trend.insight);
  const urgency = card(data.overview.urgency.title, data.overview.urgency.insight);
  overviewGrid.append(trend.section, urgency.section);
  built.overview.append(overviewGrid, meansBox(data.means.overview));
  line(trend.plot, data.overview.trend.rows);
  hbar(
    urgency.plot,
    data.overview.urgency.rows.map((row) => ({ label: `${row.label} · within ${row.within_days} days`, value: row.on_time })),
    COLOURS.teal,
    "%",
  );

  const stateWide = card(data.states.on_time.title, data.states.on_time.insight, "tall");
  const stateGrid = document.createElement("div");
  stateGrid.className = "chart-grid";
  const change = card(data.states.change.title, data.states.change.insight);
  const volume = card(data.states.volume.title, data.states.volume.insight);
  stateGrid.append(change.section, volume.section);
  built.states.append(stateWide.section, stateGrid, meansBox(data.means.states));
  grouped(stateWide.plot, data.states.on_time.rows, data.states.on_time.categories, URGENCY_COLOURS);
  signedBars(change.plot, data.states.change.rows);
  hbar(volume.plot, data.volumeRows || data.states.volume.rows, COLOURS.blue, "");

  const hospitalWide = card(data.hospitals.priority.title, data.hospitals.priority.insight, "tall");
  const hospitalGrid = document.createElement("div");
  hospitalGrid.className = "chart-grid";
  const peers = card(data.hospitals.peers.title, data.hospitals.peers.insight);
  const breaches = card(data.hospitals.breaches.title, data.hospitals.breaches.insight, "short");
  hospitalGrid.append(peers.section, breaches.section);
  built.hospitals.append(hospitalWide.section, hospitalGrid, meansBox(data.means.hospitals));
  hbar(hospitalWide.plot, data.hospitals.priority.rows, COLOURS.ochre, "");
  hbar(peers.plot, data.hospitals.peers.rows, COLOURS.teal, "%");
  hbar(breaches.plot, data.hospitals.breaches.rows, COLOURS.clay, "");

  const urgencyTrend = card(data.urgency_tab.trend.title, data.urgency_tab.trend.insight);
  const spec = card(data.urgency_tab.specialties.title, data.urgency_tab.specialties.insight, "tall");
  const proc = card(data.urgency_tab.procedures.title, data.urgency_tab.procedures.insight, "tall");
  built.urgency.append(urgencyTrend.section, spec.section, proc.section, meansBox(data.means.urgency));
  multiLine(urgencyTrend.plot, data.urgency_tab.trend.rows, data.urgency_tab.trend.categories);
  hbar(spec.plot, data.urgency_tab.specialties.rows, COLOURS.teal, " days");
  hbar(proc.plot, data.urgency_tab.procedures.rows, COLOURS.ochre, " days");

  const actionGrid = document.createElement("div");
  actionGrid.className = "chart-grid";
  const urgent = card(data.actions.urgent.title, data.actions.urgent.insight);
  const semi = card(data.actions.semi.title, data.actions.semi.insight);
  actionGrid.append(urgent.section, semi.section);
  const list = document.createElement("div");
  list.className = "actions";
  data.actions.cards.forEach((item, index) => {
    const article = document.createElement("article");
    article.className = `action ${item.status}`;
    const heading = document.createElement("h3");
    heading.textContent = `${index + 1}. ${item.title}`;
    const body = document.createElement("p");
    body.textContent = item.body;
    article.append(heading, body);
    list.append(article);
  });
  built.actions.append(actionGrid, list, meansBox(data.means.actions));
  hbar(urgent.plot, data.actions.urgent.rows, COLOURS.clay, "%");
  hbar(semi.plot, data.actions.semi.rows, COLOURS.ochre, "%");

  const footer = document.getElementById("footer");
  const heading = document.createElement("h2");
  heading.textContent = "Sources";
  footer.append(heading);
  data.sources.forEach((source) => {
    const paragraph = document.createElement("p");
    const strong = document.createElement("strong");
    strong.textContent = source.name;
    paragraph.append(strong, document.createTextNode(` — ${source.detail}`));
    footer.append(paragraph);
  });
  const quality = document.createElement("p");
  const link = document.createElement("a");
  link.href = "data-docs/index.html";
  link.textContent = "How the figures were checked";
  quality.append(link);
  footer.append(quality);

  function select(id, updateHash) {
    TABS.forEach(([key]) => {
      const button = document.getElementById(`tab-${key}`);
      const panel = document.getElementById(`panel-${key}`);
      const on = key === id;
      button.setAttribute("aria-selected", on ? "true" : "false");
      button.tabIndex = on ? 0 : -1;
      panel.classList.toggle("active", on);
    });
    if (updateHash) history.replaceState(null, "", `#${id}`);
    const fit = () => charts.forEach((chart) => chart.resize());
    requestAnimationFrame(fit);
    setTimeout(fit, 60);
  }

  tabs.addEventListener("keydown", (event) => {
    const current = TABS.findIndex(([id]) => document.getElementById(`tab-${id}`).getAttribute("aria-selected") === "true");
    if (event.key !== "ArrowRight" && event.key !== "ArrowLeft") return;
    event.preventDefault();
    const next = event.key === "ArrowRight" ? (current + 1) % TABS.length : (current - 1 + TABS.length) % TABS.length;
    const id = TABS[next][0];
    select(id, true);
    document.getElementById(`tab-${id}`).focus();
  });

  const requested = location.hash.replace("#", "");
  if (requested && built[requested]) select(requested, false);

  window.addEventListener("resize", () => charts.forEach((chart) => chart.resize()));
}

fetch("data/metrics.json")
  .then((response) => {
    if (!response.ok) throw new Error("The figures file is missing.");
    return response.json();
  })
  .then(render)
  .catch((error) => {
    document.getElementById("dek").textContent = error.message;
  });
