import psutil
import json
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
    print("Comando /download recebido")  # Adicione este print
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
    context.user_data['folder'] = 'Filmes' if query.data == 'movies' else 'Series'
    
    await query.edit_message_text(
        f"📥 Pasta selecionada: {'Filmes' if query.data == 'movies' else 'Séries'}\n"
        "Por favor, envie o link do torrent:"
    )
    return WAITING_FOR_TORRENT

async def process_torrent(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Processa o link do torrent recebido"""
    torrent_link = update.message.text
    folder = context.user_data['folder']
    cache_path = f"/home/patrick/download_cache/{folder}/"  # Caminho do cache local
    final_path = f"/mnt/rclone/{folder}/"  # Caminho final no rclone
    
    try:
        # Login no qBittorrent
        login_cmd = """curl -X POST -c cookie.txt \
                    -d 'username=admin&password=adminadmin' \
                    http://localhost:8080/api/v2/auth/login"""
        
        login_process = await asyncio.create_subprocess_shell(
            login_cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        
        login_stdout, login_stderr = await login_process.communicate()
        
        if login_process.returncode != 0:
            await update.message.reply_text("❌ Erro de autenticação no qBittorrent")
            return ConversationHandler.END
            
        # Adiciona o torrent usando o diretório de cache
        command = f"""curl -X POST -b cookie.txt \
                  -F "urls={torrent_link}" \
                  -F "savepath={cache_path}" \
                  -F "category={folder}" \
                  http://localhost:8080/api/v2/torrents/add"""
        
        process = await asyncio.create_subprocess_shell(
            command,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        
        stdout, stderr = await process.communicate()
        
        if process.returncode == 0:
            msg = await update.message.reply_text(
                f"✅ Torrent adicionado com sucesso!\n"
                f"📂 Baixando em: {cache_path}\n"
                f"🔄 Será movido para: {final_path}\n"
                f"⏳ Iniciando download..."
            )
            
            # Loop para mostrar o progresso
            while True:
                progress_cmd = """curl -b cookie.txt http://localhost:8080/api/v2/torrents/info"""
                progress_process = await asyncio.create_subprocess_shell(
                    progress_cmd,
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE
                )
                
                progress_stdout, progress_stderr = await progress_process.communicate()
                
                if progress_process.returncode == 0:
                    try:
                        data = json.loads(progress_stdout.decode())
                        if data:
                            for torrent in data:
                                progress = torrent.get('progress', 0) * 100
                                name = torrent.get('name', 'Desconhecido')
                                size = torrent.get('size', 0) / (1024*1024*1024)  # GB
                                speed = torrent.get('dlspeed', 0) / (1024*1024)  # MB/s
                                state = torrent.get('state', '')
                                
                                status = (
                                    f"📥 Download em andamento:\n"
                                    f"📁 {name}\n"
                                    f"▪️ Progresso: {progress:.1f}%\n"
                                    f"▪️ Tamanho: {size:.2f} GB\n"
                                    f"▪️ Velocidade: {speed:.2f} MB/s\n"
                                    f"▪️ Estado: {state}"
                                )
                                
                                await msg.edit_text(status)
                                
                               if progress >= 100 or state == 'completed':
                                    # Move o arquivo para o rclone
                                    move_cmd = f"mv '{os.path.join(cache_path, name)}' '{final_path}'"
                                    move_process = await asyncio.create_subprocess_shell(
                                        move_cmd,
                                        stdout=asyncio.subprocess.PIPE,
                                        stderr=asyncio.subprocess.PIPE
                                    )
                                    await move_process.communicate()
                                    
                                    await update.message.reply_text(
                                        "✅ Download concluído!\n"
                                        f"📦 Arquivo movido para: {final_path}"
                                    )
                                    return ConversationHandler.END

                    except json.JSONDecodeError:
                        continue
                
                await asyncio.sleep(5)  # Atualiza a cada 5 segundos
        else:
            await update.message.reply_text(f"❌ Erro ao adicionar torrent:\n{stderr.decode().strip()}")
    
    except Exception as e:
        await update.message.reply_text(f"🔥 Erro: {str(e)}")
    
    return ConversationHandler.END


# async def check_progress(update: Update, context: ContextTypes.DEFAULT_TYPE):
#     try:
#         # Primeiro faz login
#         login_cmd = """curl -X POST -d 'username=admin&password=adminadmin' http://localhost:8080/api/v2/auth/login"""
#         await asyncio.create_subprocess_shell(login_cmd)
        
#         # Depois verifica os torrents
#         command = """curl --cookie "cookie.txt" http://localhost:8080/api/v2/torrents/info"""
        
#         process = await asyncio.create_subprocess_shell(
#             command,
#             stdout=asyncio.subprocess.PIPE,
#             stderr=asyncio.subprocess.PIPE
#         )
        
#         stdout, stderr = await process.communicate()
        
#         if stdout:
#             data = json.loads(stdout.decode())
#             if not data:
#                 await update.message.reply_text("Nenhum torrent em download.")
#                 return
                
#             status = "📥 Downloads em Andamento:\n\n"
#             for torrent in data:
#                 progress = torrent.get('progress', 0) * 100
#                 name = torrent.get('name', 'Desconhecido')
#                 size = torrent.get('size', 0) / (1024*1024*1024)  # Converter para GB
#                 speed = torrent.get('dlspeed', 0) / (1024*1024)  # Converter para MB/s
                
#                 status += (f"📁 {name}\n"
#                           f"▪️ Progresso: {progress:.1f}%\n"
#                           f"▪️ Tamanho: {size:.2f} GB\n"
#                           f"▪️ Velocidade: {speed:.2f} MB/s\n\n")
            
#             await update.message.reply_text(status)
#         else:
#             await update.message.reply_text("❌ Nenhuma resposta do servidor qBittorrent")
            
#     except json.JSONDecodeError:
#         await update.message.reply_text("❌ Erro: Resposta inválida do servidor")
#     except Exception as e:
#         await update.message.reply_text(f"🔥 Falha ao verificar downloads: {str(e)}")
# Adicione o handler



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
    resposta = (  # Define a variável resposta
        f"📊 CPU: {cpu}%\n"
        f"💾 Memória: {mem}%\n"
        f"💽 Disco: {disco}%"
    )
    await update.message.reply_text(resposta)  # Envia apenas uma vez

async def start_rclone(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        # Primeiro mata qualquer processo rclone existente
        kill_cmd = "pkill -f rclone"
        await asyncio.create_subprocess_shell(kill_cmd)
        await asyncio.sleep(2)  # Espera 2 segundos para garantir que o processo foi finalizado
        
        # Inicia o rclone
        command = """rclone mount onedrive: /mnt/rclone \
            --allow-other \
            --dir-cache-time 96h \
            --vfs-cache-mode full \
            --vfs-cache-max-size 20G \
            --buffer-size 512M \
            --log-level INFO \
            """
        
        process = await asyncio.create_subprocess_shell(
            command,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        
        stdout, stderr = await process.communicate()
        
        if process.returncode == 0:
            await update.message.reply_text("✅ Rclone reiniciado com sucesso!")
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
    # Remova esta linha
    # application.add_handler(CommandHandler("progress", check_progress))
    
    # Mantenha o resto dos handlers
    application.add_handler(conv_handler)
    application.add_handler(CommandHandler("restart", restart_jellyfin))
    application.add_handler(CommandHandler("getid", get_id))
    application.add_handler(CommandHandler("metrics", metrics))
    application.add_handler(CommandHandler("rclone", start_rclone))
    application.add_handler(CommandHandler("start", start_jellyfin))
    
    # Configurar job queue
    application.job_queue.run_repeating(check_cpu, interval=60, first=0)
    
        # Iniciar o bot
    print("Bot iniciado...")  # Adicione este print para debug
    application.run_polling()
