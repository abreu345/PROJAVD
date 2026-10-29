(function () {
  "use strict";
  var NS = "http://www.w3.org/2000/svg";
  var R = window.RESULTS;
  var $ = function (id) { return document.getElementById(id); };
  if (!R || !R.meta) { document.body.innerHTML = "<p style='padding:2rem'>Dados indisponíveis.</p>"; return; }

  var classes = R.meta.classes || [];
  var PAL = ["#0072B2", "#E69F00", "#009E73", "#CC79A7", "#56B4E9", "#B5361C"];
  var color = function (c) { var i = classes.indexOf(c); return PAL[(i < 0 ? 0 : i) % PAL.length]; };
  var pct = function (v, d) { return (v * 100).toFixed(d == null ? 1 : d).replace(".", ",") + "%"; };
  var num = function (v) { return Number(v).toLocaleString("pt-BR"); };
  var fmt = function (v) { return String(+Number(v).toFixed(Math.abs(v) >= 100 ? 0 : 2)).replace(".", ","); };
  function esc(s) { return String(s).replace(/[&<>"]/g, function (c) { return { "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[c]; }); }
  function trunc(s, n) { s = String(s); return s.length > n ? s.slice(0, n - 1) + "…" : s; }
  function el(tag, attrs, parent, txt) {
    var e = document.createElementNS(NS, tag);
    for (var k in attrs) e.setAttribute(k, attrs[k]);
    if (txt != null) e.textContent = txt;
    if (parent) parent.appendChild(e);
    return e;
  }
  function h(tag, cls, html, parent) {
    var e = document.createElement(tag);
    if (cls) e.className = cls;
    if (html != null) e.innerHTML = html;
    if (parent) parent.appendChild(e);
    return e;
  }

  /* ---------- rótulos curtos (mapa único) ---------- */
  function cls(c) {
    var u = String(c).toUpperCase(), ped = u.indexOf("PEDI") >= 0;
    if (u.indexOf("CHADOX") >= 0 || u.indexOf("ASTRAZENECA") >= 0) return "CHADOX1 · AstraZeneca";
    if (u.indexOf("COMIRNATY") >= 0 || u.indexOf("PFIZER") >= 0) return ped ? "Pfizer pediátrica" : "Pfizer";
    if (u.indexOf("CORONAVAC") >= 0 || u.indexOf("SINOVAC") >= 0) return ped ? "Coronavac pediátrica" : "Coronavac";
    if (u.indexOf("JANSSEN") >= 0) return "Janssen";
    return titleCase(c);
  }
  var SMALL = { de: 1, da: 1, do: 1, das: 1, dos: 1, e: 1, em: 1 };
  function titleCase(s) {
    return String(s).toLowerCase().replace(/[a-zà-ú0-9]+/g, function (w, i) {
      if (/^ds$/.test(w)) return "DS";
      return i > 0 && SMALL[w] ? w : w.charAt(0).toUpperCase() + w.slice(1);
    });
  }
  var KEYS = { idade: "Idade", dose: "Dose", mes: "Mês", semana: "Semana", dia_do_ano: "Dia do ano", dia_da_semana: "Dia da semana",
    grupo: "Grupo", sexo: "Sexo", raca_cor: "Raça/cor", unidade_saude: "Unidade", distrito_sanitario: "Distrito", sistema_origem: "Sistema",
    municipio: "Município", categoria: "Categoria", faixa_etaria: "Faixa etária" };
  var GRUPOS = {
    "CRIANÇAS DE 05 A 11 ANOS": "crianças 5–11", "PÚBLICO EM GERAL (18 A 59 ANOS)": "público geral 18–59",
    "PÚBLICO EM GERAL - MENOR DE 18 ANOS": "público geral <18", "IDOSOS": "idosos"
  };
  function feat(f) {
    f = String(f);
    var i = f.indexOf("=");
    var k = i < 0 ? f : f.slice(0, i), v = i < 0 ? null : f.slice(i + 1);
    var kn = KEYS[k] || titleCase(k.replace(/_/g, " "));
    if (v == null) return kn;
    var vn = k === "grupo" && GRUPOS[v] ? GRUPOS[v] : titleCase(v.replace(/_/g, " ")).replace(/\b0(\d)\b/g, "$1").replace(/ A (\d+)/g, "–$1").replace(/\.$/, "");
    return kn + ": " + vn;
  }
  function attemptName(t) {
    var n = String(t.nome || "#" + t.id);
    if (/^baseline/i.test(n)) return "Linha de base";
    n = n.replace(/^Grid\s*\((.*)\)$/i, "Grade · $1").replace(/todas as features/i, "todas");
    n = n.replace(/\s*\([^)]*\)/g, "");
    return n;
  }
  function baseCaption(B) {
    return B.estrategia === "most_frequent" && B.classe ? "Sempre " + cls(B.classe) : "Previsão trivial";
  }

  /* tooltip */
  var tip = $("tip");
  function showTip(e, html) {
    tip.innerHTML = html; tip.hidden = false;
    var x = e.clientX + 14, y = e.clientY + 14, w = tip.offsetWidth, hh = tip.offsetHeight;
    if (x + w > innerWidth - 6) x = e.clientX - w - 14;
    if (y + hh > innerHeight - 6) y = e.clientY - hh - 14;
    tip.style.left = Math.max(4, x) + "px"; tip.style.top = Math.max(4, y) + "px";
  }
  function hideTip() { tip.hidden = true; }

  /* ---------- hero ---------- */
  var F = R.final, B = R.baseline, goal = R.meta.meta_acuracia || 0.8;
  $("hero-sub").textContent = num(R.meta.n_linhas) + " registros · " + classes.length + " classes";
  $("s-acc").textContent = pct(F.acuracia_teste);
  $("c-acc").textContent = "Teste";
  $("s-base").textContent = pct(B.acuracia_teste);
  $("c-base").textContent = baseCaption(B);
  if (B.classe) $("c-base").title = B.classe;
  $("s-goal").textContent = pct(goal, 0);
  $("c-goal").textContent = F.acuracia_teste >= goal ? "Atingida" : "Não atingida";
  (function gauge() {
    var W = 600, x0 = 2, w = W - 4;
    var s = el("svg", { viewBox: "0 0 " + W + " 40", role: "img", "aria-label": "Acurácia " + pct(F.acuracia_teste) + ", linha de base " + pct(B.acuracia_teste) + ", meta " + pct(goal, 0) }, null);
    var X = function (v) { return x0 + w * v; };
    el("rect", { x: x0, y: 6, width: w, height: 8, rx: 4, fill: "var(--track)" }, s);
    el("rect", { x: x0, y: 6, width: Math.max(2, w * F.acuracia_teste), height: 8, rx: 4, fill: "var(--accent)" }, s);
    function mark(v, label, anchor) {
      el("line", { x1: X(v), x2: X(v), y1: 2, y2: 18, stroke: "var(--ink)", "stroke-width": 1.5 }, s);
      el("text", { x: X(v), y: 33, "text-anchor": anchor, "font-size": 12, fill: "var(--muted)", "font-family": "Barlow,sans-serif" }, s, label);
    }
    mark(B.acuracia_teste, "base", "middle");
    mark(goal, "meta", "middle");
    $("gauge").appendChild(s);
  })();

  /* ---------- tentativas ---------- */
  (function () {
    var tb = $("tbl").tBodies[0];
    (R.tentativas || []).forEach(function (t) {
      var tr = h("tr", t.escolhida ? "sel" : "", null, tb);
      tr.innerHTML = '<td class="n">' + esc(t.id) + '</td><td class="nm" title="' + esc(t.nome || "") + '">' + esc(attemptName(t)) + '</td><td class="r">' + pct(t.cv_media) + '</td><td class="r">' + pct(t.acuracia_treino) + '</td><td class="r">' + pct(t.acuracia_teste) + "</td>";
    });
  })();

  /* ---------- árvore ---------- */
  var NW = 160, NH = 58, GX = 14, GY = 54;
  var svg = $("tree"), gRoot = null, view = { x: 0, y: 0, k: 1 };
  var cur = { which: "did", root: null, collapsed: new Set(), sel: null, nodes: [] };

  classes.forEach(function (c) { h("span", "", '<i style="background:' + color(c) + '"></i>' + esc(cls(c)), $("legend")).title = c; });

  function sumDist(n) { var s = 0; for (var k in n.distribuicao) s += n.distribuicao[k]; return s; }
  function isLeaf(n) { return !n.esquerda || !n.direita; }
  function isBin(n) { return n.feature && n.feature.indexOf("=") >= 0; }
  function countLeaves(n) { return isLeaf(n) ? 1 : countLeaves(n.esquerda) + countLeaves(n.direita); }
  function depthOf(n) { return isLeaf(n) ? 0 : 1 + Math.max(depthOf(n.esquerda), depthOf(n.direita)); }
  function condText(n) {
    if (!n.feature) return "";
    return isBin(n) ? feat(n.feature) + "?" : feat(n.feature) + " ≤ " + fmt(n.limiar);
  }
  function collapseFrom(root, depth) {
    var set = new Set();
    (function walk(n, d) { if (isLeaf(n)) return; if (d >= depth) set.add(n); else { walk(n.esquerda, d + 1); walk(n.direita, d + 1); } })(root, 0);
    return set;
  }

  function setTree(which) {
    cur.which = which;
    cur.root = which === "did" ? R.arvore_didatica : F.arvore;
    cur.collapsed = which === "fin" ? collapseFrom(cur.root, 3) : new Set();
    cur.sel = cur.root;
    $("t-did").classList.toggle("on", which === "did");
    $("t-fin").classList.toggle("on", which === "fin");
    $("tree-info").textContent = countLeaves(cur.root) + " folhas · prof. " + depthOf(cur.root);
    render(true);
    showDetail(cur.root);
  }

  function layout() {
    var slot = 0, nodes = [], total = cur.root.amostras || sumDist(cur.root) || 1;
    (function walk(n, d, parent, side) {
      var o = { n: n, d: d, parent: parent, side: side, id: nodes.length, kids: [] };
      nodes.push(o);
      if (!isLeaf(n) && !cur.collapsed.has(n)) {
        o.kids = [walk(n.esquerda, d + 1, o, "L"), walk(n.direita, d + 1, o, "R")];
        o.x = (o.kids[0].x + o.kids[1].x) / 2;
      } else { o.x = slot * (NW + GX); slot++; }
      o.y = d * (NH + GY);
      return o;
    })(cur.root, 0, null, null);
    cur.nodes = nodes; cur.total = total;
  }

  function render(fit) {
    layout();
    svg.innerHTML = "";
    gRoot = el("g", {}, svg);
    var gE = el("g", {}, gRoot), gN = el("g", {}, gRoot), total = cur.total;
    cur.nodes.forEach(function (o) {
      o.kids.forEach(function (k) {
        var x1 = o.x + NW / 2, y1 = o.y + NH, x2 = k.x + NW / 2, y2 = k.y, my = (y1 + y2) / 2;
        var sw = 1 + 6 * Math.sqrt((k.n.amostras || 1) / total);
        el("path", { d: "M" + x1 + " " + y1 + "C" + x1 + " " + my + " " + x2 + " " + my + " " + x2 + " " + y2, fill: "none", stroke: color(k.n.classe), "stroke-opacity": 0.5, "stroke-width": sw.toFixed(1) }, gE);
        var yes = isBin(o.n) ? k.side === "R" : k.side === "L";
        el("text", { x: (x1 + x2) / 2 + (k.side === "L" ? -4 : 4), y: my + 4, "text-anchor": k.side === "L" ? "end" : "start", "font-size": 11, "font-weight": 600, style: "fill:var(--muted);stroke:var(--card);stroke-width:3px;paint-order:stroke" }, gE, yes ? "sim" : "não");
      });
    });
    cur.nodes.forEach(function (o) {
      var n = o.n, leaf = isLeaf(n), coll = !leaf && cur.collapsed.has(n), c = color(n.classe);
      var g = el("g", { transform: "translate(" + o.x + "," + o.y + ")", "data-id": o.id, style: "cursor:pointer" }, gN);
      el("title", {}, g, (leaf ? cls(n.classe) : condText(n)) + " · " + num(n.amostras) + " amostras · " + n.classe);
      el("rect", { width: NW, height: NH, rx: 10, fill: "var(--card)" }, g);
      el("rect", { width: NW, height: NH, rx: 10, fill: c, "fill-opacity": 0.14, stroke: c, "stroke-width": 1.5, "stroke-dasharray": coll ? "4 3" : "none" }, g);
      if (cur.sel === n) el("rect", { x: -4, y: -4, width: NW + 8, height: NH + 8, rx: 13, fill: "none", stroke: "#FF6100", "stroke-width": 2.5 }, g);
      var title = leaf ? cls(n.classe) : condText(n);
      el("text", { x: NW / 2, y: 20, "text-anchor": "middle", "font-size": 13, "font-weight": 600 }, g, trunc(title, 23));
      var sub = coll ? "+" + countLeaves(n) + " folhas · n=" + num(n.amostras) : leaf ? "n=" + num(n.amostras) : "n=" + num(n.amostras) + " · " + trunc(cls(n.classe), 14);
      el("text", { x: NW / 2, y: 36, "text-anchor": "middle", "font-size": 11, style: "fill:var(--muted)" }, g, sub);
      var bx = 10, bw = NW - 20, tot = sumDist(n) || 1, xx = bx;
      el("clipPath", { id: "cp" + o.id }, g).appendChild(el("rect", { x: bx, y: 44, width: bw, height: 6, rx: 3 }));
      var gb = el("g", { "clip-path": "url(#cp" + o.id + ")" }, g);
      classes.forEach(function (cl) {
        var v = n.distribuicao[cl] || 0; if (!v) return;
        var wv = bw * v / tot; el("rect", { x: xx, y: 44, width: Math.max(wv - 1, 0.5), height: 6, fill: color(cl) }, gb); xx += wv;
      });
    });
    if (fit) fitView(); else applyView();
  }

  function applyView() { gRoot.setAttribute("transform", "translate(" + view.x + "," + view.y + ") scale(" + view.k + ")"); }
  function fitView() {
    var minx = Infinity, maxx = -Infinity, maxy = 0;
    cur.nodes.forEach(function (o) { minx = Math.min(minx, o.x); maxx = Math.max(maxx, o.x + NW); maxy = Math.max(maxy, o.y + NH); });
    var r = svg.getBoundingClientRect(), pad = 20, w = maxx - minx, hh = maxy;
    var k = Math.min((r.width - 2 * pad) / w, (r.height - 2 * pad) / hh, 1.2);
    k = Math.max(k, 0.6);
    view.k = k;
    view.x = w * k <= r.width - 2 * pad ? (r.width - w * k) / 2 - minx * k : r.width / 2 - (cur.nodes[0].x + NW / 2) * k;
    view.y = Math.max(pad, (r.height - hh * k) / 2);
    applyView();
  }

  function showDetail(n) {
    var d = $("detail"), leaf = isLeaf(n);
    var head = leaf ? "Folha" : condText(n);
    d.innerHTML = "<b>" + esc(head) + "</b><span>" + num(n.amostras) + " amostras</span><span title=\"" + esc(n.classe) + "\"><i class=\"dot\" style=\"background:" + color(n.classe) + "\"></i>" + esc(cls(n.classe)) + "</span>";
    if (!leaf) {
      var b = h("button", "", cur.collapsed.has(n) ? "Expandir" : "Recolher", d);
      b.onclick = function () { toggle(n); };
    }
  }
  function toggle(n) {
    if (isLeaf(n)) return;
    if (cur.collapsed.has(n)) cur.collapsed.delete(n); else cur.collapsed.add(n);
    cur.sel = n; render(false); showDetail(n);
  }

  /* pan / zoom / click */
  (function () {
    var drag = null;
    svg.addEventListener("pointerdown", function (e) {
      drag = { x: e.clientX, y: e.clientY, vx: view.x, vy: view.y, moved: false, t: e.target.closest("[data-id]") };
      svg.setPointerCapture(e.pointerId);
    });
    svg.addEventListener("pointermove", function (e) {
      if (!drag) return;
      var dx = e.clientX - drag.x, dy = e.clientY - drag.y;
      if (Math.abs(dx) + Math.abs(dy) > 4) { drag.moved = true; svg.classList.add("drag"); }
      if (drag.moved) { view.x = drag.vx + dx; view.y = drag.vy + dy; applyView(); }
    });
    svg.addEventListener("pointerup", function (e) {
      var t = drag && !drag.moved && drag.t;
      if (!t && drag && !drag.moved) { var u = document.elementFromPoint(e.clientX, e.clientY); t = u && u.closest && u.closest("#tree [data-id]"); }
      if (t) { var o = cur.nodes[+t.getAttribute("data-id")]; if (o) { cur.sel = o.n; render(false); showDetail(o.n); } }
      drag = null; svg.classList.remove("drag");
    });
    svg.addEventListener("pointercancel", function () { drag = null; svg.classList.remove("drag"); });
    svg.addEventListener("dblclick", function (e) {
      var t = e.target.closest("[data-id]"); if (t) toggle(cur.nodes[+t.getAttribute("data-id")].n);
    });
    svg.addEventListener("wheel", function (e) {
      if (!e.ctrlKey && !e.metaKey) return;
      e.preventDefault();
      var r = svg.getBoundingClientRect(), mx = e.clientX - r.left, my = e.clientY - r.top;
      var f = Math.exp(-e.deltaY * 0.0015), nk = Math.min(3, Math.max(0.15, view.k * f)); f = nk / view.k;
      view.x = mx - (mx - view.x) * f; view.y = my - (my - view.y) * f; view.k = nk; applyView();
    }, { passive: false });
    window.addEventListener("resize", function () { if (cur.root) fitView(); });
  })();
  $("t-did").onclick = function () { setTree("did"); };
  $("t-fin").onclick = function () { setTree("fin"); };
  $("b-fit").onclick = fitView;
  $("b-exp").onclick = function () { cur.collapsed = new Set(); render(true); };
  $("b-col").onclick = function () { cur.collapsed = collapseFrom(cur.root, 2); render(true); };
  if (!R.arvore_didatica) $("t-did").hidden = true;
  setTree(R.arvore_didatica ? "did" : "fin");

  /* ---------- matriz de confusão ---------- */
  var mode = "abs";
  function heat() {
    var M = F.matriz_confusao, cl = M.classes || classes, V = M.valores, n = cl.length;
    var cell = 70, L = 140, T = 112, W = L + cell * n + 90, H = T + cell * n + 8;
    var s = $("heat"); s.innerHTML = ""; s.setAttribute("viewBox", "0 0 " + W + " " + H); s.style.width = W + "px"; s.style.height = H + "px";
    var dark = matchMedia("(prefers-color-scheme: dark)").matches;
    var rowSum = V.map(function (r) { return r.reduce(function (a, b) { return a + b; }, 0) || 1; });
    var max = 0; V.forEach(function (r) { r.forEach(function (v) { max = Math.max(max, v); }); });
    el("text", { x: L, y: 14, "font-size": 12, style: "fill:var(--muted)" }, s, "Previsto");
    el("text", { x: 0, y: T - 8, "font-size": 12, style: "fill:var(--muted)" }, s, "Real");
    cl.forEach(function (c, i) {
      var cx = L + i * cell + cell / 2;
      var t = el("text", { x: cx, y: T - 8, "font-size": 12, style: "fill:var(--ink)", transform: "rotate(-35 " + cx + " " + (T - 8) + ")" }, s, cls(c));
      el("title", {}, t, c);
      el("rect", { x: L - 10, y: T + i * cell + cell / 2 - 5, width: 10, height: 10, rx: 3, fill: color(c) }, s);
      var tr = el("text", { x: L - 16, y: T + i * cell + cell / 2 + 4, "text-anchor": "end", "font-size": 12, style: "fill:var(--ink)" }, s, cls(c));
      el("title", {}, tr, c);
    });
    V.forEach(function (row, i) {
      row.forEach(function (v, j) {
        var frac = mode === "abs" ? v / (max || 1) : v / rowSum[i];
        var g = el("g", {}, s), a = 0.06 + 0.94 * frac;
        el("rect", { x: L + j * cell + 1, y: T + i * cell + 1, width: cell - 2, height: cell - 2, rx: 6, fill: "#FF6100", "fill-opacity": a.toFixed(3), stroke: i === j ? "var(--ink)" : "var(--line)", "stroke-width": i === j ? 1.5 : 1 }, g);
        el("text", { x: L + j * cell + cell / 2, y: T + i * cell + cell / 2 + 5, "text-anchor": "middle", "font-size": 14, "font-weight": 600, fill: a > 0.55 ? "#1a1a1a" : (dark ? "#F4EDE3" : "#232323") }, g, mode === "abs" ? num(v) : pct(v / rowSum[i], 0));
        var r = el("rect", { x: L + j * cell, y: T + i * cell, width: cell, height: cell, fill: "transparent" }, g);
        r.addEventListener("pointermove", function (e) { showTip(e, "<b>Real:</b> " + esc(cl[i]) + "<br><b>Previsto:</b> " + esc(cl[j]) + "<br>" + num(v) + " (" + pct(v / rowSum[i]) + " da linha)"); });
        r.addEventListener("pointerleave", hideTip);
      });
    });
  }
  $("m-abs").onclick = function () { mode = "abs"; $("m-abs").classList.add("on"); $("m-row").classList.remove("on"); heat(); };
  $("m-row").onclick = function () { mode = "row"; $("m-row").classList.add("on"); $("m-abs").classList.remove("on"); heat(); };
  heat();

  /* ---------- por classe ---------- */
  (function () {
    var tb = $("mt").tBodies[0];
    (F.relatorio || []).forEach(function (r) {
      var tr = h("tr", "", '<td title="' + esc(r.classe) + " · suporte " + num(r.suporte) + '"><i class="dot" style="background:' + color(r.classe) + '"></i>' + esc(cls(r.classe)) + '</td><td class="r">' + pct(r.precisao, 0) + '</td><td class="r">' + pct(r.recall, 0) + '</td><td class="r f1">' + pct(r.f1, 0) + "</td>", tb);
    });
  })();

  /* ---------- importâncias ---------- */
  (function () {
    var arr = (F.importancias || []).slice().sort(function (a, b) { return b.valor - a.valor; }).slice(0, 10);
    var mx = arr.length ? arr[0].valor || 1 : 1;
    arr.forEach(function (it) {
      h("div", "imp", '<div class="n" title="' + esc(feat(it.feature)) + '">' + esc(feat(it.feature)) + '</div><div class="tr"><div class="f" style="width:' + it.valor / mx * 100 + '%"></div></div><div class="p">' + pct(it.valor, 1) + "</div>", $("imps"));
    });
  })();

  /* ---------- regras e discussão ---------- */
  $("regras-txt").textContent = F.regras_texto || "";
  (R.respostas_discussao || []).forEach(function (q) {
    h("details", "", "<summary>" + esc(q.pergunta) + "</summary>" + (q.resumo ? "<p class=\"rs\">" + esc(q.resumo) + "</p>" : "") + "<p>" + esc(q.resposta) + "</p>", $("qa"));
  });
  matchMedia("(prefers-color-scheme: dark)").addEventListener("change", heat);
})();
