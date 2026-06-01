from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
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