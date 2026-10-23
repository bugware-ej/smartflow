from __future__ import annotations
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

ai_api_key = os.getenv("AI_API_KEY", "")
ai_model = os.getenv("AI_MODEL", "gemini-3.1-flash-lite")
ai_temperature = float(os.getenv("AI_TEMPERATURE", 0.2))

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

	@classmethod
	def from_dict(cls, dicionario: dict) -> LevantamentoRequisitos:
		return LevantamentoRequisitos(
			nome_projeto=dicionario.get("nome_projeto", ""),
			resumo_executivo=dicionario.get("resumo_executivo", ""),
			requisitos_funcionais=dicionario.get("requisitos_funcionais", []),
			requisitos_nao_funcionais=dicionario.get("requisitos_nao_funcionais", []),
			stack_sugerida=dicionario.get("stack_sugerida", []),
			horas_estimadas_desenvolvimento=dicionario.get("horas_estimadas_desenvolvimento", 0),
			complexidade=dicionario.get("complexidade", "")
		)

class MembroAlocado(BaseModel):
	nome: str
	cargo: str
	papel_no_projeto: str
	score_afinidade: float = Field(description="Score vetorial do membro vindo do banco")
	justificativa_tecnica: str

	@classmethod
	def from_dict(cls, dicionario: dict) -> MembroAlocado:
		return MembroAlocado(
			nome=dicionario.get("nome", ""),
			cargo=dicionario.get("cargo", ""),
			papel_no_projeto=dicionario.get("papel_no_projeto", ""),
			score_afinidade=dicionario.get("score_afinidade", 0.0),
			justificativa_tecnica=dicionario.get("justificativa_tecnica", ""),
		)

class OpcaoEquipe(BaseModel):
	nome_squad: str = Field(description="Ex: Squad Velocidade, Squad Inovação + Trainee, etc.")
	foco_da_equipe: str
	membros: List[MembroAlocado]

	@classmethod
	def from_dict(cls, dicionario: dict) -> OpcaoEquipe:
		return OpcaoEquipe(
			nome_squad=dicionario.get("nome_squad", ""),
			foco_da_equipe=dicionario.get("foco_da_equipe", ""),
			membros=[MembroAlocado.from_dict(ma) for ma in dicionario.get("membros", [])]
		)

class PropagacaoDiretorias(BaseModel):
	insumos_adm_fin: str = Field(description="Análise de custos base, sugestão de parcelamento e esforço em horas")
	impacto_juridico: List[str] = Field(description="Cláusulas críticas, LGPD, propriedade intelectual, SLA e riscos")
	opcoes_equipes: List[OpcaoEquipe]

class Orcamento(BaseModel):
	horas_consideradas: int
	orcamento_base_calculado: float
	orcamento_com_margem_seguranca: float
	valor_hora_tabela: float

	@classmethod
	def from_dict(cls, dicionario: dict) -> Orcamento:
		return Orcamento(
			horas_consideradas=dicionario.get("horas_consideradas", 0),
			orcamento_base_calculado=dicionario.get("orcamento_base_calculado", 0.0),
			orcamento_com_margem_seguranca=dicionario.get("orcamento_com_margem_seguranca", 0.0),
			valor_hora_tabela=dicionario.get("valor_hora_tabela", 0.0)
		)

class Propagacao(BaseModel):
	impacto_juridico: List[str]
	insumos_adm_fin: str
	opcoes_equipes: List[OpcaoEquipe]

	@classmethod
	def from_dict(cls, dicionario: dict) -> Propagacao:
		return Propagacao(
			impacto_juridico=dicionario.get("impacto_juridico", []),
			insumos_adm_fin=dicionario.get("insumos_adm_fin", ""),
			opcoes_equipes=[OpcaoEquipe.from_dict(oe) for oe in dicionario.get("opcoes_equipes", [])]
		)

class HistoricoLeads(BaseModel):
	orcamento: Orcamento
	projeto: str
	propagacao: Propagacao
	requisitos: LevantamentoRequisitos

	@classmethod
	def from_dict(cls, dicionario: dict) -> HistoricoLeads:
		return HistoricoLeads(
			orcamento=Orcamento.from_dict(dicionario.get("orcamento", {})),
			projeto=dicionario.get("projeto", ""),
			propagacao=Propagacao.from_dict(dicionario.get("propagacao", {})),
			requisitos=LevantamentoRequisitos.from_dict(dicionario.get("requisitos", {})),
		)

def aplicar_guardrails_membros(membros: list) -> list:
	status_validos = ["livre", "passivamente ocupado"]
	elegiveis = []

	for m in membros:
		atual = m.copy()
		atual.pop("embedding_skills", None)
		status_membro = str(atual.get("status", "")).strip().lower()

		if status_membro in status_validos and atual.get("horas_disponiveis", 0) > 0:
			elegiveis.append(atual)
	
	return elegiveis

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
		f"{m.get("area", "")} - Skills: {', '.join(m.get("skills", []))} - Cargo: {m.get("cargo", "")}"
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

	return res.embeddings[0].values[:2048]

def buscar_membros_vetorial_firestore(db, requisitos: LevantamentoRequisitos, limite: int = 16):
	texto_projeto = f"Projeto {requisitos.resumo_executivo}. Stack: {', '.join(requisitos.stack_sugerida)}"
	colecao = db.collection("bugwares")

	try:
		vetor_projeto = gerar_vetor(texto_requisitos_projeto)

		vetor_query = colecao.find_nearest(
			vector_field="embedding_skills",
			query_vector=Vector(vetor_projeto),
			distance_measure=DistanceMeasure.COSINE,
			limit=limite
		)

		membros_brutos = [doc.to_dict() for doc in vetor_query.stream()]

		if membros_brutos:
			# elegiveis = aplicar_guardrails_membros(membros_brutos)
			# return ranquear_membros_por_embeddings(requisitos, elegiveis)
			return aplicar_guardrails_membros(membros_brutos)
	
	except Exception:
		pass

	membros_brutos = [doc.to_dict() for doc in colecao.stream()]
	elegiveis = aplicar_guardrails_membros(membros_brutos)
	return ranquear_membros_por_embeddings(requisitos, elegiveis)

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

	1. Monte 3 OPÇÕES DE EQUIPES MULTIDISCIPLINARES diferentes (misturando Membros Efetivos e Trainees para capacitação), entre 3 a 5 pessoas quando possível.
	REGRA DE GUARDRAIL ESTRITA: Você DEVE escolher EXCLUSIVAMENTE pessoas que estão na lista 'MEMBROS DISPONÍVEIS' abaixo. É PROIBIDO inventar nomes que não estejam nessa lista JSON. Preencha o campo 'score_afinidade' com o valor exato de 'score_afinidade_vetorial' de cada membro.
	2. Elabore o parecer comercial/financeiro para a diretoria de Adm/Fin respeitando ESTRITAMENTE os valores calculados no Guardrail: {json.dumps(dados_orcamento)}.
	3. Elabore os pontos de atenção e impactos contratuais para a diretoria Jurídica (LGPD, APIs de terceiros, propriedade intelectual, escopo fechado vs aberto).

	REQUISITOS DO PROJETO:
	{requisitos.model_dump_json()}

	MEMBROS DISPONÍVEIS NO FIREBASE (Com Score de Afinidade Vetorial):
	{json.dumps(membros_ranqueados, ensure_ascii=False)}

	Lembre-se de alterar o caractere '$' para '\\$' por motivos de exibição em Markdown.
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

def gerar_relatorio_md(historico: HistoricoLeads) -> str:
	requisitos = historico.requisitos
	propagacao = historico.propagacao
	orcamento = historico.orcamento

	equipes_md = ""
	for equipe in propagacao.opcoes_equipes:
		equipes_md += f"### 🏆 {equipe.nome_squad}\n\n{equipe.foco_da_equipe}\n\n**Membros:**\n\n"

		for m in equipe.membros:
			equipes_md += f"- **{m.nome}** ({m.cargo}) - *{m.papel_no_projeto}*: "
			equipes_md += f"{m.justificativa_tecnica} (🎯 **Match Vetorial:** `{m.score_afinidade} %`)\n"
		equipes_md += "\n"

	relatorio_md = f"""# Documento de Projeto: {requisitos.nome_projeto}

**Complexidade:** {requisitos.complexidade} | **Horas Estimadas:** {requisitos.horas_estimadas_desenvolvimento}h

**Orçamento Base (Guardrail):** R\\$ {orcamento.orcamento_base_calculado:.2f} | **Com Margem:** R\\$ {orcamento.orcamento_com_margem_seguranca:.2f}

## 1. Resumo Executivo

{requisitos.resumo_executivo}

## 2. Stack Sugerida

{", ".join(requisitos.stack_sugerida)}

## 3. Requisitos Funcionais

{chr(10).join(["- " + r for r in requisitos.requisitos_funcionais])}

## 4. Requisitos Não-Funcionais

{chr(10).join(["- " + r for r in requisitos.requisitos_nao_funcionais])}

## 5. Parecer Adm/Fin

{propagacao.insumos_adm_fin}

## 6. Parecer Jurídico & Compliance

{chr(10).join(["- " + j for j in propagacao.impacto_juridico])}

## 7. Opções de Equipe

{equipes_md}
"""

	return relatorio_md

def gerar_relatorio_pdf(historico: HistoricoLeads):
	gerar_relatorio_md(historico)

