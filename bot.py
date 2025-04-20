from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, filters

from dotenv import load_dotenv
import os
from handlers import start, help_command, language_button, handle_url, format_button, quality_button

load_dotenv()

def main() -> None:
    # Bot tokenini o'rnating
    TOKEN = os.getenv('BOT_TOKEN')
    
    # Applicationni yaratish
    application = Application.builder().token(TOKEN).build()
    
    # Command handlerlari
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", help_command))
    
    # Message handlerlari
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_url))
    
    # Callback query handlerlari
    application.add_handler(CallbackQueryHandler(language_button, pattern=r"^lang_"))
    application.add_handler(CallbackQueryHandler(format_button, pattern=r"^format_"))
    application.add_handler(CallbackQueryHandler(quality_button, pattern=r"^quality_"))
    
    # Botni ishga tushirish
    application.run_polling()

if __name__ == '__main__':
    main()