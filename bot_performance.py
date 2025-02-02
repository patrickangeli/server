import psutil
from telegram import Update
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

# Função de métricas
async def metrics(update, context):
    cpu = psutil.cpu_percent()
    mem = psutil.virtual_memory().percent
    disco = psutil.disk_usage('/').percent
    
    resposta = (
        f"📊 **Métricas** 📊\n"
        f"• CPU: {cpu}%\n"
        f"• Memória: {mem}%\n"
        f"• Disco: {disco}%"
    )
    await update.message.reply_text(resposta)

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

# Configuração dos handlers
application.add_handler(CommandHandler("metrics", metrics))

# Inicialização do bot
if __name__ == "__main__":
    application.job_queue.run_once(lambda _: asyncio.create_task(monitoramento()), when=0)
    application.run_polling()
