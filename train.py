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
