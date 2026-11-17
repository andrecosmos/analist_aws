# app_frontend.py
import streamlit as st
import requests
import pandas as pd

# Configuração da página do painel
st.set_page_config(
    page_title="Copiloto de Autopeças",
    page_icon="🔧",
    layout="wide"
)

API_BASE_URL = "http://127.0.0.1:8000"

st.title("🔧 Copiloto Inteligente de Autopeças")
st.caption("Painel analítico integrado ao Supabase e Inteligência Artificial")
st.markdown("---")

# --- CHAMADAS DE API (GET) ---
def buscar_dados_financeiros():
    try:
        response = requests.get(f"{API_BASE_URL}/analise/financeira")
        if response.status_code == 200:
            return response.json()
    except Exception:
        return None

def buscar_estoque_critico():
    try:
        response = requests.get(f"{API_BASE_URL}/estoque/critico")
        if response.status_code == 200:
            return response.json()
    except Exception:
        return None

def chamar_ia_reposicao():
    try:
        response = requests.get(f"{API_BASE_URL}/ia/sugestao-compra")
        if response.status_code == 200:
            return response.json()
    except Exception:
        return {"relatorio_ia": "Erro ao conectar com a Inteligência Artificial."}

# --- NOVA CHAMADA: Enviar venda para a FastAPI ---
def registrar_venda_api(payload):
    try:
        response = requests.post(f"{API_BASE_URL}/vendas", json=payload)
        return response.status_code, response.json()
    except Exception as e:
        return 500, {"detail": f"Erro de conexão com o servidor: {str(e)}"}


# ==========================================
# 🗂️ BARRA LATERAL: FORMULÁRIO DE NOVA VENDA
# ==========================================
st.sidebar.header("🛒 Registrar Nova Venda")
st.sidebar.write("Preencha os dados abaixo para lançar no sistema:")

with st.sidebar.form(key="form_venda", clear_on_submit=True):
    # IDs baseados no seed.py para facilitar a seleção do usuário
    produto_opcao = st.selectbox(
        "Selecione a Autopeça",
        options=[
            {"id": 1, "label": "Pastilha de Freio (Gol/Uno)"},
            {"id": 2, "label": "Filtro de Óleo Motor"},
            {"id": 3, "label": "Kit Amortecedor Dianteiro (Civic)"},
            {"id": 4, "label": "Jogo de Velas Iridium (Corolla)"}
        ],
        format_func=lambda x: x["label"]
    )
    
    canal_opcao = st.selectbox(
        "Canal de Venda",
        options=[
            {"id": 1, "label": "Mercado Livre (Taxa: 11.5% + R$5.50)"},
            {"id": 2, "label": "Shopee (Taxa: 14.0% + R$3.00)"},
            {"id": 3, "label": "Balcão / Venda Direta (Taxa: 0%)"}
        ],
        format_func=lambda x: x["label"]
    )
    
    # Só exibe vendedores se for Venda de Balcão (Canal ID 3) para respeitar a regra de negócio
    vendedor_id_final = None
    if canal_opcao["id"] == 3:
        vendedor_opcao = st.selectbox(
            "Vendedor Responsável",
            options=[
                {"id": 1, "label": "João Silva (2.5%)"},
                {"id": 2, "label": "Maria Souza (3.0%)"}
            ],
            format_func=lambda x: x["label"]
        )
        vendedor_id_final = vendedor_opcao["id"]
    else:
        st.info("💡 Vendas de marketplaces não comissionam vendedores humanos.")

    quantidade = st.number_input("Quantidade", min_value=1, max_value=50, value=1)
    preco_total = st.number_input("Preço Total da Venda (R$)", min_value=1.0, value=100.0, step=10.0)
    
    botao_enviar = st.form_submit_with_button_class = st.form_submit_button(label="🚀 Concluir e Calcular Lucro")

    if botao_enviar:
        # Monta o payload exatamente como o Pydantic espera na FastAPI
        payload_venda = {
            "produto_id": produto_opcao["id"],
            "canal_venda_id": canal_opcao["id"],
            "vendedor_id": vendedor_id_final,
            "quantidade": int(quantidade),
            "preco_venda_total": float(preco_total)
        }
        
        status_code, resposta = registrar_venda_api(payload_venda)
        
        if status_code == 201:
            st.sidebar.success("✅ Venda realizada com sucesso!")
            # Mostra o cálculo de lucro em tempo real retornado pela nossa FastAPI
            detalhes = resposta["detalhes_financeiros"]
            st.sidebar.write(f"**Lucro Líquido:** R$ {detalhes['lucro_liquido_real']:.2f}")
            st.sidebar.write(f"**Estoque Atualizado:** {detalhes['novo_estoque_produto']} un")
            # Força o Streamlit a recarregar a tela principal para atualizar os gráficos
            st.cache_data.clear()
        else:
            # Captura erros como "Estoque Insuficiente" direto da FastAPI
            erro_msg = resposta.get("detail", "Erro desconhecido.")
            st.sidebar.error(f"❌ Falha: {erro_msg}")


# ==========================================
# 📈 TELA PRINCIPAL: DASHBOARD ANALÍTICO
# ==========================================
# Recarrega os dados (se o cache limpou, ele busca os novos valores na hora)
dados_fin = buscar_dados_financeiros()
dados_est = buscar_estoque_critico()

if not dados_fin or not dados_est:
    st.error("❌ Não foi possível se conectar à API FastAPI. Verifique se o Uvicorn está rodando!")
else:
    # SEÇÃO 1: METRICAS GERAIS (CARDS)
    resumo = dados_fin["resumo_geral"]
    
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric(label="Faturamento Acumulado", value=f"R$ {resumo['faturamento_total_acumulado']:,.2f}")
    with col2:
        st.metric(label="Lucro Líquido Real", value=f"R$ {resumo['lucro_liquido_total_acumulado']:,.2f}")
    with col3:
        st.metric(label="Margem de Lucro Média", value=f"{resumo['margem_media_negocio_percentual']}%")

    st.markdown("---")

    # SEÇÃO 2: DESEMPENHO POR CANAL & PDF
    st.subheader("📋 Desempenho Comercial por Canal")
    
    df_canais = pd.DataFrame(dados_fin["desempenho_por_canal"])
    df_canais.columns = ["Canal de Venda", "Faturamento (R$)", "Comissões (R$)", "Lucro Líquido (R$)", "Margem (%)"]
    
    col_tabela, col_grafico = st.columns(2)
    
    with col_tabela:
        st.dataframe(df_canais, use_container_width=True, hide_index=True)
        st.markdown("### 📥 Exportar Dados")
        pdf_url = f"{API_BASE_URL}/analise/relatorio-pdf"
        st.link_button("📄 Baixar Relatório Completo em PDF", pdf_url, use_container_width=True)

    with col_grafico:
        st.bar_chart(
            df_canais, 
            x="Canal de Venda", 
            y=["Faturamento (R$)", "Lucro Líquido (R$)"], 
            color=["#3498db", "#2ecc71"]
        )

    st.markdown("---")

    # SEÇÃO 3: LOGÍSTICA & INTELIGÊNCIA ARTIFICIAL
    st.subheader("🧠 Logística Preditiva e Sugestão de Reposição")
    
    col_est, col_ia = st.columns(2)
    
    with col_est:
        st.warning(f"⚠️ Alerta: Existem {dados_est['total_produtos_para_comprar']} itens abaixo do estoque mínimo!")
        if dados_est['itens_necessarios']:
            df_est = pd.DataFrame(dados_est['itens_necessarios'])
            df_est.columns = ["SKU", "Item/Autopeça", "Estoque Atual", "Estoque Mínimo", "Faltando", "Custo (R$)", "Veículos Aplicados"]
            st.dataframe(df_est[["Item/Autopeça", "Estoque Atual", "Faltando", "Veículos Aplicados"]], use_container_width=True, hide_index=True)
        else:
            st.success("Estoque sob controle!")

    with col_ia:
        st.info("🤖 Pergunte ao Assistente de Compras Inteligente")
        if st.button("🪄 Gerar Relatório Estratégico com IA", use_container_width=True):
            with st.spinner("O Gemini está analisando os dados de vendas e estoque do mercado..."):
                resultado_ia = chamar_ia_reposicao()
                st.markdown("### 📝 Relatório da IA:")
                st.markdown(resultado_ia["relatorio_ia"])
