#!/bin/bash
# =============================================================================
# mobiPartner - Setup de Deploy
# Ejecutar: bash scripts/setup-deploy.sh
# =============================================================================

set -e

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}  mobiPartner - Setup de Deploy${NC}"
echo -e "${BLUE}========================================${NC}"
echo ""

# --- Check prerequisites ---
echo -e "${YELLOW}Verificando prerequisitos...${NC}"

for cmd in git gh node npm; do
  if ! command -v $cmd &> /dev/null; then
    echo -e "${RED}ERROR: '$cmd' no esta instalado${NC}"
    exit 1
  fi
done
echo -e "${GREEN}OK: git, gh, node, npm instalados${NC}"

# Check gh auth
if ! gh auth status &> /dev/null 2>&1; then
  echo -e "${RED}ERROR: No estas logueado en GitHub CLI. Ejecuta: gh auth login${NC}"
  exit 1
fi
echo -e "${GREEN}OK: GitHub CLI autenticado${NC}"

# --- Check if repo exists on GitHub ---
echo ""
echo -e "${YELLOW}Paso 1: Repositorio en GitHub${NC}"

REMOTE_URL=$(git remote get-url origin 2>/dev/null || echo "")
if [ -z "$REMOTE_URL" ]; then
  echo "No hay remote 'origin'. Creando repositorio publico en GitHub..."
  gh repo create mobiPartner --public --source=. --push
  echo -e "${GREEN}Repositorio creado y pusheado${NC}"
else
  echo -e "${GREEN}Remote ya configurado: $REMOTE_URL${NC}"
fi

# --- Generate keys ---
echo ""
echo -e "${YELLOW}Paso 2: Generando claves de seguridad...${NC}"

API_KEY=$(python3 -c "import secrets; print(secrets.token_urlsafe(32))")
ADMIN_API_KEY=$(python3 -c "import secrets; print(secrets.token_urlsafe(32))")
AUTH_SECRET=$(python3 -c "import secrets; print(secrets.token_urlsafe(32))")
AUTH_PASSWORD=$(python3 -c "import secrets; print(secrets.token_urlsafe(16))")

echo -e "${GREEN}Claves generadas${NC}"

# --- Save keys to file (gitignored) ---
cat > .env.production.keys <<EOF
# =============================================
# CLAVES GENERADAS - NO COMMITEAR ESTE ARCHIVO
# =============================================
# Fecha: $(date -u +"%Y-%m-%d %H:%M:%S UTC")

API_KEY=$API_KEY
ADMIN_API_KEY=$ADMIN_API_KEY
AUTH_SECRET=$AUTH_SECRET
AUTH_PASSWORD=$AUTH_PASSWORD

# Tu contrasena para entrar al sitio es:
# $AUTH_PASSWORD
EOF

echo -e "${GREEN}Claves guardadas en .env.production.keys (gitignored)${NC}"

# --- Instructions for manual services ---
echo ""
echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}  SERVICIOS A CONFIGURAR MANUALMENTE${NC}"
echo -e "${BLUE}========================================${NC}"

echo ""
echo -e "${YELLOW}Paso 3: SUPABASE (base de datos)${NC}"
echo "  1. Ve a https://supabase.com → New Project"
echo "  2. Region: South America (Sao Paulo)"
echo "  3. Una vez creado, ve a Settings → Database"
echo "  4. Copia el 'Connection string' (URI) - puerto 5432, modo 'direct'"
echo "  5. En SQL Editor, ejecuta: CREATE EXTENSION IF NOT EXISTS postgis;"
echo ""
read -p "  Pega tu DATABASE_URL de Supabase (postgresql://...): " SUPABASE_URL

if [ -z "$SUPABASE_URL" ]; then
  echo -e "${RED}No se proporcionó URL. Abortando.${NC}"
  exit 1
fi

echo ""
echo -e "${YELLOW}Paso 4: UPSTASH (Redis)${NC}"
echo "  1. Ve a https://upstash.com → Create Database"
echo "  2. Region: South America (Sao Paulo)"
echo "  3. Copia la 'REST URL' o 'Redis URL' (rediss://...)"
echo ""
read -p "  Pega tu REDIS_URL de Upstash (rediss://...): " REDIS_URL

if [ -z "$REDIS_URL" ]; then
  echo -e "${YELLOW}WARN: Sin Redis URL. El backend funcionara sin cache.${NC}"
  REDIS_URL="redis://localhost:6379/0"
fi

# --- Run migrations against Supabase ---
echo ""
echo -e "${YELLOW}Paso 5: Corriendo migraciones en Supabase...${NC}"
cd backend
DATABASE_URL="$SUPABASE_URL" python3 -m alembic upgrade head 2>&1 || {
  echo -e "${RED}ERROR en migraciones. Verifica la DATABASE_URL y que PostGIS este habilitado.${NC}"
  echo "  Ejecuta en Supabase SQL Editor: CREATE EXTENSION IF NOT EXISTS postgis;"
  echo "  Luego reintenta: DATABASE_URL='$SUPABASE_URL' python3 -m alembic upgrade head"
}
cd ..
echo -e "${GREEN}Migraciones ejecutadas${NC}"

# --- Set GitHub Secrets ---
echo ""
echo -e "${YELLOW}Paso 6: Configurando GitHub Secrets (para el cron de scraping)...${NC}"

echo "$SUPABASE_URL" | gh secret set DATABASE_URL
echo "1300.0" | gh secret set USD_ARS_RATE_FALLBACK

echo -e "${GREEN}GitHub Secrets configurados${NC}"

# --- Render setup ---
echo ""
echo -e "${YELLOW}Paso 7: RENDER (backend API)${NC}"
echo "  1. Ve a https://render.com → New Web Service"
echo "  2. Conecta tu repo de GitHub"
echo "  3. Configuracion:"
echo "     - Name: mobipartner-api"
echo "     - Root Directory: (dejar vacio)"
echo "     - Runtime: Docker"
echo "     - Dockerfile Path: backend/Dockerfile.prod"
echo "     - Docker Context: backend"
echo "     - Instance Type: Free"
echo ""
echo "  4. Environment Variables:"
echo "     DATABASE_URL = $SUPABASE_URL"
echo "     REDIS_URL = $REDIS_URL"
echo "     API_KEY = $API_KEY"
echo "     ADMIN_API_KEY = $ADMIN_API_KEY"
echo "     CORS_ORIGINS = (lo llenaremos despues con la URL de Vercel)"
echo "     SCRAPE_ENABLED = false"
echo "     DEBUG = false"
echo "     USD_ARS_RATE_FALLBACK = 1300.0"
echo ""
read -p "  Una vez deployado, pega la URL de Render (https://mobipartner-api.onrender.com): " RENDER_URL

if [ -z "$RENDER_URL" ]; then
  RENDER_URL="https://mobipartner-api.onrender.com"
  echo -e "${YELLOW}  Usando URL por defecto: $RENDER_URL${NC}"
fi

# --- Vercel setup ---
echo ""
echo -e "${YELLOW}Paso 8: VERCEL (frontend)${NC}"
echo "  1. Ve a https://vercel.com → Import Project"
echo "  2. Conecta tu repo de GitHub"
echo "  3. Configuracion:"
echo "     - Framework: Next.js"
echo "     - Root Directory: frontend"
echo ""
echo "  4. Environment Variables:"
echo "     NEXT_PUBLIC_API_URL = ${RENDER_URL}/api"
echo "     API_KEY = $API_KEY"
echo "     AUTH_PASSWORD = $AUTH_PASSWORD"
echo "     AUTH_SECRET = $AUTH_SECRET"
echo ""
read -p "  Una vez deployado, pega la URL de Vercel (https://mobipartner.vercel.app): " VERCEL_URL

if [ -z "$VERCEL_URL" ]; then
  VERCEL_URL="https://mobipartner.vercel.app"
  echo -e "${YELLOW}  Usando URL por defecto: $VERCEL_URL${NC}"
fi

# --- Update CORS on Render ---
echo ""
echo -e "${YELLOW}Paso 9: Actualizar CORS en Render${NC}"
echo "  Ve a Render → mobipartner-api → Environment"
echo "  Actualiza CORS_ORIGINS = $VERCEL_URL"
echo ""
read -p "  Presiona Enter cuando lo hayas actualizado... "

# --- Save full config ---
cat >> .env.production.keys <<EOF

# =============================================
# URLS DE SERVICIOS
# =============================================
DATABASE_URL=$SUPABASE_URL
REDIS_URL=$REDIS_URL
RENDER_URL=$RENDER_URL
VERCEL_URL=$VERCEL_URL

# =============================================
# CONFIGURACION POR SERVICIO
# =============================================

# --- RENDER (backend) ---
# DATABASE_URL=$SUPABASE_URL
# REDIS_URL=$REDIS_URL
# API_KEY=$API_KEY
# ADMIN_API_KEY=$ADMIN_API_KEY
# CORS_ORIGINS=$VERCEL_URL
# SCRAPE_ENABLED=false
# DEBUG=false

# --- VERCEL (frontend) ---
# NEXT_PUBLIC_API_URL=${RENDER_URL}/api
# API_KEY=$API_KEY
# AUTH_PASSWORD=$AUTH_PASSWORD
# AUTH_SECRET=$AUTH_SECRET

# --- GITHUB SECRETS ---
# DATABASE_URL=$SUPABASE_URL
# USD_ARS_RATE_FALLBACK=1300.0
EOF

echo ""
echo -e "${BLUE}========================================${NC}"
echo -e "${GREEN}  SETUP COMPLETO${NC}"
echo -e "${BLUE}========================================${NC}"
echo ""
echo -e "  Frontend: ${GREEN}$VERCEL_URL${NC}"
echo -e "  Backend:  ${GREEN}$RENDER_URL${NC}"
echo -e "  Password: ${GREEN}$AUTH_PASSWORD${NC}"
echo ""
echo -e "  Todas las claves guardadas en: ${YELLOW}.env.production.keys${NC}"
echo ""
echo -e "  ${YELLOW}Para testear:${NC}"
echo "    1. Abre $VERCEL_URL → deberias ver la pagina de login"
echo "    2. Ingresa la contrasena: $AUTH_PASSWORD"
echo "    3. El scraping corre automaticamente a las 20:00 ARG (23:00 UTC)"
echo "    4. Para un scrape manual: GitHub → Actions → Daily Scrape Pipeline → Run workflow"
echo ""
