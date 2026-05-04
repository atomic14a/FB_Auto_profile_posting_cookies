# FB Auto Profile & Page Posting Bot v2.0 🚀

A powerful, pure Python-based Facebook automation tool that uses GraphQL for high-performance posting without the need for Selenium or a browser.

---

## 📋 Table of Contents
1. [Prerequisites](#-prerequisites)
2. [Installation Guide](#-installation-guide)
3. [How to Run the Bot](#-how-to-run-the-bot)
4. [How to Get Cookies](#-how-to-get-cookies)
5. [Troubleshooting](#-troubleshooting)
6. [Disclaimer](#-disclaimer)

---

## 🛠 Prerequisites

Before you begin, ensure you have the following installed on your system:
*   **Python 3.8 or higher**: [Download here](https://www.python.org/downloads/)
*   **Git**: [Download here](https://git-scm.com/downloads)

---

## 📥 Installation Guide

### 📱 For Mobile Users (Termux)
Follow these commands step-by-step in your Termux app:
```bash
pkg update && pkg upgrade
pkg install python git
git clone https://github.com/atomic14a/FB_Auto_profile_posting_cookies.git
cd FB_Auto_profile_posting_cookies
pip install -r requirements.txt
python bot.py
```

### 💻 For Windows Users (Terminal Install)
If you don't have Python, install it via CMD with this code:
```bash
winget install Python.Python.3.12
```
Then run:
```bash
git clone https://github.com/atomic14a/FB_Auto_profile_posting_cookies.git
cd FB_Auto_profile_posting_cookies
pip install -r requirements.txt
python bot.py
```

---

## 🚀 How to Run the Bot

Once the installation is complete, follow these steps to start posting:

### 1. Launch the Bot
In your terminal, run:
```bash
python bot.py
```

### 2. Enter Your Cookies
When the bot starts, it will ask for your **Cookie String**. 
*   Paste your full Facebook cookie string and press **Enter**.
*   The bot will automatically validate if the session is alive.

### 3. Enter Links to Post
*   **Single Post**: Just paste the link (e.g., `https://google.com`).
*   **Bulk Post**: Paste multiple links separated by commas (e.g., `link1.com, link2.com, link3.com`).

---

## 🍪 How to Get Cookies?

1. Open Facebook in your Chrome/Edge browser and log in.
2. Press `F12` or `Right Click > Inspect` to open Developer Tools.
3. Go to the **Network** tab.
4. Refresh the page.
5. Click on any request (like `home.php` or `bz`) and look for the **Request Headers** section.
6. Find the `Cookie:` field and copy the entire string after it.

---

## ❓ Troubleshooting

*   **"pip is not recognized"**: Ensure Python is added to your System PATH during installation.
*   **"Cookies Expired"**: Facebook sessions expire. If you see this, simply refresh your browser and get a fresh cookie string.
*   **"Post Failed"**: If you post too rapidly, Facebook might temporarily block you. The bot includes a 3-5 second delay by default to prevent this.

---

## ⚠️ Disclaimer
This tool is for educational purposes only. The developer is not responsible for any account blocks or misuse of this script. Use it responsibly and in compliance with Facebook's Terms of Service.

---
Developed by **[atomic14a](https://github.com/atomic14a)**
