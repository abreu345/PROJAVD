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
        pc = lambda x: f"{100 * x:.1f}%".replace(".", ",")
        pp = lambda x: f"{100 * x:.1f}".replace(".", ",")
        # maiores confusões fora da diagonal
        pares = sorted(((int(cm[i][j]), classes[i], classes[j]) for i in range(len(classes))
                        for j in range(len(classes)) if i != j), reverse=True)[:2]
        conf = "; ".join(f"{n} casos de '{a}' previstos como '{b}'" for n, a, b in pares)
        t = {x["id"]: x for x in self.exp.tentativas}
        data_ = t[4]
        rec = sorted(final["relatorio"], key=lambda x: x["recall"])
        mes_cv = ext.get("data_mes", {}).get("cv")
        dia_cv = ext.get("data_dia_do_ano", {}).get("cv")
        ab = ext["ablacao_cv"]
        queda = sorted(((melhor["cv_media"] - v, k) for k, v in ab.items()), reverse=True)
        ajudaram = ", ".join(f"{k} (−{pp(q)} p.p.)" for q, k in queda[:3])
        sl = ext["sem_limite"]
        ganho_lote = ext["lote"]["teste"] - final["acuracia_teste"]
        lider = ", ".join(f"{i['feature']} ({pc(i['valor'])})" for i in final["importancias"][:3])
        return [
            {"pergunta": "Por que o lote é vazamento de dados?",
             "resumo": "Porque o lote já contém a resposta que queremos prever.",
             "resposta": f"Cada lote pertence a um único fabricante, então saber o lote é quase saber a vacina. Para medir isso (fora do modelo final), treinamos uma árvore com a coluna lote: ela chegou a {pc(ext['lote']['teste'])} no teste, contra {pc(final['acuracia_teste'])} sem ela. Esses {pp(ganho_lote)} pontos percentuais a mais não vêm de aprender padrões, vêm de ver o gabarito. Além disso, na vida real o lote só é conhecido depois que a vacina já foi escolhida e aplicada, então o modelo não poderia usá-lo para prever. Por isso a atividade o proíbe e o resultado honesto é o de {pc(final['acuracia_teste'])}."},
            {"pergunta": "O mês é uma boa representação da data?",
             "resumo": "Não é a melhor: o dia do ano é mais preciso, mas numa árvore profunda a diferença é pequena.",
             "resposta": f"O mês só permite 12 cortes grosseiros. O dia do ano (dias desde 01/01/2022) permite cortes finos como 'depois do dia X', e isso importa porque cada vacina e cada público entraram na campanha em momentos diferentes. Com a árvore rasa da aula (profundidade 4), trocar mês por dia do ano subiu a CV de {pc(t[3]['cv_media'])} para {pc(data_['cv_media'])}. Na árvore final a diferença quase some: CV de {pc(mes_cv) if mes_cv else 'n/d'} com mês contra {pc(dia_cv) if dia_cv else 'n/d'} com dia do ano, porque uma árvore profunda reconstrói a data combinando vários cortes de mês. Conclusão: o dia do ano é a melhor escolha, mas só faz grande diferença quando a árvore é rasa."},
            {"pergunta": "Quais colunas mais ajudaram?",
             "resumo": "Idade, dose e a data (dia do ano).",
             "resposta": f"Na árvore final, as colunas mais importantes são {lider}. Pela ablação (remover cada grupo e medir a CV no treino), as maiores quedas ocorrem sem {ajudaram}. Idade e dose separam o público pediátrico do adulto e a primeira dose do reforço; a data separa as fases da campanha. Atenção: importância alta não é o mesmo que queda grande ao remover, porque colunas parecidas se substituem entre si. O bloco de perfil (grupo, categoria, unidade de saúde etc.) ajudou muito pouco: sem ele a CV é {pc(ext['sem_perfil']['cv'])}, contra {pc(melhor['cv_media'])} com ele. Essas colunas são conhecidas antes da vacina ser escolhida, por isso não são vazamento."},
            {"pergunta": "Onde a matriz de confusão mostra confusão?",
             "resumo": "Principalmente entre vacinas aplicadas ao mesmo público e na mesma época, e nas Coronavac.",
             "resposta": f"As duas maiores confusões no teste são: {conf}. Os piores recalls são '{rec[0]['classe']}' ({pc(rec[0]['recall'])}) e '{rec[1]['classe']}' ({pc(rec[1]['recall'])}), ou seja, o modelo erra {pc(1 - rec[0]['recall'])} e {pc(1 - rec[1]['recall'])} dessas pessoas. A causa é que as colunas descrevem a pessoa e a data, não o frasco: quando duas vacinas foram dadas à mesma faixa de idade e no mesmo período, a árvore não tem como separá-las e escolhe a mais frequente. Já as classes mais fáceis de separar são '{rec[-1]['classe']}' ({pc(rec[-1]['recall'])}) e '{rec[-2]['classe']}' ({pc(rec[-2]['recall'])})."},
            {"pergunta": "A acurácia sozinha engana?",
             "resumo": "Sim: ela só faz sentido comparada a uma linha de base e olhando cada classe.",
             "resposta": f"Um modelo que sempre responde '{base['classe']}' já acerta {pc(base['acuracia_teste'])} só porque essa é a vacina mais comum. Então os {pc(final['acuracia_teste'])} da árvore devem ser lidos como um ganho de {pp(final['acuracia_teste'] - base['acuracia_teste'])} pontos sobre essa régua. Além disso, a média esconde diferenças entre as classes: o recall vai de {pc(rec[0]['recall'])} (pior classe) a {pc(rec[-1]['recall'])} (melhor classe). Por isso também olhamos precisão, recall, F1 e a matriz de confusão."},
            {"pergunta": "O que é overfitting aqui?",
             "resumo": "A árvore decorar o treino em vez de aprender o padrão, e falhar em casos novos.",
             "resposta": f"Sem limite de profundidade nem poda, a árvore cresceu até {sl['folhas']} folhas (profundidade {sl['profundidade']}): acertou {pc(sl['treino'])} no treino, mas só {pc(sl['teste'])} no teste, uma diferença de {pp(sl['treino'] - sl['teste'])} pontos. Para evitar isso, escolhemos os hiperparâmetros (incluindo a poda ccp_alpha) por validação cruzada usando só o treino. A árvore final tem {final['n_folhas']} folhas e fica com {pc(final['acuracia_treino'])} no treino e {pc(final['acuracia_teste'])} no teste: a diferença caiu para {pp(final['acuracia_treino'] - final['acuracia_teste'])} ponto, então não há overfitting relevante."},
            {"pergunta": "A meta de 80% foi atingida e como a escolha foi feita?",
             "resumo": f"Sim: {pc(final['acuracia_teste'])} no teste, sem usar o lote.",
             "resposta": f"A tentativa vencedora foi a de maior média de validação cruzada (5-fold estratificado) no conjunto de treino, {pc(melhor['cv_media'])}. O conjunto de teste foi usado apenas para reportar o resultado, nunca para escolher ou ajustar o modelo, então os {pc(final['acuracia_teste'])} são uma estimativa honesta para dados novos. O maior salto veio de aumentar a profundidade da árvore; as colunas extras contribuíram pouco."},
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
