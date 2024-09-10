import os
import requests
import speedtest
import time
from telegram import Update
from telegram.ext import Application, CommandHandler, CallbackContext
from qbittorrent import Client

# Configurações
GOFILE_API_KEY = "KIxsOddlMz2Iy9Bbng0e3Yke2QsUEr3j"
bot_token = '7259838966:AAE69fL3BJKVXclATA8n6wYCKI0OmqStKrM'

# Inicializar qBittorrent

# Função para fazer upload do arquivo para o GoFile
def upload_file(file_path):
    try:
        with open(file_path, 'rb') as file:
            response = requests.post(
                'https://api.gofile.io/uploadFile',
                files={'file': file},
                headers={'Authorization': GOFILE_API_KEY}
            )
            response_data = response.json()
            if response_data['status'] == 'ok':
                return response_data['data']['downloadPage']
            else:
                raise Exception(f"Erro no upload: {response_data['status']}")
    except Exception as e:
        print(f"Erro ao enviar o arquivo: {e}")
        return None

# Função para monitorar o progresso do download
def monitor_download(torrent_name):
    while True:
        torrents = qb.torrents()
        for torrent in torrents:
            if torrent['name'] == torrent_name:
                progress = torrent['progress'] * 100
                print(f"Progresso do download de {torrent_name}: {progress:.2f}%")
                if torrent['progress'] == 1:  # Download completo
                    return torrent['save_path'], torrent['name']
        time.sleep(4)

# Comando para iniciar o download e fazer o upload após completar
async def start_download(update: Update, context: CallbackContext) -> None:
    if len(context.args) == 0:
        await update.message.reply_text("Por favor, forneça um link magnet para iniciar o download.")
        return
    
    magnet_link = context.args[0]
    qb.download_from_link(magnet_link)
    await update.message.reply_text('Download iniciado! Monitorando progresso...')

    # Monitorar o progresso do download
    torrent_name = qb.torrents()[-1]['name']  # Último torrent adicionado
    save_path, torrent_name = monitor_download(torrent_name)

    # Upload para GoFile após o download ser concluído
    file_path = os.path.join(save_path, torrent_name)
    gofile_link = upload_file(file_path)

    if gofile_link:
        await update.message.reply_text(f"Download concluído! Arquivo enviado: {gofile_link}")
        
        # Deletar o arquivo após o upload
        try:
            os.remove(file_path)
            await update.message.reply_text(f"Arquivo {torrent_name} deletado com sucesso!")
        except Exception as e:
            await update.message.reply_text(f"Erro ao deletar o arquivo: {e}")
    else:
        await update.message.reply_text("Falha ao fazer upload do arquivo.")

# Inicializar o bot
application = Application.builder().token(bot_token).build()

# Configurar comandos do bot
application.add_handler(CommandHandler('start_download', start_download))

# Iniciar o bot
application.run_polling()
