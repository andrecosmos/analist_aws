# seed.py
import sys
from pathlib import Path

# Injeta a raiz do projeto no PATH do Python
RAIZ_DO_PROJETO = Path(__file__).resolve().parent
if str(RAIZ_DO_PROJETO) not in sys.path:
    sys.path.insert(0, str(RAIZ_DO_PROJETO))

import os
import random
from datetime import datetime, timedelta
from decimal import Decimal
from sqlalchemy.orm import sessionmaker

# Importações limpas e corrigidas
from app.database.database import engine
from app.models.models import Base, Produto, Veiculo, Vendedor, CanalVenda, Venda

# ... a partir daqui vem a sua função def popular_banco(): ...

SessionLocal = sessionmaker(bind=engine)

def popular_banco():
    db = SessionLocal()
    print("🚀 Iniciando a inserção de dados de teste (Mock Data)...")
    
    try:
        # 1. Cadastrar Canais de Venda (Marketplaces e Direto)
        print("📺 Cadastrando Canais de Venda...")
        ml = CanalVenda(nome="Mercado Livre", taxa_percentual=11.5, taxa_fixa=Decimal("5.50"))
        shopee = CanalVenda(nome="Shopee", taxa_percentual=14.0, taxa_fixa=Decimal("3.00"))
        venda_direta = CanalVenda(nome="Balcão / Venda Direta", taxa_percentual=0.0, taxa_fixa=Decimal("0.00"))
        
        db.add_all([ml, shopee, venda_direta])
        db.flush() # Executa mas não commita ainda para pegar os IDs

        # 2. Cadastrar Vendedores Parceiros
        print("👥 Cadastrando Vendedores...")
        joao = Vendedor(nome="João Silva", comissao_percentual=2.5, ativo=1)
        maria = Vendedor(nome="Maria Souza", comissao_percentual=3.0, ativo=1)
        
        db.add_all([joao, maria])
        db.flush()

        # 3. Cadastrar Veículos para compatibilidade de autopeças
        print("🚗 Cadastrando Veículos...")
        gol = Veiculo(marca="Volkswagen", modelo="Gol", ano_inicio=2010, ano_fim=2015, motor="1.0 8V")
        uno = Veiculo(marca="Fiat", modelo="Uno", ano_inicio=2012, ano_fim=2018, motor="1.0 Fire")
        civic = Veiculo(marca="Honda", modelo="Civic", ano_inicio=2014, ano_fim=2020, motor="2.0 Flex")
        corolla = Veiculo(marca="Toyota", modelo="Corolla", ano_inicio=2015, ano_fim=2022, motor="2.0 VVT-i")
        
        db.add_all([gol, uno, civic, corolla])
        db.flush()

        # 4. Cadastrar Produtos (Autopeças) com margens e compatibilidades reais
        print("🔧 Cadastrando Produtos de Autopeças...")
        
        p1 = Produto(sku="PAST-GOL-01", nome="Pastilha de Freio Dianteira", estoque_atual=25, estoque_minimo=10, preco_custo=Decimal("45.00"), preco_venda_base=Decimal("120.00"))
        p1.veiculos_compativeis.append(gol)
        p1.veiculos_compativeis.append(uno) # Pastilhas universais/similares
        
        p2 = Produto(sku="FILT-OLE-02", nome="Filtro de Óleo Motor", estoque_atual=8, estoque_minimo=12, preco_custo=Decimal("15.00"), preco_venda_base=Decimal("40.00")) # Estoque baixo proposital para IA alertar
        p2.veiculos_compativeis.append(gol)
        
        p3 = Produto(sku="AMOR-CIV-03", nome="Kit Amortecedor Dianteira (Par)", estoque_atual=15, estoque_minimo=5, preco_custo=Decimal("280.00"), preco_venda_base=Decimal("650.00"))
        p3.veiculos_compativeis.append(civic)
        
        p4 = Produto(sku="VELA-COR-04", nome="Jogo de Velas de Ignição Iridium", estoque_atual=4, estoque_minimo=6, preco_custo=Decimal("110.00"), preco_venda_base=Decimal("290.00")) # Estoque baixo
        p4.veiculos_compativeis.append(corolla)

        db.add_all([p1, p2, p3, p4])
        db.flush()

        # 5. Gerar Histórico de Vendas Inteligente (Últimos 30 dias)
        print("📈 Gerando Histórico de Vendas com regras de comissão...")
        canais = [ml, shopee, venda_direta]
        vendedores = [joao, maria, None] # None para vendas automáticas de marketplace
        produtos = [p1, p2, p3, p4]

        # Vamos gerar exatamente 40 vendas aleatórias espalhadas no tempo
        for i in range(40):
            prod = random.choice(produtos)
            canal = random.choice(canais)
            
            # Regra de negócio: Se for marketplace, não tem vendedor humano associado
            if canal.nome in ["Mercado Livre", "Shopee"]:
                vendedor = None
            else:
                vendedor = random.choice([joao, maria]) # Venda direta no balcão tem vendedor

            qtd = random.randint(1, 2)
            preco_total = prod.preco_venda_base * qtd
            custo_total = prod.preco_custo * qtd
            
            # CÁLCULOS DE REGRAS DE NEGÓCIO (Feitos automaticamente pela nossa regra da API)
            # 1. Comissão do Marketplace
            comissao_mkt = (preco_total * Decimal(canal.taxa_percentual / 100)) + Decimal(canal.taxa_fixa)
            
            # 2. Comissão do Vendedor Humano
            comissao_vend = Decimal("0.00")
            if vendedor:
                comissao_vend = preco_total * Decimal(vendedor.comissao_percentual / 100)
            
            # 3. Lucro Líquido Real
            lucro = preco_total - custo_total - comissao_mkt - comissao_vend

            # Data retroativa para simular um gráfico de linha temporal estável
            data_aleatoria = datetime.utcnow() - timedelta(days=random.randint(0, 30))

            venda = Venda(
                data_venda=data_aleatoria,
                quantidade=qtd,
                preco_venda_total=preco_total,
                produto_id=prod.id,
                canal_venda_id=canal.id,
                vendedor_id=vendedor.id if vendedor else None,
                comissao_marketplace=comissao_mkt,
                comissao_vendedor=comissao_vend,
                lucro_liquido=lucro
            )
            db.add(venda)
        
        # Salva tudo de uma vez só na transação do Supabase
        db.commit()
        print("✨ Banco de dados populado com sucesso e conexões encerradas!")

    except Exception as e:
        db.rollback()
        print(f"❌ Erro ao popular banco de dados: {e}")
    finally:
        db.close()

if __name__ == "__main__":
    popular_banco()
