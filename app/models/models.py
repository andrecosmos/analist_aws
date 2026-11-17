from sqlalchemy import Column, Integer, String, Float, ForeignKey, DateTime, Numeric, Table
from sqlalchemy.orm import declarative_base, relationship
from datetime import datetime

Base = declarative_base()

# Tabela intermediária para relacionamento Muitos-para-Muitos (Um produto serve em vários carros, um carro usa vários produtos)
produto_veiculo = Table(
    'produto_veiculo',
    Base.metadata,
    Column('produto_id', Integer, ForeignKey('produtos.id'), primary_key=True),
    Column('veiculo_id', Integer, ForeignKey('veiculos.id'), primary_key=True)
)

class Veiculo(Base):
    __tablename__ = 'veiculos'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    marca = Column(String, nullable=False)   # Ex: Volkswagen
    modelo = Column(String, nullable=False)  # Ex: Gol
    ano_inicio = Column(Integer, nullable=False) # Ex: 2010
    ano_fim = Column(Integer, nullable=False)    # Ex: 2014
    motor = Column(String)                   # Ex: 1.0 8V
    
    produtos = relationship("Produto", secondary=produto_veiculo, back_populates="veiculos_compativeis")

class Vendedor(Base):
    __tablename__ = 'vendedores'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    nome = Column(String, nullable=False)
    comissao_percentual = Column(Float, default=0.0) # Comissão específica do vendedor (ex: 2.0 para 2%)
    ativo = Column(Integer, default=1) # 1 para ativo, 0 para inativo
    
    vendas = relationship("Venda", back_populates="vendedor")

class Produto(Base):
    __tablename__ = 'produtos'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    sku = Column(String, unique=True, nullable=False, index=True)
    nome = Column(String, nullable=False)
    estoque_atual = Column(Integer, default=0)
    estoque_minimo = Column(Integer, default=10)
    preco_custo = Column(Numeric(10, 2), nullable=False)
    preco_venda_base = Column(Numeric(10, 2), nullable=False)
    
    vendas = relationship("Venda", back_populates="produto")
    # Relacionamento com veículos
    veiculos_compativeis = relationship("Veiculo", secondary=produto_veiculo, back_populates="produtos")

class CanalVenda(Base):
    __tablename__ = 'canais_venda'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    nome = Column(String, unique=True, nullable=False) # Ex: Mercado Livre, Shopee, Venda Direta
    taxa_percentual = Column(Float, default=0.0)      # Taxa do Marketplace (ex: 11.5%)
    taxa_fixa = Column(Numeric(10, 2), default=0.0)    # Taxa fixa por venda do Marketplace (ex: R$ 5,50)
    
    vendas = relationship("Venda", back_populates="canal")

class Venda(Base):
    __tablename__ = 'vendas'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    data_venda = Column(DateTime, default=datetime.utcnow)
    quantidade = Column(Integer, nullable=False, default=1)
    preco_venda_total = Column(Numeric(10, 2), nullable=False)
    
    produto_id = Column(Integer, ForeignKey('produtos.id'), nullable=False)
    canal_venda_id = Column(Integer, ForeignKey('canais_venda.id'), nullable=False)
    vendedor_id = Column(Integer, ForeignKey('vendedores.id'), nullable=True) # Nullable=True porque vendas do ML não têm vendedor humano
    
    # Campos que sua API FastAPI vai calcular antes de salvar
    comissao_marketplace = Column(Numeric(10, 2), default=0.0)
    comissao_vendedor = Column(Numeric(10, 2), default=0.0)
    lucro_liquido = Column(Numeric(10, 2), nullable=False)

    produto = relationship("Produto", back_populates="vendas")
    canal = relationship("CanalVenda", back_populates="vendas")
    vendedor = relationship("Vendedor", back_populates="vendas")
