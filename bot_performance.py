import psutil
import json
import asyncio
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (ContextTypes, CommandHandler, Application,
                          CallbackQueryHandler, ConversationHandler, MessageHandler, filters)
from time import sleep
import subprocess

# Configurações
BOT_TOKEN = '7609833263:AAEmDv3ORnSZEEGjA0OHQBGFvXEoeGaYiww'
CHAT_ID = '7609833263'
LIMITE_CPU = 80

# Estados para a conversa
WAITING_FOR_TORRENT = 1
WAITING_FOR_FOLDER = 2

torrent_links = {}

async def start_download(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [[InlineKeyboardButton("🎬 Filmes", callback_data='movies'),
                 InlineKeyboardButton("📺 Séries", callback_data='series')]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text('Escolha onde salvar o download:', reply_markup=reply_markup)
    return WAITING_FOR_FOLDER

async def folder_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    context.user_data['folder'] = 'Filmes' if query.data == 'movies' else 'Series'
    await query.edit_message_text(f"📥 Pasta selecionada: {context.user_data['folder']}\nPor favor, envie o link do torrent:")
    return WAITING_FOR_TORRENT

async def process_torrent(update: Update, context: ContextTypes.DEFAULT_TYPE):
    torrent_link = update.message.text
    folder = context.user_data['folder']
    cache_path = f"/home/patrick/download_cache/{folder}/"
    final_path = f"/mnt/rclone/{folder}/"
    
    try:
        login_cmd = """curl -X POST -c cookie.txt -d 'username=admin&password=adminadmin' http://localhost:8080/api/v2/auth/login"""
        login_process = await asyncio.create_subprocess_shell(login_cmd, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE)
        await login_process.communicate()
        
        if login_process.returncode != 0:
            await update.message.reply_text("❌ Erro de autenticação no qBittorrent")
            return ConversationHandler.END
        
        command = f"""curl -X POST -b cookie.txt -F "urls={torrent_link}" -F "savepath={cache_path}" -F "category={folder}" http://localhost:8080/api/v2/torrents/add"""
        process = await asyncio.create_subprocess_shell(command, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE)
        stdout, stderr = await process.communicate()
        
        if process.returncode == 0:
            await update.message.reply_text(f"✅ Torrent adicionado com sucesso!\n📂 Baixando em: {cache_path}\n🔄 Será movido para: {final_path}\n⏳ Iniciando download...")
        else:
            await update.message.reply_text(f"❌ Erro ao adicionar torrent:\n{stderr.decode().strip()}")
    
    except Exception as e:
        await update.message.reply_text(f"🔥 Erro: {str(e)}")
    
    return ConversationHandler.END

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("❌ Operação cancelada.")
    return ConversationHandler.END

async def get_id(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    await update.message.reply_text(f"📨 Chat ID: {chat_id}")

async def metrics(update: Update, context: ContextTypes.DEFAULT_TYPE):
    cpu = psutil.cpu_percent()
    mem = psutil.virtual_memory().percent
    disco = psutil.disk_usage('/').percent
    resposta = f"📊 CPU: {cpu}%\n💾 Memória: {mem}%\n💽 Disco: {disco}%"
    await update.message.reply_text(resposta)

async def start_rclone(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        await asyncio.create_subprocess_shell("pkill -f rclone")
        await asyncio.sleep(2)
        command = """rclone mount onedrive: /mnt/rclone --allow-other --dir-cache-time 96h --vfs-cache-mode full --vfs-cache-max-size 20G --buffer-size 512M --log-level INFO"""
        process = await asyncio.create_subprocess_shell(command, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE)
        stdout, stderr = await process.communicate()
        if process.returncode == 0:
            await update.message.reply_text("✅ Rclone reiniciado com sucesso!")
        else:
            await update.message.reply_text(f"❌ Erro ao iniciar Rclone:\n{stderr.decode().strip()}")
    except Exception as e:
        await update.message.reply_text(f"🔥 Falha ao iniciar Rclone: {str(e)}")

async def start_jellyfin(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        process = await asyncio.create_subprocess_shell("/usr/bin/docker start jellyfin", stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE)
        stdout, stderr = await process.communicate()
        if process.returncode == 0:
            await update.message.reply_text("✅ Jellyfin iniciado com sucesso!")
        else:
            await update.message.reply_text(f"❌ Erro ao iniciar Jellyfin:\n{stderr.decode().strip()}")
    except Exception as e:
        await update.message.reply_text(f"🔥 Falha ao iniciar Jellyfin: {str(e)}")

conv_handler = ConversationHandler(
    entry_points=[CommandHandler('download', start_download)],
    states={
        WAITING_FOR_FOLDER: [CallbackQueryHandler(folder_callback)],
        WAITING_FOR_TORRENT: [MessageHandler(filters.TEXT & ~filters.COMMAND, process_torrent)]
    },
    fallbacks=[CommandHandler('cancel', cancel)]
)

async def check_cpu(context: ContextTypes.DEFAULT_TYPE):
    uso_cpu = psutil.cpu_percent()
    if uso_cpu > LIMITE_CPU:
        await context.bot.send_message(chat_id=CHAT_ID, text=f"⚠️ ALERTA: CPU a {uso_cpu}%")

if __name__ == "__main__":
    application = Application.builder().token(BOT_TOKEN).build()
    application.add_handler(conv_handler)
    application.add_handler(CommandHandler("getid", get_id))
    application.add_handler(CommandHandler("metrics", metrics))
    application.add_handler(CommandHandler("rclone", start_rclone))
    application.add_handler(CommandHandler("start", start_jellyfin))
    application.job_queue.run_repeating(check_cpu, interval=60, first=0)
    print("Bot iniciado...")
    application.run_polling()
