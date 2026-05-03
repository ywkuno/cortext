from __future__ import annotations

from pathlib import Path

from ..activity import write_activity_payload
from ..graph import GraphStore
from .json_export import export_json

HTML = """<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>CodePrism Brain Map</title>
  <link rel="stylesheet" href="styles.css" />
</head>
<body>
  <aside class="sidebar">
    <h1>CodePrism Brain Map</h1>
    <p class="muted">Local project graph for agent context and visual inspection.</p>
    <section class="panel">
      <label for="search">Search</label>
      <input id="search" placeholder="file, symbol, route, folder..." />
      <label for="kindFilter">Kind</label>
      <select id="kindFilter"><option value="all">All</option></select>
      <label for="roleFilter">Role</label>
      <select id="roleFilter"><option value="all">All</option></select>
      <label for="layoutMode">Layout</label>
      <select id="layoutMode">
        <option value="repo-tree" selected>Repo tree</option>
        <option value="cluster-grid">Cluster grid</option>
      </select>
      <div class="button-row">
        <button id="layoutBtn" type="button">Re-layout</button>
        <button id="fitBtn" type="button">Fit</button>
      </div>
    </section>
    <section class="panel">
      <h2>Layers</h2>
      <label class="toggle"><input id="layerStructure" type="checkbox" checked /> Structure</label>
      <label class="toggle"><input id="layerSymbols" type="checkbox" /> Symbols</label>
      <label class="toggle"><input id="layerImports" type="checkbox" /> Imports</label>
      <label class="toggle"><input id="layerModules" type="checkbox" /> External modules</label>
      <label class="toggle"><input id="layerTests" type="checkbox" /> Tests</label>
      <label class="toggle"><input id="layerActivity" type="checkbox" checked /> Activity</label>
      <label class="toggle"><input id="layerLabels" type="checkbox" checked /> Labels</label>
      <div class="button-row">
        <button id="overviewBtn" type="button">Clean overview</button>
        <button id="showAllBtn" type="button">Show all</button>
      </div>
    </section>
    <section class="panel">
      <h2>Activity</h2>
      <div class="button-row">
        <button id="playBtn" type="button">Play</button>
        <button id="pauseBtn" type="button">Pause</button>
      </div>
      <div class="button-row">
        <button id="resetBtn" type="button">Reset</button>
        <button id="nextBtn" type="button">Next</button>
      </div>
      <label for="timeline">Timeline</label>
      <input id="timeline" type="range" min="0" max="0" value="0" />
      <label for="speed">Speed</label>
      <select id="speed">
        <option value="0.5">0.5x</option>
        <option value="1" selected>1x</option>
        <option value="1.5">1.5x</option>
        <option value="2">2x</option>
        <option value="3">3x</option>
      </select>
      <div id="activitySummary" class="activity-summary">No activity stream loaded.</div>
      <div id="activityNow" class="activity-now">Ready.</div>
      <label for="activitySearch">Find event</label>
      <input id="activitySearch" placeholder="event, agent, path..." />
      <label for="activityRunFilter">Run</label>
      <select id="activityRunFilter">
        <option value="all">All</option>
      </select>
      <label for="activityAgentFilter">Agent</label>
      <select id="activityAgentFilter">
        <option value="all">All</option>
      </select>
      <div class="button-row">
        <button id="jumpEventBtn" type="button">Jump to node</button>
        <button id="touchedOnlyBtn" type="button">Touched only</button>
      </div>
      <ol id="eventList" class="event-list"></ol>
      <pre id="activityDetails">No activity stream loaded.</pre>
    </section>
    <section class="panel">
      <h2>Context</h2>
      <div id="contextSummary" class="activity-summary">No context overlay loaded.</div>
    </section>
    <section class="panel">
      <h2>Selected</h2>
      <div class="button-row">
        <button id="focusSelectionBtn" type="button">Focus</button>
        <button id="clearSelectionBtn" type="button">Clear</button>
      </div>
      <pre id="details">Click a node to inspect it.</pre>
    </section>
    <section class="panel">
      <h2>Legend</h2>
      <h3>Kind</h3>
      <ul id="legend"></ul>
      <h3>Role</h3>
      <ul id="roleLegend"></ul>
    </section>
    <section class="panel">
      <h2>Stats</h2>
      <div id="stats"></div>
    </section>
  </aside>
  <main>
    <div id="tooltip" role="tooltip"></div>
    <svg id="graph" viewBox="0 0 1600 1000" aria-label="Interactive project map">
      <g id="viewport">
        <g id="edges"></g>
        <g id="activityTrailLayer"></g>
        <g id="nodes"></g>
        <g id="labels"></g>
        <g id="activityMarkerLayer"></g>
        <g id="agentMarkerLayer"></g>
      </g>
    </svg>
  </main>
  <script src="app.js"></script>
</body>
</html>
"""

CSS = """
:root {
  --bg: #111318;
  --panel: #181c24;
  --panel-strong: #202733;
  --text: #edf2f7;
  --muted: #a6b1c2;
  --border: #303948;
  --accent: #49d6a3;
  --accent-2: #65b5ff;
  --warn: #f6c85f;
}
* { box-sizing: border-box; }
body {
  margin: 0;
  background: var(--bg);
  color: var(--text);
  font-family: ui-sans-serif, system-ui, -apple-system, Segoe UI, Roboto, sans-serif;
  display: grid;
  grid-template-columns: 360px minmax(0, 1fr);
  height: 100vh;
}
.sidebar {
  padding: 16px;
  overflow: auto;
  border-right: 1px solid var(--border);
  background: var(--panel);
}
main { min-width: 0; height: 100vh; position: relative; }
#graph {
  width: 100%;
  height: 100%;
  display: block;
  background:
    linear-gradient(rgba(255,255,255,0.028) 1px, transparent 1px),
    linear-gradient(90deg, rgba(255,255,255,0.028) 1px, transparent 1px),
    #10141b;
  background-size: 42px 42px;
}
h1, h2, h3 { margin: 0 0 8px; }
h1 { font-size: 1.35rem; font-weight: 700; }
h2 { font-size: 0.95rem; font-weight: 650; }
h3 {
  color: var(--muted);
  font-size: 0.78rem;
  font-weight: 650;
  margin-top: 10px;
  text-transform: uppercase;
}
.panel {
  background: var(--panel-strong);
  border: 1px solid var(--border);
  border-radius: 8px;
  padding: 12px;
  margin: 12px 0;
}
label { display: block; margin: 8px 0 4px; font-size: 0.85rem; color: var(--muted); }
.toggle {
  display: flex;
  align-items: center;
  gap: 8px;
  margin: 7px 0;
  color: var(--text);
}
.toggle input {
  width: auto;
  accent-color: var(--accent);
}
input, select, button {
  width: 100%;
  background: #141922;
  color: var(--text);
  border: 1px solid var(--border);
  border-radius: 6px;
  padding: 9px;
}
.button-row { display: grid; grid-template-columns: 1fr 1fr; gap: 8px; margin-top: 8px; }
button { cursor: pointer; }
button:hover { border-color: var(--accent); }
button.active { border-color: var(--accent); background: rgba(73,214,163,0.16); }
input[type="range"] { accent-color: var(--accent); padding: 0; }
.muted { color: var(--muted); }
pre {
  white-space: pre-wrap;
  overflow-wrap: anywhere;
  font-size: 0.78rem;
  margin: 0;
  color: var(--text);
}
#legend, #roleLegend { list-style: none; padding: 0; margin: 0; }
#legend li, #roleLegend li { display: flex; align-items: center; gap: 8px; margin: 4px 0; color: var(--muted); }
.event-list {
  max-height: 140px;
  overflow: auto;
  margin: 10px 0;
  padding-left: 22px;
  color: var(--muted);
  font-size: 0.78rem;
}
.event-list li {
  cursor: pointer;
  padding: 3px 4px;
  border-radius: 4px;
}
.event-list li.active {
  background: rgba(73,214,163,0.16);
  color: var(--text);
}
.event-list li.empty {
  cursor: default;
  color: var(--muted);
  list-style: none;
}
.activity-summary,
.activity-now {
  background: #141922;
  border: 1px solid var(--border);
  border-radius: 6px;
  color: var(--muted);
  font-size: 0.78rem;
  margin-top: 10px;
  padding: 9px;
}
.activity-now {
  border-color: rgba(246, 200, 95, 0.34);
  color: var(--text);
}
.swatch { width: 12px; height: 12px; border-radius: 999px; display: inline-block; }
.role-chip {
  border: 1px solid rgba(255, 255, 255, 0.18);
  border-radius: 999px;
  color: var(--text);
  display: inline-block;
  font-size: 0.66rem;
  font-weight: 700;
  min-width: 28px;
  padding: 1px 6px;
  text-align: center;
}
.node { cursor: grab; transition: opacity 120ms ease; }
.node circle { stroke: rgba(255,255,255,0.32); stroke-width: 1.2; }
.node.selected circle { stroke: white; stroke-width: 3; }
.node.neighbor circle { stroke: var(--accent); stroke-width: 2; }
.node.activity circle { stroke: var(--warn); stroke-width: 4; }
.node.context circle { stroke: var(--accent); stroke-width: 3; }
.node.dimmed { opacity: 0.16; }
.label { font-size: 12px; fill: rgba(255,255,255,0.88); pointer-events: none; }
.label.dimmed { opacity: 0.16; }
.edge { stroke: rgba(166,177,194,0.28); stroke-width: 1.1; }
.edge.highlight { stroke: var(--accent); stroke-width: 2.4; }
.edge.activity { stroke: var(--warn); stroke-width: 3; }
.activity-trail {
  stroke: var(--warn);
  stroke-width: 2;
  stroke-dasharray: 4 7;
  opacity: 0.56;
}
.activity-marker-core { fill: var(--warn); stroke: white; stroke-width: 2; }
.activity-marker-ring {
  fill: transparent;
  stroke: var(--warn);
  stroke-width: 2;
  opacity: 0.48;
}
.agent-marker {
  pointer-events: none;
}
.agent-marker .agent-marker-core {
  stroke: rgba(255, 255, 255, 0.86);
  stroke-width: 2;
}
.agent-marker text {
  fill: var(--text);
  font-size: 10px;
  font-weight: 800;
  paint-order: stroke;
  stroke: rgba(10, 13, 18, 0.92);
  stroke-width: 3;
  text-anchor: middle;
}
#tooltip {
  position: fixed;
  z-index: 5;
  max-width: 360px;
  pointer-events: none;
  transform: translate(14px, 14px);
  background: rgba(21, 26, 35, 0.96);
  border: 1px solid rgba(101, 181, 255, 0.36);
  border-radius: 6px;
  color: var(--text);
  padding: 9px 10px;
  box-shadow: 0 12px 28px rgba(0, 0, 0, 0.28);
  opacity: 0;
  transition: opacity 90ms ease;
}
#tooltip.visible { opacity: 1; }
#tooltip strong { display: block; margin-bottom: 3px; }
#tooltip span { display: block; color: var(--muted); font-size: 0.78rem; overflow-wrap: anywhere; }
"""

JS = r"""
const COLORS = {
  folder: '#65b5ff',
  file: '#49d6a3',
  doc: '#8fb7ff',
  module: '#f6c85f',
  class: '#c58cff',
  function: '#62dfcf',
  method: '#8be28b',
  heading: '#ff8fb7',
  route: '#ff9f68',
  parse_error: '#ff6b6b',
  unknown: '#9ba6b5',
};

const STRUCTURE_KINDS = new Set(['folder', 'file', 'doc', 'route', 'parse_error', 'unknown']);
const SYMBOL_KINDS = new Set(['class', 'function', 'method', 'heading']);
const TEST_PATTERN = /(^|\/)(tests?|specs?)(\/|$)|(^|\/)test_|_test\.|\.test\.|\.spec\./;
const ROLE_STYLES = {
  agent: { label: 'Agent', badge: 'AI', color: '#d7a6ff' },
  repo: { label: 'Repo control', badge: 'GIT', color: '#d4b36a' },
  package: { label: 'Package', badge: 'PKG', color: '#f0cc5a' },
  source: { label: 'Source', badge: 'SRC', color: '#49d6a3' },
  test: { label: 'Tests', badge: 'TST', color: '#62dfcf' },
  doc: { label: 'Docs', badge: 'DOC', color: '#8fb7ff' },
  example: { label: 'Examples', badge: 'EX', color: '#ff9f68' },
  generated: { label: 'Generated/cache', badge: 'GEN', color: '#7a8494' },
  dependency: { label: 'Dependency', badge: 'LIB', color: '#9ba6b5' },
  project: { label: 'Project', badge: 'PRJ', color: '#65b5ff' },
};
const AGENT_COLORS = ['#f0cc5a', '#d7a6ff', '#62dfcf', '#ff9f68', '#8fb7ff', '#49d6a3'];

const state = {
  data: { meta: {}, nodes: [], edges: [] },
  nodes: [],
  edges: [],
  nodeById: new Map(),
  selectedId: null,
  focusMode: false,
  activeEventNodeId: null,
  scale: 1,
  tx: 0,
  ty: 0,
  dragNode: null,
  pan: null,
  layers: {
    structure: true,
    symbols: false,
    imports: false,
    modules: false,
    tests: false,
    activity: true,
    labels: true,
  },
  activity: {
    events: [],
    warnings: [],
    summary: null,
    index: -1,
    timer: null,
    speed: 1,
    query: '',
    run: 'all',
    agent: 'all',
  },
  activityNodeIds: new Set(),
  touchedOnly: false,
  context: null,
  contextNodeIds: new Set(),
  marker: { x: 0, y: 0, visible: false, animation: null },
  agentMarkers: new Map(),
  activityTrails: [],
};

const svg = document.getElementById('graph');
const viewport = document.getElementById('viewport');
const nodeLayer = document.getElementById('nodes');
const edgeLayer = document.getElementById('edges');
const labelLayer = document.getElementById('labels');
const activityTrailLayer = document.getElementById('activityTrailLayer');
const activityMarkerLayer = document.getElementById('activityMarkerLayer');
const agentMarkerLayer = document.getElementById('agentMarkerLayer');
const tooltip = document.getElementById('tooltip');
const details = document.getElementById('details');
const stats = document.getElementById('stats');
const legend = document.getElementById('legend');
const roleLegend = document.getElementById('roleLegend');
const activitySummary = document.getElementById('activitySummary');
const activityNow = document.getElementById('activityNow');
const activityDetails = document.getElementById('activityDetails');
const contextSummary = document.getElementById('contextSummary');
const activitySearch = document.getElementById('activitySearch');
const activityRunFilter = document.getElementById('activityRunFilter');
const activityAgentFilter = document.getElementById('activityAgentFilter');
const timelineInput = document.getElementById('timeline');
const speedSelect = document.getElementById('speed');
const eventList = document.getElementById('eventList');
const searchInput = document.getElementById('search');
const kindFilter = document.getElementById('kindFilter');
const roleFilter = document.getElementById('roleFilter');
const layoutMode = document.getElementById('layoutMode');
const focusSelectionBtn = document.getElementById('focusSelectionBtn');
const layerControls = {
  structure: document.getElementById('layerStructure'),
  symbols: document.getElementById('layerSymbols'),
  imports: document.getElementById('layerImports'),
  modules: document.getElementById('layerModules'),
  tests: document.getElementById('layerTests'),
  activity: document.getElementById('layerActivity'),
  labels: document.getElementById('layerLabels'),
};

document.getElementById('layoutBtn').addEventListener('click', () => {
  applyLayout();
  fitView();
  renderGraph();
});
document.getElementById('fitBtn').addEventListener('click', fitView);
document.getElementById('playBtn').addEventListener('click', playActivity);
document.getElementById('pauseBtn').addEventListener('click', pauseActivity);
document.getElementById('resetBtn').addEventListener('click', resetActivity);
document.getElementById('nextBtn').addEventListener('click', nextActivity);
document.getElementById('clearSelectionBtn').addEventListener('click', clearSelection);
focusSelectionBtn.addEventListener('click', toggleFocusMode);
document.getElementById('overviewBtn').addEventListener('click', () => setLayers({
  structure: true,
  symbols: false,
  imports: false,
  modules: false,
  tests: false,
  activity: true,
  labels: true,
}));
document.getElementById('showAllBtn').addEventListener('click', () => setLayers({
  structure: true,
  symbols: true,
  imports: true,
  modules: true,
  tests: true,
  activity: true,
  labels: true,
}));
for (const control of Object.values(layerControls)) {
  control.addEventListener('change', updateLayersFromControls);
}
timelineInput.addEventListener('input', () => {
  if (!state.activity.events.length) return;
  pauseActivity();
  state.activity.index = Number(timelineInput.value);
  showActivityEvent();
});
speedSelect.addEventListener('change', () => {
  state.activity.speed = Number(speedSelect.value) || 1;
  if (state.activity.timer) {
    pauseActivity();
    playActivity();
  }
});
activitySearch.addEventListener('input', () => {
  state.activity.query = activitySearch.value;
  renderEventList();
});
activityRunFilter.addEventListener('change', () => {
  state.activity.run = activityRunFilter.value;
  renderEventList();
});
activityAgentFilter.addEventListener('change', () => {
  state.activity.agent = activityAgentFilter.value;
  renderEventList();
});
document.getElementById('jumpEventBtn').addEventListener('click', jumpToActivityNode);
document.getElementById('touchedOnlyBtn').addEventListener('click', () => {
  setTouchedOnly(!state.touchedOnly);
});
searchInput.addEventListener('input', applyFilters);
kindFilter.addEventListener('change', applyFilters);
roleFilter.addEventListener('change', applyFilters);
layoutMode.addEventListener('change', () => {
  applyLayout();
  applyFilters();
  fitView();
});

svg.addEventListener('wheel', (event) => {
  event.preventDefault();
  const factor = event.deltaY > 0 ? 0.92 : 1.08;
  const nextScale = Math.max(0.18, Math.min(5, state.scale * factor));
  zoomAtPointer(event.clientX, event.clientY, nextScale);
}, { passive: false });

svg.addEventListener('mousedown', (event) => {
  if (event.target === svg) {
    state.pan = { x: event.clientX, y: event.clientY, tx: state.tx, ty: state.ty };
  }
});
svg.addEventListener('click', (event) => {
  if (event.target === svg) clearSelection();
});
window.addEventListener('keydown', (event) => {
  if (event.key === 'Escape') clearSelection();
});
window.addEventListener('mousemove', (event) => {
  if (state.dragNode) {
    const point = clientToWorld(event.clientX, event.clientY);
    state.dragNode.x = point.x;
    state.dragNode.y = point.y;
    renderGraph();
  } else if (state.pan) {
    state.tx = state.pan.tx + (event.clientX - state.pan.x);
    state.ty = state.pan.ty + (event.clientY - state.pan.y);
    renderTransform();
  }
});
window.addEventListener('mouseup', () => {
  state.dragNode = null;
  state.pan = null;
});

function clientToWorld(clientX, clientY) {
  const point = clientToSvgPoint(clientX, clientY);
  return {
    x: (point.x - state.tx) / state.scale,
    y: (point.y - state.ty) / state.scale,
  };
}

function clientToSvgPoint(clientX, clientY) {
  const matrix = svg.getScreenCTM();
  if (!matrix) {
    const rect = svg.getBoundingClientRect();
    return { x: clientX - rect.left, y: clientY - rect.top };
  }
  const point = svg.createSVGPoint();
  point.x = clientX;
  point.y = clientY;
  const transformed = point.matrixTransform(matrix.inverse());
  return { x: transformed.x, y: transformed.y };
}

function zoomAtPointer(clientX, clientY, nextScale) {
  const pointer = clientToSvgPoint(clientX, clientY);
  const world = {
    x: (pointer.x - state.tx) / state.scale,
    y: (pointer.y - state.ty) / state.scale,
  };
  state.scale = nextScale;
  state.tx = pointer.x - world.x * nextScale;
  state.ty = pointer.y - world.y * nextScale;
  renderTransform();
}

function renderTransform() {
  viewport.setAttribute('transform', `translate(${state.tx}, ${state.ty}) scale(${state.scale})`);
}

function setLayers(nextLayers) {
  state.layers = { ...state.layers, ...nextLayers };
  for (const [key, control] of Object.entries(layerControls)) {
    control.checked = Boolean(state.layers[key]);
  }
  applyFilters();
}

function updateLayersFromControls() {
  for (const [key, control] of Object.entries(layerControls)) {
    state.layers[key] = Boolean(control.checked);
  }
  applyFilters();
}

function normalizeNode(node, index) {
  const id = node.id || `missing-id::${index}`;
  const meta = node.meta && typeof node.meta === 'object' ? node.meta : {};
  return {
    id,
    kind: node.kind || 'unknown',
    path: node.path || '',
    name: node.name || id,
    label: node.label || node.name || id,
    start_line: node.start_line ?? null,
    end_line: node.end_line ?? null,
    meta,
    role: nodeRole({ id, kind: node.kind || 'unknown', path: node.path || '', name: node.name || id, meta }),
    visible: true,
    matchesFilter: true,
    x: 0,
    y: 0,
  };
}

function buildScene(data) {
  const rawNodes = Array.isArray(data.nodes) ? data.nodes : [];
  const rawEdges = Array.isArray(data.edges) ? data.edges : [];
  const nodes = rawNodes.map(normalizeNode);
  const nodeById = new Map(nodes.map((node) => [node.id, node]));
  const edges = rawEdges
    .filter((edge) => edge && nodeById.has(edge.source) && nodeById.has(edge.target))
    .map((edge) => ({
      source: edge.source,
      target: edge.target,
      kind: edge.kind || 'relates',
      meta: edge.meta && typeof edge.meta === 'object' ? edge.meta : {},
    }));

  state.data = data || { meta: {}, nodes: [], edges: [] };
  state.nodes = nodes;
  state.edges = edges;
  state.nodeById = nodeById;
  applyLayout();
  populateFilters(nodes);
  populateRoleFilter(nodes);
  populateLegend(nodes);
  populateRoleLegend(nodes);
  applyFilters();
  fitView();
}

function buildBuckets(nodes) {
  const buckets = new Map();
  for (const node of nodes) {
    const key = node.kind === 'folder' ? node.id : (node.path.split('/').slice(0, -1).join('/') || 'root');
    if (!buckets.has(key)) buckets.set(key, []);
    buckets.get(key).push(node);
  }
  return [...buckets.entries()].sort((a, b) => a[0].localeCompare(b[0]));
}

function applyLayout() {
  const nodes = state.nodes;
  if (layoutMode.value === 'cluster-grid') {
    applyClusterGridLayout(nodes);
  } else {
    applyRepoTreeLayout(nodes);
  }
}

function applyClusterGridLayout(nodes) {
  if (!nodes.length) return;
  const buckets = buildBuckets(nodes);
  const columnGap = 280;
  const rowGap = 190;
  buckets.forEach(([, group], index) => {
    const col = index % 5;
    const row = Math.floor(index / 5);
    const baseX = 180 + col * columnGap;
    const baseY = 130 + row * rowGap;
    const anchor = group.find((node) => ['folder', 'file', 'doc'].includes(node.kind)) || group[0];
    anchor.x = baseX;
    anchor.y = baseY;
    const children = group.filter((node) => node !== anchor);
    const radius = 68 + Math.min(children.length, 10) * 5;
    children.forEach((child, childIndex) => {
      const angle = (Math.PI * 2 * childIndex) / Math.max(1, children.length);
      child.x = baseX + Math.cos(angle) * radius;
      child.y = baseY + Math.sin(angle) * radius;
    });
  });
}

function pathDepth(path) {
  return path ? path.split('/').filter(Boolean).length : 0;
}

function parentPath(path) {
  const parts = path.split('/').filter(Boolean);
  parts.pop();
  return parts.join('/');
}

function repoTreeSortKey(node) {
  const kindWeight = {
    folder: 0,
    doc: 1,
    file: 2,
    route: 3,
    parse_error: 4,
  };
  return `${node.path || node.name || node.id}::${kindWeight[node.kind] ?? 9}::${node.name || ''}`;
}

function buildTreeRows(nodes) {
  const visibleStructure = nodes
    .filter((node) => !isExternalModule(node) && STRUCTURE_KINDS.has(node.kind))
    .sort((a, b) => repoTreeSortKey(a).localeCompare(repoTreeSortKey(b)));
  const foldersByPath = new Map(
    visibleStructure
      .filter((node) => node.kind === 'folder')
      .map((node) => [node.path, node]),
  );
  const rows = [];
  const seen = new Set();
  for (const node of visibleStructure) {
    const chain = [];
    let currentPath = node.kind === 'folder' ? node.path : parentPath(node.path || '');
    while (currentPath) {
      const folder = foldersByPath.get(currentPath);
      if (folder) chain.unshift(folder);
      currentPath = parentPath(currentPath);
    }
    for (const folder of chain) {
      if (!seen.has(folder.id)) {
        rows.push(folder);
        seen.add(folder.id);
      }
    }
    if (!seen.has(node.id)) {
      rows.push(node);
      seen.add(node.id);
    }
  }
  return rows;
}

function topLevelGroupKey(node) {
  const path = node.path || node.name || '';
  const parts = path.split('/').filter(Boolean);
  return parts.length ? parts[0] : '~root';
}

function treeGroupSortKey(groupKey) {
  return groupKey === '~root' ? '' : groupKey;
}

function applyRepoTreeLayout(nodes) {
  if (!nodes.length) return;
  const assigned = new Set();
  const baseX = 120;
  const baseY = 100;
  const indent = 130;
  const rowGap = 40;
  const groupGap = 46;
  const columnGap = 430;
  const groupsPerColumn = 4;
  const grouped = new Map();
  for (const node of nodes) {
    if (isExternalModule(node)) continue;
    const groupKey = topLevelGroupKey(node);
    if (!grouped.has(groupKey)) grouped.set(groupKey, []);
    grouped.get(groupKey).push(node);
  }

  const groups = [...grouped.entries()]
    .sort((a, b) => treeGroupSortKey(a[0]).localeCompare(treeGroupSortKey(b[0])));
  const columnHeights = new Map();
  groups.forEach(([groupKey, groupNodes], groupIndex) => {
    const column = Math.floor(groupIndex / groupsPerColumn);
    const columnX = baseX + column * columnGap;
    const currentY = columnHeights.get(column) || baseY;
    const rows = buildTreeRows(groupNodes);
    rows.forEach((node, rowIndex) => {
      const depth = groupKey === '~root' ? 0 : Math.max(0, pathDepth(node.path || node.name) - 1);
      node.x = columnX + depth * indent;
      node.y = currentY + rowIndex * rowGap;
      assigned.add(node.id);
    });
    columnHeights.set(column, currentY + Math.max(1, rows.length) * rowGap + groupGap);
  });

  const childrenByPath = new Map();
  for (const node of nodes) {
    if (assigned.has(node.id) || isExternalModule(node)) continue;
    const key = node.path || '';
    if (!childrenByPath.has(key)) childrenByPath.set(key, []);
    childrenByPath.get(key).push(node);
  }
  for (const [path, children] of childrenByPath.entries()) {
    const anchor = nodes.find((node) => assigned.has(node.id) && node.path === path);
    if (!anchor) continue;
    const radius = 30 + Math.min(children.length, 12) * 3;
    children.forEach((child, childIndex) => {
      const angle = (Math.PI * 2 * childIndex) / Math.max(1, children.length);
      child.x = anchor.x + 88 + Math.cos(angle) * radius;
      child.y = anchor.y + Math.sin(angle) * radius;
      assigned.add(child.id);
    });
  }

  let overflowIndex = 0;
  for (const node of nodes) {
    if (assigned.has(node.id)) continue;
    node.x = baseX + 6 * indent + (overflowIndex % 4) * 110;
    node.y = baseY + Math.floor(overflowIndex / 4) * rowGap;
    overflowIndex += 1;
  }
}

function populateFilters(nodes) {
  const current = kindFilter.value || 'all';
  const kinds = [...new Set(nodes.map((node) => node.kind))].sort();
  kindFilter.innerHTML = '<option value="all">All</option>' + kinds.map((kind) => `<option value="${kind}">${kind}</option>`).join('');
  kindFilter.value = kinds.includes(current) ? current : 'all';
}

function roleLabel(role) {
  return (ROLE_STYLES[role] || ROLE_STYLES.project).label;
}

function roleColor(role) {
  return (ROLE_STYLES[role] || ROLE_STYLES.project).color;
}

function roleBadge(role) {
  return (ROLE_STYLES[role] || ROLE_STYLES.project).badge;
}

function nodeRole(node) {
  if (node.meta && typeof node.meta.role === 'string' && node.meta.role) return node.meta.role;
  if (isExternalModule(node)) return 'dependency';
  if (isTestNode(node)) return 'test';
  if (node.path && node.path.startsWith('docs/')) return 'doc';
  if (node.kind === 'doc') return 'doc';
  return 'project';
}

function populateRoleFilter(nodes) {
  const current = roleFilter.value || 'all';
  const roles = [...new Set(nodes.map((node) => node.role || nodeRole(node)))].sort((a, b) => roleLabel(a).localeCompare(roleLabel(b)));
  roleFilter.innerHTML = '<option value="all">All</option>' + roles.map((role) => `<option value="${role}">${roleLabel(role)}</option>`).join('');
  roleFilter.value = roles.includes(current) ? current : 'all';
}

function populateLegend(nodes) {
  const kinds = [...new Set(nodes.map((node) => node.kind))].sort();
  legend.innerHTML = kinds.map((kind) => `<li><span class="swatch" style="background:${COLORS[kind] || COLORS.unknown}"></span>${kind}</li>`).join('');
}

function populateRoleLegend(nodes) {
  const roles = [...new Set(nodes.map((node) => node.role || nodeRole(node)))].sort((a, b) => roleLabel(a).localeCompare(roleLabel(b)));
  roleLegend.innerHTML = roles.map((role) => `
    <li>
      <span class="swatch" style="background:${roleColor(role)}"></span>
      <span class="role-chip" style="background:${roleColor(role)}">${roleBadge(role)}</span>
      ${roleLabel(role)}
    </li>
  `).join('');
}

function renderStats() {
  const meta = state.data.meta || {};
  const visibleCount = visibleNodes().length;
  const visibleRoles = [...new Set(visibleNodes().map((node) => roleLabel(node.role || nodeRole(node))))].sort();
  stats.innerHTML = `
    <div>Root: <strong>${escapeHtml(meta.root || '-')}</strong></div>
    <div>Schema: <strong>${escapeHtml(String(meta.schema_version || '-'))}</strong></div>
    <div>Nodes: <strong>${state.nodes.length}</strong></div>
    <div>Edges: <strong>${state.edges.length}</strong></div>
    <div>Visible: <strong>${visibleCount}</strong></div>
    <div>Mode: <strong>${state.focusMode ? 'focus' : 'overview'}</strong></div>
    <div>Roles: <strong>${visibleRoles.length ? visibleRoles.join(', ') : '-'}</strong></div>
  `;
}

function fitView() {
  const nodes = visibleNodes();
  if (!nodes.length) {
    state.scale = 1;
    state.tx = 24;
    state.ty = 24;
    renderTransform();
    return;
  }
  const minX = Math.min(...nodes.map((node) => node.x));
  const maxX = Math.max(...nodes.map((node) => node.x));
  const minY = Math.min(...nodes.map((node) => node.y));
  const maxY = Math.max(...nodes.map((node) => node.y));
  const viewWidth = 1600;
  const viewHeight = 1000;
  const padding = 96;
  const width = Math.max(1, maxX - minX);
  const height = Math.max(1, maxY - minY);
  const minScale = layoutMode.value === 'repo-tree' ? 0.42 : 0.18;
  state.scale = Math.max(minScale, Math.min(2.2, Math.min(
    (viewWidth - padding * 2) / width,
    (viewHeight - padding * 2) / height,
  )));
  state.tx = (viewWidth - (minX + maxX) * state.scale) / 2;
  state.ty = (viewHeight - (minY + maxY) * state.scale) / 2;
  renderTransform();
}

function centerNodeInView(node) {
  const viewWidth = 1600;
  const viewHeight = 1000;
  state.tx = viewWidth / 2 - node.x * state.scale;
  state.ty = viewHeight / 2 - node.y * state.scale;
  renderTransform();
}

function applyFilters() {
  hideTooltip();
  const text = searchInput.value.trim().toLowerCase();
  const kind = kindFilter.value;
  const role = roleFilter.value;
  for (const node of state.nodes) {
    const nodeRoleValue = node.role || nodeRole(node);
    const haystack = `${node.id} ${node.kind} ${nodeRoleValue} ${roleLabel(nodeRoleValue)} ${node.path} ${node.name} ${node.label}`.toLowerCase();
    const matchesText = !text || haystack.includes(text);
    const matchesKind = kind === 'all' || node.kind === kind;
    const matchesRole = role === 'all' || nodeRoleValue === role;
    node.matchesFilter = matchesText && matchesKind && matchesRole;
    node.visible = nodeVisibleForCurrentView(node);
  }
  renderStats();
  renderGraph();
}

function isTestNode(node) {
  return TEST_PATTERN.test(`${node.path || ''}/${node.name || ''}`.toLowerCase());
}

function isExternalModule(node) {
  return node.kind === 'module' || node.id.startsWith('module:') || node.id.startsWith('module::');
}

function nodeLayerVisible(node) {
  const hasSearch = searchInput.value.trim().length > 0;
  if (isExternalModule(node)) return state.layers.modules || hasSearch;
  if (isTestNode(node)) return state.layers.tests || hasSearch;
  if (STRUCTURE_KINDS.has(node.kind)) return state.layers.structure || hasSearch;
  if (SYMBOL_KINDS.has(node.kind)) return state.layers.symbols || hasSearch;
  return true;
}

function edgeLayerVisible(edge) {
  if (edge.kind === 'imports') return state.layers.imports;
  if (edge.kind === 'defines') return state.layers.symbols;
  if (edge.kind === 'contains') return state.layers.structure || state.layers.symbols;
  return true;
}

function nodeVisibleForCurrentView(node, neighborIds = neighborsFor(state.selectedId)) {
  const active = state.layers.activity && node.id === state.activeEventNodeId;
  const focusRelated = state.focusMode && state.selectedId && (node.id === state.selectedId || neighborIds.has(node.id));
  const touchedRelated = state.touchedOnly && state.activityNodeIds.has(node.id);
  if (state.touchedOnly && !touchedRelated && !active && !focusRelated && node.id !== state.selectedId) {
    return false;
  }
  if (!node.matchesFilter && !active) return false;
  if (!nodeLayerVisible(node) && !active && !focusRelated) return false;
  if (state.focusMode && state.selectedId && node.id !== state.selectedId && !neighborIds.has(node.id) && !active) {
    return false;
  }
  return true;
}

function visibleNodes(neighborIds = neighborsFor(state.selectedId)) {
  return state.nodes.filter((node) => nodeVisibleForCurrentView(node, neighborIds));
}

function neighborsFor(nodeId) {
  const neighbors = new Set();
  if (!nodeId) return neighbors;
  for (const edge of state.edges) {
    if (edge.source === nodeId) neighbors.add(edge.target);
    if (edge.target === nodeId) neighbors.add(edge.source);
  }
  return neighbors;
}

function renderGraph() {
  const neighborIds = neighborsFor(state.selectedId);
  const currentVisibleNodes = visibleNodes(neighborIds);
  const visibleIds = new Set(currentVisibleNodes.map((node) => node.id));
  const visibleCount = currentVisibleNodes.length;
  edgeLayer.innerHTML = '';
  nodeLayer.innerHTML = '';
  labelLayer.innerHTML = '';

  for (const edge of state.edges) {
    if (!visibleIds.has(edge.source) || !visibleIds.has(edge.target)) continue;
    const source = state.nodeById.get(edge.source);
    const target = state.nodeById.get(edge.target);
    if (!source || !target) continue;
    const line = document.createElementNS('http://www.w3.org/2000/svg', 'line');
    line.setAttribute('x1', source.x);
    line.setAttribute('y1', source.y);
    line.setAttribute('x2', target.x);
    line.setAttribute('y2', target.y);
    const active = state.activeEventNodeId && (edge.source === state.activeEventNodeId || edge.target === state.activeEventNodeId);
    const selected = state.selectedId && (edge.source === state.selectedId || edge.target === state.selectedId);
    if (!edgeLayerVisible(edge) && !selected && !active) continue;
    line.setAttribute('class', `edge${selected ? ' highlight' : ''}${active ? ' activity' : ''}`);
    edgeLayer.appendChild(line);
  }

  for (const node of currentVisibleNodes) {
    const selected = node.id === state.selectedId;
    const neighbor = neighborIds.has(node.id);
    const active = node.id === state.activeEventNodeId;
    const contextIncluded = state.contextNodeIds.has(node.id);
    const dimmed = state.selectedId && !selected && !neighbor;
    const g = document.createElementNS('http://www.w3.org/2000/svg', 'g');
    g.setAttribute('class', `node${selected ? ' selected' : ''}${neighbor ? ' neighbor' : ''}${active ? ' activity' : ''}${contextIncluded ? ' context' : ''}${dimmed ? ' dimmed' : ''}`);
    g.setAttribute('transform', `translate(${node.x}, ${node.y})`);
    const circle = document.createElementNS('http://www.w3.org/2000/svg', 'circle');
    circle.setAttribute('r', node.kind === 'folder' ? 18 : ['file', 'doc'].includes(node.kind) ? 15 : 10);
    const nodeRoleValue = node.role || nodeRole(node);
    circle.setAttribute('fill', roleColor(nodeRoleValue));
    circle.setAttribute('stroke', COLORS[node.kind] || COLORS.unknown);
    g.appendChild(circle);
    g.addEventListener('mouseenter', (event) => showTooltip(event, node));
    g.addEventListener('mousemove', moveTooltip);
    g.addEventListener('mouseleave', hideTooltip);
    g.addEventListener('mousedown', (event) => {
      event.stopPropagation();
      state.dragNode = node;
      selectNode(node.id);
    });
    g.addEventListener('click', (event) => {
      event.stopPropagation();
      selectNode(node.id);
    });
    nodeLayer.appendChild(g);

    if (!shouldShowLabel(node, { selected, neighbor, active, visibleCount })) continue;
    const label = document.createElementNS('http://www.w3.org/2000/svg', 'text');
    label.setAttribute('x', node.x + 16);
    label.setAttribute('y', node.y + 4);
    label.setAttribute('class', `label${dimmed ? ' dimmed' : ''}`);
    label.textContent = node.label;
    labelLayer.appendChild(label);
  }
  renderActivityTrails();
  renderActivityMarker();
  renderAgentMarkers();
}

function shouldShowLabel(node, context) {
  if (!state.layers.labels) return false;
  if (context.selected || context.neighbor || context.active) return true;
  if (['agent', 'repo', 'package'].includes(node.role || nodeRole(node))) return true;
  if (context.visibleCount > 70) return node.kind === 'folder';
  if (context.visibleCount > 38) return ['folder', 'doc'].includes(node.kind);
  if (!state.layers.symbols && SYMBOL_KINDS.has(node.kind)) return false;
  return true;
}

function selectNode(nodeId) {
  state.selectedId = nodeId;
  updateFocusButton();
  const node = state.nodeById.get(nodeId);
  if (node) showDetails(node);
  renderGraph();
}

function clearSelection() {
  if (!state.selectedId) return;
  state.selectedId = null;
  state.focusMode = false;
  updateFocusButton();
  details.textContent = 'Click a node to inspect it.';
  hideTooltip();
  renderGraph();
}

function toggleFocusMode() {
  if (!state.selectedId && !state.focusMode) return;
  state.focusMode = !state.focusMode;
  updateFocusButton();
  renderStats();
  renderGraph();
}

function updateFocusButton() {
  focusSelectionBtn.textContent = state.focusMode ? 'Exit focus' : 'Focus';
  focusSelectionBtn.disabled = !state.selectedId && !state.focusMode;
}

function showTooltip(event, node) {
  const nodeRoleValue = node.role || nodeRole(node);
  tooltip.innerHTML = `
    <strong>${escapeHtml(node.label || node.name || node.id)}</strong>
    <span>${escapeHtml(roleLabel(nodeRoleValue))} / ${escapeHtml(node.kind)}${node.path ? ' - ' + escapeHtml(node.path) : ''}</span>
    <span>${node.start_line ? 'L' + escapeHtml(node.start_line) : escapeHtml(node.id)}</span>
  `;
  moveTooltip(event);
  tooltip.classList.add('visible');
}

function moveTooltip(event) {
  tooltip.style.left = `${event.clientX}px`;
  tooltip.style.top = `${event.clientY}px`;
}

function hideTooltip() {
  tooltip.classList.remove('visible');
}

function showDetails(node) {
  const incoming = state.edges
    .filter((edge) => edge.target === node.id)
    .map((edge) => ({ kind: edge.kind, from: edge.source }));
  const outgoing = state.edges
    .filter((edge) => edge.source === node.id)
    .map((edge) => ({ kind: edge.kind, to: edge.target }));
  details.textContent = JSON.stringify({
    id: node.id,
    kind: node.kind,
    role: node.role || nodeRole(node),
    path: node.path,
    name: node.name,
    label: node.label,
    start_line: node.start_line,
    end_line: node.end_line,
    meta: node.meta || {},
    incoming,
    outgoing,
  }, null, 2);
}

function eventNodeId(event) {
  if (!event) return null;
  if (event.to_node_id && state.nodeById.has(event.to_node_id)) return event.to_node_id;
  if (event.node_id && state.nodeById.has(event.node_id)) return event.node_id;
  if (event.path) {
    const normalizedPath = event.path.replace(/\\/g, '/');
    const match = state.nodes.find((node) => node.path === normalizedPath);
    return match ? match.id : null;
  }
  return null;
}

function eventSourceId(event) {
  if (!event) return null;
  if (event.from_node_id && state.nodeById.has(event.from_node_id)) return event.from_node_id;
  if (state.activity.index > 0) return eventNodeId(state.activity.events[state.activity.index - 1]);
  return eventNodeId(event);
}

function setMarkerPosition(x, y, visible = true) {
  state.marker.x = x;
  state.marker.y = y;
  state.marker.visible = visible;
  renderActivityMarker();
}

function activityAgentId(event) {
  return (event && event.agent_id) ? String(event.agent_id) : 'agent';
}

function agentColor(agentId) {
  let hash = 0;
  for (const char of agentId) hash = (hash * 31 + char.charCodeAt(0)) >>> 0;
  return AGENT_COLORS[hash % AGENT_COLORS.length];
}

function renderActivityMarker() {
  activityMarkerLayer.innerHTML = '';
  if (!state.marker.visible) return;
  const g = document.createElementNS('http://www.w3.org/2000/svg', 'g');
  g.setAttribute('transform', `translate(${state.marker.x}, ${state.marker.y})`);
  const ring = document.createElementNS('http://www.w3.org/2000/svg', 'circle');
  ring.setAttribute('r', 18);
  ring.setAttribute('class', 'activity-marker-ring');
  const core = document.createElementNS('http://www.w3.org/2000/svg', 'circle');
  core.setAttribute('r', 7);
  core.setAttribute('class', 'activity-marker-core');
  g.appendChild(ring);
  g.appendChild(core);
  activityMarkerLayer.appendChild(g);
}

function setAgentMarker(agentId, x, y, label) {
  state.agentMarkers.set(agentId, { x, y, label: label || agentId, color: agentColor(agentId) });
  renderAgentMarkers();
}

function renderAgentMarkers() {
  agentMarkerLayer.innerHTML = '';
  if (!state.layers.activity) return;
  for (const [agentId, marker] of state.agentMarkers.entries()) {
    const g = document.createElementNS('http://www.w3.org/2000/svg', 'g');
    g.setAttribute('class', 'agent-marker');
    g.setAttribute('transform', `translate(${marker.x}, ${marker.y})`);
    const core = document.createElementNS('http://www.w3.org/2000/svg', 'circle');
    core.setAttribute('r', 11);
    core.setAttribute('class', 'agent-marker-core');
    core.setAttribute('fill', marker.color);
    const label = document.createElementNS('http://www.w3.org/2000/svg', 'text');
    label.setAttribute('x', 0);
    label.setAttribute('y', -16);
    label.textContent = marker.label.slice(0, 12);
    g.appendChild(core);
    g.appendChild(label);
    agentMarkerLayer.appendChild(g);
  }
}

function addActivityTrail(source, target, agentId) {
  if (!source || !target || source === target) return;
  const sourceNode = state.nodeById.get(source);
  const targetNode = state.nodeById.get(target);
  if (!sourceNode || !targetNode) return;
  state.activityTrails.push({
    source,
    target,
    agentId,
    color: agentColor(agentId),
    x1: sourceNode.x,
    y1: sourceNode.y,
    x2: targetNode.x,
    y2: targetNode.y,
  });
  state.activityTrails = state.activityTrails.slice(-40);
  renderActivityTrails();
}

function renderActivityTrails() {
  activityTrailLayer.innerHTML = '';
  if (!state.layers.activity) return;
  for (const trail of state.activityTrails) {
    const line = document.createElementNS('http://www.w3.org/2000/svg', 'line');
    line.setAttribute('class', 'activity-trail');
    line.setAttribute('x1', trail.x1);
    line.setAttribute('y1', trail.y1);
    line.setAttribute('x2', trail.x2);
    line.setAttribute('y2', trail.y2);
    line.setAttribute('stroke', trail.color);
    activityTrailLayer.appendChild(line);
  }
}

function populateActivityFilters() {
  const runs = [...new Set(state.activity.events.map((event) => event.run_id).filter(Boolean))].sort();
  const agents = [...new Set(state.activity.events.map(activityAgentId))].sort();
  activityRunFilter.innerHTML = '<option value="all">All</option>' + runs.map((run) => `<option value="${escapeHtml(run)}">${escapeHtml(run)}</option>`).join('');
  activityAgentFilter.innerHTML = '<option value="all">All</option>' + agents.map((agent) => `<option value="${escapeHtml(agent)}">${escapeHtml(agent)}</option>`).join('');
  state.activity.run = runs.includes(state.activity.run) ? state.activity.run : 'all';
  state.activity.agent = agents.includes(state.activity.agent) ? state.activity.agent : 'all';
  activityRunFilter.value = state.activity.run;
  activityAgentFilter.value = state.activity.agent;
}

function updateActivityNodeIds() {
  state.activityNodeIds = new Set();
  for (const event of state.activity.events) {
    const target = eventNodeId(event);
    if (target) state.activityNodeIds.add(target);
    if (event.from_node_id && state.nodeById.has(event.from_node_id)) {
      state.activityNodeIds.add(event.from_node_id);
    }
  }
}

function setTouchedOnly(enabled) {
  state.touchedOnly = Boolean(enabled);
  const button = document.getElementById('touchedOnlyBtn');
  button.textContent = state.touchedOnly ? 'Show all nodes' : 'Touched only';
  button.classList.toggle('active', state.touchedOnly);
  applyFilters();
  fitView();
}

function jumpToActivityNode() {
  const event = state.activity.events[state.activity.index] || null;
  const nodeId = eventNodeId(event);
  if (!nodeId) return;
  state.activeEventNodeId = nodeId;
  const node = state.nodeById.get(nodeId);
  applyFilters();
  selectNode(nodeId);
  if (node) centerNodeInView(node);
}

function animateActivityMarker(fromId, toId, durationMs) {
  if (state.marker.animation) window.cancelAnimationFrame(state.marker.animation);
  const target = state.nodeById.get(toId);
  if (!target) {
    state.marker.visible = false;
    renderActivityMarker();
    return;
  }
  const source = state.nodeById.get(fromId) || target;
  const event = state.activity.events[state.activity.index] || null;
  const agentId = activityAgentId(event);
  const duration = Math.max(120, Math.min(1400, (durationMs || 900) / Math.max(0.5, state.activity.speed)));
  const startedAt = performance.now();
  function step(now) {
    const progress = Math.min(1, (now - startedAt) / duration);
    const eased = 1 - Math.pow(1 - progress, 3);
    const x = source.x + (target.x - source.x) * eased;
    const y = source.y + (target.y - source.y) * eased;
    setMarkerPosition(x, y, true);
    setAgentMarker(agentId, x, y, agentId);
    if (progress < 1) {
      state.marker.animation = window.requestAnimationFrame(step);
    } else {
      state.marker.animation = null;
    }
  }
  state.marker.animation = window.requestAnimationFrame(step);
}

function renderEventList() {
  eventList.innerHTML = '';
  let visibleCount = 0;
  state.activity.events.forEach((event, index) => {
    if (!eventMatchesQuery(event, state.activity.query)) return;
    visibleCount += 1;
    const item = document.createElement('li');
    item.className = index === state.activity.index ? 'active' : '';
    item.textContent = eventLabel(event, index);
    item.addEventListener('click', () => {
      pauseActivity();
      state.activity.index = index;
      showActivityEvent();
    });
    eventList.appendChild(item);
  });
  if (!visibleCount && state.activity.events.length) {
    const item = document.createElement('li');
    item.className = 'empty';
    item.textContent = 'No matching events.';
    eventList.appendChild(item);
  }
}

function formatTokens(value) {
  return value ? `${Number(value).toLocaleString()} est. tokens` : 'no token estimate';
}

function renderContextSummary() {
  if (!state.context) {
    contextSummary.textContent = 'No context overlay loaded.';
    return;
  }
  const sliceTokens = state.context.estimated_tokens || 0;
  const fullTokens = state.context.full_context_estimated_tokens || 0;
  const ratio = fullTokens ? Math.round((sliceTokens / fullTokens) * 100) : 0;
  contextSummary.textContent = `${state.context.node_ids?.length || 0} included nodes - ${formatTokens(sliceTokens)} of ${formatTokens(fullTokens)} (${ratio}%)`;
}

function loadContextOverlay(payload) {
  if (!payload || !Array.isArray(payload.node_ids)) {
    renderContextSummary();
    return;
  }
  state.context = payload;
  state.contextNodeIds = new Set(payload.node_ids);
  renderContextSummary();
  renderGraph();
}

function eventLabel(event, index) {
  const agent = activityAgentId(event);
  const target = event.path || event.node_id || event.to_node_id || 'graph';
  const tokens = event.estimated_tokens ? ` - ${formatTokens(event.estimated_tokens)}` : '';
  return `${index + 1}. ${agent} - ${event.event || 'event'} - ${target}${tokens}`;
}

function eventMatchesQuery(event, query) {
  if (state.activity.run !== 'all' && event.run_id !== state.activity.run) return false;
  if (state.activity.agent !== 'all' && activityAgentId(event) !== state.activity.agent) return false;
  const normalized = (query || '').trim().toLowerCase();
  if (!normalized) return true;
  const haystack = [
    activityAgentId(event),
    event.event,
    event.path,
    event.node_id,
    event.from_node_id,
    event.to_node_id,
    event.status,
    event.severity,
  ].filter(Boolean).join(' ').toLowerCase();
  return haystack.includes(normalized);
}

function renderActivitySummary() {
  const summary = state.activity.summary;
  if (!summary) {
    activitySummary.textContent = 'No activity stream loaded.';
    return;
  }
  const agents = Array.isArray(summary.agents) ? summary.agents.join(', ') : '-';
  activitySummary.textContent = `${summary.event_count || 0} events - ${summary.agent_count || 0} agents (${agents}) - ${formatTokens(summary.estimated_tokens || 0)}`;
}

function renderActivityNow(event) {
  if (!event) {
    activityNow.textContent = state.activity.events.length ? 'Replay reset. Press Play or Next.' : 'Ready.';
    return;
  }
  const index = state.activity.index + 1;
  const total = state.activity.events.length;
  const agent = activityAgentId(event);
  const target = event.path || event.node_id || event.to_node_id || 'graph';
  activityNow.textContent = `${index}/${total} ${agent} - ${event.event || 'event'} - ${target} - ${formatTokens(event.estimated_tokens || 0)}`;
}

function showActivityEvent() {
  const event = state.activity.events[state.activity.index] || null;
  state.activeEventNodeId = eventNodeId(event);
  if (!event) {
    activityDetails.textContent = state.activity.events.length ? 'Reset. Press play or next.' : 'No activity stream loaded.';
    renderActivityNow(null);
    timelineInput.value = 0;
    state.marker.visible = false;
    state.agentMarkers.clear();
    state.activityTrails = [];
    renderActivityMarker();
    renderAgentMarkers();
    renderActivityTrails();
  } else {
    timelineInput.value = state.activity.index;
    const agentId = activityAgentId(event);
    const sourceId = eventSourceId(event);
    activityDetails.textContent = JSON.stringify({
      index: state.activity.index + 1,
      total: state.activity.events.length,
      agent_id: agentId,
      event,
      highlighted_node_id: state.activeEventNodeId,
    }, null, 2);
    renderActivityNow(event);
    if (state.activeEventNodeId) state.selectedId = state.activeEventNodeId;
    addActivityTrail(sourceId, state.activeEventNodeId, agentId);
    animateActivityMarker(sourceId, state.activeEventNodeId, event.duration_ms || 900);
  }
  renderEventList();
  renderGraph();
}

function nextActivity() {
  if (!state.activity.events.length) return;
  state.activity.index = (state.activity.index + 1) % state.activity.events.length;
  showActivityEvent();
}

function playActivity() {
  if (state.activity.timer || !state.activity.events.length) return;
  nextActivity();
  const delay = Math.max(250, 1200 / Math.max(0.5, state.activity.speed));
  state.activity.timer = window.setInterval(nextActivity, delay);
}

function pauseActivity() {
  if (state.activity.timer) {
    window.clearInterval(state.activity.timer);
    state.activity.timer = null;
  }
}

function resetActivity() {
  pauseActivity();
  state.activity.index = -1;
  state.activeEventNodeId = null;
  state.agentMarkers.clear();
  state.activityTrails = [];
  if (state.marker.animation) window.cancelAnimationFrame(state.marker.animation);
  state.marker.animation = null;
  showActivityEvent();
}

function loadActivity(payload) {
  if (!payload || !Array.isArray(payload.events) || payload.events.length === 0) {
    activityDetails.textContent = 'No activity stream loaded.';
    return;
  }
  state.activity.events = payload.events;
  state.activity.warnings = Array.isArray(payload.warnings) ? payload.warnings : [];
  state.activity.summary = payload.summary || null;
  state.activity.index = -1;
  updateActivityNodeIds();
  populateActivityFilters();
  timelineInput.max = Math.max(0, payload.events.length - 1);
  timelineInput.value = 0;
  renderEventList();
  renderActivitySummary();
  renderActivityNow(null);
  activityDetails.textContent = `Loaded ${payload.events.length} events` +
    (state.activity.warnings.length ? ` with ${state.activity.warnings.length} warnings.` : '.');
}

function escapeHtml(value) {
  return String(value).replace(/[&<>"']/g, (char) => ({
    '&': '&amp;',
    '<': '&lt;',
    '>': '&gt;',
    '"': '&quot;',
    "'": '&#39;',
  }[char]));
}

Promise.all([
  fetch('graph-data.json').then((response) => response.json()),
  fetch('activity-stream.json').then((response) => response.ok ? response.json() : null).catch(() => null),
  fetch('context-overlay.json').then((response) => response.ok ? response.json() : null).catch(() => null),
])
  .then(([graphData, activityData, contextData]) => {
    buildScene(graphData || { meta: {}, nodes: [], edges: [] });
    loadActivity(activityData);
    loadContextOverlay(contextData);
  })
  .catch((error) => {
    details.textContent = 'Failed to load graph-data.json\n\n' + String(error);
  });
"""


def export_web_visualization(
    store: GraphStore,
    out_dir: Path,
    *,
    activity_path: Path | None = None,
    context_path: Path | None = None,
) -> Path:
    out_dir.mkdir(parents=True, exist_ok=True)
    export_json(store, out_dir / "graph-data.json")
    activity_out = out_dir / "activity-stream.json"
    if activity_path is not None:
        write_activity_payload(activity_path, activity_out)
    elif activity_out.exists():
        activity_out.unlink()
    context_out = out_dir / "context-overlay.json"
    if context_path is not None:
        context_out.write_text(context_path.read_text(encoding="utf-8"), encoding="utf-8")
    elif context_out.exists():
        context_out.unlink()
    (out_dir / "index.html").write_text(HTML, encoding="utf-8")
    (out_dir / "styles.css").write_text(CSS, encoding="utf-8")
    (out_dir / "app.js").write_text(JS, encoding="utf-8")
    return out_dir / "index.html"
