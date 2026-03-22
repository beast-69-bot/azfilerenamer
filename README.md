# 🤖 Telegram File Manager Bot

A powerful Python-based Telegram Bot that handles ZIP and RAR files with smart upload and rename features.

## ✨ Features

- 📦 **ZIP/RAR Extraction** - Automatically extracts and shows file contents
- 📋 **File Overview** - See total files count, size, and archive name
- 📤 **Smart Upload** - Upload files individually or all at once
- ✏️ **Rename Files** - Rename files before downloading
- 📥 **New ZIP Download** - Get a renamed ZIP file after renaming
- 🔄 **Pagination** - Handle large archives with paginated file lists

## 🚀 Quick Start

### 1. Get Bot Token

1. Message [@BotFather](https://t.me/BotFather) on Telegram
2. Create a new bot with `/newbot`
3. Copy the bot token

### 2. Installation

```bash
# Clone or download the project
cd telegram_bot

# Install dependencies
pip install -r requirements.txt

# For RAR support on Termux:
apt install unrar
```

### 3. Configuration

**Option 1:** Set token in `config.py`
```python
BOT_TOKEN = "YOUR_BOT_TOKEN_HERE"
```

**Option 2:** Use environment variable
```bash
export BOT_TOKEN="your_bot_token_here"
```

### 4. Run the Bot

```bash
python bot.py
```

## 📖 Usage

1. **Start the bot** - Send `/start` to see welcome message
2. **Send a file** - Upload any ZIP or RAR file
3. **Choose action:**
   - 📋 **Show File List** - View all files with individual upload buttons
   - 📤 **Upload All** - Send all files at once
   - ✏️ **Rename Files** - Rename files and get a new ZIP

## 📁 Project Structure

```
telegram_bot/
├── bot.py                  # Main entry point
├── config.py               # Configuration settings
├── requirements.txt        # Python dependencies
├── handlers/
│   ├── file_handler.py     # ZIP/RAR receive & extract
│   ├── upload_handler.py   # Single & bulk upload
│   └── rename_handler.py   # Rename flow & ZIP creation
└── utils/
    ├── extractor.py        # Archive extraction
    ├── zipper.py           # ZIP creation
    └── cleaner.py          # Temp file cleanup
```

## ⚙️ Configuration Options

Edit `config.py` to customize:

```python
TEMP_DIR = "/tmp/telegram_bot"        # Temp storage location
MAX_FILE_SIZE = 50 * 1024 * 1024      # 50MB Telegram limit
FILES_PER_PAGE = 20                   # Files per page in list
UPLOAD_DELAY = 1                      # Delay between uploads (seconds)
```

## 🛠️ Tech Stack

- **Python 3.10+**
- **python-telegram-bot** - Telegram Bot API wrapper
- **patool/rarfile** - Archive extraction
- **zipfile** - ZIP creation (built-in)

## ⚠️ Known Limitations

| Limitation | Cause | Solution |
|------------|-------|----------|
| Max 50MB file size | Telegram Bot API limit | Use local Bot API server |
| RAR needs unrar tool | External dependency | Install: `apt install unrar` |
| Rate limits on uploads | Telegram limits | Built-in delay between uploads |

## 🔮 Future Enhancements

- [ ] Cloud storage support (Google Drive / Mega)
- [ ] Password-protected ZIP support
- [ ] File preview thumbnails
- [ ] SQLite session persistence
- [ ] Admin panel
- [ ] Multi-language support

## 📱 Termux Compatible

This bot works perfectly on Android via Termux:

```bash
# Install Termux from F-Droid
# Update packages
pkg update && pkg upgrade

# Install Python and dependencies
pkg install python unrar
pip install python-telegram-bot patool rarfile

# Run the bot
python bot.py
```

## 📝 License

This project is open source and available under the MIT License.

---

**Built with Python + python-telegram-bot | Termux Compatible**
