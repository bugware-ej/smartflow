import streamlit as st
import firebase_admin
from firebase_admin import credentials, firestore
from google.cloud.firestore_v1.vector import Vector
from ai_engine import (
	extrair_requisitos_lead,
	calcular_orcamento_guardrail,
	buscar_membros_vetorial_firestore,
	gerar_alocacao_e_propagacao,
	gerar_vetor,
	gerar_relatorio_md,
	gerar_relatorio_pdf,
	HistoricoLeads
)

if not firebase_admin._apps:
	cred = credentials.Certificate("firebase_key.json")
	firebase_admin.initialize_app(cred)

db = firestore.client()

st.set_page_config(
	page_title="Bugware SmartFlow | Desafio V360",
	page_icon="👾",
	layout="wide"
)

with st.sidebar:
	st.markdown("## 🛡️ Painel de Governança IA")
	st.success("🟢 **API Gemini:** Conectada")
	st.success("🟢 **Vector DB:** Firestore KNN Ativo")

	negocio = db.collection("regras_negocio").document("adm_fin").get().to_dict()

	st.info(
		"**Guardrails Ativos no Código:**\n"
		"- 🔒 **Alocação:** Bloqueio de membros 'Ocupados' ou com '0h' disponíveis.\n"
		f"- 💰 **Adm/Fin:** Piso de {negocio.get("horas_minimas_projeto", 40)}h, R$ {negocio.get("valor_hora", 45)}/h e margem fixa de {negocio.get("margem_seguranca_percentual", 15)}%.\n"
		"- ⚖️ **Compliance:** Verificação LGPD e Propriedade Intelectual."
	)

	st.divider()
	st.metric(icon="⏱️", label="**Tempo Médio Antes (Manual)**", value="~4 dia(s)", delta="Gargalo Comercial", delta_color="inverse")
	st.metric(icon="⚡", label="**Tempo com SmartFlow**", value="5 minuto(s)", delta="- 99.91% no tempo de resposta", delta_color="inverse")

st.title("👾 Bugware SmartFlow - Copiloto de Requisitos, Alocação e Governança")
st.caption("Desafio de Inovação Conecta V360 - Trilha B (Tecnologia & TI) | Python + Firebase Vector DB + Gemini API")

aba_copiloto, aba_banco, aba_historico = st.tabs([
	"🤖 Processar Novo Lead",
	"🗄️ Banco de Bugwares (Firebase + Vector DB)",
	"📂 Histórico de Projetos"
])

with aba_copiloto:
	if "texto_lead" not in st.session_state:
		st.session_state.texto_lead = ""
	
	col_btn_demo, _ = st.columns([1, 1])

	if col_btn_demo.button("📋 Preencher com Caso de Exemplo"):
		st.session_state.texto_lead = (
			"# Reunião de Alinhamento Inicial - ReparaCAR\n\n"
			"Duração: 72 minutos.\n\n"
			"Demanda do Cliente: Desenvolvimento de um aplicativo mobile nativo para sistema Android, focado no segmento emergente de mobilidade elétrica (carros e motos). "
			"O ecossistema da aplicação deve contemplar:\n\n"
			"\t1. **Gestão e Lembretes Preventivos:** cadastro e gerenciamento de veículos elétricos (motos e carros); "
			"alertas e lembretes inteligentes configurados para revisões periódicas e manutenção preventiva de componentes específicos (ex: saúde da bateria, sistema de arrefecimento do inversor, pastilha de freio regenerativo, calibração e desgaste ded pneus).\n\n"
			"\t2. **Rede de Parceiros e Serviços:** mapeamento e exibição de **lojas de autopeças parceiras** integradas ao app para compra direta ou consulta de itens e peças de reposição; "
			"catálogo e geolocalização de oficinas e **redes autorizadas** para agendamento de serviços e reparos especializados em veículos elétricos; "
			"alerta para baterias fraca e recomendações de postos de carregamento elétrico próximos (proporcionalmente à quantidade de bateria e autonomia restante)."
		)

	anotacoes = st.text_area(
		"📝 Cole aqui a transcrição ou anotações da Reunião de Diagnósticos com o Lead:",
		value=st.session_state.texto_lead,
		height=320,
		placeholder="Ex: Reunião de Alinhamento - Empresa XPTO..."
	)

	if st.button("⚡ Gerar Documentação, Alocar Equipes e Propagar para Diretorias", type="primary", use_container_width=True):
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
				historico_gerado = HistoricoLeads(
					orcamento=orcamento_travado,
					projeto=requisitos.nome_projeto,
					propagacao=resultado_final.model_dump(),
					requisitos=requisitos.model_dump()
				)

				db.collection("historico_leads").add({
					"projeto": requisitos.nome_projeto,
					"requisitos": requisitos.model_dump(),
					"orcamento": orcamento_travado,
					"propagacao": resultado_final.model_dump()
				})

			st.success("✅ Processamento concluído e salvo no Firebase!")

			k1, k2, k3, k4 = st.columns(4)

			k1.metric("Complexidade Técnica", requisitos.complexidade)
			k2.metric("Esforço Estimado", f"{orcamento_travado.get("horas_consideradas", 0)} horas")
			k3.metric("Orçamento Base (Adm/Fin)", f"R\\$ {orcamento_travado.get("orcamento_base_calculado", 0):.2f}")
			k4.metric(f"Com Margem de Segurança ({regras_adm.get("margem_seguranca_percentual", 0)}%)", f"R\\$ {orcamento_travado.get("orcamento_com_margem_seguranca" , 0):.2f}")

			st.divider()

			col1, col2 = st.columns(2)

			with col1:
				st.subheader(f"📋 Documento de Requisitos: {requisitos.nome_projeto}")
				# st.write(f"**Complexidade:** {requisitos.complexidade} | **Esforço Estimado:** {requisitos.horas_estimadas_desenvolvimento}h")
				st.write(requisitos.resumo_executivo)
				st.markdown("**Stack Recomendada:** " + ", ".join([f"`{s}`" for s in requisitos.stack_sugerida]))

				st.markdown("**Requisitos Funcionais:**")
				for rf in requisitos.requisitos_funcionais:
					st.markdown(f"- {rf}")

				st.markdown("**Requisitos Não-Funcionais:**")
				for rnf in requisitos.requisitos_nao_funcionais:
					st.markdown(f"- {rnf}")

			with col2:
				st.subheader("🏛️ Propagação Inter-Diretorias (Guardrail Ativo)")
				st.info(
					# f"💰 **Adm/Fin (Cálculo Travado por Guardrail):**\n\n"
					# f"- **Esforço Considerado:** {orcamento_travado.get("horas_consideradas")}h (R\\$ {orcamento_travado.get("valor_hora_tabela")}/h)\n"
					# f"- **Orçamento Base:** R\\$ {orcamento_travado.get("orcamento_base_calculado"):.2f}\n"
					# f"- **Sugestão com Margem ({regras_adm.get("margem_seguranca_percentual")} %):** R\\$ {orcamento_travado.get("orcamento_com_margem_seguranca"):.2f}\n\n"
					f"💰 **Parecer Diretoria Adm/Fin (Travado por Guardrail):**\n\n"
					f"{resultado_final.insumos_adm_fin}"
				)

				st.warning("⚖️ **Impacto Jurídico & Compliance:**\n" + "\n".join([f"- {item}" for item in resultado_final.impacto_juridico]))

			st.divider()
			st.subheader("👥 Múltiplas Sugestões de Equipes Multidisciplinares (Membros + Trainees)")

			with st.expander("🔍 Auditoria do Banco Vetorial: Ver Score de Similaridade Vetorial (Embeddings) dos Membros Elegíveis:"):
				st.dataframe(membros_ranqueados, use_container_width=True)

			cols_squad = st.columns(len(resultado_final.opcoes_equipes))
			for idx, squad in enumerate(resultado_final.opcoes_equipes):
				with cols_squad[idx]:
					st.markdown(f"### 🏆 {squad.nome_squad}")
					st.caption(squad.foco_da_equipe)

					for m in squad.membros:
						st.markdown(f"**{m.nome}** ({m.cargo}) - *{m.papel_no_projeto}*  \n🎯 **Match Vetorial:** `{m.score_afinidade} %`")
						st.write(f"↳ {m.justificativa_tecnica}")

			st.download_button(
				label="📥 Baixar Documentação Completa (.md)",
				data=gerar_relatorio_md(historico_gerado),
				file_name=f"Escopo_{requisitos.nome_projeto.replace(" ", "_")}.md",
				mime="text/markdown",
				use_container_width=True,
				on_click="ignore"
			)

with aba_banco:
	st.subheader("👥 Membros Atuais e Trainees Sincronizados no Firestore")
	docs = db.collection("bugwares").stream()
	membros_lista = []
	for doc in docs:
		atual = doc.to_dict()
		atual["vetor_ativo"] = "✅ Sim (2048 dims)" if "embedding_skills" in atual else "❌ Não"
		atual.pop("embedding_skills", None)
		membros_lista.append(atual)

	livres = sum(1 for m in membros_lista if str(m.get("status", "")).lower() == "livre")
	trainees = sum(1 for m in membros_lista if str(m.get("cargo", "")).lower() == "trainee")

	c_m1, c_m2, c_m3 = st.columns(3)
	
	c_m1.metric("Total de Bugwares no Banco", len(membros_lista))
	c_m2.metric("Membros/Trainees Livres", livres)
	c_m3.metric("Trainees para Capacitação", trainees)

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

				db.collection("bugwares").add({
					"area": area,
					"cargo": cargo,
					"horas_disponiveis": horas,
					"nivel_experiencia": nivel,
					"nome": nome,
					"skills": lista_skills,
					"status": status,
					"embedding_skills": Vector(vetor)
				})
				st.success(f"✅ {nome} ({cargo}) cadastrado e vetorizado no Firestore! Recarregue a página para atualizar.")

with aba_historico:
	st.subheader("Histórico de Leads e Propostas Geradas no Firebase")
	historico_docs = db.collection("historico_leads").stream()

	for h in historico_docs:
		id = h.id
		dicionario = h.to_dict()
		atual = HistoricoLeads.from_dict(dicionario)
		orcamento = atual.orcamento

		with st.expander(f"📌 {atual.projeto} | Esforço: {orcamento.horas_consideradas}h | Orçamento c/ Margem: R\\$ {orcamento.orcamento_com_margem_seguranca}"):
			st.download_button(
				label="📥 Baixar Documentação Completa do Projeto (.md)",
				data=gerar_relatorio_md(atual),
				file_name=f"Escopo_{atual.requisitos.nome_projeto.replace(" ", "_")}.md",
				mime="text/markdown",
				use_container_width=True,
				key="md-" + id,
				on_click="ignore"
			)

			# st.download_button(
			# 	label="📥 Baixar Documentação Completa do Projeto (.pdf)",
			# 	data=gerar_relatorio_pdf(atual),
			# 	file_name=f"Escopo_{atual.requisitos.nome_projeto.replace(" ", "_")}.pdf",
			# 	mime="application/pdf",
			# 	use_container_width=True,
			# 	key="odt-" + id,
			# 	on_click="ignore"
			# )

			st.json(atual.json())
