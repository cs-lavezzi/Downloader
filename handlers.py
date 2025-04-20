from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes

import logging
from config import LANGUAGES
from utils import is_valid_url, update_status_message
from downloaders import download_media, download_image
import yt_dlp

# Logging nastroykasi
logging.basicConfig(level=logging.ERROR)
logger = logging.getLogger(__name__)

# Foydalanuvchi tilini saqlash uchun
user_languages = {}

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
    url = update.message.text
    user_id = update.effective_user.id
    user_lang = user_languages.get(user_id, 'uz')
    
    if not is_valid_url(url):
        await update.message.reply_text(LANGUAGES[user_lang]['invalid_url'])
        return
    
    # URL-ni context.user_data-ga saqlash
    context.user_data['url'] = url
    
    # X/Twitter havolasini tekshirish
    if ('twitter.com' in url or 'x.com' in url) and '/status/' in url:
        # Dastlab media turini aniqlash uchun yuklab ko'ramiz
        status_message = await update.message.reply_text(LANGUAGES[user_lang]['processing'])
        await detect_media_type(update, context, status_message)
        return
    
    # Instagram reels aniq video ekanini bilamiz
    if 'instagram.com' in url and '/reel/' in url:
        # Format tanlash (video yoki audio)
        keyboard = [
            [
                InlineKeyboardButton(LANGUAGES[user_lang]['video'], callback_data="format_video"),
                InlineKeyboardButton(LANGUAGES[user_lang]['audio'], callback_data="format_audio")
            ]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await update.message.reply_text(LANGUAGES[user_lang]['choose_format'], reply_markup=reply_markup)
        return
    
    # Instagram posts - rasm yoki video bo'lishi mumkin
    if 'instagram.com' in url and '/p/' in url:
        status_message = await update.message.reply_text(LANGUAGES[user_lang]['processing'])
        await detect_media_type(update, context, status_message)
        return
    
    # Pinterest uchun tekshirish
    if 'pinterest.com' in url and '/pin/' in url:
        status_message = await update.message.reply_text(LANGUAGES[user_lang]['processing'])
        await detect_media_type(update, context, status_message)
        return
    
    # YouTube va TikTok doim video
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
    
    # Boshqa barcha havolalar uchun turi aniqlanmagan, tekshirishga harakat qilamiz
    status_message = await update.message.reply_text(LANGUAGES[user_lang]['processing'])
    await detect_media_type(update, context, status_message)

async def detect_media_type(update: Update, context: ContextTypes.DEFAULT_TYPE, status_message) -> None:
    """Havola media turini (rasm yoki video) aniqlash"""
    user_id = update.effective_user.id
    user_lang = user_languages.get(user_id, 'uz')
    url = context.user_data.get('url')
    
    try:
        # yt-dlp orqali media ma'lumotlarini olish
        ydl_opts = {
            'quiet': True,
            'no_warnings': True,
            'extract_flat': True,
            'skip_download': True,
        }
        
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False)
            
            # Video mavjudligini tekshirish
            is_video = False
            
            # Video yoki streaming mavjudligini tekshirish
            if info.get('is_live'):
                is_video = True
            elif info.get('formats'):
                is_video = True
            elif info.get('entries') and any(entry.get('formats') for entry in info.get('entries', [])):
                is_video = True
            elif info.get('duration') and info.get('duration') > 0:
                is_video = True
            elif info.get('ext') in ['mp4', 'mov', 'webm', 'mkv', 'avi']:
                is_video = True
            
            # Twitter havolasi uchun qo'shimcha tekshiruvlar
            if ('twitter.com' in url or 'x.com' in url) and '/status/' in url:
                # Video formatlari mavjud bo'lsa, video
                if info.get('formats'):
                    for format_info in info.get('formats', []):
                        if format_info.get('vcodec') != 'none' and format_info.get('acodec') != 'none':
                            is_video = True
                            break
                
                # Video bo'lmasa, ehtimol rasm
                if not is_video:
                    # Rasmi borligini tekshirish
                    if info.get('thumbnails') and len(info.get('thumbnails', [])) > 0:
                        # Rasmni yuborish
                        await update_status_message(context, user_id, status_message, LANGUAGES[user_lang]['download_image'], edit_only=True)
                        await download_image(update, context, status_message)
                        return
            
            if is_video:
                # Videoni format va sifat tanlov menusi bilan yuborish
                keyboard = [
                    [
                        InlineKeyboardButton(LANGUAGES[user_lang]['video'], callback_data="format_video"),
                        InlineKeyboardButton(LANGUAGES[user_lang]['audio'], callback_data="format_audio")
                    ]
                ]
                reply_markup = InlineKeyboardMarkup(keyboard)
                await status_message.edit_text(LANGUAGES[user_lang]['choose_format'], reply_markup=reply_markup)
            else:
                # Rasmlarni yuborish
                await update_status_message(context, user_id, status_message, LANGUAGES[user_lang]['download_image'], edit_only=True)
                await download_image(update, context, status_message)
                
    except Exception as e:
        logger.error(f"Error detecting media type: {e}")
        # Xatolik bo'lsa video deb hisoblaymiz (xavfsizroq)
        keyboard = [
            [
                InlineKeyboardButton(LANGUAGES[user_lang]['video'], callback_data="format_video"),
                InlineKeyboardButton(LANGUAGES[user_lang]['audio'], callback_data="format_audio")
            ]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await status_message.edit_text(LANGUAGES[user_lang]['choose_format'], reply_markup=reply_markup)

async def format_button(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
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
