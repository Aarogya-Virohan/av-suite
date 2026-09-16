@echo off
echo ==========================================
echo       Starting AV Suite Backend
echo ==========================================

cd backend

IF NOT EXIST "venv\" (
    echo [INFO] Virtual environment not found. Creating one...
    python -m venv venv
    
    echo [INFO] Activating virtual environment...
    call venv\Scripts\activate.bat
    
    echo [INFO] Installing requirements...
    pip install -r requirements.txt
    pip install -e .
) ELSE (
    echo [INFO] Virtual environment found. Activating...
    call venv\Scripts\activate.bat
)

echo [INFO] Starting FastAPI server...
uvicorn app.main:app --reload
