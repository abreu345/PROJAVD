from src.extract import Extract
from src.model import Classificador, Experimentos
from src.relatorio import Relatorio

extrator = Extract()
clf = Classificador()
df = extrator.ler_silver()
X, y = clf.preparar(df)
clf.dividir(X, y)

exp = Experimentos(clf)
base, melhor = exp.rodar()  # tentativas; escolha pela CV no treino

modelo = exp.modelos[melhor["id"]]
clf.definir_final(modelo, melhor["grupos"])
classes, cm = clf.matriz_confusao("matriz_confusao.png")
imp = clf.explicar()

rel = Relatorio(clf, exp)
resultado = rel.montar(base, melhor, modelo, classes, cm, imp)
rel.salvar(resultado, "web/data")
rel.imprimir_tabela()
print(f"[train] acurácia final no teste: {resultado['final']['acuracia_teste']:.4f} (meta 0.80)")

# Persistência do artefato final, incluindo o preparo e a seleção de features.
caminho_modelo = clf.salvar()
artefato = Classificador.carregar(caminho_modelo)
clf_carregado = Classificador().carregar_final(artefato)
X_teste_carregado = clf_carregado.preparar_entrada(
    clf.df.loc[clf.X_teste_full.index].drop(columns=["vacina"])
)
from sklearn.metrics import accuracy_score
acc_carregado = accuracy_score(clf.y_teste, clf_carregado.modelo.predict(X_teste_carregado))
acc_original = accuracy_score(clf.y_teste, clf.modelo.predict(clf.Xte_final))
print(f"[train] acurácia após carregar: {acc_carregado:.4f}; recém-treinado: {acc_original:.4f}")
if acc_carregado != acc_original:
    raise RuntimeError("A acurácia do modelo carregado diverge do modelo final")

# Mantém salvar() como última ação do treino e garante o artefato final.
clf.salvar()
