(function () {
  var menu = document.querySelector(".header-menu");
  if (!menu) return;
  var mobile = window.matchMedia("(max-width: 900px)");

  function updateMenu() {
    menu.open = !mobile.matches;
  }

  updateMenu();
  mobile.addEventListener("change", updateMenu);

  document.addEventListener("keydown", function (event) {
    if (!mobile.matches || event.key !== "Escape" || !menu.open) return;
    menu.open = false;
    menu.querySelector("summary").focus();
  });

  document.addEventListener("click", function (event) {
    if (mobile.matches && menu.open && !menu.contains(event.target)) menu.open = false;
  });
})();
