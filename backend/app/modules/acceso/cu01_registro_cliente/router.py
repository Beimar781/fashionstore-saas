from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.modules.acceso.cu01_registro_cliente import schemas
from app.modules.acceso.cu01_registro_cliente.service import RegistroClienteService
from app.modules.acceso.cu02_login.schemas import TokenOut

router = APIRouter(prefix="/auth", tags=["CU-01 Registrar cuenta de cliente"])


@router.post("/registro", response_model=TokenOut, status_code=201)
def registrar_cliente(datos: schemas.RegistroClienteIn, db: Session = Depends(get_db)):
    """Crea la cuenta de un Cliente en la empresa indicada y devuelve la sesión iniciada."""
    return RegistroClienteService(db).registrar(datos)
