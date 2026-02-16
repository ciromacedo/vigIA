#!/bin/bash
# Script de setup para o MVP do Parque Altamiro
# Execute com: bash scripts/setup_mvp.sh

set -e

echo "=============================================="
echo "Setup MVP - Parque Altamiro de Moura Pacheco"
echo "=============================================="
echo

# Verifica se está no diretório correto
if [ ! -f "pyproject.toml" ]; then
    echo "Erro: Execute este script a partir do diretório raiz do projeto"
    echo "  cd /caminho/para/vigIA"
    echo "  bash scripts/setup_mvp.sh"
    exit 1
fi

# Verifica Python
echo "Verificando Python..."
if command -v python3.9 &> /dev/null; then
    PYTHON_CMD="python3.9"
elif command -v python3 &> /dev/null; then
    PYTHON_CMD="python3"
else
    echo "Erro: Python 3 não encontrado"
    exit 1
fi

PYTHON_VERSION=$($PYTHON_CMD --version 2>&1 | cut -d' ' -f2)
echo "  Python encontrado: $PYTHON_VERSION"

# Verifica se a versão é compatível (3.9.x)
MAJOR_MINOR=$(echo $PYTHON_VERSION | cut -d'.' -f1,2)
if [ "$MAJOR_MINOR" != "3.9" ]; then
    echo "  AVISO: O projeto requer Python 3.9"
    echo "  Versão atual: $PYTHON_VERSION"
    echo
    echo "  Para instalar Python 3.9:"
    echo "    Ubuntu/Debian: sudo apt install python3.9 python3.9-venv"
    echo "    Conda: conda create -n simfire python=3.9"
    echo
fi

# Verifica Poetry
echo
echo "Verificando Poetry..."
if command -v poetry &> /dev/null; then
    POETRY_VERSION=$(poetry --version 2>&1)
    echo "  Poetry encontrado: $POETRY_VERSION"
else
    echo "  Poetry não encontrado. Instalando..."
    curl -sSL https://install.python-poetry.org | $PYTHON_CMD -
    export PATH="$HOME/.local/bin:$PATH"
fi

# Instala dependências
echo
echo "Instalando dependências..."
poetry install

# Cria diretório de saída
echo
echo "Criando diretórios..."
mkdir -p ~/.simfire/parque_altamiro

echo
echo "=============================================="
echo "Setup concluído!"
echo "=============================================="
echo
echo "Para executar o MVP:"
echo "  poetry run python scripts/run_mvp_parque_altamiro.py"
echo
echo "Opções de execução:"
echo "  --mode default     : Com visualização (padrão)"
echo "  --mode headless    : Sem interface gráfica"
echo "  --mode interactive : Modo interativo com logs"
echo
