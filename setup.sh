#!/bin/bash

# Telegram File Manager Bot - Setup Script
# This script sets up the bot environment

echo "🤖 Telegram File Manager Bot - Setup"
echo "======================================"

# Check Python version
echo "📋 Checking Python version..."
python_version=$(python3 --version 2>&1 | awk '{print $2}')
echo "Found Python $python_version"

# Check if pip is available
echo "📋 Checking pip..."
if ! command -v pip3 &> /dev/null; then
    echo "❌ pip3 not found. Please install pip first."
    exit 1
fi
echo "✅ pip3 found"

# Install dependencies
echo "📦 Installing dependencies..."
pip3 install -r requirements.txt

if [ $? -eq 0 ]; then
    echo "✅ Dependencies installed successfully!"
else
    echo "❌ Failed to install dependencies"
    exit 1
fi

# Check for unrar (for RAR support)
echo "📋 Checking for unrar..."
if command -v unrar &> /dev/null; then
    echo "✅ unrar found"
else
    echo "⚠️ unrar not found. RAR files won't be supported."
    echo "   To install unrar:"
    echo "   - Ubuntu/Debian: sudo apt install unrar"
    echo "   - Termux: pkg install unrar"
    echo "   - macOS: brew install unrar"
fi

# Create temp directory
echo "📁 Creating temp directory..."
mkdir -p /tmp/telegram_bot
echo "✅ Temp directory ready"

# Check for bot token
echo ""
echo "======================================"
echo "🔑 Bot Token Setup"
echo "======================================"

if [ -f .env ]; then
    source .env
fi

if [ -z "$BOT_TOKEN" ] || [ "$BOT_TOKEN" = "your_bot_token_here" ]; then
    echo "⚠️ BOT_TOKEN not set!"
    echo ""
    echo "To get your bot token:"
    echo "1. Message @BotFather on Telegram"
    echo "2. Create a new bot with /newbot"
    echo "3. Copy the token"
    echo ""
    echo "Then set it using one of these methods:"
    echo "  - Edit config.py and set BOT_TOKEN"
    echo "  - Create .env file with BOT_TOKEN=your_token"
    echo "  - Export as environment variable: export BOT_TOKEN=your_token"
    echo ""
else
    echo "✅ BOT_TOKEN is set"
fi

echo ""
echo "======================================"
echo "🚀 Setup Complete!"
echo "======================================"
echo ""
echo "To start the bot, run:"
echo "  python3 bot.py"
echo ""
echo "Or on Termux:"
echo "  python bot.py"
echo ""
