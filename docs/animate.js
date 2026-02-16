(function () {
  "use strict";

  function deepClone(obj) {
    return JSON.parse(JSON.stringify(obj || {}));
  }

  function asCount(beats) {
    var n = Number(beats);
    if (!Number.isFinite(n) || n <= 0) return 0;
    return Math.round(n);
  }

  function rotateForward(arr, delta) {
    if (!Array.isArray(arr) || !arr.length) return arr;
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

  function allOrderLists(state) {
    var lists = [];
    if (Array.isArray(state.circleOrder) && state.circleOrder.length) lists.push(state.circleOrder);

    var lineOrders = state.lineOrders || {};
    Object.keys(lineOrders).forEach(function (id) {
      if (Array.isArray(lineOrders[id])) lists.push(lineOrders[id]);
    });

    var twoOrders = state.twoLinesOrders || {};
    Object.keys(twoOrders).forEach(function (id) {
      if (Array.isArray(twoOrders[id])) lists.push(twoOrders[id]);
    });

    return lists;
  }

  function applyEvent(state, event) {
    var kind = String(event.kind || "").toLowerCase();

    if (kind === "swapplaces") {
      var a = String(event.a || "");
      var b = String(event.b || "");
      if (!a || !b) return;

      var orders = allOrderLists(state);
      for (var i = 0; i < orders.length; i++) {
        if (swapInOrder(orders[i], a, b)) return;
      }
      return;
    }

    if (kind === "progress") {
      var delta = parseInt(String(event.delta || "0"), 10);
      if (!Number.isFinite(delta)) delta = 0;
      var lineOrders = state.lineOrders || {};
      Object.keys(lineOrders).forEach(function (id) {
        lineOrders[id] = rotateForward(lineOrders[id], delta);
      });
      return;
    }

    if (kind === "approach") {
      state.twoLinesSeparation = Number(state.twoLinesSeparation || 0) - 1;
      return;
    }

    if (kind === "retreat") {
      state.twoLinesSeparation = Number(state.twoLinesSeparation || 0) + 1;
    }
  }

  function buildEvents(payload) {
    var figures = Array.isArray(payload && payload.figures) ? payload.figures : [];
    var events = [];
    var t = 0;

    figures.forEach(function (fig) {
      var steps = Array.isArray(fig && fig.steps) ? fig.steps : [];
      steps.forEach(function (step) {
        t += asCount(step && step.beats);
        var primitives = Array.isArray(step && step.primitives) ? step.primitives : [];
        primitives.forEach(function (p) {
          events.push({
            t: t,
            kind: p.kind || "",
            a: p.a || "",
            b: p.b || "",
            delta: p.delta || ""
          });
        });
      });
    });

    return { events: events, totalCounts: t };
  }

  function stateAt(baseState, events, t) {
    var state = deepClone(baseState);
    for (var i = 0; i < events.length; i++) {
      if (events[i].t <= t) applyEvent(state, events[i]);
      else break;
    }
    return state;
  }

  async function init() {
    var controlsRoot = document.getElementById("fdml-anim-controls");
    var diagramRoot = document.getElementById("fdml-diagram");
    if (!controlsRoot || !diagramRoot) return;

    var fetchPayload = window.fdmlFetchCardPayload;
    var buildState = window.fdmlBuildDiagramState;
    var renderDiagram = window.fdmlRenderDiagram;
    if (typeof fetchPayload !== "function" || typeof buildState !== "function" || typeof renderDiagram !== "function") {
      return;
    }

    var payload = await fetchPayload();
    if (!payload || !payload.meta || !payload.meta.formationKind) return;
    var formationKind = String(payload.meta.formationKind || "");
    if (formationKind === "line" || formationKind === "twoLinesFacing") return;

    var baseState = buildState(payload);
    var timeline = buildEvents(payload);
    var events = timeline.events;
    var max = Math.max(0, timeline.totalCounts);

    var wrap = document.createElement("div");
    wrap.className = "anim-controls";

    var button = document.createElement("button");
    button.className = "anim-btn";
    button.type = "button";
    button.textContent = "Play";

    var slider = document.createElement("input");
    slider.type = "range";
    slider.id = "fdml-scrub";
    slider.min = "0";
    slider.max = String(max);
    slider.step = "1";
    slider.value = "0";

    var label = document.createElement("span");
    label.className = "anim-time";

    wrap.appendChild(button);
    wrap.appendChild(slider);
    wrap.appendChild(label);
    controlsRoot.innerHTML = "";
    controlsRoot.appendChild(wrap);

    var timer = null;

    function setPlaying(playing) {
      if (playing) {
        button.textContent = "Pause";
        return;
      }
      button.textContent = "Play";
      if (timer) {
        clearInterval(timer);
        timer = null;
      }
    }

    function renderCurrent() {
      var t = parseInt(slider.value, 10) || 0;
      label.textContent = "t = " + String(t) + " counts";
      var state = stateAt(baseState, events, t);
      renderDiagram(diagramRoot, payload, state);
    }

    slider.addEventListener("input", function () {
      renderCurrent();
    });

    button.addEventListener("click", function () {
      if (max <= 0) return;
      if (timer) {
        setPlaying(false);
        return;
      }
      setPlaying(true);
      timer = setInterval(function () {
        var v = parseInt(slider.value, 10) || 0;
        if (v >= max) {
          setPlaying(false);
          return;
        }
        slider.value = String(v + 1);
        renderCurrent();
      }, 350);
    });

    renderCurrent();
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", init);
  } else {
    init();
  }
})();
