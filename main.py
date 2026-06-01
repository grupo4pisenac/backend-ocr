from fastapi import FastAPI, File, HTTPException, UploadFile
from pydantic import BaseModel
import pytesseract
from PIL import Image
import requests
from io import BytesIO
from dotenv import load_dotenv
import os
import re
import cloudinary
import cloudinary.uploader

load_dotenv()

tesseract_cmd = os.getenv("TESSERACT_CMD")
if tesseract_cmd:
    pytesseract.pytesseract.tesseract_cmd = tesseract_cmd

cloudinary.config(
    cloud_name=os.getenv("CLOUDINARY_CLOUD_NAME"),
    api_key=os.getenv("CLOUDINARY_API_KEY"),
    api_secret=os.getenv("CLOUDINARY_API_SECRET"),
    secure=True,
)

app = FastAPI()

class OcrRequest(BaseModel):
    url: str

def normalizar_texto(texto: str) -> str:
    return " ".join(texto.split())

def extrair_descricao(texto: str) -> str | None:
    linhas = [linha.strip() for linha in texto.splitlines() if linha.strip()]
    for linha in linhas:
        if len(linha) >= 12:
            return linha[:255]
    return normalizar_texto(texto)[:255] or None

def extrair_horas(texto: str) -> int | None:
    match = re.search(
        r"(\d{1,3})\s*(?:h|hora|horas|horas-aula|hrs)\b",
        texto,
        re.IGNORECASE,
    )
    return int(match.group(1)) if match else None

def extrair_semestre(texto: str) -> int | None:
    semestre_match = re.search(
        r"\b(?:semestre|periodo)\D*([1-9])\b",
        texto,
        re.IGNORECASE,
    )
    if semestre_match:
        return int(semestre_match.group(1))

    data_match = re.search(r"\b\d{2}/(\d{2})/\d{4}\b", texto)
    if data_match:
        mes = int(data_match.group(1))
        return 1 if mes <= 6 else 2

    return None

def extrair_campos(texto: str) -> dict:
    return {
        "descricao": extrair_descricao(texto),
        "area": None,
        "horasSolicitadas": extrair_horas(texto),
        "semestre": extrair_semestre(texto),
    }

def processar_imagem(conteudo: bytes) -> tuple[str, dict]:
    imagem = Image.open(BytesIO(conteudo))
    texto = pytesseract.image_to_string(imagem, lang="por").strip()
    return texto, extrair_campos(texto)

def enviar_cloudinary(conteudo: bytes, filename: str | None = None) -> str:
    if not all([
        os.getenv("CLOUDINARY_CLOUD_NAME"),
        os.getenv("CLOUDINARY_API_KEY"),
        os.getenv("CLOUDINARY_API_SECRET"),
    ]):
        raise HTTPException(
            status_code=500,
            detail="Credenciais do Cloudinary nao configuradas",
        )

    resultado = cloudinary.uploader.upload(
        conteudo,
        folder=os.getenv("CLOUDINARY_FOLDER", "certificados"),
        resource_type="auto",
        public_id=os.path.splitext(filename)[0] if filename else None,
        overwrite=False,
    )
    return resultado["secure_url"]

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

        texto, campos = processar_imagem(response.content)

        return {
            "success": True,
            "texto": texto,
            "campos": campos,
            "solicitacao": campos,
        }
    except requests.exceptions.RequestException as e:
        raise HTTPException(status_code=400, detail=f"Erro ao baixar imagem: {str(e)}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erro ao processar OCR: {str(e)}")

@app.post("/ocr/upload")
async def processar_upload(file: UploadFile = File(...)):
    if not file.content_type or not file.content_type.startswith("image/"):
        raise HTTPException(status_code=400, detail="Envie um arquivo de imagem")

    try:
        conteudo = await file.read()
        texto, campos = processar_imagem(conteudo)
        cloudinary_url = enviar_cloudinary(conteudo, file.filename)

        return {
            "success": True,
            "texto": texto,
            "campos": campos,
            "solicitacao": {
                **campos,
                "urlCertificado": cloudinary_url,
            },
            "urlCertificado": cloudinary_url,
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erro ao processar upload: {str(e)}")
