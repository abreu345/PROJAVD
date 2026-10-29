(function () {
  var tip = document.getElementById("tip"), cur = null;
  function show(b) {
    tip.textContent = b.getAttribute("data-info"); tip.hidden = false; cur = b;
    var r = b.getBoundingClientRect(), w = tip.offsetWidth, h = tip.offsetHeight;
    var x = Math.min(Math.max(8, r.left + r.width / 2 - w / 2), innerWidth - w - 8);
    var y = r.bottom + 8; if (y + h > innerHeight - 8) y = r.top - h - 8;
    tip.style.left = x + "px"; tip.style.top = Math.max(8, y) + "px";
  }
  function hide() { tip.hidden = true; cur = null; }
  document.addEventListener("mouseover", function (e) { var b = e.target.closest(".info"); if (b) show(b); });
  document.addEventListener("mouseout", function (e) { if (e.target.closest(".info")) hide(); });
  document.addEventListener("focusin", function (e) { var b = e.target.closest(".info"); if (b) show(b); });
  document.addEventListener("focusout", hide);
  document.addEventListener("click", function (e) {
    var b = e.target.closest(".info");
    if (b) { cur === b && !tip.hidden ? hide() : show(b); } else hide();
  });
  window.addEventListener("scroll", hide, { passive: true });
})();
