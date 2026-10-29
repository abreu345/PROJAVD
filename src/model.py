import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from sklearn.dummy import DummyClassifier
from sklearn.tree import DecisionTreeClassifier, export_text
from sklearn.model_selection import train_test_split, GridSearchCV, StratifiedKFold, cross_val_score
from sklearn.metrics import accuracy_score, confusion_matrix

ALVO = "vacina"
SEMENTE = 42
INICIO = pd.Timestamp("2022-01-01")


class Features:
    """Constrói as colunas (features) a partir da silver. NUNCA usa `lote`.
    Texto vira 0/1 (one-hot), como na aula; nenhuma coluna usa o alvo."""

    # coluna -> quantas categorias manter (None = todas)
    CATEGORICAS = {"sexo": None, "raca_cor": None, "distrito_sanitario": None,
                   "unidade_saude": None, "sistema_origem": None, "grupo": None,
                   "categoria": None, "faixa_etaria": None, "municipio": None}

    def __init__(self, extras=None):
        self.niveis = {}
        self.categoricas = dict(self.CATEGORICAS)
        if extras:  # só para o experimento de vazamento (lote)
            self.categoricas.update(extras)

    def fit(self, df):
        for col, topo in self.categoricas.items():
            freq = df[col].fillna("SEM INFORMACAO").value_counts()
            self.niveis[col] = list(freq.index[:topo]) if topo else list(freq.index)
        return self

    def transformar(self, df):
        datas = pd.to_datetime(df["data_vacinacao"])
        cols = {"idade": df["idade"], "dose": df["dose"], "mes": datas.dt.month,
                "dia_do_ano": (datas - INICIO).dt.days,  # ordinal: dias desde 01/01/2022
                "semana": datas.dt.isocalendar().week.astype(int),
                "dia_da_semana": datas.dt.dayofweek}
        for col, niveis in self.niveis.items():
            serie = df[col].fillna("SEM INFORMACAO")
            serie = serie.where(serie.isin(niveis), "OUTRAS")
            nomes = niveis + (["OUTRAS"] if self.categoricas[col] else [])
            for n in nomes:
                cols[f"{col}={n}"] = (serie == n).astype(int)
        return pd.DataFrame(cols, index=df.index)

    @staticmethod
    def selecionar(X, grupos):
        """Mantém só as colunas dos grupos pedidos (ex.: 'idade', 'sexo')."""
        return X[[c for c in X.columns if c.split("=")[0] in grupos]]


class Classificador:
    """Árvore de decisão (DecisionTreeClassifier) para prever o tipo de vacina."""

    def __init__(self, extras=None):
        self.features = Features(extras)
        self.cv = StratifiedKFold(n_splits=5, shuffle=True, random_state=SEMENTE)
        self.modelo = None

    def preparar(self, df):
        """Da silver para X e y (one-hot das categorias, data em colunas numéricas)."""
        df = df.copy()
        df["data_vacinacao"] = pd.to_datetime(df["data_vacinacao"])
        df = df.dropna(subset=["idade", "dose", "data_vacinacao", ALVO])
        self.df = df
        self.features.fit(df)
        X = self.features.transformar(df)
        y = df[ALVO]
        print(f"[model] {len(X)} linhas, {y.nunique()} classes")
        return X, y

    def dividir(self, X, y):
        # mesmo dividir() da aula: 80/20, random_state=42, estratificado
        X_treino, X_teste, y_treino, y_teste = train_test_split(
            X, y, test_size=0.2, random_state=SEMENTE, stratify=y)
        self.X_treino_full, self.X_teste_full = X_treino, X_teste
        self.y_treino, self.y_teste = y_treino, y_teste
        print(f"[model] treino={len(X_treino)} teste={len(X_teste)}")
        return X_treino, X_teste, y_treino, y_teste

    def linha_de_base(self):
        d = DummyClassifier(strategy="most_frequent").fit(self.X_treino_full, self.y_treino)
        acc = float(accuracy_score(self.y_teste, d.predict(self.X_teste_full)))
        classe = str(self.y_treino.value_counts().index[0])
        print(f"[model] linha de base (most_frequent = {classe}): {acc:.4f}")
        return {"acuracia_teste": acc, "estrategia": "most_frequent", "classe": classe}

    def xy(self, grupos):
        return (Features.selecionar(self.X_treino_full, grupos),
                Features.selecionar(self.X_teste_full, grupos))

    def tuning(self, grupos, grade):
        """GridSearchCV (5-fold estratificado) SOMENTE no treino."""
        Xtr, _ = self.xy(grupos)
        gs = GridSearchCV(DecisionTreeClassifier(random_state=SEMENTE), grade,
                          cv=self.cv, scoring="accuracy", n_jobs=4, refit=True)
        gs.fit(Xtr, self.y_treino)
        i = gs.best_index_
        print(f"[model] melhor CV={gs.best_score_:.4f} params={gs.best_params_}")
        return (gs.best_estimator_, gs.best_params_,
                float(gs.cv_results_["mean_test_score"][i]), float(gs.cv_results_["std_test_score"][i]))

    def treinar(self, grupos, params):
        Xtr, _ = self.xy(grupos)
        modelo = DecisionTreeClassifier(random_state=SEMENTE, **params).fit(Xtr, self.y_treino)
        s = cross_val_score(DecisionTreeClassifier(random_state=SEMENTE, **params),
                            Xtr, self.y_treino, cv=self.cv, scoring="accuracy", n_jobs=4)
        return modelo, float(s.mean()), float(s.std())

    def avaliar(self, modelo, grupos):
        Xtr, Xte = self.xy(grupos)
        return (float(accuracy_score(self.y_treino, modelo.predict(Xtr))),
                float(accuracy_score(self.y_teste, modelo.predict(Xte))))

    def definir_final(self, modelo, grupos):
        self.modelo, self.grupos_final = modelo, grupos
        self.Xtr_final, self.Xte_final = self.xy(grupos)
        self.pred = modelo.predict(self.Xte_final)

    def matriz_confusao(self, caminho="matriz_confusao.png"):
        classes = [str(c) for c in self.modelo.classes_]
        cm = confusion_matrix(self.y_teste, self.pred, labels=classes)
        fig, ax = plt.subplots(figsize=(9, 7))
        ax.imshow(cm, cmap="Blues")
        rot = [c.replace("�", "A")[:28] for c in classes]
        ax.set_xticks(range(len(classes)), rot, rotation=45, ha="right", fontsize=8)
        ax.set_yticks(range(len(classes)), rot, fontsize=8)
        for i in range(len(classes)):
            for j in range(len(classes)):
                ax.text(j, i, cm[i, j], ha="center", va="center",
                        color="white" if cm[i, j] > cm.max() / 2 else "black")
        ax.set_xlabel("Previsto")
        ax.set_ylabel("Real")
        ax.set_title("Matriz de confusão (teste)")
        fig.tight_layout()
        fig.savefig(caminho, dpi=120)
        plt.close(fig)
        print(f"[model] matriz de confusão salva em {caminho}")
        return classes, cm

    def explicar(self):
        print(export_text(self.modelo, feature_names=list(self.Xtr_final.columns), max_depth=4))
        imp = pd.Series(self.modelo.feature_importances_, index=self.Xtr_final.columns).sort_values(ascending=False)
        print("[model] importâncias (top 10):")
        print(imp.head(10).round(4).to_string())
        return imp


def serializar_arvore(modelo, nomes, classes, profundidade_max=None):
    """Serializa recursivamente a árvore a partir de modelo.tree_."""
    t = modelo.tree_

    def no(i, prof):
        v = t.value[i][0]
        if v.sum() <= 1.0 + 1e-9:  # proporções (sklearn novo) -> contagens
            v = v * t.n_node_samples[i]
        folha = t.children_left[i] == -1
        d = {"feature": None if folha else nomes[t.feature[i]],
             "limiar": None if folha else float(t.threshold[i]),
             "amostras": int(t.n_node_samples[i]), "impureza": float(t.impurity[i]),
             "classe": classes[int(np.argmax(v))],
             "distribuicao": {c: int(round(x)) for c, x in zip(classes, v)},
             "esquerda": None, "direita": None}
        if not folha and (profundidade_max is None or prof < profundidade_max):
            d["esquerda"] = no(t.children_left[i], prof + 1)
            d["direita"] = no(t.children_right[i], prof + 1)
        return d
    return no(0, 0)


class Experimentos:
    """Roda as tentativas progressivas; escolhe pela CV (treino) e só REPORTA o teste."""

    ORIG = ["idade", "dose", "mes", "sexo", "raca_cor", "distrito_sanitario"]
    PERFIL = ["grupo", "categoria", "faixa_etaria"]
    GRADE = {"max_depth": [6, 8, 10, 12, 16, None],
             "min_samples_leaf": [1, 3, 10, 30],
             "criterion": ["gini", "entropy"],
             "ccp_alpha": [0.0, 0.0005]}

    def __init__(self, clf):
        self.clf = clf
        self.tentativas = []
        self.modelos = {}

    def registrar(self, nome, mudanca, grupos, modelo, params, cv_m, cv_d):
        tr, te = self.clf.avaliar(modelo, grupos)
        t = {"id": len(self.tentativas) + 1, "nome": nome, "mudanca": mudanca,
             "features": list(Features.selecionar(self.clf.X_treino_full, grupos).columns),
             "grupos": grupos, "params": params, "cv_media": cv_m, "cv_desvio": cv_d,
             "acuracia_treino": tr, "acuracia_teste": te, "escolhida": False}
        self.tentativas.append(t)
        self.modelos[t["id"]] = modelo
        print(f"[model] #{t['id']} {nome}: CV={cv_m:.4f}+-{cv_d:.4f} treino={tr:.4f} teste={te:.4f}")

    def fixa(self, nome, mudanca, grupos, params):
        m, cm, cd = self.clf.treinar(grupos, params)
        self.registrar(nome, mudanca, grupos, m, params, cm, cd)

    def grade(self, nome, mudanca, grupos):
        m, p, cm, cd = self.clf.tuning(grupos, self.GRADE)
        self.registrar(nome, mudanca, grupos, m, p, cm, cd)

    def rodar(self):
        c = self.clf
        base = c.linha_de_base()
        Xtr, _ = c.xy(self.ORIG)
        d = DummyClassifier(strategy="most_frequent")
        s = cross_val_score(d, Xtr, c.y_treino, cv=c.cv, scoring="accuracy")
        d.fit(Xtr, c.y_treino)
        self.registrar("Baseline (dummy)", "Sempre prevê a classe mais frequente", self.ORIG, d,
                       {"strategy": "most_frequent"}, float(s.mean()), float(s.std()))
        self.fixa("Árvore da aula", "DecisionTree max_depth=4, features originais", self.ORIG, {"max_depth": 4})
        g = self.ORIG + ["unidade_saude", "sistema_origem"]
        self.fixa("+ unidade e sistema", "Adiciona unidade_saude (8, one-hot) e sistema_origem", g, {"max_depth": 4})
        g2 = [x for x in g if x != "mes"] + ["dia_do_ano"]
        self.fixa("Data como dia do ano", "Troca mes por dia do ano (dias desde 01/01/2022)", g2, {"max_depth": 4})
        g3 = g2 + self.PERFIL
        self.fixa("+ perfil (grupo/categoria/faixa)", "Adiciona grupo, categoria e faixa_etaria", g3, {"max_depth": 4})
        self.fixa("Mais profundidade", "max_depth=8", g3, {"max_depth": 8})
        g4 = g3 + ["municipio", "semana", "dia_da_semana", "mes"]
        self.fixa("+ município e calendário", "Adiciona municipio (top 8), semana, dia da semana e mês", g4, {"max_depth": 8})
        self.grade("Grid (perfil + dia do ano)", "GridSearchCV 5-fold no treino", g3)
        self.grade("Grid (todas as features)", "GridSearchCV 5-fold no treino, todas as features", g4)
        # escolha pela CV (nunca pelo teste); o dummy fica fora
        melhor = max(self.tentativas[1:], key=lambda t: t["cv_media"])
        melhor["escolhida"] = True
        print(f"[model] escolhida pela CV: #{melhor['id']} {melhor['nome']} (CV={melhor['cv_media']:.4f})")
        return base, melhor
