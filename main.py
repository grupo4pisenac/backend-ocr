from fastapi import FastAPI, File, HTTPException, UploadFile
from pydantic import BaseModel, Field
import pytesseract
from PIL import Image
import requests
from io import BytesIO
from dotenv import load_dotenv
import os
import re
import json
import cloudinary
import cloudinary.uploader
from pdf2image import convert_from_bytes

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

TIPOS_PERMITIDOS = {"image/jpeg", "image/jpg", "image/png", "application/pdf"}


app = FastAPI(
    title="Backend OCR - Horas Complementares",
    description=(
        "Servico de OCR para certificados de horas complementares. "
        "Use `/ocr/upload` para extrair dados antes da confirmacao do aluno "
        "e `/certificados/upload` para salvar o arquivo no Cloudinary apenas "
        "apos a confirmacao."
    ),
    version="1.0.0",
    contact={
        "name": "Grupo 4 PI Senac",
    },
    openapi_tags=[
        {
            "name": "Health",
            "description": "Verificacao basica do servico.",
        },
        {
            "name": "OCR",
            "description": "Extracao de texto e campos do certificado, sem upload para Cloudinary.",
        },
        {
            "name": "Certificados",
            "description": "Upload definitivo do certificado apos confirmacao do aluno.",
        },
    ],
)

class OcrRequest(BaseModel):
    url: str = Field(
        ...,
        examples=["https://exemplo.com/certificado.png"],
        description="URL publica da imagem que sera processada pelo OCR.",
    )

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

def normalizar_campos_llm(campos: dict, fallback: dict) -> dict:
    descricao = campos.get("descricao") or fallback["descricao"]
    area = campos.get("area")
    horas_solicitadas = campos.get("horasSolicitadas") or fallback["horasSolicitadas"]
    semestre = campos.get("semestre") or fallback["semestre"]

    try:
        horas_solicitadas = int(horas_solicitadas) if horas_solicitadas is not None else None
    except (TypeError, ValueError):
        horas_solicitadas = fallback["horasSolicitadas"]

    try:
        semestre = int(semestre) if semestre is not None else None
    except (TypeError, ValueError):
        semestre = fallback["semestre"]

    return {
        "descricao": descricao[:255] if isinstance(descricao, str) else fallback["descricao"],
        "area": area if isinstance(area, str) and area.strip() else None,
        "horasSolicitadas": horas_solicitadas,
        "semestre": semestre,
    }

def interpretar_texto_com_llm(texto: str, fallback: dict) -> dict:
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        return fallback

    model = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")
    prompt = f"""
Voce interpreta textos extraidos por OCR de certificados de horas complementares.

Retorne somente JSON valido, sem markdown e sem texto adicional, no formato:
{{
  "descricao": string ou null,
  "area": string ou null,
  "horasSolicitadas": number ou null,
  "semestre": number ou null
}}

Regras:
- "descricao" deve resumir o certificado em ate 255 caracteres.
- "area" deve ficar null se o texto nao informar explicitamente uma area.
- Nao invente area, porque as areas sao dinamicas no backend Java.
- "horasSolicitadas" deve ser um numero inteiro quando houver carga horaria.
- "semestre" deve ser 1 ou 2 quando for possivel inferir por data; caso contrario null.
- Se houver duvida, use null.

Texto do OCR:
{texto}
""".strip()

    try:
        response = requests.post(
            f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent",
            params={"key": api_key},
            json={
                "contents": [
                    {
                        "parts": [
                            {"text": prompt}
                        ]
                    }
                ],
                "generationConfig": {
                    "temperature": 0,
                    "responseMimeType": "application/json",
                },
            },
            timeout=20,
        )
        response.raise_for_status()
        data = response.json()
        texto_resposta = data["candidates"][0]["content"]["parts"][0]["text"]
        campos_llm = json.loads(texto_resposta)
        return normalizar_campos_llm(campos_llm, fallback)
    except Exception:
        return fallback

def processar_imagem(conteudo: bytes, content_type: str = "image/jpeg") -> tuple[str, dict]:
    if content_type == "application/pdf":
        paginas = convert_from_bytes(conteudo)
        imagem = paginas[0]  # processa apenas a primeira página
    else:
        imagem = Image.open(BytesIO(conteudo))
    
    texto = pytesseract.image_to_string(imagem, lang="por").strip()
    campos_fallback = extrair_campos(texto)
    campos = interpretar_texto_com_llm(texto, campos_fallback)
    return texto, campos

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

@app.get("/", tags=["Health"])
def health():
    return {"status": "ok"}

@app.post(
    "/ocr",
    tags=["OCR"],
    summary="Processa OCR a partir de uma URL publica",
    description="Endpoint auxiliar que baixa uma imagem por URL e extrai texto/campos. Nao envia arquivo ao Cloudinary.",
)
def processar_ocr(request: OcrRequest):

    try:
        headers = {
            "User-Agent": "MeuAppOcrFastAPI/1.0 (contato@meuemail.com)"
        }
        response = requests.get(request.url, headers=headers, timeout=10)
        response.raise_for_status()

        texto, campos = processar_imagem(conteudo, file.content_type)

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

@app.post(
    "/ocr/upload",
    tags=["OCR"],
    summary="Processa OCR do arquivo antes da confirmacao",
    description=(
        "Recebe o certificado selecionado pelo aluno e retorna campos para pre-preencher "
        "o formulario. Este endpoint nao salva o arquivo no Cloudinary.",
    ),
)
async def processar_upload(
    file: UploadFile = File(..., description="Imagem do certificado selecionada pelo aluno."),
):
    if not file.content_type or file.content_type not in TIPOS_PERMITIDOS:
        raise HTTPException(status_code=400, detail="Envie um arquivo nos formatos: JPG, PNG ou PDF")

    try:
        conteudo = await file.read()
        texto, campos = processar_imagem(conteudo, file.content_type)

        return {
            "success": True,
            "texto": texto,
            "campos": campos,
            "solicitacao": campos,
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erro ao processar upload: {str(e)}")

@app.post(
    "/certificados/upload",
    tags=["Certificados"],
    summary="Envia certificado ao Cloudinary apos confirmacao",
    description=(
        "Deve ser chamado somente depois que o aluno confirmar a submissao. "
        "Retorna `urlCertificado`, campo esperado pelo backend Java ao criar a solicitacao."
    ),
)
async def upload_certificado(
    file: UploadFile = File(..., description="Imagem do certificado confirmada pelo aluno."),
):  

    if not file.content_type or file.content_type not in TIPOS_PERMITIDOS:
        raise HTTPException(status_code=400, detail="Envie um arquivo nos formatos: JPG, PNG ou PDF")

    try:
        conteudo = await file.read()
        url_certificado = enviar_cloudinary(conteudo, file.filename)

        return {
            "success": True,
            "urlCertificado": url_certificado,
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erro ao enviar certificado: {str(e)}")
