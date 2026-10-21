import streamlit as st
import firebase_admin
from firebase_admin import credentials, firestore
from ai_engine import (
	extrair_requisitos_lead,
	aplicar_guardrails_membros,
	calcular_orcamento_guardrail,
	ranquear_membros_por_embeddings,
	gerar_alocacao_e_propagacao
)

if not firebase_admin._apps:
	cred = credentials.Certificate("firebase_key.json")
	firebase_admin.initialize_app(cred)

db = firestore.client()

st.set_page_config(page_title="Bugware SmartFlow | Desafio V360", layout="wide")
st.title("🚀 Bugware SmartFlow - Copiloto de Requisitos, Alocação e Governança")
st.caption("Desafio de Inovação Conecta V360 - Trilha B (Tecnologia e TI)")

aba_copiloto, aba_banco = st.tabs(["🤖 Processar Novo Lead", "🗄️ Banco de Bugwares (Firebase)"])

with aba_banco:
	st.subheader("Membros Atuais e Trainees Sincronizados no Firestore")
	docs = db.collection("bugwares").stream()
	membros_lista = [doc.to_dict() for doc in docs]
	st.dataframe(membros_lista, use_container_width=True)

with aba_copiloto:
	anotacoes = st.text_area(
		"📝 Cole aqui a transcrição ou anotações da Reunião de Diagnósticos com o Lead:",
		height=160,
		placeholder="Ex: O cliente precisa de um aplicativo mobile para Android e iOS onde alunos com deficiência visual possam tirar foto de fórmulas químicas e ouvir a descrição em áudio. Precisa ter login e salvar histórico na nuvem..."
	)

	if st.button("⚡ Gerar Documentação, Alocar Equipes e Propagar para Diretorias", type="primary"):
		if not anotacoes.strip():
			st.warning("Insira as anotações do Lead primeiro.")
		else:
			with st.spinner("1/3 Extraindo requisitos técnicos com Gemini API..."):
				requisitos = extrair_requisitos_lead(anotacoes)

			with st.spinner("2/3 Aplicando Guardrails e Busca Vetorial no Firebase..."):
				membros_brutos = [doc.to_dict() for doc in db.collection("bugwares").stream()]
				regras_doc = db.collection("regras_negocio").document("adm_fin").get()
				regras_adm = regras_doc.to_dict() if regras_doc.exists else { "valor_hora": 45.0, "margem_seguranca_percentual": 15, "horas_minimas_projeto": 40 }

				membros_elegiveis = aplicar_guardrails_membros(membros_brutos)
				orcamento_travado = calcular_orcamento_guardrail(requisitos.horas_estimadas_desenvolvimento, regras_adm)

				membros_ranqueados = ranquear_membros_por_embeddings(requisitos, membros_elegiveis)

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

			with col2:
				st.subheader("🏛️ Propagação inter-diretorias (Guardrail Ativo)")
				st.info(f"💰 **Adm/Fin (Cálculo Travado por Guardrail):**\n\n" +
				f"- **Orçamento Base:** R\$ {orcamento_travado['orcamento_base_calculado']}\n" +
				f"- **Sugestão com Margem ({regras_adm.get('margem_seguranca_percentual')} %):** R\$ {orcamento_travado['orcamento_com_margem_seguranca']}\n\n" +
				f"{resultado_final.insumos_adm_fin}")

				st.warning("⚖️ **Impacto Jurídico & Compliance:**\n" + "\n".join([f"- {item}" for item in resultado_final.impacto_juridico]))

			st.divider()
			st.subheader("👥 Múltiplas Sugestões de Equipes Multidisciplinares (Membros + Trainees)")
			cols_squad = st.columns(len(resultado_final.opcoes_equipes))

			for idx, squad in enumerate(resultado_final.opcoes_equipes):
				with cols_squad[idx]:
					st.markdown(f"### 🏆 {squad.nome_squad}")
					st.caption(squad.foco_da_equipe)

					for m in squad.membros:
						st.markdown(f"**{m.nome}** ({m.cargo}) - *{m.papel_no_projeto}*")
						st.write(f"↳ {m.justificativa_tecnica}")
