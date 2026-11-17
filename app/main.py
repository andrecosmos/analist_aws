
from fastapi import FastAPI, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import func
from decimal import Decimal
from typing import List, Dict, Any
from fastapi.responses import FileResponse
import os
# Bibliotecas para gráficos e PDFs
import matplotlib
matplotlib.use('Agg')  # Configura para rodar em servidores sem interface gráfica
import matplotlib.pyplot as plt
import numpy as np
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Image, Table, TableStyle
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors

from google import genai 

from app.database.database import get_db
from app.models.models import Venda, CanalVenda, Produto, Veiculo
from app.schemas.schemas import VendaCreate 

app = FastAPI(
    title="API Inteligente de Autopeças",
    description="Análise financeira, comissões de marketplaces/vendedores e reposição preditiva.",
    version="1.0.0"
)

client = genai.Client()

@app.get("/")
def home():
    return {"status": "API Online", "projeto": "Análise de Autopeças & IA"}


@app.get("/analise/financeira", tags=["Análise de Dados"])
def obter_analise_financeira(db: Session = Depends(get_db)) -> Dict[str, Any]:
    """
    Retorna o faturamento, total de comissões pagas (marketplaces e vendedores)
    e o lucro líquido real acumulado por canal de venda.
    """
    # Consulta que agrupa vendas por Canal de Venda
    resultados = (
        db.query(
            CanalVenda.nome.label("canal"),
            func.sum(Venda.preco_venda_total).label("faturamento"),
            func.sum(Venda.comissao_marketplace).label("total_comissao_mkt"),
            func.sum(Venda.comissao_vendedor).label("total_comissao_vendedor"),
            func.sum(Venda.lucro_liquido).label("lucro_liquido")
        )
        .join(Venda, CanalVenda.id == Venda.canal_venda_id)
        .group_by(CanalVenda.nome)
        .all()
    )

    # Consolida os totais gerais do negócio
    faturamento_geral = Decimal("0.00")
    lucro_geral = Decimal("0.00")
    detalhe_canais = []

    for r in resultados:
        faturamento_geral += r.faturamento
        lucro_geral += r.lucro_liquido
        
        detalhe_canais.append({
            "canal": r.canal,
            "faturamento": float(r.faturamento),
            "comissoes_pagas": float(r.total_comissao_mkt + r.total_comissao_vendedor),
            "lucro_liquido": float(r.lucro_liquido),
            "margem_lucro_percentual": round((float(r.lucro_liquido) / float(r.faturamento)) * 100, 2) if r.faturamento > 0 else 0
        })

    return {
        "resumo_geral": {
            "faturamento_total_acumulado": float(faturamento_geral),
            "lucro_liquido_total_acumulado": float(lucro_geral),
            "margem_media_negocio_percentual": round((float(lucro_geral) / float(faturamento_geral)) * 100, 2) if faturamento_geral > 0 else 0
        },
        "desempenho_por_canal": detalhe_canais
    }


@app.get("/estoque/critico", tags=["Logística & Reposição"])
def verificar_estoque_critico(db: Session = Depends(get_db)):
    """
    Lista todos os produtos que estão abaixo do estoque mínimo estipulado,
    trazendo os veículos compatíveis para ajudar na tomada de decisão de compra.
    """
    produtos_criticos = (
        db.query(Produto)
        .filter(Produto.estoque_atual < Produto.estoque_minimo)
        .all()
    )

    relatorio = []
    for prod in produtos_criticos:
        # Mapeia os veículos compatíveis com essa autopeça
        veiculos = [f"{v.marca} {v.modelo} ({v.motor})" for v in prod.veiculos_compativeis]
        
        relatorio.append({
            "sku": prod.sku,
            "produto": prod.nome,
            "estoque_atual": prod.estoque_atual,
            "estoque_minimo_exigido": prod.estoque_minimo,
            "unidades_em_falta": prod.estoque_minimo - prod.estoque_atual,
            "preco_custo_atual": float(prod.preco_custo),
            "veiculos_aplicados": veiculos
        })

    return {
        "total_produtos_para_comprar": len(relatorio),
        "itens_necessarios": relatorio
    }


@app.get("/ia/sugestao-compra", tags=["Inteligência Artificial"])
def gerar_sugestao_compra_ia(db: Session = Depends(get_db)):
    """
    Usa IA (Gemini 2.5 Flash) para analisar os produtos em falta e os veículos aplicados, 
    gerando um plano estratégico de reposição textual para o dono da autopeças.
    """
    # 1. Reutiliza a lógica do banco para pegar os itens em estado crítico
    produtos_criticos = (
        db.query(Produto)
        .filter(Produto.estoque_atual < Produto.estoque_minimo)
        .all()
    )

    if not produtos_criticos:
        return {
            "mensagem": "Todos os produtos estão com estoque saudável. Nenhuma ação necessária da IA."
        }

    # 2. Formata os dados brutos do banco em um texto legível para o contexto da IA
    dados_estoque_texto = ""
    for prod in produtos_criticos:
        veiculos = [f"{v.marca} {v.modelo} ({v.motor})" for v in prod.veiculos_compativeis]
        dados_estoque_texto += (
            f"- SKU: {prod.sku}\n"
            f"  Produto: {prod.nome}\n"
            f"  Estoque Atual: {prod.estoque_atual} un (Mínimo exigido: {prod.estoque_minimo} un)\n"
            f"  Unidades em falta: {prod.estoque_minimo - prod.estoque_atual} un\n"
            f"  Preço de Custo Última Compra: R$ {prod.preco_custo}\n"
            f"  Veículos de Aplicação: {', '.join(veiculos)}\n\n"
        )

    # 3. Engenharia de Prompt: Define o papel (Persona) e as regras para a IA
    system_instruction = (
        "Você é um Gerente de Compras Sênior e Especialista em Logística no mercado de autopeças brasileiro. "
        "Seu objetivo é analisar dados de estoque e gerar relatórios executivos ultra-diretos, profissionais "
        "e focados em economia de capital e giro de estoque rápido."
    )

    prompt = (
        "Com base na lista de autopeças abaixo que estão com estoque CRÍTICO (abaixo do mínimo), "
        "gere um relatório de recomendação de compras para o dono da loja.\n\n"
        f"{dados_estoque_texto}\n"
        "Seu relatório deve conter:\n"
        "1. Um resumo executivo da gravidade geral da falta de peças.\n"
        "2. Análise item por item, explicando o impacto comercial de ficar sem essa peça baseado nos veículos que ela atende "
        "(ex: destacar se atende carros muito populares que rodam muito como Uber/táxi, como Gol e Uno).\n"
        "3. Uma sugestão de estratégia de negociação com as distribuidoras (ex: sugerir compra em lote de peças pequenas para conseguir frete grátis).\n\n"
        "Seja direto, use formatação markdown elegante e mantenha um tom corporativo e analítico."
    )

    try:
        # 4. Chamada oficial da API do Gemini usando o modelo recomendado
        response = client.models.generate_content(
            model="gemini-3.5-flash-lite",
            contents=prompt,
            config={"system_instruction": system_instruction}
        )
        
        return {
            "total_itens_analisados": len(produtos_criticos),
            "relatorio_ia": response.text
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=500, 
            detail=f"Falha ao comunicar com a Inteligência Artificial: {str(e)}"
        )
        
# app/main.py
from fastapi import FastAPI, Depends, HTTPException, status
from sqlalchemy.orm import Session
from decimal import Decimal

# Importe o seu esquema Pydantic (ajuste o caminho se necessário)
# from app.schemas.schemas import VendaCreate 
from app.database.database import get_db
from app.models.models import Venda, Produto, CanalVenda, Vendedor

# ... mantenha suas rotas antigas aqui ...

@app.post("/vendas", response_model=Dict[str, Any], tags=["Transacional"], status_code=status.HTTP_201_CREATED)
def cadastrar_venda(venda_in: VendaCreate, db: Session = Depends(get_db)):
    """
    Registra uma nova venda no sistema, calculando automaticamente as comissões
    do marketplace, as comissões do vendedor parceiro e o lucro líquido real.
    """
    # 1. Verificar se o produto existe e buscar o preço de custo atualizado
    produto = db.query(Produto).filter(Produto.id == venda_in.produto_id).first()
    if not produto:
        raise HTTPException(status_code=404, detail="Produto (Autopeça) não encontrado.")

    # 2. Verificar se o canal de venda existe e buscar as taxas cadastradas
    canal = db.query(CanalVenda).filter(CanalVenda.id == venda_in.canal_venda_id).first()
    if not canal:
        raise HTTPException(status_code=404, detail="Canal de venda não encontrado.")

    # 3. Validar estoque suficiente antes de concluir a venda
    if produto.estoque_atual < venda_in.quantidade:
        raise HTTPException(
            status_code=400, 
            detail=f"Estoque insuficiente. Estoque atual de {produto.nome}: {produto.estoque_atual} unidades."
        )

    # Convertendo os valores de entrada para Decimal para evitar erros de ponto flutuante
    preco_venda_total = Decimal(str(venda_in.preco_venda_total))
    custo_total_produto = produto.preco_custo * venda_in.quantidade

    # 4. CÁLCULO DE COMISSÃO DO MARKETPLACE (Se houver)
    comissao_mkt = (preco_venda_total * Decimal(str(canal.taxa_percentual / 100))) + canal.taxa_fixa

    # 5. CÁLCULO DE COMISSÃO DO VENDEDOR (Se houver)
    comissao_vend = Decimal("0.00")
    if venda_in.vendedor_id:
        vendedor = db.query(Vendedor).filter(Vendedor.id == venda_in.vendedor_id).first()
        if not vendedor:
            raise HTTPException(status_code=404, detail="Vendedor parceiro não encontrado.")
        if vendedor.ativo == 0:
            raise HTTPException(status_code=400, detail="Este vendedor está inativo no sistema.")
        
        comissao_vend = preco_venda_total * Decimal(str(vendedor.comissao_percentual / 100))

    # 6. CÁLCULO DO LUCRO LÍQUIDO REAL
    lucro_liquido = preco_venda_total - custo_total_produto - comissao_mkt - comissao_vend

    # 7. Criar a instância da nova venda
    nova_venda = Venda(
        produto_id=venda_in.produto_id,
        canal_venda_id=venda_in.canal_venda_id,
        vendedor_id=venda_in.vendedor_id,
        quantidade=venda_in.quantidade,
        preco_venda_total=preco_venda_total,
        comissao_marketplace=comissao_mkt,
        comissao_vendedor=comissao_vend,
        lucro_liquido=lucro_liquido
    )

    # 8. Dar baixa automática no estoque do produto vendido
    produto.estoque_atual -= venda_in.quantidade

    try:
        db.add(nova_venda)
        db.commit()
        db.refresh(nova_venda)
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Erro ao salvar a venda no Supabase: {str(e)}")

    return {
        "mensagem": "Venda registrada com sucesso!",
        "venda_id": nova_venda.id,
        "detalhes_financeiros": {
            "produto": produto.nome,
            "quantidade_vendida": nova_venda.quantidade,
            "preco_total_cobrado": float(preco_venda_total),
            "custo_total_pecas": float(custo_total_produto),
            "comissao_retida_marketplace": float(comissao_mkt),
            "comissao_vendedor_parceiro": float(comissao_vend),
            "lucro_liquido_real": float(lucro_liquido),
            "novo_estoque_produto": produto.estoque_atual
        }
    }

@app.get("/analise/relatorio-pdf", tags=["Análise de Dados"])
def gerar_relatorio_pdf(db: Session = Depends(get_db)):
    """
    Query de dados direto do Supabase, gera um gráfico dinâmico de performance,
    monta um PDF executivo estruturado e retorna o arquivo para download.
    """
    # 1. Buscar dados consolidados do Supabase
    resultados = (
        db.query(
            CanalVenda.nome.label("canal"),
            func.sum(Venda.preco_venda_total).label("faturamento"),
            func.sum(Venda.comissao_marketplace).label("comissao_mkt"),
            func.sum(Venda.comissao_vendedor).label("comissao_vend"),
            func.sum(Venda.lucro_liquido).label("lucro_liquido")
        )
        .join(Venda, CanalVenda.id == Venda.canal_venda_id)
        .group_by(CanalVenda.nome)
        .all()
    )

    if not resultados:
        raise HTTPException(status_code=404, detail="Não há dados de vendas suficientes para gerar o relatório.")

    # 2. Processar Listas para o Gráfico
    canais = [r.canal for r in resultados]
    faturamentos = [float(r.faturamento) for r in resultados]
    lucros = [float(r.lucro_liquido) for r in resultados]

    # Criar diretórios temporários para os arquivos se não existirem
    os.makedirs('temp', exist_ok=True)
    os.makedirs('generated', exist_ok=True)

    # 3. Gerar o Gráfico com Matplotlib
    x = np.arange(len(canais))
    width = 0.35

    fig, ax = plt.subplots(figsize=(6, 3.5))
    ax.bar(x - width/2, faturamentos, width, label='Faturamento (R$)', color='#3498db')
    ax.bar(x + width/2, lucros, width, label='Lucro Líquido (R$)', color='#2ecc71')

    ax.set_ylabel('Valores (R$)')
    ax.set_title('Desempenho Financeiro por Canal de Venda')
    ax.set_xticks(x)
    ax.set_xticklabels(canais)
    ax.legend()
    plt.tight_layout()

    chart_path = 'temp/desempenho_canais.png'
    plt.savefig(chart_path, dpi=300)
    plt.close()

    # 4. Construir o PDF Estruturado com ReportLab
    pdf_path = 'generated/relatorio_performance_autopecas.pdf'
    doc = SimpleDocTemplate(pdf_path, pagesize=letter, title="Relatório de Performance Financeira")
    story = []

    styles = getSampleStyleSheet()
    
    # Customização de estilos visuais elegantes
    title_style = ParagraphStyle('Title', parent=styles['Heading1'], fontSize=20, textColor=colors.HexColor('#2c3e50'), spaceAfter=15)
    subtitle_style = ParagraphStyle('Sub', parent=styles['Normal'], fontSize=10, textColor=colors.HexColor('#7f8c8d'), spaceAfter=20)
    header_style = ParagraphStyle('Header', parent=styles['Heading2'], fontSize=14, textColor=colors.HexColor('#2c3e50'), spaceBefore=15, spaceAfter=10)

    # Cabeçalho do Documento
    story.append(Paragraph("<b>📊 Relatório de Performance e Saúde Financeira</b>", title_style))
    story.append(Paragraph("Gerado automaticamente via API Inteligente de Autopeças • Dados Estruturados", subtitle_style))
    story.append(Spacer(1, 10))

    # Totais Gerais Calculados
    total_fat = sum(faturamentos)
    total_luc = sum(lucros)
    margem_med = (total_luc / total_fat * 100) if total_fat > 0 else 0

    # Tabela de Cards Resumo
    summary_data = [
        [Paragraph("<b>Faturamento Geral</b>", styles['Normal']), Paragraph("<b>Lucro Líquido Total</b>", styles['Normal']), Paragraph("<b>Margem Média</b>", styles['Normal'])],
        [Paragraph(f"<font size=14 color='#3498db'><b>R$ {total_fat:,.2f}</b></font>", styles['Normal']), 
         Paragraph(f"<font size=14 color='#2ecc71'><b>R$ {total_luc:,.2f}</b></font>", styles['Normal']), 
         Paragraph(f"<font size=14 color='#e67e22'><b>{margem_med:.1f}%</b></font>", styles['Normal'])]
    ]
    summary_table = Table(summary_data, colWidths=[180, 180, 140])
    summary_table.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), colors.HexColor('#f8f9fa')),
        ('ALIGN', (0,0), (-1,-1), 'CENTER'),
        ('GRID', (0,0), (-1,-1), 1, colors.HexColor('#e2e8f0')),
        ('TOPPADDING', (0,0), (-1,-1), 12),
        ('BOTTOMPADDING', (0,0), (-1,-1), 12),
    ]))
    story.append(summary_table)
    story.append(Spacer(1, 20))

    # Adicionar o Gráfico ao PDF
    story.append(Paragraph("📈 Análise Visual por Canal de Venda", header_style))
    story.append(Image(chart_path, width=450, height=262))
    story.append(Spacer(1, 15))

    # Tabela Detalhada de Resultados
    story.append(Paragraph("📋 Detalhamento de Resultados", header_style))
    table_data = [['Canal', 'Faturamento', 'Comissões', 'Lucro Líquido', 'Margem']]
    
    for r in resultados:
        comissao_total = r.comissao_mkt + r.comissao_vend
        margem = (float(r.lucro_liquido) / float(r.faturamento) * 100) if r.faturamento > 0 else 0
        table_data.append([
            r.canal,
            f"R$ {float(r.faturamento):,.2f}",
            f"R$ {float(comissao_total):,.2f}",
            f"R$ {float(r.lucro_liquido):,.2f}",
            f"{margem:.2f}%"
        ])

    detailed_table = Table(table_data, colWidths=[130, 95, 95, 100, 80])
    detailed_table.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), colors.HexColor('#2c3e50')),
        ('TEXTCOLOR', (0,0), (-1,0), colors.whitesmoke),
        ('ALIGN', (0,0), (-1,0), 'CENTER'),
        ('BOTTOMPADDING', (0,0), (-1,-1), 8),
        ('TOPPADDING', (0,0), (-1,-1), 8),
        ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor('#cbd5e1')),
        ('ROWBACKGROUNDS', (0,1), (-1,-1), [colors.white, colors.HexColor('#f8f9fa')])
    ]))
    story.append(detailed_table)

    # Nota de Rodapé
    story.append(Spacer(1, 25))
    story.append(Paragraph("<font size=8 color='#95a5a6'>Este relatório consolida métricas geradas via agregação de banco de dados e regras de negócio. Destinado exclusivamente para suporte à tomada de decisão empresarial.</font>", styles['Normal']))

    # Compila o PDF
    doc.build(story)

    # 5. Retorna o arquivo gerado para download
    return FileResponse(
        path=pdf_path, 
        filename="relatorio_performance_financeira.pdf", 
        media_type="application/pdf"
    )