"""Orquestra inferência de perfis novos e gravação na camada gold."""
import pandas as pd

from src.load import Load
from src.model import Classificador


def perfis_novos():
    """Perfis sintéticos de demonstração; não representam pessoas reais."""
    return pd.DataFrame([
        {"perfil_id": "novo-01-crianca", "idade": 8, "dose": 1,
         "data_vacinacao": "2022-01-25", "sexo": "FEMININO", "raca_cor": "PARDA",
         "distrito_sanitario": "DS 1", "unidade_saude": "UBS EXEMPLO", "sistema_origem": "ESUS",
         "grupo": "CRIANÇA", "categoria": "ROTINA", "faixa_etaria": "5 A 11 ANOS", "municipio": "RECIFE"},
        {"perfil_id": "novo-02-reforco", "idade": 38, "dose": 3,
         "data_vacinacao": "2022-10-12", "sexo": "MASCULINO", "raca_cor": "BRANCA",
         "distrito_sanitario": "DS 4", "unidade_saude": "UBS EXEMPLO", "sistema_origem": "ESUS",
         "grupo": "ADULTO", "categoria": "REFORÇO", "faixa_etaria": "30 A 39 ANOS", "municipio": "RECIFE"},
        {"perfil_id": "novo-03-distrito-desconhecido", "idade": 52, "dose": 2,
         "data_vacinacao": "2022-06-03", "sexo": "FEMININO", "raca_cor": "PRETA",
         "distrito_sanitario": "DS INEXISTENTE", "unidade_saude": "UBS NOVA", "sistema_origem": "ESUS",
         "grupo": "ADULTO", "categoria": "GERAL", "faixa_etaria": "50 A 59 ANOS", "municipio": "RECIFE"},
        {"perfil_id": "novo-04-ano-fora-silver", "idade": 29, "dose": 1,
         "data_vacinacao": "2025-03-18", "sexo": "MASCULINO", "raca_cor": "PARDA",
         "distrito_sanitario": "DS 2", "unidade_saude": "UBS EXEMPLO", "sistema_origem": "ESUS",
         "grupo": "ADULTO", "categoria": "GERAL", "faixa_etaria": "20 A 29 ANOS", "municipio": "RECIFE"},
        {"perfil_id": "novo-05-mes-fora-silver", "idade": 71, "dose": 4,
         "data_vacinacao": "2022-12-20", "sexo": "FEMININO", "raca_cor": "BRANCA",
         "distrito_sanitario": "DS 3", "unidade_saude": "UBS EXEMPLO", "sistema_origem": "ESUS",
         "grupo": "IDOSO", "categoria": "REFORÇO", "faixa_etaria": "70 A 79 ANOS", "municipio": "RECIFE"},
    ])


def main():
    artefato = Classificador.carregar()
    classificador = Classificador().carregar_final(artefato)
    perfis = perfis_novos()
    previsoes = classificador.prever(perfis)
    gold = pd.concat([perfis, previsoes], axis=1)
    Load().salvar_gold_previsoes(gold)
    print(gold[["perfil_id", "vacina_prevista", "confianca"]].to_string(index=False))


if __name__ == "__main__":
    main()
