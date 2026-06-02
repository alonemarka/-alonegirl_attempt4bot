import os
import logging
from dotenv import load_dotenv
from telegram import Update
from telegram.ext import Application, MessageHandler, filters, CommandHandler, ContextTypes
from groq import Groq

load_dotenv()

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
GROQ_API_KEY = os.getenv("GROQ_API_KEY")

if not GROQ_API_KEY:
    logger.error("GROQ_API_KEY bulunamadı! .env dosyasını kontrol et.")

groq = Groq(api_key=GROQ_API_KEY)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "🎙️ **Ses Özetleyici Bot'a Hoş Geldin!**\n\n"
        "Sesli mesaj atman yeterli, otomatik özetleyeceğim.\n"
        "Denemek için bir sesli mesaj gönder 🚀",
        parse_mode='Markdown'
    )

async def handle_voice(update: Update, context: ContextTypes.DEFAULT_TYPE):
    message = update.message
    if not message.voice:
        return

    await message.reply_text("🎙️ Ses alınıyor, özetleniyor...")

    try:
        voice_file = await context.bot.get_file(message.voice.file_id)
        file_path = f"voice_{message.message_id}.ogg"
        await voice_file.download_to_drive(file_path)

        with open(file_path, "rb") as audio:
            transcription = groq.audio.transcriptions.create(
                file=("voice.ogg", audio),
                model="whisper-large-v3-turbo",
                language="tr",
                response_format="text"
            )

        text = str(transcription).strip()

        if len(text) < 5:
            await message.reply_text("❌ Ses mesajında konuşma algılanamadı.")
            return

        summary = groq.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[{"role": "user", "content": f"Aşağıdaki sesli mesajı çok kısa ve net özetle (1-2 cümle):\n\n{text}"}],
            temperature=0.5,
            max_tokens=200
        )

        ozet = summary.choices[0].message.content.strip()

        cevap = f"**📝 Transcript:**\n{text[:800]}{'...' if len(text) > 800 else ''}\n\n**🔎 Özet:**\n{ozet}"
        await message.reply_text(cevap, parse_mode='Markdown')

    except Exception as e:
        logger.error(f"Hata: {e}")
        await message.reply_text("❌ Bir hata oluştu, tekrar dene.")
    finally:
        if os.path.exists(file_path):
            os.remove(file_path)


def main():
    app = Application.builder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.VOICE, handle_voice))

    logger.info("✅ Bot aktif!")
    app.run_polling()


if __name__ == "__main__":
    main()
