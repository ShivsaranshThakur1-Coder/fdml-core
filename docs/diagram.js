(function () {
  "use strict";

  function stemFromPathname(pathname) {
    var raw = pathname.split("/").pop() || "";
    if (!raw || !raw.toLowerCase().endsWith(".html")) return "";
    return decodeURIComponent(raw.slice(0, -5));
  }

  function firstNonEmptySlots(orders) {
    if (!Array.isArray(orders)) return [];
    for (var i = 0; i < orders.length; i++) {
      var o = orders[i];
      if (o && Array.isArray(o.slots) && o.slots.length) return o.slots.slice();
    }
    return [];
  }

  function fetchCardPayload() {
    if (window.__fdmlPayloadPromise) return window.__fdmlPayloadPromise;
    var stem = stemFromPathname(window.location.pathname || "");
    if (!stem) return Promise.resolve(null);

    window.__fdmlPayloadPromise = fetch(stem + ".json", { cache: "no-store" })
      .then(function (res) {
        if (!res.ok) return null;
        return res.json();
      })
      .then(function (data) {
        return Array.isArray(data) ? data[0] : data;
      })
      .catch(function () {
        return null;
      });

    return window.__fdmlPayloadPromise;
  }

  function buildState(payload) {
    var topology = payload && payload.topology ? payload.topology : {};
    var state = {
      circleOrder: [],
      lineIds: [],
      lineOrders: {},
      twoLinesLineIds: [],
      twoLinesOrders: {},
      twoLinesOpposites: [],
      twoLinesNeighbors: [],
      twoLinesSeparation: 0
    };

    var circleOrders = topology.circle && Array.isArray(topology.circle.orders) ? topology.circle.orders : [];
    if (circleOrders.length && Array.isArray(circleOrders[0].slots)) {
      state.circleOrder = circleOrders[0].slots.slice();
    }

    var lines = topology.line && Array.isArray(topology.line.lines) ? topology.line.lines : [];
    for (var i = 0; i < lines.length; i++) {
      var line = lines[i] || {};
      var id = line.id || "";
      if (!id) continue;
      state.lineIds.push(id);
      var initial = null;
      if (Array.isArray(line.orders)) {
        for (var j = 0; j < line.orders.length; j++) {
          var order = line.orders[j] || {};
          if (order.phase === "initial" && Array.isArray(order.slots) && order.slots.length) {
            initial = order.slots.slice();
            break;
          }
        }
        if (!initial) initial = firstNonEmptySlots(line.orders);
      }
      state.lineOrders[id] = initial || [];
    }

    var twoLines = topology.twoLines || {};
    var twoLinesRows = Array.isArray(twoLines.lines) ? twoLines.lines : [];
    for (var k = 0; k < twoLinesRows.length; k++) {
      var row = twoLinesRows[k] || {};
      var rowId = row.id || "";
      if (!rowId) continue;
      state.twoLinesLineIds.push(rowId);
      state.twoLinesOrders[rowId] = firstNonEmptySlots(row.orders || []);
    }

    state.twoLinesOpposites = Array.isArray(twoLines.opposites) ? twoLines.opposites.slice() : [];
    state.twoLinesNeighbors = Array.isArray(twoLines.neighbors) ? twoLines.neighbors.slice() : [];

    return state;
  }

  function makeSvg(viewBox) {
    var svg = document.createElementNS("http://www.w3.org/2000/svg", "svg");
    svg.setAttribute("class", "fdml-diagram-svg");
    svg.setAttribute("viewBox", viewBox);
    svg.setAttribute("role", "img");
    return svg;
  }

  function line(svg, x1, y1, x2, y2) {
    var el = document.createElementNS("http://www.w3.org/2000/svg", "line");
    el.setAttribute("x1", String(x1));
    el.setAttribute("y1", String(y1));
    el.setAttribute("x2", String(x2));
    el.setAttribute("y2", String(y2));
    el.setAttribute("class", "diagram-line");
    svg.appendChild(el);
  }

  function circle(svg, cx, cy, r, cls) {
    var el = document.createElementNS("http://www.w3.org/2000/svg", "circle");
    el.setAttribute("cx", String(cx));
    el.setAttribute("cy", String(cy));
    el.setAttribute("r", String(r));
    el.setAttribute("class", cls || "diagram-node");
    svg.appendChild(el);
  }

  function text(svg, x, y, value, cls) {
    var el = document.createElementNS("http://www.w3.org/2000/svg", "text");
    el.setAttribute("x", String(x));
    el.setAttribute("y", String(y));
    el.setAttribute("class", cls || "diagram-label");
    el.textContent = value;
    svg.appendChild(el);
  }

  function slotsForLine(state, lineId) {
    if (!state || !state.lineOrders) return [];
    var slots = state.lineOrders[lineId];
    return Array.isArray(slots) ? slots : [];
  }

  function slotsForTwoLines(state, lineId) {
    if (!state || !state.twoLinesOrders) return [];
    var slots = state.twoLinesOrders[lineId];
    return Array.isArray(slots) ? slots : [];
  }

  function drawCircle(svg, state) {
    var slots = Array.isArray(state.circleOrder) ? state.circleOrder : [];
    circle(svg, 160, 95, 56, "diagram-ring");

    if (!slots.length) return;
    for (var i = 0; i < slots.length; i++) {
      var angle = (Math.PI * 2 * i) / slots.length - Math.PI / 2;
      var cx = 160 + Math.cos(angle) * 56;
      var cy = 95 + Math.sin(angle) * 56;
      circle(svg, cx, cy, 8, "diagram-node");
      text(svg, cx, cy + 20, String(slots[i]), "diagram-label diagram-label-small");
    }
  }

  function drawLineFormation(svg, state) {
    var firstId = state.lineIds.length ? state.lineIds[0] : "";
    var slots = firstId ? slotsForLine(state, firstId) : [];

    line(svg, 44, 92, 276, 92);
    if (!slots.length) return;

    var span = 220;
    var left = 50;
    for (var i = 0; i < slots.length; i++) {
      var x = slots.length === 1 ? 160 : left + (span * i) / (slots.length - 1);
      circle(svg, x, 92, 8, "diagram-node");
      text(svg, x, 112, String(slots[i]), "diagram-label diagram-label-small");
    }
  }

  function drawTwoLines(svg, state) {
    var topId = state.twoLinesLineIds.length > 0 ? state.twoLinesLineIds[0] : "";
    var bottomId = state.twoLinesLineIds.length > 1 ? state.twoLinesLineIds[1] : "";

    var topSlots = topId ? slotsForTwoLines(state, topId) : [];
    var bottomSlots = bottomId ? slotsForTwoLines(state, bottomId) : [];

    var sep = Number(state.twoLinesSeparation || 0);
    var yTop = 64 - sep * 4;
    var yBottom = 122 + sep * 4;

    line(svg, 44, yTop, 276, yTop);
    line(svg, 44, yBottom, 276, yBottom);
    text(svg, 160, (yTop + yBottom) / 2, "facing", "diagram-label");

    function drawSlots(slots, y) {
      if (!slots.length) return;
      var span = 220;
      var left = 50;
      for (var i = 0; i < slots.length; i++) {
        var x = slots.length === 1 ? 160 : left + (span * i) / (slots.length - 1);
        circle(svg, x, y, 8, "diagram-node");
        text(svg, x, y + 20, String(slots[i]), "diagram-label diagram-label-small");
      }
    }

    drawSlots(topSlots, yTop);
    drawSlots(bottomSlots, yBottom);
  }

  function drawCouple(svg, payload) {
    var man = "dancer A";
    var woman = "dancer B";

    var topology = payload && payload.topology ? payload.topology : {};
    if (topology.couples && Array.isArray(topology.couples.pairs) && topology.couples.pairs.length) {
      var pair = topology.couples.pairs[0] || {};
      if (pair.a && pair.b) {
        man = String(pair.a);
        woman = String(pair.b);
      }
    }

    line(svg, 120, 92, 200, 92);
    circle(svg, 120, 92, 11, "diagram-node");
    circle(svg, 200, 92, 11, "diagram-node");
    text(svg, 120, 115, man, "diagram-label");
    text(svg, 200, 115, woman, "diagram-label");
  }

  function renderDiagram(root, payload, stateOverride) {
    if (!root) return;
    var formationKind = payload && payload.meta ? String(payload.meta.formationKind || "") : "";
    root.innerHTML = "";
    if (!formationKind) return;

    var state = stateOverride || buildState(payload || {});

    var wrap = document.createElement("section");
    wrap.className = "diagram-panel";

    var heading = document.createElement("h2");
    heading.textContent = "Formation Diagram";
    wrap.appendChild(heading);

    var svg = makeSvg("0 0 320 160");
    if (formationKind === "circle") drawCircle(svg, state);
    else if (formationKind === "line") drawLineFormation(svg, state);
    else if (formationKind === "twoLinesFacing") drawTwoLines(svg, state);
    else if (formationKind === "couple") drawCouple(svg, payload || {});
    else return;

    wrap.appendChild(svg);
    root.appendChild(wrap);
  }

  window.fdmlStemFromPathname = stemFromPathname;
  window.fdmlFetchCardPayload = fetchCardPayload;
  window.fdmlBuildDiagramState = buildState;
  window.fdmlRenderDiagram = renderDiagram;

  async function init() {
    var root = document.getElementById("fdml-diagram");
    if (!root) return;
    var payload = await fetchCardPayload();
    if (!payload) return;
    renderDiagram(root, payload);
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", init);
  } else {
    init();
  }
})();
