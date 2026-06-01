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
    "area": null,
    "horasSolicitadas": 20,
    "semestre": 1
  },
  "solicitacao": {
    "descricao": "Certificado de participacao...",
    "area": null,
    "horasSolicitadas": 20,
    "semestre": 1,
    "urlCertificado": "https://res.cloudinary.com/..."
  },
  "urlCertificado": "https://res.cloudinary.com/..."
}
```

O frontend pode usar `solicitacao` para preencher o formulario e, apos a confirmacao do aluno, enviar esse payload para o backend Java. Para criar a solicitacao no Java, o campo esperado e `urlCertificado`.

Configure no ambiente:

```
CLOUDINARY_CLOUD_NAME=
CLOUDINARY_API_KEY=
CLOUDINARY_API_SECRET=
CLOUDINARY_FOLDER=certificados
```
