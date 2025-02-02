import psutil
from telegram import Update
from telegram.ext import Updater, CommandHandler, CallbackContext
from threading import Thread
from time import sleep

# Configurações
BOT_TOKEN = '7609833263:AAEmDv3ORnSZEEGjA0OHQBGFvXEoeGaYiww'
CHAT_ID = '7609833263'
LIMITE_CPU = 80

# Inicializa o updater do Telegram
updater = Updater(token=BOT_TOKEN, use_context=True)

def enviar_alerta(texto: str):
    updater.bot.send_message(chat_id=CHAT_ID, text=texto)

def monitoramento_cpu():
    while True:
        uso_cpu = psutil.cpu_percent(interval=1)
        
        if uso_cpu > LIMITE_CPU:
            alerta = f"🚨 **ALERTA DE CPU** 🚨\nUso atual: {uso_cpu}%"
            enviar_alerta(alerta)
        
        sleep(60)

def metrics(update: Update, context: CallbackContext):
    cpu = psutil.cpu_percent()
    mem = psutil.virtual_memory().percent
    disco = psutil.disk_usage('/').percent
    
    resposta = (
        f"📈 **Métricas em Tempo Real**\n"
        f"• CPU: {cpu}%\n"
        f"• RAM: {mem}%\n"
        f"• Disco: {disco}%"
    )
    update.message.reply_text(resposta)

# Configura handlers e inicia threads
updater.dispatcher.add_handler(CommandHandler('metrics', metrics))
monitor_thread = Thread(target=monitoramento_cpu)

# Inicia o sistema
monitor_thread.start()
updater.start_polling()
updater.idle()
