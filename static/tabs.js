// Progressive enhancement: without this script the item page shows every tab in sequence.
(function () {
  var nav = document.querySelector("[data-tabs]");
  if (!nav) return;
  var links = Array.prototype.slice.call(nav.querySelectorAll("a[data-tab]"));
  var panels = {};
  links.forEach(function (a) {
    panels[a.dataset.tab] = document.getElementById("tab-" + a.dataset.tab);
  });
  document.documentElement.classList.add("tabs-ready");
  nav.setAttribute("role", "tablist");

  function load(panel) {
    var src = panel.dataset.src;
    if (!src || panel.dataset.loading) return;
    var body = panel.querySelector(".tab-body");
    panel.dataset.loading = "1";
    fetch(src, { headers: { "X-Requested-With": "fetch" }, credentials: "same-origin" })
      .then(function (r) {
        if (!r.ok) throw new Error(String(r.status));
        return r.text();
      })
      .then(function (html) {
        body.innerHTML = html;
        delete panel.dataset.src;
      })
      .catch(function () {
        body.textContent = "This section could not be loaded.";
      })
      .then(function () {
        delete panel.dataset.loading;
      });
  }

  // Tab switches use replaceState so they never add history entries.
  function select(key, persist) {
    if (!panels[key]) key = links[0].dataset.tab;
    links.forEach(function (a) {
      var on = a.dataset.tab === key;
      var panel = panels[a.dataset.tab];
      a.setAttribute("role", "tab");
      a.setAttribute("aria-selected", on ? "true" : "false");
      a.tabIndex = on ? 0 : -1;
      panel.setAttribute("role", "tabpanel");
      panel.hidden = !on;
    });
    load(panels[key]);
    if (persist) history.replaceState(null, "", "#tab=" + key);
  }

  function fromHash() {
    var m = /^#tab=([\w-]+)$/.exec(location.hash);
    return m ? m[1] : links[0].dataset.tab;
  }

  links.forEach(function (a, i) {
    a.addEventListener("click", function (e) {
      e.preventDefault();
      select(a.dataset.tab, true);
    });
    a.addEventListener("keydown", function (e) {
      var step = e.key === "ArrowRight" ? 1 : e.key === "ArrowLeft" ? -1 : 0;
      if (!step) return;
      var next = links[(i + step + links.length) % links.length];
      select(next.dataset.tab, true);
      next.focus();
    });
  });
  window.addEventListener("hashchange", function () {
    select(fromHash(), false);
  });
  select(fromHash(), false);
})();
