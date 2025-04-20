import os
import logging
import re
from typing import Dict, Optional
from bs4 import BeautifulSoup
import json
import asyncio
import yt_dlp
import requests
from io import BytesIO
from Pinterest import Pinterest

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, ContextTypes, filters

# Bot tillarini sozlash
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

# Havolani tekshirish funksiyasi
def is_valid_url(url: str) -> bool:
    pattern = r'^(https?:\/\/)?(www\.)?(youtube\.com|youtu\.be|tiktok\.com|instagram\.com|pinterest\.com|twitter\.com|x\.com)\/.*'
    return bool(re.match(pattern, url))

async def update_status_message(context, user_id, status_message, text, edit_only=False):
    """Xabarni xavfsiz yangilash"""
    try:
        # Xabarni o'zgartirmasdan oldin tekshirish
        if hasattr(status_message, 'text') and status_message.text != text:
            await status_message.edit_text(text)
    except Exception as e:
        logger.warning(f"Failed to update status message: {e}")
        if not edit_only:
            try:
                await context.bot.send_message(chat_id=user_id, text=text)
            except Exception as e2:
                logger.error(f"Failed to send message: {e2}")

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = update.effective_user.id
    user_languages[user_id] = user_languages.get(user_id, 'uz')  # Default til o'zbekcha
    await update.message.reply_text(LANGUAGES[user_languages[user_id]]['welcome'])
    
    # Til tanlash klaviaturasini ko'rsatish
    keyboard = [
        [
            InlineKeyboardButton("🇺🇿 O'zbekcha", callback_data="lang_uz"),
            InlineKeyboardButton("🇬🇧 English", callback_data="lang_en"),
            InlineKeyboardButton("🇷🇺 Русский", callback_data="lang_ru")
        ]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text("Tilni tanlang / Choose language / Выберите язык:", reply_markup=reply_markup)

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = update.effective_user.id
    user_lang = user_languages.get(user_id, 'uz')
    await update.message.reply_text(LANGUAGES[user_lang]['help'])

async def language_button(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()
    
    user_id = query.from_user.id
    lang = query.data.split('_')[1]
    user_languages[user_id] = lang
    
    await query.edit_message_text(LANGUAGES[lang]['language_changed'])

async def handle_url(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Havolalarni qabul qilish va qayta ishlash"""
    url = update.message.text
    user_id = update.effective_user.id
    user_lang = user_languages.get(user_id, 'uz')
    
    if not is_valid_url(url):
        await update.message.reply_text(LANGUAGES[user_lang]['invalid_url'])
        return
    
    # URL-ni context.user_data-ga saqlash
    context.user_data['url'] = url
    
    # X/Twitter uchun maxsus holat - to'g'ridan-to'g'ri yuklab berish
    if ('twitter.com' in url or 'x.com' in url) and '/status/' in url:
        status_message = await update.message.reply_text(LANGUAGES[user_lang]['downloading'])
        await download_twitter_media(update, context, status_message)
        return
    
    # Instagram reels aniq video
    if 'instagram.com' in url and '/reel/' in url:
        keyboard = [
            [
                InlineKeyboardButton(LANGUAGES[user_lang]['video'], callback_data="format_video"),
                InlineKeyboardButton(LANGUAGES[user_lang]['audio'], callback_data="format_audio")
            ]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await update.message.reply_text(LANGUAGES[user_lang]['choose_format'], reply_markup=reply_markup)
        return
    
    # Pinterest postlar odatda rasm
    if 'pinterest.com' in url and '/pin/' in url:
        status_message = await update.message.reply_text(LANGUAGES[user_lang]['downloading'])
        await download_pinterest_media(update, context, status_message)
        return
        
    # YouTube va TikTok aniq video
    if 'youtube.com' in url or 'youtu.be' in url or 'tiktok.com' in url:
        keyboard = [
            [
                InlineKeyboardButton(LANGUAGES[user_lang]['video'], callback_data="format_video"),
                InlineKeyboardButton(LANGUAGES[user_lang]['audio'], callback_data="format_audio")
            ]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await update.message.reply_text(LANGUAGES[user_lang]['choose_format'], reply_markup=reply_markup)
        return
    
    # Boshqa barcha havolalar uchun video deb hisoblaymiz
    keyboard = [
        [
            InlineKeyboardButton(LANGUAGES[user_lang]['video'], callback_data="format_video"),
            InlineKeyboardButton(LANGUAGES[user_lang]['audio'], callback_data="format_audio")
        ]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text(LANGUAGES[user_lang]['choose_format'], reply_markup=reply_markup)

async def format_button(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Format tanlash tugmasini boshqarish (video yoki audio)"""
    query = update.callback_query
    await query.answer()
    
    user_id = query.from_user.id
    user_lang = user_languages.get(user_id, 'uz')
    format_type = query.data.split('_')[1]
    
    context.user_data['format'] = format_type
    
    try:
        if format_type == 'video':
            # Video sifatini tanlash
            keyboard = [
                [
                    InlineKeyboardButton(LANGUAGES[user_lang]['quality_low'], callback_data="quality_low"),
                    InlineKeyboardButton(LANGUAGES[user_lang]['quality_medium'], callback_data="quality_medium"),
                    InlineKeyboardButton(LANGUAGES[user_lang]['quality_high'], callback_data="quality_high")
                ]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            await query.edit_message_text(LANGUAGES[user_lang]['choose_quality'], reply_markup=reply_markup)
        else:  # audio format
            # Audio uchun bevosita yuklab olish
            status_message = await query.edit_message_text(LANGUAGES[user_lang]['processing'])
            context.user_data['status_message'] = status_message
            await download_media(update, context, format_type='audio', quality='medium')
    except Exception as e:
        logger.error(f"Error in format_button: {e}")
        # Xatolik bo'lsa yangi xabar yuboramiz
        status_message = await context.bot.send_message(
            chat_id=user_id,
            text=LANGUAGES[user_lang]['processing'] if format_type == 'audio' else LANGUAGES[user_lang]['choose_quality']
        )
        context.user_data['status_message'] = status_message
        
        if format_type == 'audio':
            await download_media(update, context, format_type='audio', quality='medium')
        else:
            keyboard = [
                [
                    InlineKeyboardButton(LANGUAGES[user_lang]['quality_low'], callback_data="quality_low"),
                    InlineKeyboardButton(LANGUAGES[user_lang]['quality_medium'], callback_data="quality_medium"),
                    InlineKeyboardButton(LANGUAGES[user_lang]['quality_high'], callback_data="quality_high")
                ]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            await status_message.edit_text(LANGUAGES[user_lang]['choose_quality'], reply_markup=reply_markup)

async def quality_button(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Video sifatini tanlash tugmasini boshqarish"""
    query = update.callback_query
    await query.answer()
    
    user_id = query.from_user.id
    user_lang = user_languages.get(user_id, 'uz')
    quality = query.data.split('_')[1]
    
    # Xabarni tahrirlashdan oldin tekshiramiz
    try:
        status_message = await query.edit_message_text(LANGUAGES[user_lang]['downloading'])
        context.user_data['status_message'] = status_message
        await download_media(update, context, format_type='video', quality=quality)
    except Exception as e:
        logger.error(f"Error in quality_button: {e}")
        # Xatolik bo'lsa yangi xabar yuboramiz
        status_message = await context.bot.send_message(
            chat_id=user_id,
            text=LANGUAGES[user_lang]['downloading']
        )
        context.user_data['status_message'] = status_message
        await download_media(update, context, format_type='video', quality=quality)

async def download_twitter_media(update: Update, context: ContextTypes.DEFAULT_TYPE, status_message) -> None:
    """X/Twitter media (rasm yoki video) yuklab olish"""
    user_id = update.effective_user.id
    user_lang = user_languages.get(user_id, 'uz')
    url = context.user_data.get('url')
    
    if not url:
        url = update.message.text
    
    try:
        # await download_twitter_images(update, context, status_message, None)
        # 1. Avval media ma'lumotlarini olish (rasm yoki video ekanligini aniqlash uchun)
        ydl_info_opts = {
            'quiet': True,
            'no_warnings': True,
            'extract_flat': True,
            'skip_download': True,
        }
        
        with yt_dlp.YoutubeDL(ydl_info_opts) as ydl:
            info = ydl.extract_info(url, download=False)
            
            # 2. Videoni tekshirish
            has_video = False
            if info.get('formats'):
                for fmt in info.get('formats', []):
                    if fmt.get('vcodec') != 'none':
                        has_video = True
                        break
            
            # 3. Videosi bor bo'lsa, yuqori sifatda yuklab olish
            if has_video:
                # Video yuklab olish
                ydl_opts = {
                    'quiet': True,
                    'no_warnings': True,
                    'format': 'best[ext=mp4]/best',
                }
                
                # Vaqtinchalik fayl nomi
                temp_file = f"temp_{user_id}_twitter_video"
                ydl_opts['outtmpl'] = temp_file
                
                await update_status_message(context, user_id, status_message, LANGUAGES[user_lang]['downloading'], edit_only=True)
                
                with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                    info = ydl.extract_info(url, download=True)
                    file_path = ydl.prepare_filename(info)
                    
                    # Faylni tekshirish
                    logger.info(f"Looking for file at: {file_path}")
                    
                    # Fayl mavjud emas bo'lsa, papkada qidirish
                    if not os.path.exists(file_path):
                        logger.info(f"File not found at expected path: {file_path}. Searching directory...")
                        current_dir = os.getcwd()
                        possible_files = [f for f in os.listdir(current_dir) if f.startswith(f"temp_{user_id}")]
                        
                        if possible_files:
                            file_path = max(possible_files, key=lambda f: os.path.getmtime(os.path.join(current_dir, f)))
                            file_path = os.path.join(current_dir, file_path)
                            logger.info(f"Found alternative file: {file_path}")
                    
                    # Fayl mavjudligini tekshirish
                    if not os.path.exists(file_path):
                        # Video yuklab olishda muammo bo'lsa, rasm deb hisoblaymiz
                        await update_status_message(context, user_id, status_message, LANGUAGES[user_lang]['download_image'], edit_only=True)
                        await download_twitter_images(update, context, status_message, info)
                        return
                    
                    # Videoni yuborish
                    try:
                        with open(file_path, 'rb') as file:
                            await context.bot.send_video(
                                chat_id=user_id,
                                video=file,
                                caption=f"🎬 {info.get('title', 'Twitter video')}",
                                supports_streaming=True,
                                width=info.get('width', 640),
                                height=info.get('height', 360)
                            )
                    except Exception as video_error:
                        logger.error(f"Failed to send Twitter video: {video_error}")
                        # Dokument sifatida yuborish
                        try:
                            with open(file_path, 'rb') as file:
                                await context.bot.send_document(
                                    chat_id=user_id,
                                    document=file,
                                    caption=f"📁 {info.get('title', 'Twitter video')}"
                                )
                        except Exception as doc_error:
                            logger.error(f"Error sending Twitter video as document: {doc_error}")
                            # Rasmlarni yuborishga harakat qilish
                            await download_twitter_images(update, context, status_message, info)
                            return
                    
                    # Vaqtinchalik faylni o'chirish
                    try:
                        os.remove(file_path)
                        logger.info(f"Removed temporary file: {file_path}")
                    except Exception as e:
                        logger.error(f"Error removing file: {e}")
                    
                    await update_status_message(context, user_id, status_message, LANGUAGES[user_lang]['download_complete'])
            else:
                # 4. Video topilmasa, rasmlar mavjudligini tekshirish va yuklash
                await update_status_message(context, user_id, status_message, LANGUAGES[user_lang]['download_image'], edit_only=True)
                await download_twitter_images(update, context, status_message, info)
    
    except Exception as e:
        error_str = str(e)
        logger.error(f"Error downloading Twitter media: {e}")
        
        # "No video could be found in this tweet" xatoligi bo'lsa, rasmlarni yuborish
        if 'No video could be found in this tweet' in error_str:
            # Rasmlarni yuborish
            await update_status_message(context, user_id, status_message, LANGUAGES[user_lang]['download_image'], edit_only=True)
            await download_twitter_images(update, context, status_message, None)
        else:
            await update_status_message(context, user_id, status_message, f"{LANGUAGES[user_lang]['download_failed']} Error: {str(e)}")

async def download_twitter_images(update: Update, context: ContextTypes.DEFAULT_TYPE, status_message, info=None) -> None:
    """X/Twitter rasmlarini yuklab olish"""
    user_id = update.effective_user.id
    user_lang = user_languages.get(user_id, 'uz')
    url = context.user_data.get('url')
    
    if not url:
        url = update.message.text
    
    try:
        # Info mavjud bo'lmasa, olish kerak
        if info is None:
            ydl_opts = {
                'quiet': True,
                'no_warnings': True,
                'extract_flat': True,
                'skip_download': True,
                'ignore_no_formats_error': True,
            }
            
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(url, download=False)
        
        images_sent = 0
        
        # Rasmlarni yuborish
        if info.get('thumbnails'):
            # Rasmlarni hajmi bo'yicha tartiblash
            thumbnails = sorted(info['thumbnails'], 
                              key=lambda x: x.get('width', 0) if x.get('width') else 0, 
                              reverse=True)
            
            for thumb in thumbnails:
                if thumb.get('url'):
                    img_url = thumb['url']
                    
                    # Video rasmi emas, asosiy rasm ekanini tekshirish
                    if 'tweet_video_thumb' in img_url or 'ext_tw_video_thumb' in img_url:
                        continue
                        
                    try:
                        img_response = requests.get(img_url)
                        if img_response.status_code == 200:
                            try:
                                await context.bot.send_photo(
                                    chat_id=user_id,
                                    photo=BytesIO(img_response.content),
                                    caption=f"📷 {info.get('title', 'Twitter image')}"
                                )
                                images_sent += 1
                            except Exception as send_error:
                                logger.error(f"Error sending Twitter image: {send_error}")
                                # Dokument sifatida yuborish
                                try:
                                    await context.bot.send_document(
                                        chat_id=user_id,
                                        document=BytesIO(img_response.content),
                                        filename=f"twitter_image_{images_sent+1}.jpg",
                                        caption=f"📷 {info.get('title', 'Twitter image')}"
                                    )
                                    images_sent += 1
                                except Exception as doc_error:
                                    logger.error(f"Error sending Twitter image as document: {doc_error}")
                    except Exception as e:
                        logger.error(f"Error downloading Twitter image: {e}")
        
        # Entries bo'lsa (media gallery)
        if images_sent == 0 and 'entries' in info and info['entries']:
            for entry in info['entries']:
                if entry.get('thumbnails'):
                    try:
                        largest_thumb = max(entry['thumbnails'], 
                                         key=lambda x: x.get('width', 0) if x.get('width') else 0)
                        
                        if largest_thumb.get('url'):
                            img_url = largest_thumb['url']
                            # Video tumbnail emas, asosiy rasm ekanini tekshirish
                            if 'tweet_video_thumb' in img_url or 'ext_tw_video_thumb' in img_url:
                                continue
                                
                            img_response = requests.get(img_url)
                            if img_response.status_code == 200:
                                await context.bot.send_photo(
                                    chat_id=user_id,
                                    photo=BytesIO(img_response.content),
                                    caption=f"📷 {entry.get('title', 'Twitter image')}"
                                )
                                images_sent += 1
                    except Exception as e:
                        logger.error(f"Error sending Twitter gallery image: {e}")
        
        # Hech qanday rasm topilmagan bo'lsa
        if images_sent == 0:
            await update_status_message(context, user_id, status_message, f"{LANGUAGES[user_lang]['download_failed']} Error: No media found in tweet")
            return
        
        await update_status_message(context, user_id, status_message, LANGUAGES[user_lang]['download_complete'])
        
    except Exception as e:
        logger.error(f"Error downloading Twitter images: {e}")
        await update_status_message(context, user_id, status_message, f"{LANGUAGES[user_lang]['download_failed']} Error: {str(e)}")

async def download_image(update: Update, context: ContextTypes.DEFAULT_TYPE, status_message) -> None:
    """Rasmlarni yuklab olish funksiyasi"""
    user_id = update.effective_user.id
    user_lang = user_languages.get(user_id, 'uz')
    url = context.user_data.get('url')
    
    if not url:
        url = update.message.text
    
    try:
        # yt-dlp orqali rasm ma'lumotlarini olish
        ydl_opts = {
            'format': 'best',
            'quiet': True,
            'no_warnings': True,
            'extract_flat': True,
            'skip_download': True,
            'ignore_no_formats_error': True,  # Faylni yuklab olmaslik, faqat ma'lumot olish
        }
        
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False)
            
            # Rasmlarni yuborish
            images_sent = 0
            
            # Thumbnails bo'lsa (ko'p platformalarda shu)
            if info.get('thumbnails'):
                # Eng katta rasmni topish
                thumbnails = sorted(info['thumbnails'], 
                                   key=lambda x: x.get('width', 0) if x.get('width') else 0, 
                                   reverse=True)
                
                # Instagram postlari va Pinterest pinlari uchun eng katta rasmni yuborish
                for thumb in thumbnails:
                    if thumb.get('url'):
                        try:
                            img_response = requests.get(thumb['url'])
                            if img_response.status_code == 200:
                                await context.bot.send_photo(
                                    chat_id=user_id,
                                    photo=BytesIO(img_response.content),
                                    caption=f"📷 {info.get('title', 'Image')}"
                                )
                                images_sent += 1
                                # Faqat eng katta rasmni yuboramiz
                                break
                        except Exception as e:
                            logger.error(f"Error sending image: {e}")
                            continue
            
            # Entries bo'lsa (albom, bir nechta rasm)
            if 'entries' in info and info['entries'] and images_sent == 0:
                for entry in info['entries'][:5]:  # Birinchi 5 ta rasmni yuborish
                    if entry.get('thumbnails'):
                        try:
                            largest_thumb = max(entry['thumbnails'], 
                                              key=lambda x: x.get('width', 0) if x.get('width') else 0)
                            
                            if largest_thumb.get('url'):
                                img_response = requests.get(largest_thumb['url'])
                                if img_response.status_code == 200:
                                    await context.bot.send_photo(
                                        chat_id=user_id,
                                        photo=BytesIO(img_response.content),
                                        caption=f"📷 {entry.get('title', 'Image')}"
                                    )
                                    images_sent += 1
                        except Exception as e:
                            logger.error(f"Error sending image from entry: {e}")
            
            # Hech qanday rasm topilmagan bo'lsa
            if images_sent == 0:
                # Ehtimol bu video bo'lishi mumkin, video sifatida ko'rib ko'ring
                await update_status_message(context, user_id, status_message, LANGUAGES[user_lang]['processing'], edit_only=True)
                # Format va sifat tanlash tugmalarini ko'rsatish
                keyboard = [
                    [
                        InlineKeyboardButton(LANGUAGES[user_lang]['video'], callback_data="format_video"),
                        InlineKeyboardButton(LANGUAGES[user_lang]['audio'], callback_data="format_audio")
                    ]
                ]
                reply_markup = InlineKeyboardMarkup(keyboard)
                try:
                    await status_message.edit_text(LANGUAGES[user_lang]['choose_format'], reply_markup=reply_markup)
                except Exception as e:
                    logger.error(f"Error updating message with format keyboard: {e}")
                    await context.bot.send_message(
                        chat_id=user_id,
                        text=LANGUAGES[user_lang]['choose_format'],
                        reply_markup=reply_markup
                    )
                return
                    
            await update_status_message(context, user_id, status_message, LANGUAGES[user_lang]['download_complete'])
            
    except Exception as e:
        logger.error(f"Error downloading image: {e}")
        await update_status_message(context, user_id, status_message, f"{LANGUAGES[user_lang]['download_failed']} Error: {str(e)}")

async def download_media(update: Update, context: ContextTypes.DEFAULT_TYPE, format_type: str, quality: str) -> None:
    """Video va audiolarni yuklab olish"""
    user_id = update.callback_query.from_user.id
    user_lang = user_languages.get(user_id, 'uz')
    url = context.user_data.get('url')
    status_message = context.user_data.get('status_message')
    
    if not url:
        await update_status_message(context, user_id, status_message, LANGUAGES[user_lang]['download_failed'])
        return
    
    try:
        await update_status_message(context, user_id, status_message, LANGUAGES[user_lang]['downloading'], edit_only=True)
        
        # X/Twitter uchun maxsus tekshiruv - video yo'qligi xatoligini oldini olish
        if ('twitter.com' in url or 'x.com' in url) and '/status/' in url:
            status_message = await update.message.reply_text(LANGUAGES[user_lang]['download_image'])

            # X/Twitter havolalarini maxsus funksiya bilan qayta ishlash
            await download_twitter_media(update, context, status_message, None)
            return
        
        # yt-dlp optsiyalari
        ydl_opts = {
            'quiet': True,
            'no_warnings': True,
            'outtmpl': '%(title)s.%(ext)s',
        }
        
        # Format tanlash
        # Format tanlash
        if format_type == 'audio':
            ydl_opts['format'] = 'bestaudio/best'
            ydl_opts['postprocessors'] = [{
                'key': 'FFmpegExtractAudio',
                'preferredcodec': 'mp3',
                'preferredquality': '192',
            }]
        else:  # video
            # Pinterest uchun maxsus format
            if 'pinterest.com' in url:
                ydl_opts['format'] = 'best'  # Pinterest uchun oddiy 'best' format ishlashi kerak
            else:
                # Boshqa platformalar uchun
                if quality == 'low':
                    ydl_opts['format'] = 'worst[ext=mp4]/worst'
                elif quality == 'medium':
                    ydl_opts['format'] = 'best[height<=480][ext=mp4]/best[height<=480]/best'
                else:  # high
                    ydl_opts['format'] = 'best[ext=mp4]/best'
        
        # Vaqtinchalik fayl nomi
        temp_file = f"temp_{user_id}_{format_type}_{quality}"
        ydl_opts['outtmpl'] = temp_file
        
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)
            file_path = ydl.prepare_filename(info)
            
            # MP3 ga konvertlangan bo'lsa
            if format_type == 'audio':
                file_path = f"{temp_file}.mp3"
            
            # Faylni tekshirish
            logger.info(f"Looking for file at: {file_path}")
            
            # Fayl mavjud emas bo'lsa, papkada qidirish
            if not os.path.exists(file_path):
                logger.info(f"File not found at expected path: {file_path}. Searching directory...")
                current_dir = os.getcwd()
                possible_files = [f for f in os.listdir(current_dir) if f.startswith(f"temp_{user_id}")]
                
                if possible_files:
                    # Eng yangi faylni olish
                    file_path = max(possible_files, key=lambda f: os.path.getmtime(os.path.join(current_dir, f)))
                    file_path = os.path.join(current_dir, file_path)
                    logger.info(f"Found alternative file: {file_path}")
            
            # Fayl mavjudligini tekshirish
            if not os.path.exists(file_path):
                await update_status_message(
                    context, user_id, status_message, 
                    f"{LANGUAGES[user_lang]['download_failed']} Error: File not found: {file_path}"
                )
                return
                
            # Telegram serveriga fayl yuborish
            try:
                with open(file_path, 'rb') as file:
                    if format_type == 'audio':
                        await context.bot.send_audio(
                            chat_id=user_id,
                            audio=file,
                            title=info.get('title', 'Audio'),
                            performer=info.get('uploader', 'Unknown'),
                            caption=f"🎵 {info.get('title', 'Audio')}"
                        )
                    else:  # video
                        # Kengaytmani tekshirish va zarur bo'lsa o'zgartirish
                        file_ext = os.path.splitext(file_path)[1].lower()
                        if not file_ext or file_ext not in ['.mp4', '.avi', '.mov', '.mkv']:
                            new_file_path = f"{os.path.splitext(file_path)[0]}.mp4"
                            try:
                                os.rename(file_path, new_file_path)
                                file_path = new_file_path
                                logger.info(f"Renamed file to ensure video extension: {file_path}")
                                file.close()
                                file = open(file_path, 'rb')
                            except Exception as e:
                                logger.error(f"Error renaming file: {e}")
                        
                        # Videoni yuborish
                        try:
                            await context.bot.send_video(
                                chat_id=user_id,
                                video=file,
                                caption=f"🎬 {info.get('title', 'Video')}",
                                supports_streaming=True,
                                width=info.get('width', 640),
                                height=info.get('height', 360)
                            )
                        except Exception as video_error:
                            logger.error(f"Failed to send as video: {video_error}")
                            # Dokument sifatida yuborish
                            file.seek(0)
                            await context.bot.send_document(
                                chat_id=user_id,
                                document=file,
                                caption=f"📁 {info.get('title', 'Video file')} (video)"
                            )
            except Exception as e:
                logger.error(f"Error sending file: {e}")
                # Yana bir marta urinib ko'rish
                try:
                    with open(file_path, 'rb') as file:
                        await context.bot.send_document(
                            chat_id=user_id,
                            document=file,
                            caption=f"📁 {info.get('title', 'Media file')}"
                        )
                except Exception as send_error:
                    logger.error(f"Error sending as document: {send_error}")
                    await update_status_message(
                        context, user_id, status_message,
                        f"{LANGUAGES[user_lang]['download_failed']} Error: {str(e)}"
                    )
                    return
            
            # Vaqtinchalik faylni o'chirish
            try:
                os.remove(file_path)
                logger.info(f"Removed temporary file: {file_path}")
            except Exception as e:
                logger.error(f"Error removing file: {e}")
            
            await update_status_message(context, user_id, status_message, LANGUAGES[user_lang]['download_complete'])
            
    except Exception as e:
        logger.error(f"Error downloading media: {e}")
        error_str = str(e)
        
        # Pinterest uchun format xatoligini tekshirish
        if 'pinterest.com' in url and 'Requested format is not available' in error_str:
            # Boshqa format bilan qayta urinish
            try:
                logger.info("Retrying Pinterest video with simpler format options")
                # Ydl optionlarni o'zgartirish
                ydl_opts['format'] = 'best'
                
                with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                    info = ydl.extract_info(url, download=True)
                    # Qolgan kod...
                    
            except Exception as retry_error:
                logger.error(f"Retry also failed: {retry_error}")
                await update_status_message(context, user_id, status_message, 
                    f"{LANGUAGES[user_lang]['download_failed']} Error: Format not available for this Pinterest video")
        else:
            await update_status_message(context, user_id, status_message, 
                f"{LANGUAGES[user_lang]['download_failed']} Error: {str(e)}")

# Pinterest videolari uchun maxsus yuklab olish funksiyasi
async def download_pinterest_media(update: Update, context: ContextTypes.DEFAULT_TYPE, status_message) -> None:
    """Pinterest rasim va videolarini yuklab olish uchun maxsus funksiya"""
    user_id = update.effective_user.id
    user_lang = user_languages.get(user_id, 'uz')
    url = context.user_data.get('url')
    
    if not url:
        url = update.message.text
    
    await update_status_message(context, user_id, status_message, LANGUAGES[user_lang]['downloading'], edit_only=True)
    
    try:
        # Pinterest extractor klassini ishlatish
        pinterest = Pinterest(url)
        media_info = pinterest.get_media_link()
        
        if not media_info["success"]:
            await update_status_message(context, user_id, status_message, 
                                     f"{LANGUAGES[user_lang]['download_failed']} Error: Could not extract media from Pinterest")
            return
        
        media_type = media_info["type"]
        media_link = media_info["link"]
        
        if not media_link:
            await update_status_message(context, user_id, status_message, 
                                     f"{LANGUAGES[user_lang]['download_failed']} Error: No media link found")
            return
        
        # Media yuklab olish
        response = requests.get(media_link)
        if response.status_code != 200:
            await update_status_message(context, user_id, status_message, 
                                     f"{LANGUAGES[user_lang]['download_failed']} Error: Failed to download media")
            return
        
        # Media turini tekshirish va yuborish
        if media_type == "video":
            # Video yuborish
            temp_file = f"temp_pinterest_{user_id}.mp4"
            with open(temp_file, 'wb') as f:
                f.write(response.content)
            
            with open(temp_file, 'rb') as file:
                try:
                    await context.bot.send_video(
                        chat_id=user_id,
                        video=file,
                        caption="🎬 Pinterest video",
                        supports_streaming=True
                    )
                except Exception as video_error:
                    logger.error(f"Failed to send Pinterest video: {video_error}")
                    file.seek(0)
                    await context.bot.send_document(
                        chat_id=user_id,
                        document=file,
                        caption="📁 Pinterest video"
                    )
            
            # Vaqtinchalik faylni o'chirish
            try:
                os.remove(temp_file)
            except Exception as e:
                logger.error(f"Error removing temp file: {e}")
        
        elif media_type == "image":
            # Rasim yuborish
            await context.bot.send_photo(
                chat_id=user_id,
                photo=BytesIO(response.content),
                caption="📷 Pinterest image"
            )
        
        await update_status_message(context, user_id, status_message, LANGUAGES[user_lang]['download_complete'])
        
    except Exception as e:
        logger.error(f"Error downloading Pinterest media: {e}")
        # Muqobil usulni sinab ko'rish
        try:
            logger.info("Falling back to yt-dlp for Pinterest")
            await download_image(update, context, status_message)
        except Exception as ytdlp_error:
            logger.error(f"yt-dlp also failed: {ytdlp_error}")
            await update_status_message(context, user_id, status_message, 
                                     f"{LANGUAGES[user_lang]['download_failed']} Error: {str(e)}")

def main() -> None:
    # Bot tokenini o'rnating
    TOKEN = "8107931275:AAETPUD8nEnOey1erBwuzaYc1v28-AMn41A"
    
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