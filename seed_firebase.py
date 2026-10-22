import firebase_admin
from firebase_admin import credentials, firestore
from google.cloud.firestore_v1.vector import Vector
from google import genai
from dotenv import load_dotenv
from ai_engine import gerar_vetor
import os

load_dotenv()

ai_api_key = os.getenv("AI_API_KEY")

client = genai.Client(api_key=ai_api_key)

cred = credentials.Certificate("firebase_key.json")
firebase_admin.initialize_app(cred)
db = firestore.client()

membros_iniciais = [
	{"nome": "Carlos Eduardo", "cargo": "Membro Efetivo", "status": "livre", "area": "Mobile", "skills": ["Kotlin", "Flutter", "Firebase"], "nivel_experiencia": "junior", "horas_disponiveis": 15},
	{"nome": "Beatriz Souza", "cargo": "Trainee", "status": "livre", "area": "UI/UX", "skills": ["Figma", "Prototipação", "Design System"], "nivel_experiencia": "junior", "horas_disponiveis": 12},
	{"nome": "Lucas Mendes", "cargo": "Membro Efetivo", "status": "passivamente ocupado", "area": "Backend", "skills": ["Python", "FastAPI", "PostgreSQL", "IA"], "nivel_experiencia": "junior", "horas_disponiveis": 8},
	{"nome": "Fernanda Lima", "cargo": "Membro Efetivo", "status": "ocupado", "area": "Frontend", "skills": ["React", "TypeScript", "Tailwind"], "nivel_experiencia": "junior", "horas_disponiveis": 0},
	{"nome": "Gabriel Costa", "cargo": "Trainee", "status": "livre", "area": "Frontend", "skills": ["HTML", "CSS", "JavaScript", "React"], "nivel_experiencia": "junior", "horas_disponiveis": 15},
	{"nome": "Mariana Alves", "cargo": "Membro Efetivo", "status": "livre", "area": "Backend", "skills": ["Node.js", "Firebase", "APIs REST"], "nivel_experiencia": "junior", "horas_disponiveis": 14}
]

for m in membros_iniciais:
	perfil_texto = f"Área: {m['area']}. Cargo: {m['cargo']}. Habilidades técnicas: {', '.join(m['skills'])}"
	vetor = gerar_vetor(perfil_texto)

	# NOTE: Truncando o vetor para tamanho máximo permitido: 2048 elementos
	m["embedding_skills"] = Vector(vetor[:2048])
	db.collection("bugwares").add(m)

db.collection("regras_negocio").document("adm_fin").set({
	"valor_hora": 45.0,
	"margem_seguranca_percentual": 15,
	"horas_minimas_projeto": 40
})

print("Branco populado com sucesso!")
