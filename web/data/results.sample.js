/* DADOS FICTICIOS DE EXEMPLO - apenas para desenvolver/testar a interface.
   NAO representam o resultado real do classificador. */
(function () {
  var classes = ["Viral vetorizada", "mRNA", "Inativada", "Subunidade proteica", "Atenuada", "Toxoide"];
  function dist(a) { var d = {}; classes.forEach(function (c, i) { d[c] = a[i]; }); return d; }
  function sum(a) { return a.reduce(function (x, y) { return x + y; }, 0); }
  function leaf(a, cls, imp) { return { feature: null, limiar: null, amostras: sum(a), impureza: imp, classe: cls, distribuicao: dist(a), esquerda: null, direita: null }; }
  function node(f, t, a, cls, imp, l, r) { return { feature: f, limiar: t, amostras: sum(a), impureza: imp, classe: cls, distribuicao: dist(a), esquerda: l, direita: r }; }
  var deep = node("temp_armazenamento", -15.0, [60, 80, 50, 40, 30, 20], "mRNA", 0.78,
    node("dose_ug", 40.0, [5, 75, 8, 4, 2, 1], "mRNA", 0.30,
      leaf([2, 70, 3, 1, 1, 0], "mRNA", 0.18),
      node("via_intramuscular", 0.5, [3, 5, 5, 3, 1, 1], "Inativada", 0.80, leaf([1, 4, 1, 2, 0, 1], "mRNA", 0.75), leaf([2, 1, 4, 1, 1, 0], "Inativada", 0.72))),
    node("n_doses", 1.5, [55, 5, 42, 36, 28, 19], "Viral vetorizada", 0.80,
      node("adjuvante", 0.5, [50, 2, 10, 6, 20, 2], "Viral vetorizada", 0.65,
        leaf([46, 1, 4, 2, 3, 1], "Viral vetorizada", 0.40),
        leaf([4, 1, 6, 4, 17, 1], "Atenuada", 0.72)),
      node("idade_min_anos", 12.0, [5, 3, 32, 30, 8, 17], "Inativada", 0.73,
        leaf([2, 1, 25, 6, 3, 2], "Inativada", 0.55),
        node("proteina_s", 0.5, [3, 2, 7, 24, 5, 15], "Subunidade proteica", 0.75,
          leaf([1, 0, 3, 20, 2, 2], "Subunidade proteica", 0.45),
          leaf([2, 2, 4, 4, 3, 13], "Toxoide", 0.70)))));
  function trunc(n, d) {
    if (n.feature === null) return n;
    if (d === 0) return leaf(classes.map(function (c) { return n.distribuicao[c]; }), n.classe, n.impureza);
    return Object.assign({}, n, { esquerda: trunc(n.esquerda, d - 1), direita: trunc(n.direita, d - 1) });
  }
  window.RESULTS_SAMPLE = {
    _amostra: true,
    meta: { n_linhas: 1200, n_treino: 900, n_teste: 300, classes: classes, meta_acuracia: 0.8, gerado_em: "EXEMPLO (dados ficticios)" },
    baseline: { acuracia_teste: 0.30, estrategia: "classe mais frequente", classe: "mRNA" },
    tentativas: [
      { id: 1, nome: "Tentativa 1", mudanca: "Arvore padrao, todas as features", features: ["a", "b", "c"], params: { max_depth: null }, cv_media: 0.71, cv_desvio: 0.03, acuracia_treino: 1.0, acuracia_teste: 0.69, escolhida: false },
      { id: 2, nome: "Tentativa 2", mudanca: "Limitar profundidade a 6", features: ["a", "b", "c"], params: { max_depth: 6 }, cv_media: 0.78, cv_desvio: 0.025, acuracia_treino: 0.9, acuracia_teste: 0.77, escolhida: false },
      { id: 3, nome: "Tentativa 3", mudanca: "Features derivadas + poda (ccp_alpha)", features: ["a", "b", "c", "d"], params: { max_depth: 8, ccp_alpha: 0.004 }, cv_media: 0.84, cv_desvio: 0.02, acuracia_treino: 0.89, acuracia_teste: 0.83, escolhida: true }
    ],
    final: {
      acuracia_teste: 0.83, acuracia_treino: 0.89, cv_media: 0.84, params: { max_depth: 8, ccp_alpha: 0.004 }, n_features: 7, n_folhas: 9, profundidade: 5,
      relatorio: classes.map(function (c, i) { return { classe: c, precisao: 0.9 - i * 0.04, recall: 0.88 - i * 0.05, f1: 0.89 - i * 0.045, suporte: 60 - i * 6 }; }),
      matriz_confusao: { classes: classes, valores: [[48, 3, 2, 1, 4, 0], [2, 52, 3, 1, 0, 0], [3, 2, 40, 5, 1, 1], [1, 1, 6, 30, 2, 2], [4, 0, 1, 2, 20, 1], [0, 1, 2, 3, 1, 14]] },
      importancias: [["temp_armazenamento", 0.31], ["n_doses", 0.22], ["dose_ug", 0.15], ["adjuvante", 0.12], ["idade_min_anos", 0.1], ["proteina_s", 0.06], ["via_intramuscular", 0.04]].map(function (x) { return { feature: x[0], valor: x[1] }; }),
      regras_texto: "EXEMPLO FICTICIO\n|--- temp_armazenamento <= -15.00\n|   |--- dose_ug <= 40.00\n|   |   |--- classe: mRNA\n|--- temp_armazenamento >  -15.00\n|   |--- n_doses <= 1.50\n|   |   |--- classe: Viral vetorizada",
      arvore: deep, arvore_truncada: false
    },
    arvore_didatica: trunc(deep, 3), acuracia_teste_didatica: 0.74,
    respostas_discussao: [
      { pergunta: "(Exemplo) Por que a profundidade importa?", resposta: "Texto ficticio de exemplo: arvores profundas tendem a decorar o treino." },
      { pergunta: "(Exemplo) Por que escolher por validacao cruzada?", resposta: "Texto ficticio de exemplo: o teste fica reservado para a avaliacao final." }
    ]
  };
})();
