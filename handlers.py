from io import BytesIO
import os
import requests
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
        status_message = await update.message.reply_text(LANGUAGES[user_lang]['download_image'])
        await download_image(update, context, status_message)
        return
    
    # Instagram posts - aniqlab olish kerak
    if 'instagram.com' in url and '/p/' in url:
        # Instagram havola turi aniqlab olish
        try:
            ydl_opts = {
                'quiet': True,
                'no_warnings': True,
                'skip_download': True,
            }
            
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(url, download=False)
                
                # Video formatlar mavjud bo'lsa, video
                if info.get('formats') and len(info.get('formats', [])) > 0:
                    keyboard = [
                        [
                            InlineKeyboardButton(LANGUAGES[user_lang]['video'], callback_data="format_video"),
                            InlineKeyboardButton(LANGUAGES[user_lang]['audio'], callback_data="format_audio")
                        ]
                    ]
                    reply_markup = InlineKeyboardMarkup(keyboard)
                    await update.message.reply_text(LANGUAGES[user_lang]['choose_format'], reply_markup=reply_markup)
                    return
                else:
                    # Video formatlar topilmasa, rasm
                    status_message = await update.message.reply_text(LANGUAGES[user_lang]['download_image'])
                    await download_image(update, context, status_message)
                    return
                    
        except Exception as e:
            logger.error(f"Error detecting Instagram media type: {e}")
            # Xato yuz berganda rasm deb olish
            status_message = await update.message.reply_text(LANGUAGES[user_lang]['download_image'])
            await download_image(update, context, status_message)
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

async def download_twitter_media(update: Update, context: ContextTypes.DEFAULT_TYPE, status_message) -> None:
    """X/Twitter media (rasm yoki video) yuklab olish"""
    user_id = update.effective_user.id
    user_lang = user_languages.get(user_id, 'uz')
    url = context.user_data.get('url')
    
    if not url:
        url = update.message.text
    
    try:
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
                
                await status_message.edit_text(LANGUAGES[user_lang]['downloading'])
                
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
                        await status_message.edit_text(LANGUAGES[user_lang]['download_image'])
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
                    
                    await status_message.edit_text(LANGUAGES[user_lang]['download_complete'])
            else:
                # 4. Video topilmasa, rasmlar mavjudligini tekshirish va yuklash
                await status_message.edit_text(LANGUAGES[user_lang]['download_image'])
                await download_twitter_images(update, context, status_message, info)
    
    except Exception as e:
        error_str = str(e)
        logger.error(f"Error downloading Twitter media: {e}")
        
        # "No video could be found in this tweet" xatoligi bo'lsa, rasmlarni yuborish
        if 'No video could be found in this tweet' in error_str:
            # Rasmlarni yuborish
            await status_message.edit_text(LANGUAGES[user_lang]['download_image'])
            await download_twitter_images(update, context, status_message, None)
        else:
            await status_message.edit_text(f"{LANGUAGES[user_lang]['download_failed']} Error: {str(e)}")


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
            await status_message.edit_text(f"{LANGUAGES[user_lang]['download_failed']} Error: No media found in tweet")
            return
        
        await status_message.edit_text(LANGUAGES[user_lang]['download_complete'])
        
    except Exception as e:
        logger.error(f"Error downloading Twitter images: {e}")
        await status_message.edit_text(f"{LANGUAGES[user_lang]['download_failed']} Error: {str(e)}")


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
