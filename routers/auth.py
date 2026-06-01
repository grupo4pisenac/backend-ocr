from fastapi import APIRouter, Depends, BackgroundTasks, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel, EmailStr
from passlib.context import CryptContext
from datetime import datetime

from database import get_db
from models import Usuario
from auth.password_reset import gerar_token_reset, enviar_email_reset

router = APIRouter(prefix="/auth", tags=["auth"])
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

class ForgotPasswordRequest(BaseModel):
    email: EmailStr

class ResetPasswordRequest(BaseModel):
    token:      str
    nova_senha: str

@router.post("/forgot-password", status_code=200)
def forgot_password(
    payload:          ForgotPasswordRequest,
    background_tasks: BackgroundTasks,
    db:               Session = Depends(get_db),
):
    usuario = db.query(Usuario).filter(Usuario.email == payload.email).first()

    if usuario:
        token, expira_em = gerar_token_reset()
        usuario.reset_token         = token
        usuario.reset_token_expires = expira_em
        db.commit()
        background_tasks.add_task(enviar_email_reset, payload.email, token)

    return {"message": "Se o e-mail estiver cadastrado, você receberá as instruções em breve."}

@router.post("/reset-password", status_code=200)
def reset_password(
    payload: ResetPasswordRequest,
    db:      Session = Depends(get_db),
):
    usuario = db.query(Usuario).filter(Usuario.reset_token == payload.token).first()

    if not usuario:
        raise HTTPException(status_code=400, detail="Token inválido ou expirado.")

    if usuario.reset_token_expires < datetime.utcnow():
        raise HTTPException(status_code=400, detail="Token expirado. Solicite um novo.")

    usuario.senha               = pwd_context.hash(payload.nova_senha)
    usuario.reset_token         = None
    usuario.reset_token_expires = None
    db.commit()

    return {"message": "Senha redefinida com sucesso."}