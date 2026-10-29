from src.extract import Extract
from src.load import Load
from src.transformer import Transform

extrator = Extract()
loader = Load()
transformer = Transform()

# registros = extrator.ler_api()
# loader.salvar_bronze(registros)

# BRONZE -> SILVER (NeonDB)
df = extrator.ler_bronze()
df = transformer.limpar(df)
loader.salvar_silver(df)