import json
import os
from datetime import datetime
import pandas as pd
from sklearn.dummy import DummyClassifier
from sklearn.tree import DecisionTreeClassifier, export_text
from sklearn.metrics import accuracy_score, precision_recall_fscore_support
from src.model import Classificador, Features, SEMENTE, serializar_arvore


class Relatorio:
    """Monta o results.json/results.js (consumido pelo frontend) e imprime a tabela de tentativas."""

    def __init__(self, clf, exp):
        self.clf = clf
        self.exp = exp

    def _numeros(self, o):
        if isinstance(o, dict):
            return {k: self._numeros(v) for k, v in o.items()}
        if isinstance(o, (list, tuple)):
            return [self._numeros(v) for v in o]
        if hasattr(o, "item"):
            return o.item()
        return o

    def _arvore(self, modelo, nomes, classes):
        arv = serializar_arvore(modelo, nomes, classes)
        n_nos = modelo.tree_.node_count
        trunc = False
        if n_nos > 300:
            arv = serializar_arvore(modelo, nomes, classes, profundidade_max=6)
            trunc = True
        return arv, trunc

    def experimentos_extras(self, melhor):
        """Medições só para a discussão (nada disso vira modelo final)."""
        c, g = self.clf, melhor["grupos"]
        ext = {}
        # overfitting: sem limite de profundidade
        m = DecisionTreeClassifier(random_state=SEMENTE).fit(c.xy(g)[0], c.y_treino)
        tr, te = c.avaliar(m, g)
        ext["sem_limite"] = {"treino": tr, "teste": te, "profundidade": int(m.get_depth()), "folhas": int(m.get_n_leaves())}
        # vazamento: lote (só para medir)
        cl = Classificador(extras={"lote": None})
        cl.dividir(*cl.preparar(c.df))
        gl = g + ["lote"]
        ml = DecisionTreeClassifier(random_state=SEMENTE, **melhor["params"]).fit(cl.xy(gl)[0], cl.y_treino)
        ext["lote"] = {"teste": cl.avaliar(ml, gl)[1], "treino": cl.avaliar(ml, gl)[0]}
        # mês vs dia do ano com a mesma árvore (depth da melhor)
        for nome, trocar in (("mes", "dia_do_ano"), ("dia_do_ano", "mes")):
            if trocar in g:
                g2 = [x if x != trocar else nome for x in g]
                m2, cvm, _ = c.treinar(g2, melhor["params"])
                ext["data_" + nome] = {"cv": cvm, "teste": c.avaliar(m2, g2)[1]}
        # sem perfil (ablation)
        g3 = [x for x in g if x not in Experimentos_PERFIL]
        m3, cvm, _ = c.treinar(g3, melhor["params"])
        ext["sem_perfil"] = {"cv": cvm, "teste": c.avaliar(m3, g3)[1]}
        # ablação por grupo
        abl = {}
        for gr in g:
            g4 = [x for x in g if x != gr]
            m4, cvm, _ = c.treinar(g4, melhor["params"])
            abl[gr] = cvm
        ext["ablacao_cv"] = abl
        print(f"[relatorio] extras: {json.dumps(self._numeros(ext), ensure_ascii=False)}")
        return ext

    def montar(self, base, melhor, modelo, classes, cm, imp):
        c = self.clf
        nomes = list(c.Xtr_final.columns)
        tr, te = c.avaliar(modelo, melhor["grupos"])
        prec, rec, f1, sup = precision_recall_fscore_support(c.y_teste, c.pred, labels=classes, zero_division=0)
        arv, trunc = self._arvore(modelo, nomes, classes)
        # árvore didática simples: max_depth=3, mesmas features
        did = DecisionTreeClassifier(random_state=SEMENTE, max_depth=3).fit(c.Xtr_final, c.y_treino)
        arv_did, _ = self._arvore(did, nomes, classes)
        acc_did = float(accuracy_score(c.y_teste, did.predict(c.Xte_final)))
        ext = self.experimentos_extras(melhor)
        final = {"acuracia_teste": te, "acuracia_treino": tr, "cv_media": melhor["cv_media"],
                 "params": melhor["params"], "n_features": len(nomes),
                 "n_folhas": int(modelo.get_n_leaves()), "profundidade": int(modelo.get_depth()),
                 "relatorio": [{"classe": k, "precisao": float(p), "recall": float(r), "f1": float(f), "suporte": int(s)}
                               for k, p, r, f, s in zip(classes, prec, rec, f1, sup)],
                 "matriz_confusao": {"classes": classes, "valores": cm.tolist()},
                 "importancias": [{"feature": k, "valor": float(v)} for k, v in imp.head(15).items()],
                 "regras_texto": export_text(modelo, feature_names=nomes, max_depth=4),
                 "arvore": arv}
        if trunc:
            final["arvore_truncada"] = True
        tentativas = [{k: v for k, v in t.items() if k != "grupos"} for t in self.exp.tentativas]
        r = {"meta": {"n_linhas": len(c.df), "n_treino": len(c.y_treino), "n_teste": len(c.y_teste),
                      "classes": classes, "meta_acuracia": 0.8, "gerado_em": datetime.now().isoformat()},
             "baseline": base, "tentativas": tentativas, "final": final,
             "arvore_didatica": arv_did, "acuracia_teste_didatica": acc_did,
             "respostas_discussao": self.respostas(base, melhor, final, ext, cm, classes)}
        return self._numeros(r)

    def respostas(self, base, melhor, final, ext, cm, classes):
        pc = lambda x: f"{100 * x:.1f}%"
        # maiores confusões fora da diagonal
        pares = sorted(((int(cm[i][j]), classes[i], classes[j]) for i in range(len(classes))
                        for j in range(len(classes)) if i != j), reverse=True)[:2]
        conf = "; ".join(f"{n} casos de '{a}' previstos como '{b}'" for n, a, b in pares)
        t = {x["id"]: x for x in self.exp.tentativas}
        aula, data_ = t[2], t[4]
        rec_min = min(final["relatorio"], key=lambda x: x["recall"])
        mes_cv = ext.get("data_mes", {}).get("cv")
        dia_cv = ext.get("data_dia_do_ano", {}).get("cv")
        ab = ext["ablacao_cv"]
        queda = sorted(((melhor["cv_media"] - v, k) for k, v in ab.items()), reverse=True)
        ajudaram = ", ".join(f"{k} (-{100 * q:.1f} pp na CV se removida)" for q, k in queda[:4])
        sl = ext["sem_limite"]
        return [
            {"pergunta": "Por que o lote é vazamento de dados?",
             "resposta": f"O lote identifica o frasco de uma vacina específica: cada lote pertence a um único fabricante, então a coluna entrega o rótulo quase diretamente. Só para medir (fora do modelo final), uma árvore com lote chegou a {pc(ext['lote']['teste'])} no teste, contra {pc(final['acuracia_teste'])} sem ele. Na prática o lote só existe depois que a vacina já foi escolhida, então não estaria disponível para prever."},
            {"pergunta": "O mês é uma boa representação da data?",
             "resposta": f"É razoável, mas não a melhor. Com a árvore rasa da aula (profundidade 4), trocar mês por dia do ano (dias desde 01/01/2022) mudou a CV de {pc(t[3]['cv_media'])} para {pc(data_['cv_media'])}: o mês só dá 12 cortes grosseiros, enquanto o dia do ano permite cortes finos como 'depois do dia X', já que cada vacina/público entrou em campanha em momentos distintos de 2022. Na árvore final (mais profunda) a diferença encolhe: CV de {pc(mes_cv) if mes_cv else 'n/d'} com mês contra {pc(dia_cv) if dia_cv else 'n/d'} com dia do ano, porque uma árvore profunda recompõe a data com vários cortes."},
            {"pergunta": "Quais colunas mais ajudaram?",
             "resposta": f"Pela ablação (remover cada grupo e medir a CV no treino): {ajudaram}. As importâncias da árvore final lideram com {', '.join(i['feature'] for i in final['importancias'][:3])}. Idade e dose separam o público pediátrico dos adultos; a data separa campanhas; grupo/categoria descrevem o perfil da pessoa vacinada (público-alvo), informação conhecida antes da escolha da vacina, por isso não são vazamento. Sem o bloco de perfil a CV fica em {pc(ext['sem_perfil']['cv'])}."},
            {"pergunta": "Onde a matriz de confusão mostra confusão?",
             "resposta": f"As maiores confusões no teste: {conf}. A classe com pior recall é '{rec_min['classe']}' ({pc(rec_min['recall'])}). As variantes do mesmo fabricante (adulto vs pediátrica) e vacinas aplicadas ao mesmo público e período se misturam, porque as features descrevem a pessoa e a data, não o frasco."},
            {"pergunta": "A acurácia sozinha engana?",
             "resposta": f"Sim. O dummy que sempre prevê '{base['classe']}' já acerta {pc(base['acuracia_teste'])} só pelo desbalanceamento das classes. A acurácia final de {pc(final['acuracia_teste'])} deve ser lida em relação a essa linha de base e junto de precisão/recall por classe: classes menores podem ter recall baixo e o total esconder isso."},
            {"pergunta": "O que é overfitting aqui?",
             "resposta": f"Com profundidade=None a árvore chega a {sl['folhas']} folhas (profundidade {sl['profundidade']}) e acerta {pc(sl['treino'])} no treino, mas {pc(sl['teste'])} no teste: decorou o treino. Os hiperparâmetros do modelo final (escolhidos por validação cruzada só no treino) deixaram treino em {pc(final['acuracia_treino'])} e teste em {pc(final['acuracia_teste'])}, uma diferença bem menor."},
            {"pergunta": "A meta de 80% foi atingida e como a escolha foi feita?",
             "resposta": f"Acurácia no teste: {pc(final['acuracia_teste'])} (meta 80%). A tentativa foi escolhida pela maior média de CV (5-fold estratificado) no conjunto de treino; o teste foi apenas reportado, nunca usado para tunar. Sem usar lote."},
        ]

    def salvar(self, resultado, pasta):
        os.makedirs(pasta, exist_ok=True)
        js = json.dumps(resultado, ensure_ascii=False, indent=1)
        with open(os.path.join(pasta, "results.json"), "w", encoding="utf-8") as f:
            f.write(js)
        with open(os.path.join(pasta, "results.js"), "w", encoding="utf-8") as f:
            f.write(f"window.RESULTS = {js};\n")
        print(f"[relatorio] salvo em {pasta}/results.json e results.js")

    def imprimir_tabela(self):
        print("\n=== TABELA DE TENTATIVAS (escolha pela CV no treino; teste apenas reportado) ===")
        print(f"{'#':>2} {'nome':<34} {'CV media+-dp':>15} {'treino':>7} {'teste':>7} esc")
        for t in self.exp.tentativas:
            print(f"{t['id']:>2} {t['nome']:<34} {t['cv_media']:.4f}+-{t['cv_desvio']:.4f} "
                  f"{t['acuracia_treino']:.4f} {t['acuracia_teste']:.4f}  {'*' if t['escolhida'] else ''}")
            print(f"     mudanca: {t['mudanca']} | params: {t['params']} | {len(t['features'])} features")


from src.model import Experimentos
Experimentos_PERFIL = Experimentos.PERFIL
