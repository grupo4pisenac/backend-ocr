## Deploy

A API esta disponivel em producao no Render:

```
https://backend-ocr-ivkg.onrender.com
```

## Documentacao online

Swagger UI:

```
https://backend-ocr-ivkg.onrender.com/docs
```

OpenAPI JSON:

```
https://backend-ocr-ivkg.onrender.com/openapi.json
```

## OCR antes da confirmacao

Envie o arquivo selecionado no frontend como `multipart/form-data`. Este endpoint apenas faz OCR e nao envia o arquivo ao Cloudinary:

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
    "area": null,
    "horasSolicitadas": 20,
    "semestre": 1
  },
  "solicitacao": {
    "descricao": "Certificado de participacao...",
    "area": null,
    "horasSolicitadas": 20,
    "semestre": 1
  }
}
```

O frontend pode usar `solicitacao` para preencher o formulario. Se o aluno cancelar, nenhum arquivo fica salvo no Cloudinary.

## Upload apos confirmacao

Quando o aluno confirmar a solicitacao, envie o mesmo arquivo para:

```
POST /certificados/upload
file: imagem
```

Resposta:

```json
{
  "success": true,
  "urlCertificado": "https://res.cloudinary.com/..."
}
```

Depois disso, o frontend envia ao backend Java os dados revisados pelo aluno junto com `urlCertificado`.

Configure no ambiente:

```
CLOUDINARY_CLOUD_NAME=
CLOUDINARY_API_KEY=
CLOUDINARY_API_SECRET=
CLOUDINARY_FOLDER=certificados
```
