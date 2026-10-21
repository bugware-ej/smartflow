# Bugware SmartFlow

Prova de Conceito para o desafio V360 (disponível em `assets/Kick-off Batalha de Inovação Conecta v360.pdf`).

## Inicialização

Para inicializar o projeto, é necessário criar o arquivo `.env` baseado no arquivo `.env.example` e inserindo os dados apropriados para o ambiente de desenvolvimento/produção.

> [!note]
> Sugere-se fortemente o uso do modelo 'gemini-3.8-flash' pela leveza e qualidade satisfatória do resultado.

Além disso, também é necessário a chave do *Firebase*, crie um arquivo chamado `firebase_key.json` e hidráte-o com os dados de configuração do banco.

Para a utilização do ambiente virtual do python, é necessário criá-lo e ativá-lo:

```sh
# Criar o ambiente virtual
python -m venv venv

# Ativar o ambiente virtual
source venv/bin/activate
```

> [!tip]
> Para saber que o ambiente virtual está ativo, no terminal aparecerá (venv)

Para baixar as dependências do projeto, utilize o seguinte comando:

```sh
pip install -r requirements.txt
```

Por fim, para inicializar a página web do projeto, utilize o seguinte comando (note que a rota ficará disponível na mensagem do terminal):

```sh
streamlit run app.py
```

## Coleções

```json
"bugwares": {
	"nome": "string",
	"cargo": "string",
	"status": "livre" | "passivamente ocupado" | "ocupado",
	"area": "frontend" | "backend" | "mobile" | "ux/ui" | "dados" | "qa" | "pm/po" | "tech lead",
	"habilidades": [""],
	"nivel_experiencia": "trainee" | "junior" | "pleno" | "senior",
	"horas_disponiveis": "number"
}

"regras_negocio": {
	"adm_fin": {
		"valor_hora": "number",
		"margem_seguranca_percentual": "number",
		"horas_minimas_projeto": "number"
	},
	"precificacao": {
		"valor_hora_base": "number",
		"taxa_urgencia": "number",
		"custo_fixo_infra": "number"
	}
}
```
