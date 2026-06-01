## Deploy

A API esta disponivel em producao no Render:

```
https://backend-ocr-ivkg.onrender.com
```

## OCR com upload

Envie o arquivo selecionado no frontend como `multipart/form-data`:

```
POST /ocr/upload
file: imagem
```

Resposta:

```json
{
  "success": true,
  "texto": "...",
  "campos": {
    "descricao": "Certificado de participacao...",
    "area": "EXTENSAO",
    "horasSolicitadas": 20,
    "semestre": 1
  },
  "solicitacao": {
    "descricao": "Certificado de participacao...",
    "area": "EXTENSAO",
    "horasSolicitadas": 20,
    "semestre": 1,
    "urlArquivo": "https://res.cloudinary.com/..."
  },
  "urlArquivo": "https://res.cloudinary.com/...",
  "cloudinary_url": "https://res.cloudinary.com/..."
}
```

O frontend pode usar `solicitacao` para preencher o formulario e, após a confirmacao do aluno, enviar esse payload para o backend Java. Os campos `urlArquivo` e `cloudinary_url` apontam para o mesmo arquivo; `urlArquivo` segue o nome usado no backend Java.

Configure no ambiente:

```
CLOUDINARY_CLOUD_NAME=
CLOUDINARY_API_KEY=
CLOUDINARY_API_SECRET=
CLOUDINARY_FOLDER=certificados
```
