# Usar imagem base do Python
FROM python:3.11-slim

# 1. Instalar apenas utilitários básicos para download
# O apt resolverá automaticamente as dependências do Chrome ao instalar o .deb
RUN apt-get update && apt-get install -y \
    wget \
    curl \
    gnupg \
    unzip \
    --no-install-recommends && \
    rm -rf /var/lib/apt/lists/*

# 2. Baixar e instalar Google Chrome Stable diretamente via .deb
# O comando 'apt-get install -y ./google-chrome-stable_current_amd64.deb' 
# resolve as dependências (alsa, nss, x11, etc.) automaticamente
# Isso evita erros de pacotes obsoletos como libgconf-2-4
RUN wget -q https://dl.google.com/linux/direct/google-chrome-stable_current_amd64.deb && \
    apt-get update && \
    apt-get install -y ./google-chrome-stable_current_amd64.deb && \
    rm google-chrome-stable_current_amd64.deb && \
    rm -rf /var/lib/apt/lists/*

# 3. Configurar variáveis de ambiente para Chrome em containers
ENV CHROME_BIN=/usr/bin/google-chrome
ENV CHROMEDRIVER_PATH=/usr/local/bin/chromedriver
ENV DISPLAY=:99

# Definir diretório de trabalho
WORKDIR /app

# Copiar arquivo de dependências
COPY requirements.txt .

# Instalar dependências
RUN pip install --no-cache-dir -r requirements.txt

# Copiar código da aplicação
COPY . .

# Expor a porta da aplicação (Cloud Run define dinamicamente via variável PORT)
EXPOSE ${PORT:-3000}

# Comando para executar a aplicação usando a porta definida pelo Cloud Run
# IMPORTANTE: Use 0.0.0.0 para tornar acessível do host, não localhost
CMD sh -c "uvicorn main:app --host 0.0.0.0 --port ${PORT:-3000}"

