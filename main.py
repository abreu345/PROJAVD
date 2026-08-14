import requests
import json

url = "https://servicodados.ibge.gov.br/api/v3/agregados/4093/periodos/201201|201202|201203|201204|201301|201302|201303|201304|201401|201402|201403|201404|201501|201502|201503|201504|201601|201602|201603|201604|201701|201702|201703|201704|201801|201802|201803|201804|201901|201902|201903|201904|202001|202002|202003|202004|202101|202102|202103|202104|202201|202202|202203|202204|202301|202302|202303|202304|202401|202402|202403|202404|202501|202502|202503|202504|202601/variaveis/4093|4096|4099|12466?localidades=N3[26]&classificacao=2[all]"

r = requests.get(url)
print("status code:", r.status_code)

data = r.json()

extrai_dados = []

for var in data:
    nome_variavel = var["variavel"]

    for res in var["resultados"]:
        categoria = res["classificacoes"][0]["categoria"]
        serie = res["series"][0]["serie"]

        print("Variável:", nome_variavel)
        print("Categoria (Sexo):", categoria)
        print("Série:", serie)
        print("-" * 50)

        extrai_dados.append(
            {"variavel": nome_variavel, "sexo": categoria, "serie": serie}
        )

with open("total.json", "w", encoding="utf-8") as f:
    json.dump(extrai_dados, f, ensure_ascii=False, indent=4)