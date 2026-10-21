import firebase_admin
from firebase_admin import credentials, firestore
from google.cloud.firestore_v1.vector import Vector
from google import genai
from dotenv import load_dotenv
from ai_engine import gerar_vetor
import os

import json
import numpy as np
from google.genai import types
from google.cloud.firestore_v1.base_vector_query import DistanceMeasure
from pydantic import BaseModel, Field
from typing import List

load_dotenv()

ai_api_key = os.getenv("AI_API_KEY")
ai_model = os.getenv("AI_MODEL")
ai_temperature = os.getenv("AI_TEMPERATURE")

client = genai.Client(api_key=ai_api_key)

cred = credentials.Certificate("firebase_key.json")
firebase_admin.initialize_app(cred)
db = firestore.client()

membros_iniciais = [
	{"nome": "Carlos Eduardo", "cargo": "Membro Efetivo", "status": "Livre", "area": "Mobile", "skills": ["Kotlin", "Flutter", "Firebase"], "nivel_experiencia": "junior", "horas_disponiveis": 15},
	{"nome": "Beatriz Souza", "cargo": "Trainee", "status": "Livre", "area": "UI/UX", "skills": ["Figma", "Prototipação", "Design System"], "nivel_experiencia": "junior", "horas_disponiveis": 12},
	{"nome": "Lucas Mendes", "cargo": "Membro Efetivo", "status": "Passivamente Ocupado", "area": "Backend", "skills": ["Python", "FastAPI", "PostgreSQL", "IA"], "nivel_experiencia": "junior", "horas_disponiveis": 8},
	{"nome": "Fernanda Lima", "cargo": "Membro Efetivo", "status": "Ocupado", "area": "Frontend", "skills": ["React", "TypeScript", "Tailwind"], "nivel_experiencia": "junior", "horas_disponiveis": 0},
	{"nome": "Gabriel Costa", "cargo": "Trainee", "status": "Livre", "area": "Frontend", "skills": ["HTML", "CSS", "JavaScript", "React"], "nivel_experiencia": "junior", "horas_disponiveis": 15},
	{"nome": "Mariana Alves", "cargo": "Membro Efetivo", "status": "Livre", "area": "Backend", "skills": ["Node.js", "Firebase", "APIs REST"], "nivel_experiencia": "junior", "horas_disponiveis": 14}
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
