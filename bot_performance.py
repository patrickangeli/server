import psutil
from telegram import Update
from telegram.ext import ContextTypes
from telegram.ext import Updater, CommandHandler, CallbackContext, Application
from threading import Thread
from time import sleep
import asyncio
# Configurações
BOT_TOKEN = '7609833263:AAEmDv3ORnSZEEGjA0OHQBGFvXEoeGaYiww'
CHAT_ID = '7609833263'
LIMITE_CPU = 80

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
application.add_handler(CommandHandler("restart", restart_jellyfin))
application.add_handler(CommandHandler("getid", get_id))
application.add_handler(CommandHandler("metrics", metrics))
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
