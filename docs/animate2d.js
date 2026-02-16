(function () {
  "use strict";

  var FORMATIONS = { line: true, twoLinesFacing: true, circle: true };
  var EPS = 1e-9;

  function clamp(v, lo, hi) {
    return Math.max(lo, Math.min(hi, v));
  }

  function deepClone(obj) {
    return JSON.parse(JSON.stringify(obj || {}));
  }

  function asCount(beats) {
    var n = Number(beats);
    if (!Number.isFinite(n) || n <= 0) return 0;
    return Math.round(n);
  }

  function rotateForward(arr, delta) {
    if (!Array.isArray(arr) || !arr.length) return [];
    var n = arr.length;
    var d = delta % n;
    if (d < 0) d += n;
    if (d === 0) return arr.slice();
    var out = [];
    for (var i = 0; i < n; i++) out.push(arr[(i + d) % n]);
    return out;
  }

  function swapInOrder(order, a, b) {
    if (!Array.isArray(order)) return false;
    var ia = order.indexOf(a);
    var ib = order.indexOf(b);
    if (ia < 0 || ib < 0 || ia === ib) return false;
    var tmp = order[ia];
    order[ia] = order[ib];
    order[ib] = tmp;
    return true;
  }

  function isTruthy(value) {
    var raw = String(value == null ? "" : value).toLowerCase();
    return raw === "true" || raw === "1" || raw === "yes";
  }

  function isCyclicEquivalent(a, b) {
    if (!Array.isArray(a) || !Array.isArray(b)) return false;
    if (a.length !== b.length) return false;
    if (!a.length) return true;
    var n = a.length;
    var start = b.indexOf(a[0]);
    if (start < 0) return false;
    for (var i = 0; i < n; i++) {
      if (a[i] !== b[(start + i) % n]) return false;
    }
    return true;
  }

  function sameArray(a, b) {
    if (!Array.isArray(a) || !Array.isArray(b)) return false;
    if (a.length !== b.length) return false;
    for (var i = 0; i < a.length; i++) {
      if (a[i] !== b[i]) return false;
    }
    return true;
  }

  function rotateTargetsInOrder(order, targets, deltaStep) {
    var out = Array.isArray(order) ? order.slice() : [];
    if (!out.length) return out;
    var targetSet = {};
    (targets || []).forEach(function (id) {
      if (id) targetSet[id] = true;
    });
    var indices = [];
    for (var i = 0; i < out.length; i++) {
      if (targetSet[out[i]]) indices.push(i);
    }
    if (indices.length < 2) return out;

    var src = out.slice();
    if (deltaStep > 0) {
      for (i = 0; i < indices.length; i++) {
        out[indices[i]] = src[indices[(i + 1) % indices.length]];
      }
      return out;
    }

    if (deltaStep < 0) {
      for (i = 0; i < indices.length; i++) {
        out[indices[i]] = src[indices[(i - 1 + indices.length) % indices.length]];
      }
    }
    return out;
  }

  function dirToDeltaX(dir) {
    var d = String(dir || "").toLowerCase();
    if (!d) return 0;
    if (d === "left" || d === "counterclockwise" || d === "ccw" || d === "west") return -0.14;
    if (d === "right" || d === "clockwise" || d === "cw" || d === "east") return 0.14;
    return 0;
  }

  function splitWho(who) {
    var raw = String(who || "").trim();
    if (!raw) return [];
    return raw.split(/[\s,|/]+/).filter(Boolean);
  }

  function sortUnique(xs) {
    var m = {};
    (xs || []).forEach(function (x) {
      if (x) m[x] = true;
    });
    return Object.keys(m).sort();
  }

  function firstOrderSlots(orders, preferPhase) {
    if (!Array.isArray(orders)) return [];
    if (preferPhase) {
      for (var i = 0; i < orders.length; i++) {
        var order = orders[i] || {};
        if (String(order.phase || "").toLowerCase() === preferPhase && Array.isArray(order.slots) && order.slots.length) {
          return order.slots.slice();
        }
      }
    }
    for (var j = 0; j < orders.length; j++) {
      var o = orders[j] || {};
      if (Array.isArray(o.slots) && o.slots.length) return o.slots.slice();
    }
    return [];
  }

  function getPayload() {
    if (typeof window.fdmlFetchCardPayload === "function") {
      return window.fdmlFetchCardPayload();
    }
    var stem = "";
    if (typeof window.fdmlStemFromPathname === "function") {
      stem = window.fdmlStemFromPathname(window.location.pathname || "");
    } else {
      var raw = (window.location.pathname || "").split("/").pop() || "";
      if (raw.toLowerCase().endsWith(".html")) stem = decodeURIComponent(raw.slice(0, -5));
    }
    if (!stem) return Promise.resolve(null);
    return fetch(stem + ".json", { cache: "no-store" })
      .then(function (res) {
        if (!res.ok) return null;
        return res.json();
      })
      .then(function (data) {
        return Array.isArray(data) ? (data[0] || null) : data;
      })
      .catch(function () {
        return null;
      });
  }

  function lineSlotAnchors(count) {
    if (count <= 0) return [];
    if (count === 1) return [{ x: 0, y: 0 }];
    var out = [];
    for (var i = 0; i < count; i++) {
      out.push({ x: -1 + (2 * i) / (count - 1), y: 0 });
    }
    return out;
  }

  function twoLineSlotAnchors(countTop, countBottom, sep) {
    var top = [];
    var bottom = [];
    var i;
    if (countTop === 1) top.push({ x: 0, y: sep });
    else {
      for (i = 0; i < countTop; i++) top.push({ x: countTop <= 0 ? 0 : -1 + (2 * i) / (countTop - 1), y: sep });
    }
    if (countBottom === 1) bottom.push({ x: 0, y: -sep });
    else {
      for (i = 0; i < countBottom; i++) bottom.push({ x: countBottom <= 0 ? 0 : -1 + (2 * i) / (countBottom - 1), y: -sep });
    }
    return { top: top, bottom: bottom };
  }

  function buildInitialState(payload) {
    var meta = payload && payload.meta ? payload.meta : {};
    var topology = payload && payload.topology ? payload.topology : {};
    var formationKind = String(meta.formationKind || "");

    var state = {
      formationKind: formationKind,
      ids: [],
      positions: {},
      separation: 0.8,
      circle: {
        order: [],
        radius: 0.85,
        angleOffset: -Math.PI / 2
      },
      line: {
        lineId: "",
        order: []
      },
      twoLines: {
        topId: "",
        bottomId: "",
        orders: {}
      }
    };

    if (formationKind === "line") {
      var lines = topology.line && Array.isArray(topology.line.lines) ? topology.line.lines : [];
      if (lines.length) {
        var first = lines[0] || {};
        state.line.lineId = String(first.id || "line");
        state.line.order = firstOrderSlots(first.orders, "initial");
      }
      assignPositionsFromStructure(state);
      return state;
    }

    if (formationKind === "circle") {
      var circleOrders = topology.circle && Array.isArray(topology.circle.orders) ? topology.circle.orders : [];
      state.circle.order = firstOrderSlots(circleOrders, "initial");
      assignPositionsFromStructure(state);
      return state;
    }

    if (formationKind === "twoLinesFacing") {
      var rows = topology.twoLines && Array.isArray(topology.twoLines.lines) ? topology.twoLines.lines : [];
      var byId = {};
      rows.forEach(function (row) {
        if (!row || !row.id) return;
        byId[row.id] = row;
      });

      var facing = topology.twoLines && topology.twoLines.facing ? topology.twoLines.facing : {};
      var topId = String(facing.a || "");
      var bottomId = String(facing.b || "");

      if (!topId && rows.length) topId = String(rows[0].id || "");
      if (!bottomId && rows.length > 1) bottomId = String(rows[1].id || "");

      state.twoLines.topId = topId;
      state.twoLines.bottomId = bottomId;

      rows.forEach(function (row) {
        var id = String((row && row.id) || "");
        if (!id) return;
        state.twoLines.orders[id] = firstOrderSlots(row.orders, "initial");
      });

      assignPositionsFromStructure(state);
    }

    return state;
  }

  function assignPositionsFromStructure(state) {
    state.positions = {};

    if (state.formationKind === "circle") {
      var orderCircle = Array.isArray(state.circle.order) ? state.circle.order : [];
      var radius = Number(state.circle.radius || 0.85);
      var offset = Number(state.circle.angleOffset || (-Math.PI / 2));
      var n = orderCircle.length;
      for (var k = 0; k < n; k++) {
        var angle = offset + (2 * Math.PI * k) / Math.max(1, n);
        state.positions[orderCircle[k]] = {
          x: Math.cos(angle) * radius,
          y: Math.sin(angle) * radius
        };
      }
      state.ids = sortUnique(orderCircle);
      return;
    }

    if (state.formationKind === "line") {
      var order = Array.isArray(state.line.order) ? state.line.order : [];
      var anchors = lineSlotAnchors(order.length);
      for (var i = 0; i < order.length; i++) {
        state.positions[order[i]] = { x: anchors[i].x, y: anchors[i].y };
      }
      state.ids = sortUnique(order);
      return;
    }

    if (state.formationKind === "twoLinesFacing") {
      var topId = state.twoLines.topId;
      var bottomId = state.twoLines.bottomId;
      var topOrder = (state.twoLines.orders[topId] || []).slice();
      var bottomOrder = (state.twoLines.orders[bottomId] || []).slice();
      var anchors2 = twoLineSlotAnchors(topOrder.length, bottomOrder.length, state.separation);
      var j;
      for (j = 0; j < topOrder.length; j++) {
        state.positions[topOrder[j]] = { x: anchors2.top[j].x, y: anchors2.top[j].y };
      }
      for (j = 0; j < bottomOrder.length; j++) {
        state.positions[bottomOrder[j]] = { x: anchors2.bottom[j].x, y: anchors2.bottom[j].y };
      }
      state.ids = sortUnique(topOrder.concat(bottomOrder));
    }
  }

  function resolveWhoTargets(who, state) {
    var ids = state.ids || [];
    var tokens = splitWho(who);
    if (!tokens.length) return [];
    if (tokens.length === 1 && tokens[0] === "all") return ids.slice();
    var set = {};
    ids.forEach(function (id) {
      set[id] = true;
    });
    return tokens.filter(function (t) {
      return !!set[t];
    });
  }

  function parseDelta(value) {
    var n = parseInt(String(value || "0"), 10);
    return Number.isFinite(n) ? n : 0;
  }

  function applyEvent(state, event) {
    var kind = String(event.kind || "").toLowerCase();
    var preserveOrder = isTruthy(event.preserveOrder);

    if (kind === "approach") {
      state.separation = clamp(state.separation - 0.1, 0.25, 1.4);
      if (state.formationKind === "twoLinesFacing") assignPositionsFromStructure(state);
      return;
    }

    if (kind === "retreat") {
      state.separation = clamp(state.separation + 0.1, 0.25, 1.4);
      if (state.formationKind === "twoLinesFacing") assignPositionsFromStructure(state);
      return;
    }

    if (kind === "progress") {
      var delta = parseDelta(event.delta);
      if (state.formationKind === "line") {
        state.line.order = rotateForward(state.line.order, delta);
        assignPositionsFromStructure(state);
      } else if (state.formationKind === "twoLinesFacing") {
        var keys = Object.keys(state.twoLines.orders || {});
        keys.forEach(function (id) {
          state.twoLines.orders[id] = rotateForward(state.twoLines.orders[id], delta);
        });
        assignPositionsFromStructure(state);
      }
      return;
    }

    if (kind === "swapplaces") {
      var a = String(event.a || "");
      var b = String(event.b || "");
      if (!a || !b) return;

      if (state.formationKind === "circle") {
        var beforeCircleSwap = state.circle.order.slice();
        var afterCircleSwap = beforeCircleSwap.slice();
        if (!swapInOrder(afterCircleSwap, a, b)) return;
        if (preserveOrder && !isCyclicEquivalent(beforeCircleSwap, afterCircleSwap)) return;
        state.circle.order = afterCircleSwap;
        assignPositionsFromStructure(state);
        return;
      }

      var swappedInOrder = false;
      if (state.formationKind === "line") {
        swappedInOrder = swapInOrder(state.line.order, a, b);
      } else if (state.formationKind === "twoLinesFacing") {
        var ids = Object.keys(state.twoLines.orders || {});
        for (var i = 0; i < ids.length; i++) {
          if (swapInOrder(state.twoLines.orders[ids[i]], a, b)) {
            swappedInOrder = true;
            break;
          }
        }
      }

      if (swappedInOrder) {
        assignPositionsFromStructure(state);
        return;
      }

      if (state.positions[a] && state.positions[b]) {
        var tmp = state.positions[a];
        state.positions[a] = state.positions[b];
        state.positions[b] = tmp;
      }
      return;
    }

    if (kind === "move") {
      if (String(event.frame || "") !== "formation") return;

      if (state.formationKind === "circle") {
        var dirCircle = String(event.dir || "").toLowerCase();
        var deltaStep = 0;
        if (dirCircle === "counterclockwise" || dirCircle === "ccw") deltaStep = 1;
        else if (dirCircle === "clockwise" || dirCircle === "cw") deltaStep = -1;
        if (!deltaStep) return;

        var beforeCircleMove = state.circle.order.slice();
        if (!beforeCircleMove.length) return;
        var targetsCircle = resolveWhoTargets(event.who, state);
        var afterCircleMove;
        if (!targetsCircle.length || targetsCircle.length === beforeCircleMove.length) {
          afterCircleMove = rotateForward(beforeCircleMove, deltaStep);
        } else {
          afterCircleMove = rotateTargetsInOrder(beforeCircleMove, targetsCircle, deltaStep);
        }
        if (preserveOrder && !isCyclicEquivalent(beforeCircleMove, afterCircleMove)) return;
        if (sameArray(beforeCircleMove, afterCircleMove)) return;
        state.circle.order = afterCircleMove;
        assignPositionsFromStructure(state);
        return;
      }

      var dx = dirToDeltaX(event.dir);
      if (Math.abs(dx) < EPS) return;
      var targets = resolveWhoTargets(event.who, state);
      for (var j = 0; j < targets.length; j++) {
        var id = targets[j];
        var pos = state.positions[id];
        if (!pos) continue;
        pos.x = clamp(pos.x + dx, -1.2, 1.2);
      }
    }
  }

  function buildEvents(payload) {
    var figures = Array.isArray(payload && payload.figures) ? payload.figures : [];
    var events = [];
    var totalCounts = 0;

    figures.forEach(function (fig) {
      var steps = Array.isArray(fig && fig.steps) ? fig.steps : [];
      steps.forEach(function (step) {
        var stepCount = asCount(step && step.beats);
        totalCounts += stepCount;
        var primitives = Array.isArray(step && step.primitives) ? step.primitives : [];
        primitives.forEach(function (p) {
          events.push({
            t: totalCounts,
            kind: p.kind || "",
            frame: p.frame || "",
            dir: p.dir || "",
            who: p.who || step.who || "",
            a: p.a || "",
            b: p.b || "",
            delta: p.delta || "",
            preserveOrder: p.preserveOrder || ""
          });
        });
      });
    });

    return { events: events, totalCounts: totalCounts };
  }

  function snapshotState(state, t) {
    var ids = sortUnique(Object.keys(state.positions || {}));
    var positions = {};
    ids.forEach(function (id) {
      var p = state.positions[id] || { x: 0, y: 0 };
      positions[id] = { x: p.x, y: p.y };
    });
    return {
      t: t,
      formationKind: state.formationKind,
      ids: ids,
      separation: state.separation,
      positions: positions
    };
  }

  function buildIntegerSnapshots(baseState, events, totalCounts) {
    var snapshots = [];
    var state = deepClone(baseState);
    snapshots.push(snapshotState(state, 0));

    var idx = 0;
    for (var t = 1; t <= totalCounts; t++) {
      while (idx < events.length && Number(events[idx].t) <= t) {
        applyEvent(state, events[idx]);
        idx += 1;
      }
      snapshots.push(snapshotState(state, t));
    }
    return snapshots;
  }

  function interpolate(a, b, alpha) {
    var ids = sortUnique((a.ids || []).concat(b.ids || []));
    var positions = {};
    ids.forEach(function (id) {
      var pa = a.positions[id] || { x: 0, y: 0 };
      var pb = b.positions[id] || pa;
      positions[id] = {
        x: pa.x + (pb.x - pa.x) * alpha,
        y: pa.y + (pb.y - pa.y) * alpha
      };
    });
    return {
      t: a.t + alpha,
      ids: ids,
      separation: a.separation + (b.separation - a.separation) * alpha,
      positions: positions,
      formationKind: a.formationKind || b.formationKind
    };
  }

  function renderSvg(container, frame) {
    var scene = container.__fdmlAnimate2dScene;
    if (!scene) {
      var sec = document.createElement("section");
      sec.className = "diagram-panel";

      var h = document.createElement("h2");
      h.textContent = "Formation Diagram";
      sec.appendChild(h);

      var svg = document.createElementNS("http://www.w3.org/2000/svg", "svg");
      svg.setAttribute("class", "fdml-diagram-svg");
      svg.setAttribute("preserveAspectRatio", "xMidYMid meet");

      var ring = document.createElementNS("http://www.w3.org/2000/svg", "circle");
      ring.setAttribute("class", "diagram-ring");
      ring.setAttribute("fill", "none");
      svg.appendChild(ring);

      var lineA = document.createElementNS("http://www.w3.org/2000/svg", "line");
      lineA.setAttribute("class", "diagram-line");
      svg.appendChild(lineA);

      var lineB = document.createElementNS("http://www.w3.org/2000/svg", "line");
      lineB.setAttribute("class", "diagram-line");
      svg.appendChild(lineB);

      var facingLabel = document.createElementNS("http://www.w3.org/2000/svg", "text");
      facingLabel.setAttribute("class", "diagram-label");
      facingLabel.setAttribute("text-anchor", "middle");
      facingLabel.textContent = "facing";
      svg.appendChild(facingLabel);

      var nodes = document.createElementNS("http://www.w3.org/2000/svg", "g");
      nodes.setAttribute("id", "nodes");
      svg.appendChild(nodes);

      sec.appendChild(svg);
      while (container.firstChild) container.removeChild(container.firstChild);
      container.appendChild(sec);

      scene = {
        svg: svg,
        ring: ring,
        lineA: lineA,
        lineB: lineB,
        facingLabel: facingLabel,
        nodes: nodes,
        nodeMap: {}
      };
      container.__fdmlAnimate2dScene = scene;
    }

    scene.svg.setAttribute("viewBox", frame.formationKind === "circle" ? "-1.2 -1.2 2.4 2.4" : "-1.4 -1.1 2.8 2.2");
    scene.svg.setAttribute("preserveAspectRatio", "xMidYMid meet");

    function setVisible(el, visible) {
      el.style.display = visible ? "" : "none";
    }

    if (frame.formationKind === "circle") {
      setVisible(scene.ring, true);
      setVisible(scene.lineA, false);
      setVisible(scene.lineB, false);
      setVisible(scene.facingLabel, false);
      scene.ring.setAttribute("cx", "0");
      scene.ring.setAttribute("cy", "0");
      scene.ring.setAttribute("r", "0.92");
      scene.ring.setAttribute("fill", "none");
    } else if (frame.formationKind === "line") {
      setVisible(scene.ring, false);
      setVisible(scene.lineA, true);
      setVisible(scene.lineB, false);
      setVisible(scene.facingLabel, false);
      scene.lineA.setAttribute("x1", "-1.1");
      scene.lineA.setAttribute("y1", "0");
      scene.lineA.setAttribute("x2", "1.1");
      scene.lineA.setAttribute("y2", "0");
    } else if (frame.formationKind === "twoLinesFacing") {
      setVisible(scene.ring, false);
      setVisible(scene.lineA, true);
      setVisible(scene.lineB, true);
      setVisible(scene.facingLabel, true);
      scene.lineA.setAttribute("x1", "-1.1");
      scene.lineA.setAttribute("y1", String(frame.separation));
      scene.lineA.setAttribute("x2", "1.1");
      scene.lineA.setAttribute("y2", String(frame.separation));
      scene.lineB.setAttribute("x1", "-1.1");
      scene.lineB.setAttribute("y1", String(-frame.separation));
      scene.lineB.setAttribute("x2", "1.1");
      scene.lineB.setAttribute("y2", String(-frame.separation));
      scene.facingLabel.setAttribute("x", "0");
      scene.facingLabel.setAttribute("y", "0.03");
    } else {
      setVisible(scene.ring, false);
      setVisible(scene.lineA, false);
      setVisible(scene.lineB, false);
      setVisible(scene.facingLabel, false);
    }

    var targetIds = sortUnique(frame.ids || []);
    var targetSet = {};
    targetIds.forEach(function (id) {
      targetSet[id] = true;
    });

    Object.keys(scene.nodeMap).forEach(function (id) {
      if (targetSet[id]) return;
      var stale = scene.nodeMap[id];
      if (stale.circleEl && stale.circleEl.parentNode) stale.circleEl.parentNode.removeChild(stale.circleEl);
      if (stale.textEl && stale.textEl.parentNode) stale.textEl.parentNode.removeChild(stale.textEl);
      delete scene.nodeMap[id];
    });

    targetIds.forEach(function (id) {
      var pair = scene.nodeMap[id];
      if (!pair) {
        var c = document.createElementNS("http://www.w3.org/2000/svg", "circle");
        c.setAttribute("r", "0.07");
        c.setAttribute("class", "diagram-node");
        scene.nodes.appendChild(c);

        var t = document.createElementNS("http://www.w3.org/2000/svg", "text");
        t.setAttribute("class", "diagram-label diagram-label-small");
        t.setAttribute("text-anchor", "middle");
        scene.nodes.appendChild(t);

        pair = { circleEl: c, textEl: t };
        scene.nodeMap[id] = pair;
      }

      var p = frame.positions[id] || { x: 0, y: 0 };
      pair.circleEl.setAttribute("cx", String(p.x));
      pair.circleEl.setAttribute("cy", String(p.y));
      pair.textEl.setAttribute("x", String(p.x));
      pair.textEl.setAttribute("y", String(p.y + 0.14));
      pair.textEl.textContent = id;
    });
  }

  async function init() {
    var controlsRoot = document.getElementById("fdml-anim-controls");
    var diagramRoot = document.getElementById("fdml-diagram");
    if (!controlsRoot || !diagramRoot) return;

    var payload = await getPayload();
    if (!payload || !payload.meta) return;

    var formationKind = String(payload.meta.formationKind || "");
    if (!FORMATIONS[formationKind]) return;

    window.__fdmlAnimate2DHandledFormation = formationKind;

    var base = buildInitialState(payload);
    if (!base || !base.formationKind) return;

    var timeline = buildEvents(payload);
    var total = Math.max(0, timeline.totalCounts);
    var snapshots = buildIntegerSnapshots(base, timeline.events, total);

    var wrap = document.createElement("div");
    wrap.className = "anim-controls";

    var playBtn = document.createElement("button");
    playBtn.className = "anim-btn";
    playBtn.type = "button";
    playBtn.textContent = "Play";

    var slider = document.createElement("input");
    slider.type = "range";
    slider.id = "fdml-scrub";
    slider.min = "0";
    slider.max = String(total);
    slider.step = "1";
    slider.value = "0";

    var label = document.createElement("span");
    label.className = "anim-time";

    wrap.appendChild(playBtn);
    wrap.appendChild(slider);
    wrap.appendChild(label);
    controlsRoot.innerHTML = "";
    controlsRoot.appendChild(wrap);

    var playing = false;
    var rafId = 0;
    var lastTs = 0;
    var current = 0;
    var speed = 2.0; // counts per second

    function frameAt(tFloat) {
      var t = clamp(tFloat, 0, total);
      var t0 = Math.floor(t);
      var t1 = Math.min(t0 + 1, total);
      var alpha = t - t0;
      return interpolate(snapshots[t0], snapshots[t1], alpha);
    }

    function renderAt(tFloat) {
      var f = frameAt(tFloat);
      renderSvg(diagramRoot, f);
      label.textContent = "t = " + tFloat.toFixed(2).replace(/\.00$/, "") + " counts";
    }

    function stopPlaying() {
      playing = false;
      playBtn.textContent = "Play";
      if (rafId) {
        cancelAnimationFrame(rafId);
        rafId = 0;
      }
      lastTs = 0;
    }

    function tick(ts) {
      if (!playing) return;
      if (!lastTs) lastTs = ts;
      var dt = (ts - lastTs) / 1000;
      lastTs = ts;

      current = clamp(current + dt * speed, 0, total);
      slider.value = String(Math.floor(current));
      renderAt(current);

      if (current >= total) {
        stopPlaying();
        return;
      }
      rafId = requestAnimationFrame(tick);
    }

    slider.addEventListener("input", function () {
      stopPlaying();
      current = Number(slider.value || "0");
      renderAt(current);
    });

    playBtn.addEventListener("click", function () {
      if (total <= 0) return;
      if (playing) {
        stopPlaying();
        return;
      }
      playing = true;
      playBtn.textContent = "Pause";
      rafId = requestAnimationFrame(tick);
    });

    renderAt(0);
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", init);
  } else {
    init();
  }
})();
