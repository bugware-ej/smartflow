import firebase_admin
from firebase_admin import credentials, firestore
from google.cloud.firestore_v1.vector import Vector
from ai_engine import gerar_vetor
import csv

if not firebase_admin._apps:
	cred = credentials.Certificate("firebase_key.json")
	firebase_admin.initialize_app(cred)

db = firestore.client()

membros = []
with open("membros.csv", newline="") as csv_file:
	reader = csv.reader(csv_file, delimiter=",", quotechar='"')
	cabecalhos = []

	for idx, row in enumerate(reader):
		if idx == 0:
			# Cabeçalho: Pares entre índice e nome
			cabecalhos = [(idx, r) for idx, r in enumerate(row)]
		else:
			atual = {}
			for i, dado in enumerate(row):
				chave = cabecalhos[i][1]
				valor = dado
				
				# Chaves com valor numérico
				if chave in ["periodo", "horas_disponiveis"]:
					valor = int(dado)
				# Chaves com valor de Lista
				elif chave in ["skills"]:
					valor = [skill.strip() for skill in dado.split(",")]
				
				atual[chave] = valor
			membros.append(atual)

for m in membros:
	perfil_texto = f"Área: {m['area']}. Cargo: {m['cargo']}. Habilidades técnicas: {', '.join(m['skills'])}"
	vetor = gerar_vetor(perfil_texto)

	m["embedding_skills"] = Vector(vetor)
	db.collection("bugwares").add(m)

print("1/2 Banco 'bugwares' populado com sucesso!")

db.collection("regras_negocio").document("adm_fin").set({
	"valor_hora": 45.0,
	"margem_seguranca_percentual": 15,
	"horas_minimas_projeto": 40
})

print("2/2 Banco 'regras_negocio/adm_fin' populado com sucesso!")
print("✅ Branco populado com sucesso!")
