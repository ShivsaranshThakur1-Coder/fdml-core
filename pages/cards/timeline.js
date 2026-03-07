(function () {
  "use strict";

  function stemFromPathname(pathname) {
    var raw = pathname.split("/").pop() || "";
    if (!raw || !raw.toLowerCase().endsWith(".html")) return "";
    return decodeURIComponent(raw.slice(0, -5));
  }

  function asNumber(value) {
    var n = Number(value);
    return Number.isFinite(n) && n > 0 ? n : 1;
  }

  function tooltipForStep(step) {
    var action = step.action || "step";
    var beats = step.beats || "";
    var count = step.count || "";
    return count ? action + " - " + beats + " beats - count " + count : action + " - " + beats + " beats";
  }

  function renderTimeline(root, payload) {
    var figures = Array.isArray(payload && payload.figures) ? payload.figures : [];
    if (!figures.length) {
      root.innerHTML = '<p class="sub">Timeline unavailable (no figures).</p>';
      return;
    }

    var title = document.createElement("h2");
    title.textContent = "Timeline";
    root.appendChild(title);

    figures.forEach(function (figure, figureIdx) {
      var wrap = document.createElement("section");
      wrap.className = "timeline-figure";

      var heading = document.createElement("h3");
      heading.className = "timeline-figure-title";
      var figName = (figure && figure.name) || "";
      var figId = (figure && figure.id) || "";
      heading.textContent = figName || figId || ("Figure " + String(figureIdx + 1));
      wrap.appendChild(heading);

      var rail = document.createElement("div");
      rail.className = "timeline-rail";

      var steps = Array.isArray(figure && figure.steps) ? figure.steps : [];
      steps.forEach(function (step) {
        var seg = document.createElement("div");
        seg.className = "timeline-seg";
        seg.style.flexGrow = String(asNumber(step && step.beats));
        var tip = tooltipForStep(step || {});
        seg.setAttribute("title", tip);
        seg.setAttribute("data-tip", tip);

        var label = document.createElement("span");
        label.className = "timeline-seg-label";
        label.textContent = (step && step.action) || "step";
        seg.appendChild(label);

        rail.appendChild(seg);
      });

      wrap.appendChild(rail);
      root.appendChild(wrap);
    });
  }

  async function init() {
    var root = document.getElementById("fdml-timeline");
    if (!root) return;

    var stem = stemFromPathname(window.location.pathname || "");
    if (!stem) return;

    try {
      var res = await fetch(stem + ".json", { cache: "no-store" });
      if (!res.ok) throw new Error("HTTP " + String(res.status));
      var data = await res.json();
      var payload = Array.isArray(data) ? data[0] : data;
      renderTimeline(root, payload || {});
    } catch (_err) {
      root.innerHTML = '<p class="sub">Timeline unavailable (missing JSON artifact).</p>';
    }
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", init);
  } else {
    init();
  }
})();
