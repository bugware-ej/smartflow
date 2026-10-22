import streamlit as st
import firebase_admin
from firebase_admin import credentials, firestore
from google.cloud.firestore_v1.vector import Vector
from ai_engine import (
	extrair_requisitos_lead,
	calcular_orcamento_guardrail,
	buscar_membros_vetorial_firestore,
	gerar_alocacao_e_propagacao,
	gerar_vetor
)

if not firebase_admin._apps:
	cred = credentials.Certificate("firebase_key.json")
	firebase_admin.initialize_app(cred)

db = firestore.client()

st.set_page_config(page_title="Bugware SmartFlow | Desafio V360", layout="wide")
st.title("🚀 Bugware SmartFlow - Copiloto de Requisitos, Alocação e Governança")
st.caption("Desafio de Inovação Conecta V360 - Trilha B (Tecnologia & TI)")

aba_copiloto, aba_banco, aba_historico = st.tabs([
	"🤖 Processar Novo Lead",
	"🗄️ Banco de Bugwares (Firebase + Vector DB)",
	"📂 Histórico de Projetos"
])

with aba_copiloto:
	anotacoes = st.text_area(
		"📝 Cole aqui a transcrição ou anotações da Reunião de Diagnósticos com o Lead:",
		height=160,
		placeholder="Ex: Reunião de Alinhamento - Empresa XPTO..."
	)

	if st.button("⚡ Gerar Documentação, Alocar Equipes e Propagar para Diretorias", type="primary"):
		if not anotacoes.strip():
			st.warning("Insira as anotações do Lead primeiro.")
		else:
			with st.spinner("1/3 Extraindo requisitos técnicos com Gemini API..."):
				requisitos = extrair_requisitos_lead(anotacoes)

			with st.spinner("2/3 Aplicando Guardrails e Busca Vetorial no Firebase..."):
				regras_doc = db.collection("regras_negocio").document("adm_fin").get()
				regras_adm = regras_doc.to_dict() if regras_doc.exists else {
					"valor_hora": 45.0,
					"margem_seguranca_percentual": 15,
					"horas_minimas_projeto": 40
				}
				
				orcamento_travado = calcular_orcamento_guardrail(requisitos.horas_estimadas_desenvolvimento, regras_adm)
				membros_ranqueados = buscar_membros_vetorial_firestore(db, requisitos)

			with st.spinner("3/3 Montando Squads Multidisciplinares e Relatórios (Adm/Fin e Jurídico)..."):
				resultado_final = gerar_alocacao_e_propagacao(requisitos, membros_ranqueados, orcamento_travado)

				db.collection("historico_leads").add({
					"projeto": requisitos.nome_projeto,
					"requisitos": requisitos.model_dump(),
					"orcamento": orcamento_travado,
					"propagacao": resultado_final.model_dump()
				})

			st.success("✅ Processamento concluído e salvo no Firebase!")

			col1, col2 = st.columns(2)

			with col1:
				st.subheader(f"📋 Documento de Requisitos: {requisitos.nome_projeto}")
				st.write(f"**Complexidade:** {requisitos.complexidade} | **Esforço Estimado:** {requisitos.horas_estimadas_desenvolvimento}h")
				st.write(requisitos.resumo_executivo)
				st.markdown("**Stack Recomendada:** " + ", ".join([f"`{s}`" for s in requisitos.stack_sugerida]))

				st.markdown("**Requisitos Funcionais:**")
				for rf in requisitos.requisitos_funcionais:
					st.markdown(f"- {rf}")

				st.markdown("**Requisitos Não-Funcionais:**")
				for rnf in requisitos.requisitos_nao_funcionais:
					st.markdown(f"- {rnf}")

			with col2:
				st.subheader("🏛️ Propagação inter-diretorias (Guardrail Ativo)")
				st.info(
					f"💰 **Adm/Fin (Cálculo Travado por Guardrail):**\n\n"
					f"- **Esforço Considerado:** {orcamento_travado.get("horas_consideradas")}h (R\\$ {orcamento_travado.get("valor_hora_tabela")}/h)\n"
					f"- **Orçamento Base:** R\\$ {orcamento_travado.get("orcamento_base_calculado"):.2f}\n"
					f"- **Sugestão com Margem ({regras_adm.get("margem_seguranca_percentual")} %):** R\\$ {orcamento_travado.get("orcamento_com_margem_seguranca"):.2f}\n\n"
					f"{resultado_final.insumos_adm_fin}"
				)

				st.warning("⚖️ **Impacto Jurídico & Compliance:**\n" + "\n".join([f"- {item}" for item in resultado_final.impacto_juridico]))

			st.divider()
			st.subheader("👥 Múltiplas Sugestões de Equipes Multidisciplinares (Membros + Trainees)")

			with st.expander("🔍 Ver Score de Similaridade Vetorial (Embeddings) dos Membros Elegíveis:"):
				st.dataframe(membros_ranqueados, use_container_width=True)

			cols_squad = st.columns(len(resultado_final.opcoes_equipes))
			for idx, squad in enumerate(resultado_final.opcoes_equipes):
				with cols_squad[idx]:
					st.markdown(f"### 🏆 {squad.nome_squad}")
					st.caption(squad.foco_da_equipe)

					for m in squad.membros:
						st.markdown(f"**{m.nome}** ({m.cargo}) - *{m.papel_no_projeto}* \n 🎯 **Match Vetorial:** `{m.score_afinidade} %`")
						st.write(f"↳ {m.justificativa_tecnica}")
			
			relatorio_md = f"""# Documento de Projeto: {requisitos.nome_projeto}

**Complexidade:** {requisitos.complexidade} | **Horas Estimadas:** {requisitos.horas_estimadas_desenvolvimento}h

**Orçamento Base (Guardrail):** R\\$ {orcamento_travado.get("orcamento_base_calculado"):.2f} | **Com Margem:** R\\$ {orcamento_travado.get("orcamento_com_margem_seguranca"):.2f}

## 1. Resumo Executivo

{requisitos.resumo_executivo}

## 2. Stack Sugerida

{", ".join(requisitos.stack_sugerida)}

## 3. Requisitos Funcionais

{chr(10).join(["- " + r for r in requisitos.requisitos_funcionais])}

## 4. Requisitos Não-Funcionais

{chr(10).join(["- " + r for r in requisitos.requisitos_nao_funcionais])}

## 5. Parecer Adm/Fin

{resultado_final.insumos_adm_fin}

## 6. Parecer Jurídico & Compliance

{chr(10).join(["- " + j for j in resultado_final.impacto_juridico])}
"""

			st.download_button(
				label="📥 Baixar Documentação Completa (.md)",
				data=relatorio_md,
				file_name=f"Escopo_{requisitos.nome_projeto.replace(" ", "_")}.md",
				mime="text/markdown"
			)

with aba_banco:
	st.subheader("Membros Atuais e Trainees Sincronizados no Firestore")
	docs = db.collection("bugwares").stream()
	membros_lista = []
	for doc in docs:
		atual = doc.to_dict()
		atual["vetor_ativo"] = "✅ Sim (2048 dims)" if "embedding_skills" in atual else "❌ Não"
		atual.pop("embedding_skills", None)
		membros_lista.append(atual)

	st.dataframe(membros_lista, use_container_width=True)

	with st.expander("➕ Cadastrar Novo Membro ou Trainee (Gera Embedding Vetorial Automaticamente)"):
		with st.form("form_novo_bugware"):
			c1, c2, c3 = st.columns(3)

			nome = c1.text_input("Nome Completo")
			cargo = c2.selectbox("Cargo", ["Treinee", "Membro Efetivo"])
			status = c3.selectbox("Status Atual", ["Livre", "Passivamente Ocupado", "Ocupado"])

			c4, c5, c6 = st.columns(3)

			area = c4.selectbox("Área Principal", ["Backend", "Frontend", "Mobile", "UI/UX", "Dados/IA", "QA", "DevOps", "PM/PO"])
			nivel = c5.selectbox("Nível de Experiência", ["Trainee", "Junior", "Pleno", "Senior"])
			horas = c6.number_input("Horas Semanais Disponíveis", min_value=4, max_value=20, value=10)

			skills_str = st.text_input("Skills Técnicas (separadas por vírgula)", placeholder="Ex: PHP, Node.js, MySQL, Docker, Figma")
			salvar = st.form_submit_button("Salvar e Vetorizar no Firebase")

			if salvar and nome and skills_str:
				lista_skills = [s.strip() for s in skills_str.split(",") if s.strip()]
				perfil_texto = f"Área: {area}. Cargo: {cargo}. Habilidades técnicas: {', '.join(lista_skills)}"
				vetor = gerar_vetor(perfil_texto)

				novo = {
					"area": area,
					"cargo": cargo,
					"horas_disponiveis": horas,
					"nivel_experiencia": nivel,
					"nome": nome,
					"skills": lista_skills,
					"status": status,
					"embedding_skills": Vector(vetor)
				}

				db.collection("bugwares").add(novo)
				st.success(f"✅ {nome} ({cargo}) cadastrado e vetorizado no Firestore! Recarregue a página para atualizar.")

with aba_historico:
	st.subheader("Histórico de Leads e Propostas Geradas")
	historico_docs = db.collection("historico_leads").stream()

	for h in historico_docs:
		atual = h.to_dict()

		with st.expander(f"📌 {atual.get("projeto", "Projeto")} - Orçamento c/ Margem: R\\$ {atual.get("orcamento", {}).get("orcamento_com_margem_seguranca", 0)}"):
			st.json(atual)
