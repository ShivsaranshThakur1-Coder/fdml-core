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
      if (o && Array.isArray(o.slots) && o.slots.length) return o.slots;
    }
    return [];
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
    return el;
  }

  function circle(svg, cx, cy, r, cls) {
    var el = document.createElementNS("http://www.w3.org/2000/svg", "circle");
    el.setAttribute("cx", String(cx));
    el.setAttribute("cy", String(cy));
    el.setAttribute("r", String(r));
    el.setAttribute("class", cls || "diagram-node");
    svg.appendChild(el);
    return el;
  }

  function text(svg, x, y, value, cls) {
    var el = document.createElementNS("http://www.w3.org/2000/svg", "text");
    el.setAttribute("x", String(x));
    el.setAttribute("y", String(y));
    el.setAttribute("class", cls || "diagram-label");
    el.textContent = value;
    svg.appendChild(el);
    return el;
  }

  function drawCircle(svg, topology) {
    var orders = topology && topology.circle && Array.isArray(topology.circle.orders) ? topology.circle.orders : [];
    var slots = [];
    if (orders.length && Array.isArray(orders[0].slots)) slots = orders[0].slots;

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

  function drawLineFormation(svg, topology) {
    var lines = topology && topology.line && Array.isArray(topology.line.lines) ? topology.line.lines : [];
    var slots = [];
    if (lines.length) {
      var chosen = lines[0];
      if (chosen && Array.isArray(chosen.orders)) {
        var initial = chosen.orders.find(function (o) { return o && o.phase === "initial"; });
        slots = initial && Array.isArray(initial.slots) ? initial.slots : firstNonEmptySlots(chosen.orders);
      }
    }

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

  function drawTwoLines(svg, topology) {
    var linesData = topology && topology.twoLines && Array.isArray(topology.twoLines.lines) ? topology.twoLines.lines : [];
    var topSlots = [];
    var bottomSlots = [];
    if (linesData.length >= 1) topSlots = firstNonEmptySlots(linesData[0].orders);
    if (linesData.length >= 2) bottomSlots = firstNonEmptySlots(linesData[1].orders);

    line(svg, 44, 64, 276, 64);
    line(svg, 44, 122, 276, 122);
    text(svg, 160, 88, "facing", "diagram-label");

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

    drawSlots(topSlots, 64);
    drawSlots(bottomSlots, 122);
  }

  function drawCouple(svg, topology) {
    var man = "man";
    var woman = "woman";
    var usedPair = false;

    if (topology && topology.couples && Array.isArray(topology.couples.pairs) && topology.couples.pairs.length) {
      var pair = topology.couples.pairs[0] || {};
      var a = pair.a || "";
      var b = pair.b || "";
      if (a && b) {
        man = String(a);
        woman = String(b);
        usedPair = true;
      }
    }

    if (!usedPair) {
      man = "dancer A";
      woman = "dancer B";
    }

    line(svg, 120, 92, 200, 92);
    circle(svg, 120, 92, 11, "diagram-node");
    circle(svg, 200, 92, 11, "diagram-node");
    text(svg, 120, 115, man, "diagram-label");
    text(svg, 200, 115, woman, "diagram-label");
  }

  function renderDiagram(root, payload) {
    var formationKind = payload && payload.meta ? String(payload.meta.formationKind || "") : "";
    if (!formationKind) return;

    var wrap = document.createElement("section");
    wrap.className = "diagram-panel";

    var heading = document.createElement("h2");
    heading.textContent = "Formation Diagram";
    wrap.appendChild(heading);

    var svg = makeSvg("0 0 320 160");
    var topology = payload && payload.topology ? payload.topology : {};
    if (formationKind === "circle") drawCircle(svg, topology);
    else if (formationKind === "line") drawLineFormation(svg, topology);
    else if (formationKind === "twoLinesFacing") drawTwoLines(svg, topology);
    else if (formationKind === "couple") drawCouple(svg, topology);
    else return;

    wrap.appendChild(svg);
    root.appendChild(wrap);
  }

  async function init() {
    var root = document.getElementById("fdml-diagram");
    if (!root) return;

    var stem = stemFromPathname(window.location.pathname || "");
    if (!stem) return;

    try {
      var res = await fetch(stem + ".json", { cache: "no-store" });
      if (!res.ok) throw new Error("HTTP " + String(res.status));
      var data = await res.json();
      var payload = Array.isArray(data) ? data[0] : data;
      renderDiagram(root, payload || {});
    } catch (_err) {
      // No-op for missing payloads.
    }
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", init);
  } else {
    init();
  }
})();
