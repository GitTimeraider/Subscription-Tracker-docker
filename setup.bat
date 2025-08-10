@echo off
REM Subscription Tracker Setup Script for Windows

echo 🔔 Setting up Subscription Tracker...

REM Check if Python is installed
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo ❌ Python is not installed. Please install Python 3.7 or higher.
    pause
    exit /b 1
)

REM Create virtual environment
echo 📦 Creating virtual environment...
python -m venv venv

REM Activate virtual environment
echo 🔧 Activating virtual environment...
call venv\Scripts\activate.bat

REM Install dependencies
echo 📥 Installing dependencies...
pip install -r requirements.txt

REM Copy environment file
if not exist .env (
    echo 📝 Creating environment file...
    copy .env.example .env
    echo ⚠️  Please edit .env file with your configuration!
)

REM Run the application
echo 🚀 Starting Subscription Tracker...
echo 📱 Open http://localhost:5000 in your browser
echo 🔑 Default login: admin / changeme
echo ⚠️  CHANGE THE DEFAULT PASSWORD IMMEDIATELY!

python run.py

pause
