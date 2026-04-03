#!/bin/bash

# Quick Start Script for Fulton County Reading Lift Pilot POC
echo "🎓 Fulton County Reading Lift Pilot - Quick Start"
echo "================================================="

# Check if Python is available
if ! command -v python3 &> /dev/null; then
    echo "❌ Python 3 not found. Please install Python 3.8 or higher."
    exit 1
fi

# Install requirements
echo "📦 Installing Python requirements..."
pip3 install -r requirements.txt

# Run setup
echo "🔧 Setting up synthetic data and models..."
python3 setup.py

# Generate fresh recommendations
echo "🤖 Running batch recommendation generation..."
python3 batch_processor.py

echo ""
echo "✅ Setup complete! Ready to run demo."
echo ""
echo "To start all applications:"
echo "  python3 run_demo.py"
echo ""
echo "Or start components individually:"
echo "  API Server:        python3 api/main.py"
echo "  Student App:       streamlit run ui/student_app.py --server.port 8501"
echo "  Librarian App:     streamlit run ui/librarian_app.py --server.port 8502"
echo "  District Dashboard: streamlit run ui/district_dashboard.py --server.port 8503"