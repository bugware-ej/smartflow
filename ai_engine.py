import json
import numpy as np
from google import genai
from google.genai import types
from google.cloud.firestore_v1.base_vector_query import DistanceMeasure
from google.cloud.firestore_v1.vector import Vector
from pydantic import BaseModel, Field
from typing import List
from dotenv import load_dotenv
import os

load_dotenv()

ai_api_key = os.getenv("AI_API_KEY")
ai_model = os.getenv("AI_MODEL")
ai_temperature = os.getenv("AI_TEMPERATURE")

client = genai.Client(api_key=ai_api_key)

HORAS_MINIMAS_PROJETO = 40
VALOR_HORA = 45.0
MARGEM_SEGURANCA_PERCENTUAL = 15
BASE_ARREDONDAMENTO = 6

class LevantamentoRequisitos(BaseModel):
	nome_projeto: str
	resumo_executivo: str
	requisitos_funcionais: List[str]
	requisitos_nao_funcionais: List[str]
	stack_sugerida: List[str]
	horas_estimadas_desenvolvimento: int
	complexidade: str = Field(description="Baixa, Média ou Alta")

class MembroAlocado(BaseModel):
	nome: str
	cargo: str
	papel_no_projeto: str
	justificativa_tecnica: str

class OpcaoEquipe(BaseModel):
	nome_squad: str = Field(description="Ex: Squad Velocidade, Squad Inovação + Trainee, etc.")
	foco_da_equipe: str
	membros: List[MembroAlocado]

class PropagacaoDiretorias(BaseModel):
	insumos_adm_fin: str = Field(description="Análise de custos base, sugestão de parcelamento e esforço em horas")
	impacto_juridico: List[str] = Field(description="Cláusulas críticas, LGPD, propriedade intelectual, SLA e riscos")
	opcoes_equipes: List[OpcaoEquipe]

def aplicar_guardrails_membros(membros: list) -> list:
	status_validos = ["livre", "passivamente ocupado"]
	
	return [
		m for m in membros
		if m.get("status") in status_validos and m.get("horas_disponiveis", 0) > 0
	]

def calcular_orcamento_guardrail(horas_estimadas: int, regras_adm: dict) -> dict:
	horas_reais = max(horas_estimadas, regras_adm.get("horas_minimas_projeto", HORAS_MINIMAS_PROJETO))
	valor_hora = regras_adm.get("valor_hora", VALOR_HORA)
	margem = 1 + (regras_adm.get("margem_seguranca_percentual", MARGEM_SEGURANCA_PERCENTUAL) / 100.0)

	preco_base = horas_reais * valor_hora
	preco_final_sugerido = round(preco_base * margem, BASE_ARREDONDAMENTO)

	return {
		"horas_consideradas": horas_reais,
		"valor_hora_tabela": valor_hora,
		"orcamento_base_calculado": round(preco_base, BASE_ARREDONDAMENTO),
		"orcamento_com_margem_seguranca": preco_final_sugerido
	}

def ranquear_membros_por_embeddings(requisitos: LevantamentoRequisitos, membros_elegiveis: list) -> list:
	if not membros_elegiveis:
		return []

	texto_projeto = f"Projeto {requisitos.resumo_executivo}. Tecnologias: {', '.join(requisitos.stack_sugerida)}"
	textos_membros = [
		f"{m['area']} - Skills: {', '.join(m['skills'])} - Cargo: {m['cargo']}"
		for m in membros_elegiveis
	]

	todos_textos = [texto_projeto] + textos_membros
	res = client.models.embed_content(
		# model="text-embedding-004",
		model="gemini-embedding-001",
		contents=todos_textos
	)

	vetor_projeto = np.array(res.embeddings[0].values)

	for idx, m in enumerate(membros_elegiveis):
		vetor_membro = np.array(res.embeddings[idx + 1].values)

		# NOTE: Similaridade de cosseno
		score = np.dot(vetor_projeto, vetor_membro) / (np.linalg.norm(vetor_projeto) * np.linalg.norm(vetor_membro))
		m["score_afinidade_vetorial"] = round(float(score) * 100, 1)

	return sorted(membros_elegiveis, key=lambda x: x["score_afinidade_vetorial"], reverse=True)

def gerar_vetor(texto: str) -> list[float]:
	res = client.models.embed_content(
		# model="text-embedding-004",
		model="gemini-embedding-001",
		contents=texto
	)

	return res.embeddings[0].values

def buscar_membros_vetorial_firestore(db, texto_requisitos_projeto: str, limite: int = 6):
	vetor_projeto = gerar_vetor(texto_requisitos_projeto)

	colecao = db.collection("bugwares")

	vector_query = colecao.find_nearest(
		vector_field="embedding_skills",
		query_vector=Vector(vetor_projeto),
		distance_measure=DistanceMeasure.COSINE,
		limit=limite
	)

	resultados = []
	for doc in vector_query.stream():
		dados = doc.to_dict()
		dados.pop("embedding_skills", None)

		if dados.get("status") in ["Livre", "Passivamente Ocupado"]:
			resultados.append(dados)

	return resultados

def extrair_requisitos_lead(anotacoes_reuniao: str) -> LevantamentoRequisitos:
	prompt = f"""
	Você é um Engenheiro de Requisitos Sênior da Bugware (Empresa Júnior de Computação).
	Analise a transcrição/anotações da reunião com o Lead abaixo e gere o documento formal de Levantamento de Requisitos.

	ANOTAÇÕES DO LEAD:
	{anotacoes_reuniao}
	"""

	res = client.models.generate_content(
		model=ai_model,
		contents=prompt,
		config=types.GenerateContentConfig(
			response_mime_type="application/json",
			response_schema=LevantamentoRequisitos,
			temperature=ai_temperature
		)
	)

	return LevantamentoRequisitos.model_validate_json(res.text)

def gerar_alocacao_e_propagacao(
	requisitos: LevantamentoRequisitos,
	membros_ranqueados: list,
	dados_orcamento: dict
) -> PropagacaoDiretorias:

	prompt = f"""
	Você é o Coordenador de Operações Inteligente da Bugware (Empresa Júnior de Computação).
	Com base nos requisitos extraídos, nos membros elegíveis ranqueados por busca vetorial e no cálculo travado de Adm/Fin:

	1. Monte 3 OPÇÕES DE EQUIPES MULTIDISCIPLINARES diferentes (misturando Membros Efetivos e Trainees para capacitação, respeitando status Livre ou Passivamente Ocupado).
	2. Elabore o parecer comercial/financeiro para a diretoria de Adm/Fin respeitando ESTRITAMENTE os valores calculados no Guardrail: {json.dumps(dados_orcamento)}.
	3. Elabore os pontos de atenção e impactos contratuais para a diretoria Jurídica (LGPD, APIs de terceiros, propriedade intelectual, escopo fechado vs aberto).

	REQUISITOS DO PROJETO:
	{requisitos.model_dump_json()}

	MEMBROS DISPONÍVEIS (Com Score de Afinidade Vetorial):
	{json.dumps(membros_ranqueados, ensure_ascii=False)}

	Lembre-se de alterar o caractere '$' para '\$' por motivos de exibição em Markdown.
	"""

	res = client.models.generate_content(
		model=ai_model,
		contents=prompt,
		config=types.GenerateContentConfig(
			response_mime_type="application/json",
			response_schema=PropagacaoDiretorias,
			temperature=ai_temperature
		)
	)

	return PropagacaoDiretorias.model_validate_json(res.text)


