import os
import logging
import requests
from io import BytesIO
import yt_dlp
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes

from config import LANGUAGES, user_languages
from utils import update_status_message, logger

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
        
        # Platforma turi aniqlab olish
        is_twitter = 'twitter.com' in url or 'x.com' in url
        is_instagram = 'instagram.com' in url
        is_tiktok = 'tiktok.com' in url
        is_youtube = 'youtube.com' in url or 'youtu.be' in url
        
        # yt-dlp optsiyalari
        ydl_opts = {
            'quiet': True,
            'no_warnings': True,
            'outtmpl': '%(title)s.%(ext)s',
        }
        
        # Audio formati tanlangan bo'lsa
        if format_type == 'audio':
            ydl_opts['format'] = 'bestaudio/best'
            ydl_opts['postprocessors'] = [{
                'key': 'FFmpegExtractAudio',
                'preferredcodec': 'mp3',
                'preferredquality': '192',
            }]
        else:  # video
            # Sifatiga qarab format tanlash
            if quality == 'low':
                if is_twitter or is_instagram:
                    ydl_opts['format'] = 'worst[ext=mp4]/worst'
                else:
                    ydl_opts['format'] = 'worst[ext=mp4]/worst'
            elif quality == 'medium':
                if is_twitter:
                    ydl_opts['format'] = 'best[height<=480][ext=mp4]/best[height<=480]/best'
                elif is_instagram:
                    ydl_opts['format'] = 'dash-HD-mp4/best[height<=720][ext=mp4]/best[ext=mp4]/best'
                else:
                    ydl_opts['format'] = 'best[height<=480][ext=mp4]/best[height<=480]/best'
            else:  # high
                if is_twitter or is_instagram:
                    ydl_opts['format'] = 'best[ext=mp4]/best'
                else:
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
                        
                        # Video yuborish
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
                            # Fayl sifatida yuborish
                            file.seek(0)
                            await context.bot.send_document(
                                chat_id=user_id,
                                document=file,
                                caption=f"📁 {info.get('title', 'Video file')} (video)"
                            )
                            
            except Exception as e:
                logger.error(f"Error sending file: {e}")
                # Dokument sifatida yuborishga harakat qilish
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
            'skip_download': True,  # Faylni yuklab olmaslik, faqat ma'lumot olish
        }
        
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False)
            
            # Rasmlarni yuborish
            images_sent = 0
            
            # X/Twitter rasmlarini ajratib olish
            if ('twitter.com' in url or 'x.com' in url) and '/status/' in url:
                if info.get('thumbnails'):
                    # Twitter thumbnails - odatda tweet rasmlari
                    thumbnails = sorted(info['thumbnails'], 
                                      key=lambda x: x.get('width', 0) if x.get('width') else 0, 
                                      reverse=True)
                    
                    for thumb in thumbnails:
                        if thumb.get('url'):
                            try:
                                # X/Twitter rasmlarini filtrlash
                                img_url = thumb['url']
                                # Video tumbnail emas, asosiy rasm ekanini tekshirish
                                # Videolarni filtrlash
                                if 'tweet_video_thumb' in img_url or 'ext_tw_video_thumb' in img_url:
                                    continue
                                
                                img_response = requests.get(img_url)
                                if img_response.status_code == 200:
                                    await context.bot.send_photo(
                                        chat_id=user_id,
                                        photo=BytesIO(img_response.content),
                                        caption=f"📷 {info.get('title', 'Twitter image')}"
                                    )
                                    images_sent += 1
                            except Exception as e:
                                logger.error(f"Error sending Twitter image: {e}")
                                continue
                
                # Entries bo'lsa (tweet media gallery)
                if 'entries' in info and info['entries'] and images_sent == 0:
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
                                logger.error(f"Error sending Twitter image from entry: {e}")
            else:
                # Boshqa platformalar uchun (Instagram, Pinterest va h.k)
                if info.get('thumbnails'):
                    # Eng katta rasmni topish
                    thumbnails = sorted(info['thumbnails'], 
                                       key=lambda x: x.get('width', 0) if x.get('width') else 0, 
                                       reverse=True)
                    
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
                                    # Faqat eng katta rasmni yuboramiz (galereya bo'lsa)
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
                # Ehtimol bu video bo'lishi mumkin
                await update_status_message(context, user_id, status_message, 
                                          LANGUAGES[user_lang]['choose_format'], edit_only=True)
                
                # Video/Audio formatini tanlash
                keyboard = [
                    [
                        InlineKeyboardButton(LANGUAGES[user_lang]['video'], callback_data="format_video"),
                        InlineKeyboardButton(LANGUAGES[user_lang]['audio'], callback_data="format_audio")
                    ]
                ]
                reply_markup = InlineKeyboardMarkup(keyboard)
                await status_message.edit_text(LANGUAGES[user_lang]['choose_format'], reply_markup=reply_markup)
                return
                    
            await update_status_message(context, user_id, status_message, LANGUAGES[user_lang]['download_complete'])
            
    except Exception as e:
        logger.error(f"Error downloading image: {e}")
        await update_status_message(context, user_id, status_message, f"{LANGUAGES[user_lang]['download_failed']} Error: {str(e)}")

# CallbackQuery simulyatsiya qilish uchun
class DummyCallbackQuery:
    def __init__(self, user_id):
        self.from_user = type('obj', (object,), {'id': user_id})
