/* Warm Precision motion: vanilla, tiny, honest. Static ships complete;
   this script only adds arrival. Values come from data attributes authored
   from evidence — the script never invents a number. */
(function () {
  "use strict";
  var reduce = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
  if (reduce) return; // finished static composition stands as-is
  document.documentElement.classList.add("wp-motion");

  /* Arrival: anything marked draws/fades/rises once it enters view. */
  var arrived = new IntersectionObserver(function (entries) {
    entries.forEach(function (e) {
      if (e.isIntersecting) { e.target.classList.add("wp-on"); arrived.unobserve(e.target); }
    });
  }, { threshold: 0.3 });
  document.querySelectorAll("[data-draw],[data-fade],[data-rise]").forEach(function (el) {
    arrived.observe(el);
  });

  /* Tick-to-value: counts to the exact registered decimal, lands exactly. */
  function tick(el) {
    var to = parseFloat(el.getAttribute("data-tick"));
    var decimals = parseInt(el.getAttribute("data-decimals") || "1", 10);
    var dur = parseInt(el.getAttribute("data-duration") || "900", 10);
    var prefix = el.getAttribute("data-prefix") || "";
    var suffix = el.getAttribute("data-suffix") || "";
    var start = null;
    function frame(now) {
      if (!start) start = now;
      var t = Math.min((now - start) / dur, 1);
      var eased = 1 - Math.pow(1 - t, 3); // easeOutCubic, matches CSS ease-out
      var value = t >= 1 ? to : to * eased; // exact landing, never overshoot
      el.textContent = prefix + value.toFixed(decimals).replace("-", "−") + suffix;
      if (t < 1) requestAnimationFrame(frame);
    }
    requestAnimationFrame(frame);
  }
  var ticked = new IntersectionObserver(function (entries) {
    entries.forEach(function (e) {
      if (e.isIntersecting) { tick(e.target); ticked.unobserve(e.target); }
    });
  }, { threshold: 0.5 });
  document.querySelectorAll("[data-tick]").forEach(function (el) {
    ticked.observe(el);
  });

  /* Scrub-between-states: geometry interpolates, readout stays registered. */
  document.querySelectorAll("[data-scrub]").forEach(function (control) {
    var target = document.getElementById(control.getAttribute("data-scrub"));
    if (!target) return;
    var states = JSON.parse(target.getAttribute("data-states"));
    var readout = document.getElementById(control.getAttribute("data-readout"));
    function land(i) {
      var s = states[i];
      Object.keys(s.geom).forEach(function (key) {
        var node = target.querySelector("[data-geom='" + key + "']");
        if (node) node.setAttribute("d", s.geom[key]);
      });
      Object.keys(s.text || {}).forEach(function (key) {
        var node = target.querySelector("[data-text='" + key + "']");
        if (node) node.textContent = s.text[key];
      });
      if (readout) readout.textContent = s.label;
      control.setAttribute("aria-valuetext", s.label);
    }
    control.addEventListener("change", function () { land(control.value); });
    land(control.value); // settle on the authored default
  });
})();
