from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from routers.auth import router as auth_router
import pytesseract
from PIL import Image
import requests
from io import BytesIO
from dotenv import load_dotenv
import os

load_dotenv()

tesseract_cmd = os.getenv("TESSERACT_CMD")
if tesseract_cmd:
    pytesseract.pytesseract.tesseract_cmd = tesseract_cmd

app = FastAPI()

class OcrRequest(BaseModel):
    url: str

@app.get("/")
def health():
    return {"status": "ok"}

@app.post("/ocr")
def processar_ocr(request: OcrRequest):

    try:
        headers = {
            "User-Agent": "MeuAppOcrFastAPI/1.0 (contato@meuemail.com)"
        }
        response = requests.get(request.url, headers=headers, timeout=10)
        response.raise_for_status()

        imagem = Image.open(BytesIO(response.content))
        texto = pytesseract.image_to_string(imagem, lang="por")

        return {
            "success": True,
            "texto": texto.strip()
        }
    except requests.exceptions.RequestException as e:
        raise HTTPException(status_code=400, detail=f"Erro ao baixar imagem: {str(e)}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erro ao processar OCR: {str(e)}")
    

from auth.password_reset import (
    ForgotPasswordRequest, ResetPasswordRequest,
    solicitar_reset, redefinir_senha
)
from database import get_db
from sqlalchemy.orm import Session
from fastapi import Depends

@app.post("/auth/forgot-password")
def forgot_password(request: ForgotPasswordRequest, db: Session = Depends(get_db)):
    return solicitar_reset(db, request.email)

@app.post("/auth/reset-password")
def reset_password(request: ResetPasswordRequest, db: Session = Depends(get_db)):
    return redefinir_senha(db, request.token, request.nova_senha)

# LINHA ADICIONADA — registra as rotas /auth/forgot-password e /auth/reset-password
app.include_router(auth_router)