import os
import logging
from dotenv import load_dotenv

load_dotenv()

BOT_TOKEN = os.getenv('BOT_TOKEN')

LANGUAGES = {
    'uz': {
        'welcome': "🇺🇿 Salom! Men media yuklab oluvchi botman. Menga YouTube, TikTok, Instagram, Pinterest yoki X(Twitter) havolasini yuboring.",
        'help': "🇺🇿 Bot ishlashi uchun quyidagi platformalardan birining havolasini yuboring:\n- YouTube\n- TikTok\n- Instagram\n- Pinterest\n- X (Twitter)\n\nHavolani yuborganingizdan so'ng, men sizga sifat tanlovini taqdim etaman.",
        'language_changed': "🇺🇿 Til o'zbekchaga o'zgartirildi!",
        'choose_quality': "🇺🇿 Video sifatini tanlang:",
        'downloading': "🇺🇿 Yuklab olinmoqda... Bu bir necha soniya vaqt olishi mumkin.",
        'download_complete': "🇺🇿 Yuklab olish tugadi!",
        'download_failed': "🇺🇿 Yuklab olishda xatolik yuz berdi. Qayta urinib ko'ring yoki boshqa havola yuboring.",
        'invalid_url': "🇺🇿 Noto'g'ri havola. Iltimos, to'g'ri havolani yuboring.",
        'choose_format': "🇺🇿 Formatni tanlang:",
        'video': "🇺🇿 Video",
        'audio': "🇺🇿 Audio (MP3)",
        'quality_low': "🇺🇿 Past sifat",
        'quality_medium': "🇺🇿 O'rta sifat",
        'quality_high': "🇺🇿 Yuqori sifat",
        'processing': "🇺🇿 Qayta ishlanmoqda... Biroz kuting.",  
        'download_image': "🇺🇿 Rasm yuklab olinmoqda..."
    },
    'en': {
        'welcome': "🇬🇧 Hello! I am a media downloader bot. Send me a YouTube, TikTok, Instagram, Pinterest or X(Twitter) link.",
        'help': "🇬🇧 To use the bot, send a link from one of the following platforms:\n- YouTube\n- TikTok\n- Instagram\n- Pinterest\n- X (Twitter)\n\nAfter sending the link, I will provide you with quality options.",
        'language_changed': "🇬🇧 Language changed to English!",
        'choose_quality': "🇬🇧 Choose video quality:",
        'downloading': "🇬🇧 Downloading... This may take a few seconds.",
        'download_complete': "🇬🇧 Download completed!",
        'download_failed': "🇬🇧 Download failed. Please try again or send another link.",
        'invalid_url': "🇬🇧 Invalid URL. Please send a correct link.",
        'choose_format': "🇬🇧 Choose format:",
        'video': "🇬🇧 Video",
        'audio': "🇬🇧 Audio (MP3)",
        'quality_low': "🇬🇧 Low quality",
        'quality_medium': "🇬🇧 Medium quality",
        'quality_high': "🇬🇧 High quality",
        'processing': "🇬🇧 Processing... Please wait.",
        'download_image': "🇬🇧 Downloading image..."
    },
    'ru': {
        'welcome': "🇷🇺 Привет! Я бот для скачивания медиа. Отправьте мне ссылку на YouTube, TikTok, Instagram, Pinterest или X(Twitter).",
        'help': "🇷🇺 Для использования бота отправьте ссылку с одной из следующих платформ:\n- YouTube\n- TikTok\n- Instagram\n- Pinterest\n- X (Twitter)\n\nПосле отправки ссылки я предоставлю вам варианты качества.",
        'language_changed': "🇷🇺 Язык изменен на русский!",
        'choose_quality': "🇷🇺 Выберите качество видео:",
        'downloading': "🇷🇺 Загрузка... Это может занять несколько секунд.",
        'download_complete': "🇷🇺 Загрузка завершена!",
        'download_failed': "🇷🇺 Ошибка загрузки. Пожалуйста, попробуйте еще раз или отправьте другую ссылку.",
        'invalid_url': "🇷🇺 Неверная ссылка. Пожалуйста, отправьте правильную ссылку.",
        'choose_format': "🇷🇺 Выберите формат:",
        'video': "🇷🇺 Видео",
        'audio': "🇷🇺 Аудио (MP3)",
        'quality_low': "🇷🇺 Низкое качество",
        'quality_medium': "🇷🇺 Среднее качество",
        'quality_high': "🇷🇺 Высокое качество",
        'processing': "🇷🇺 Обработка... Пожалуйста, подождите.",
        'download_image': "🇷🇺 Загрузка изображения..."
    }
}

# Foydalanuvchi tilini saqlash uchun
user_languages = {}

# Logging nastroykasi
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)
