from pydantic import BaseModel
from typing import Optional

class VendaCreate(BaseModel):
    produto_id: int
    canal_venda_id: int
    vendedor_id: Optional[int] = None  # Pode ser None se for venda automática de marketplace
    quantidade: int
    preco_venda_total: float

    class Config:
        from_attributes = True
