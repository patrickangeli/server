import psutil
from telegram import Update
from telegram.ext import ContextTypes
from telegram.ext import Updater, CommandHandler, CallbackContext, Application
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import CallbackQueryHandler, ConversationHandler, MessageHandler, filters
from threading import Thread
from time import sleep
import subprocess
import asyncio

# Configurações
BOT_TOKEN = '7609833263:AAEmDv3ORnSZEEGjA0OHQBGFvXEoeGaYiww'
CHAT_ID = '7609833263'
LIMITE_CPU = 80

# Estados para a conversa
WAITING_FOR_TORRENT = 1
WAITING_FOR_FOLDER = 2

# Dicionário para armazenar temporariamente os links dos torrents
torrent_links = {}

async def start_download(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Inicia o processo de download perguntando onde salvar"""
    keyboard = [
        [
            InlineKeyboardButton("🎬 Filmes", callback_data='movies'),
            InlineKeyboardButton("📺 Séries", callback_data='series')
        ]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text(
        'Escolha onde salvar o download:',
        reply_markup=reply_markup
    )
    return WAITING_FOR_FOLDER

async def folder_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Processa a escolha da pasta e solicita o link do torrent"""
    query = update.callback_query
    await query.answer()
    
    # Salva a escolha da pasta no contexto
    context.user_data['folder'] = 'movies' if query.data == 'movies' else 'series'
    
    await query.edit_message_text(
        f"📥 Pasta selecionada: {'Filmes' if query.data == 'movies' else 'Séries'}\n"
        "Por favor, envie o link do torrent:"
    )
    return WAITING_FOR_TORRENT

async def process_torrent(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Processa o link do torrent recebido"""
    torrent_link = update.message.text
    folder = context.user_data['folder']
    save_path = f"/mnt/rclone/{folder}/"  # Ajuste o caminho conforme necessário
    
    try:
        # Comando para adicionar o torrent ao qBittorrent
        command = f"""curl -X POST -F "urls={torrent_link}" -F "savepath={save_path}" \
                  http://localhost:8080/api/v2/torrents/add"""
        
        process = await asyncio.create_subprocess_shell(
            command,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        
        stdout, stderr = await process.communicate()
        
        if process.returncode == 0:
            await update.message.reply_text(
                f"✅ Torrent adicionado com sucesso!\n"
                f"📂 Salvando em: {folder}"
            )
        else:
            await update.message.reply_text(f"❌ Erro ao adicionar torrent:\n{stderr.decode().strip()}")
    
    except Exception as e:
        await update.message.reply_text(f"🔥 Erro: {str(e)}")
    
    return ConversationHandler.END

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Cancela a operação de download"""
    await update.message.reply_text("❌ Operação cancelada.")
    return ConversationHandler.END

# Configuração moderna
application = Application.builder().token(BOT_TOKEN).build()

# 1. Defina a função get_id ANTES de usá-la
async def get_id(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    await update.message.reply_text(f"📨 Chat ID: {chat_id}")

async def metrics(update: Update, context: ContextTypes.DEFAULT_TYPE):
    cpu = psutil.cpu_percent()
    mem = psutil.virtual_memory().percent
    disco = psutil.disk_usage('/').percent
    await update.message.reply_text(
        f"📊 CPU: {cpu}%\n"
        f"💾 Memória: {mem}%\n"
        f"💽 Disco: {disco}%"
    )
    await update.message.reply_text(resposta)

async def start_rclone(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        command = """rclone mount onedrive: /mnt/rclone \
            --allow-other \
            --dir-cache-time 96h \
            --vfs-cache-mode full \
            --vfs-cache-max-size 20G \
            --buffer-size 512M \
            --log-level INFO \
            --daemon"""  # Adiciona --daemon para rodar em background
        
        process = await asyncio.create_subprocess_shell(
            command,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        
        stdout, stderr = await process.communicate()
        
        if process.returncode == 0:
            await update.message.reply_text("✅ Rclone iniciado com sucesso!")
        else:
            await update.message.reply_text(f"❌ Erro ao iniciar Rclone:\n{stderr.decode().strip()}")
            
    except Exception as e:
        await update.message.reply_text(f"🔥 Falha ao iniciar Rclone: {str(e)}")

async def start_jellyfin(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        command = "/usr/bin/docker start jellyfin"
        
        process = await asyncio.create_subprocess_shell(
            command,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        
        stdout, stderr = await process.communicate()
        
        if process.returncode == 0:
            await update.message.reply_text("✅ Jellyfin iniciado com sucesso!")
        else:
            await update.message.reply_text(f"❌ Erro ao iniciar Jellyfin:\n{stderr.decode().strip()}")
            
    except Exception as e:
        await update.message.reply_text(f"🔥 Falha ao iniciar Jellyfin: {str(e)}")

# Crie o conversation handler
conv_handler = ConversationHandler(
    entry_points=[CommandHandler('download', start_download)],
    states={
        WAITING_FOR_FOLDER: [CallbackQueryHandler(folder_callback)],
        WAITING_FOR_TORRENT: [MessageHandler(filters.TEXT & ~filters.COMMAND, process_torrent)]
    },
    fallbacks=[CommandHandler('cancel', cancel)]
)



async def restart_jellyfin(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        # Executa o comando com sudo
        process = await asyncio.create_subprocess_shell(
            "sudo docker restart jellyfin",
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        
        # Captura saída e erros
        stdout, stderr = await process.communicate()
        
        # Resposta personalizada
        if process.returncode == 0:
            await update.message.reply_text("✅ Jellyfin reiniciado com sucesso")
        else:
            await update.message.reply_text(f"❌ Erro:\n{stderr.decode().strip()}")
            
    except Exception as e:
        await update.message.reply_text(f"🔥 Falha crítica: {str(e)}")

# Adicione o handler ANTES de iniciar o bot
application.add_handler(conv_handler)
application.add_handler(CommandHandler("restart", restart_jellyfin))
application.add_handler(CommandHandler("getid", get_id))
application.add_handler(CommandHandler("metrics", metrics))
application.add_handler(CommandHandler("rclone", start_rclone))
application.add_handler(CommandHandler("start", start_jellyfin))
# Monitoramento contínuo (executado em segundo plano)
async def monitoramento():
    while True:
        uso_cpu = psutil.cpu_percent(interval=1)
        if uso_cpu > LIMITE_CPU:
            await application.bot.send_message(
                chat_id=CHAT_ID,
                text=f"⚠️ ALERTA DE CPU: {uso_cpu}%"
            )
        await asyncio.sleep(60)
async def check_cpu(context: ContextTypes.DEFAULT_TYPE):
    try:
        uso_cpu = psutil.cpu_percent()
        if uso_cpu > LIMITE_CPU:
            await context.bot.send_message(
                chat_id=CHAT_ID,
                text=f"⚠️ ALERTA: CPU a {uso_cpu}%"
            )
    except Exception as e:
        print(f"Erro ao enviar alerta: {e}")

# Configuração final
if __name__ == "__main__":
    application.add_handler(CommandHandler("getid", get_id))  # Novo comando para debug
    application.job_queue.run_repeating(check_cpu, interval=60, first=0)
    application.run_polling()
# Configuração dos handlers
application.add_handler(CommandHandler("metrics", metrics))
