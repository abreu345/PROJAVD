from datetime import datetime, timezone
from pymongo import MongoClient
from src import config
from sqlalchemy import create_engine

class Load:
    """Grava os dados: na camada BRONZE (MongoDB Atlas) ou na SILVER (NeonDB)."""
    def salvar_bronze(self, registros):
        for registro in registros:
            registro["_data_carga"] = datetime.now()
        cliente = MongoClient(config.MONGO_URI)
        colecao = cliente[config.MONGO_BANCO][config.MONGO_COLECAO]
        colecao.delete_many({})  # apaga a carga anterior para não duplicar
        colecao.insert_many(registros)
        cliente.close()
        print(f"[load] {len(registros)} documentos gravados na bronze")
        return registros

    def salvar_silver(self, df):
        engine = create_engine(config.NEON_URL)
        df.to_sql(config.TABELA_SILVER, engine, if_exists="replace", index=False)
        print(f"[load] {len(df)} linhas gravadas na tabela '{config.TABELA_SILVER}'")

    def salvar_gold_previsoes(self, df):
        """Acrescenta previsões à gold, sem substituir execuções anteriores."""
        engine = create_engine(config.NEON_URL)
        saida = df.copy()
        if "data_previsao" not in saida:
            saida["data_previsao"] = datetime.now(timezone.utc)
        saida.to_sql("gold_previsoes", engine, if_exists="append", index=False)
        engine.dispose()
        print(f"[load] {len(saida)} previsões acrescentadas em gold_previsoes")
        return saida
