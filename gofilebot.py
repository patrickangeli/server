import os
import requests
from telegram import Update, Bot
from telegram.ext import Updater, CommandHandler, CallbackContext
from qbittorrent import Client

# Configurações
GOFILE_API_KEY = "KIxsOddlMz2Iy9Bbng0e3Yke2QsUEr3j"

# Inicializar bot e qBittorrent
bot = Bot(token='7259838966:AAE69fL3BJKVXclATA8n6wYCKI0OmqStKrM')

# Comando para iniciar o download
def start_download(update: Update, context: CallbackContext) -> None:
    magnet_link = context.args[0]
    qb.download_from_link(magnet_link)
    update.message.reply_text('Download iniciado!')

# Comando para enviar arquivo para o GoFile
def upload_to_gofile(update: Update, context: CallbackContext) -> None:
    torrent_name = context.args[0]
    torrent = qb.get_torrent(torrent_name)
    file_path = torrent['save_path'] + torrent['name']
    
    with open(file_path, 'rb') as file:
        response = requests.post(
            'https://api.gofile.io/uploadFile',
            files={'file': file},
            headers={'Authorization': GOFILE_API_KEY}
        )
    update.message.reply_text(f"Arquivo enviado: {response.json()['data']['downloadPage']}")

# Comando para ativar/desativar o bot
def toggle_bot(update: Update, context: CallbackContext) -> None:
    global bot_active
    bot_active = not bot_active
    status = 'ativado' if bot_active else 'desativado'
    update.message.reply_text(f"Bot {status}!")

# Comando para realizar o Speedtest
def run_speedtest(update: Update, context: CallbackContext) -> None:
    st = speedtest.Speedtest()
    st.download()
    st.upload()
    results = st.results.dict()
    
    response_message = (
        f"**Speedtest Resultados:**\n"
        f"Download: {results['download'] / 1_000_000:.2f} Mbps\n"
        f"Upload: {results['upload'] / 1_000_000:.2f} Mbps\n"
        f"Ping: {results['ping']} ms\n"
        f"Servidor: {results['server']['name']} ({results['server']['country']})"
    )
    update.message.reply_text(response_message, parse_mode='Markdown')

# Comando para exibir o status do download
def download_status(update: Update, context: CallbackContext) -> None:
    torrents = qb.torrents()
    if not torrents:
        update.message.reply_text('Nenhum download em andamento.')
        return

    status_messages = []
    for torrent in torrents:
        name = torrent['name']
        progress = torrent['progress'] * 100
        state = torrent['state']
        download_speed = torrent['dlspeed'] / 1_000_000  # Convertendo para Mbps
        upload_speed = torrent['upspeed'] / 1_000_000  # Convertendo para Mbps
        eta = torrent['eta']  # Tempo estimado em segundos

        # Convertendo ETA para horas, minutos e segundos
        hours, remainder = divmod(eta, 3600)
        minutes, seconds = divmod(remainder, 60)
        eta_formatted = f"{int(hours)}h {int(minutes)}m {int(seconds)}s"

        status_message = (
            f"**{name}**\n"
            f"Progresso: {progress:.2f}%\n"
            f"Estado: {state}\n"
            f"Velocidade de Download: {download_speed:.2f} Mbps\n"
            f"Velocidade de Upload: {upload_speed:.2f} Mbps\n"
            f"Tempo Restante: {eta_formatted}"
        )
        status_messages.append(status_message)

    update.message.reply_text("\n\n".join(status_messages), parse_mode='Markdown')

# Configurar comandos do bot
updater = Updater(token='7259838966:AAE69fL3BJKVXclATA8n6wYCKI0OmqStKrM')
dispatcher = updater.dispatcher
dispatcher.add_handler(CommandHandler('start_download', start_download))
dispatcher.add_handler(CommandHandler('upload_to_gofile', upload_to_gofile))
dispatcher.add_handler(CommandHandler('toggle_bot', toggle_bot))
dispatcher.add_handler(CommandHandler('speedtest', run_speedtest))
dispatcher.add_handler(CommandHandler('download_status', download_status))

# Iniciar o bot
updater.start_polling()
updater.idle()
