# 🚀 Despliegue en Streamlit Cloud - Manuelita Assistant

## Despliegue Gratuito (Streamlit Community Cloud)

### Requisitos Previos
- Cuenta de GitHub
- Cuenta de Streamlit Cloud (usa tu GitHub): https://share.streamlit.io/

### Pasos para Desplegar

#### 1. Sube a GitHub
```bash
cd agent-app
git add .
git commit -m "Preparar para despliegue"
git push origin main
```

#### 2. Ve a Streamlit Cloud
1. Accede a: https://share.streamlit.io/
2. Haz clic en "New app"
3. Conecta tu repositorio de GitHub

#### 3. Configura la App
- **Repository**: `tu-usuario/Webscraping_manuelita1`
- **Branch**: `main`
- **Main file path**: `agent-app/app.py`
- **Python version**: 3.9+

#### 4. Configura Secrets (API Keys)
En Streamlit Cloud, ve a "Advanced settings" → "Secrets" y agrega:

```toml
OPENAI_API_KEY = "sk-..."
# O si usas Google Gemini:
GOOGLE_API_KEY = "AIza..."
```

#### 5. Deploy
Haz clic en "Deploy!" y espera 2-5 minutos.

### URL de la App
Tu app estará disponible en:
```
https://[app-name]-[random-string].streamlit.app
```

---

## Alternativas Gratuitas

### Opción 2: Hugging Face Spaces
**Ventajas:** Gratis, GPU opcional
**Límite:** 16GB RAM, 8 CPUs

1. Crea cuenta en: https://huggingface.co/
2. Crea un Space con Streamlit
3. Sube tu código
4. Configura secrets en Settings

### Opción 3: Railway (Free Tier)
**Ventajas:** 500hrs/mes gratis
**Límite:** $5 crédito mensual

```bash
# Instala Railway CLI
npm i -g @railway/cli

# Deploy
railway login
railway init
railway up
```

### Opción 4: Render (Free Tier)
**Ventajas:** SSL gratis, custom domains
**Límite:** Se duerme después de 15 min de inactividad

1. Crea cuenta en: https://render.com/
2. New → Web Service
3. Conecta GitHub repo
4. Build: `pip install -r requirements.txt`
5. Start: `streamlit run app.py --server.port $PORT`

---

## Consideraciones para Despliegue Gratuito

### ⚠️ Limitaciones
- **RAM limitada**: ~1GB en free tier
- **Tiempo de arranque**: 30-60 segundos
- **Inactividad**: Se apaga después de 15-30 min sin uso
- **ChromaDB**: La base vectorial se recrea en cada deploy

### ✅ Recomendaciones

1. **Reduce el modelo de embeddings** si hay problemas de RAM:
```python
# En rag.py línea 45
embedding_model: str = "sentence-transformers/all-MiniLM-L6-v2"
# Cambiar a:
embedding_model: str = "sentence-transformers/paraphrase-MiniLM-L3-v2"  # Más ligero
```

2. **Usa Ollama localmente** para no depender de APIs de pago

3. **Cachea la base vectorial**:
```python
@st.cache_resource
def load_rag():
    return RAGSystem()
```

4. **Limita documentos** en testing (pon menos archivos en `data/`)

---

## URLs de los Servicios

- **Streamlit Cloud**: https://share.streamlit.io/
- **Hugging Face Spaces**: https://huggingface.co/spaces
- **Railway**: https://railway.app/
- **Render**: https://render.com/

---

## Troubleshooting

### Error: "Out of memory"
Reduce el número de documentos o usa modelo de embeddings más ligero.

### Error: "Port already in use"
Streamlit Cloud maneja esto automáticamente. Si es local, cambia el puerto:
```bash
streamlit run app.py --server.port 8502
```

### La app se carga muy lento
- Reduce tamaño de la base vectorial
- Usa caché de Streamlit (`@st.cache_resource`)

### No aparece la API key
Verifica que los secrets estén configurados correctamente en la plataforma.
