import psutil
import json
import asyncio
import aiohttp
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (ContextTypes, CommandHandler, Application,
                          CallbackQueryHandler, ConversationHandler, MessageHandler, filters)
from dotenv import load_dotenv
import os
import time
import re
from datetime import datetime, timedelta

# Carrega variáveis de ambiente
load_dotenv()

# Configurações
BOT_TOKEN = os.getenv('BOT_TOKEN')
CHAT_ID = os.getenv('CHAT_ID')
GITHUB_TOKEN = os.getenv('GITHUB_TOKEN')
GITHUB_REPO = os.getenv('GITHUB_REPO')
LIMITE_CPU = 80

# Estados para a conversa
WAITING_FOR_TORRENT = 1
WAITING_FOR_FOLDER = 2

# Dicionário para armazenar informações dos downloads ativos
active_downloads = {}

def format_size(size_bytes):
    """Formata o tamanho em bytes para formato legível"""
    for unit in ['B', 'KB', 'MB', 'GB']:
        if size_bytes < 1024:
            return f"{size_bytes:.2f} {unit}"
        size_bytes /= 1024
    return f"{size_bytes:.2f} TB"

def format_speed(speed):
    """Formata a velocidade para formato legível"""
    if not speed:
        return "0 B/s"
    try:
        speed_val = float(speed)
        return f"{speed_val:.2f} MB/s"
    except:
        return speed

async def get_workflow_status(run_id: str):
    url = f"https://api.github.com/repos/{GITHUB_REPO}/actions/runs/{run_id}"
    headers = {
        "Accept": "application/vnd.github.v3+json",
        "Authorization": f"Bearer {GITHUB_TOKEN}",
    }
    
    async with aiohttp.ClientSession() as session:
        async with session.get(url, headers=headers) as response:
            if response.status == 200:
                data = await response.json()
                return data['status'], data['conclusion']
    return None, None

async def get_download_progress(run_id: str):
    """Obtém informações detalhadas do progresso do download"""
    url = f"https://api.github.com/repos/{GITHUB_REPO}/actions/runs/{run_id}/logs"
    headers = {
        "Accept": "application/vnd.github.v3+json",
        "Authorization": f"Bearer {GITHUB_TOKEN}",
    }
    
    async with aiohttp.ClientSession() as session:
        async with session.get(url, headers=headers) as response:
            if response.status == 200:
                logs = await response.text()
                # Procura por informações de progresso nos logs
                progress_match = re.search(r'(\d+\.\d+)%.*?(\d+\.\d+)\s*[KMG]iB/s.*?(\d+:\d+)', logs)
                if progress_match:
                    progress = float(progress_match.group(1))
                    speed = progress_match.group(2)
                    eta = progress_match.group(3)
                    return progress, speed, eta
    return None, None, None

async def trigger_github_workflow(magnet_link: str, dest_type: str):
    url = f"https://api.github.com/repos/{GITHUB_REPO}/dispatches"
    
    headers = {
        "Accept": "application/vnd.github.v3+json",
        "Authorization": f"Bearer {GITHUB_TOKEN}",
        "X-GitHub-Api-Version": "2022-11-28"
    }
    
    data = {
        "event_type": "torrent_command",
        "client_payload": {
            "magnet": magnet_link,
            "dest_type": dest_type.lower()
        }
    }
    
    async with aiohttp.ClientSession() as session:
        async with session.post(url, headers=headers, json=data) as response:
            if response.status == 204:
                # Obtém o ID do workflow mais recente
                async with session.get(
                    f"https://api.github.com/repos/{GITHUB_REPO}/actions/runs",
                    headers=headers
                ) as runs_response:
                    if runs_response.status == 200:
                        runs_data = await runs_response.json()
                        if runs_data['workflow_runs']:
                            return runs_data['workflow_runs'][0]['id']
    return None

async def update_progress(context: ContextTypes.DEFAULT_TYPE, chat_id: int, message_id: int, run_id: str):
    start_time = time.time()
    last_progress = 0
    
    while True:
        status, conclusion = await get_workflow_status(run_id)
        progress, speed, eta = await get_download_progress(run_id)
        
        if status == "completed":
            if conclusion == "success":
                total_time = time.time() - start_time
                await context.bot.edit_message_text(
                    chat_id=chat_id,
                    message_id=message_id,
                    text=f"✅ Download concluído com sucesso!\n"
                         f"⏱️ Tempo total: {timedelta(seconds=int(total_time))}"
                )
            else:
                await context.bot.edit_message_text(
                    chat_id=chat_id,
                    message_id=message_id,
                    text=f"❌ Download falhou. Conclusão: {conclusion}"
                )
            if run_id in active_downloads:
                del active_downloads[run_id]
            break
        
        elif status == "in_progress":
            progress_bar = "▓" * int(progress/5) + "░" * (20 - int(progress/5)) if progress else "░" * 20
            
            # Calcula velocidade média
            if progress and progress > last_progress:
                time_diff = time.time() - start_time
                progress_diff = progress - last_progress
                avg_speed = progress_diff / time_diff if time_diff > 0 else 0
            else:
                avg_speed = 0
            
            status_text = (
                f"⏳ Download em andamento...\n"
                f"[{progress_bar}] {progress:.1f}%\n"
                f"🚀 Velocidade: {format_speed(speed)}\n"
                f"⏱️ ETA: {eta}\n"
                f"📈 Velocidade média: {avg_speed:.2f} MB/s\n"
                f"🔗 Actions: https://github.com/{GITHUB_REPO}/actions/runs/{run_id}"
            )
            
            try:
                await context.bot.edit_message_text(
                    chat_id=chat_id,
                    message_id=message_id,
                    text=status_text
                )
            except Exception as e:
                print(f"Erro ao atualizar mensagem: {e}")
            
            last_progress = progress if progress else last_progress
        
        await asyncio.sleep(10)  # Atualiza a cada 10 segundos
async def start_download(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [[InlineKeyboardButton("🎬 Filmes", callback_data='movies'),
                 InlineKeyboardButton("📺 Séries", callback_data='series')]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text('Escolha onde salvar o download:', reply_markup=reply_markup)
    return WAITING_FOR_FOLDER

async def folder_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    context.user_data['folder'] = 'filmes' if query.data == 'movies' else 'series'
    await query.edit_message_text(f"📥 Pasta selecionada: {context.user_data['folder']}\nPor favor, envie o link do torrent:")
    return WAITING_FOR_TORRENT

async def process_torrent(update: Update, context: ContextTypes.DEFAULT_TYPE):
    torrent_link = update.message.text
    folder = context.user_data['folder']
    
    try:
        status_message = await update.message.reply_text(
            "🚀 Iniciando download...\n"
            "⏳ Aguarde enquanto preparo tudo..."
        )
        
        run_id = await trigger_github_workflow(torrent_link, folder)
        
        if run_id:
            # Inicia o monitoramento do progresso em background
            context.application.create_task(
                update_progress(
                    context,
                    update.effective_chat.id,
                    status_message.message_id,
                    run_id
                )
            )
            
            active_downloads[run_id] = {
                'link': torrent_link,
                'folder': folder,
                'start_time': time.time(),
                'status_message_id': status_message.message_id
            }
        else:
            await status_message.edit_text("❌ Erro ao iniciar o download")
    
    except Exception as e:
        await update.message.reply_text(f"🔥 Erro: {str(e)}")
    
    return ConversationHandler.END

async def list_downloads(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not active_downloads:
        await update.message.reply_text("📝 Não há downloads ativos no momento.")
        return

    message = "📥 Downloads Ativos:\n\n"
    for run_id, info in active_downloads.items():
        elapsed_time = time.time() - info['start_time']
        message += f"ID: {run_id}\n"
        message += f"Pasta: {info['folder']}\n"
        message += f"Tempo decorrido: {int(elapsed_time/60)} minutos\n"
        message += f"Link: {info['link'][:50]}...\n\n"

    await update.message.reply_text(message)

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

async def check_cpu(context: ContextTypes.DEFAULT_TYPE):
    uso_cpu = psutil.cpu_percent()
    if uso_cpu > LIMITE_CPU:
        await context.bot.send_message(chat_id=CHAT_ID, text=f"⚠️ ALERTA: CPU a {uso_cpu}%")

def main():
    # Configuração do bot
    application = Application.builder().token(BOT_TOKEN).build()
    
    # Handlers
    conv_handler = ConversationHandler(
        entry_points=[CommandHandler('download', start_download)],
        states={
            WAITING_FOR_FOLDER: [CallbackQueryHandler(folder_callback)],
            WAITING_FOR_TORRENT: [MessageHandler(filters.TEXT & ~filters.COMMAND, process_torrent)]
        },
        fallbacks=[CommandHandler('cancel', cancel)]
    )
    
    application.add_handler(conv_handler)
    application.add_handler(CommandHandler("getid", get_id))
    application.add_handler(CommandHandler("metrics", metrics))
    application.add_handler(CommandHandler("downloads", list_downloads))
    
    # Monitoramento de CPU
    application.job_queue.run_repeating(check_cpu, interval=60, first=0)
    
    # Inicia o bot
    print("Bot iniciado...")
    application.run_polling()

if __name__ == "__main__":
    main()
