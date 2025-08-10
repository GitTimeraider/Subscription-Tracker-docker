#!/bin/bash

# Subscription Tracker Setup Script
echo "🔔 Setting up Subscription Tracker..."

# Check if Python is installed
if ! command -v python3 &> /dev/null; then
    echo "❌ Python 3 is not installed. Please install Python 3.7 or higher."
    exit 1
fi

# Create virtual environment
echo "📦 Creating virtual environment..."
python3 -m venv venv

# Activate virtual environment
echo "🔧 Activating virtual environment..."
source venv/bin/activate

# Install dependencies
echo "📥 Installing dependencies..."
pip install -r requirements.txt

# Copy environment file
if [ ! -f .env ]; then
    echo "📝 Creating environment file..."
    cp .env.example .env
    echo "⚠️  Please edit .env file with your configuration!"
fi

# Run the application
echo "🚀 Starting Subscription Tracker..."
echo "📱 Open http://localhost:5000 in your browser"
echo "🔑 Default login: admin / changeme"
echo "⚠️  CHANGE THE DEFAULT PASSWORD IMMEDIATELY!"

python run.py
