import re
import logging

# Logging nastroykasi
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Havolani tekshirish funksiyasi
def is_valid_url(url: str) -> bool:
    pattern = r'^(https?:\/\/)?(www\.)?(youtube\.com|youtu\.be|tiktok\.com|instagram\.com|pinterest\.com|twitter\.com|x\.com)\/.*'
    return bool(re.match(pattern, url))

async def update_status_message(context, user_id, status_message, text, edit_only=False):
    """Xabarni xavfsiz yangilash"""
    try:
        await status_message.edit_text(text)
    except Exception as e:
        if not edit_only:
            try:
                await context.bot.send_message(chat_id=user_id, text=text)
            except Exception as e2:
                logger.error(f"Failed to send message: {e2}")