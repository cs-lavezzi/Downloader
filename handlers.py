from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes

import logging
from config import LANGUAGES
from utils import is_valid_url
from downloaders import download_media, download_image

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
    
    # Rasm yoki video ekanligini aniqlash
    is_image = False
    is_video = False
    
    # Instagram va Pinterest aniq rasm holatlarini aniqlash
    if 'instagram.com' in url and '/p/' in url and not ('/reel/' in url):
        # Instagram post (rasm bo'lishi mumkin)
        is_image = True
    elif 'pinterest.com' in url and '/pin/' in url:
        # Pinterest pin (ko'pincha rasm)
        is_image = True
    
    # X/Twitter, Instagram reels, YouTube, TikTok - video deb hisoblaymiz
    if ('twitter.com' in url or 'x.com' in url) and '/status/' in url:
        is_video = True
    elif 'instagram.com' in url and '/reel/' in url:
        is_video = True
    elif 'youtube.com' in url or 'youtu.be' in url:
        is_video = True
    elif 'tiktok.com' in url:
        is_video = True
    
    # Rasm bo'lsa to'g'ridan-to'g'ri yuklab olish
    if is_image and not is_video:
        status_message = await update.message.reply_text(LANGUAGES[user_lang]['download_image'])
        await download_image(update, context, status_message)
        return
    
    # Video bo'lsa format tanlash (video yoki audio)
    keyboard = [
        [
            InlineKeyboardButton(LANGUAGES[user_lang]['video'], callback_data="format_video"),
            InlineKeyboardButton(LANGUAGES[user_lang]['audio'], callback_data="format_audio")
        ]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text(LANGUAGES[user_lang]['choose_format'], reply_markup=reply_markup)

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
