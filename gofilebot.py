import os
import requests
import speedtest
import time
import libtorrent as lt
from telegram import Update, Bot
from telegram.ext import Application, CommandHandler, CallbackContext
from telegram.ext import MessageHandler, filters
from telegram import ReplyKeyboardMarkup

# Configurações
GOFILE_API_KEY = "KIxsOddlMz2Iy9Bbng0e3Yke2QsUEr3j"
bot_token = '7259838966:AAE69fL3BJKVXclATA8n6wYCKI0OmqStKrM'
MAX_FILE_NAME_LENGTH = 255  # Ajuste este valor conforme necessário

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

# Função para realizar o Speedtest
async def run_speedtest(update: Update, context: CallbackContext) -> None:
    await update.message.reply_text("Executando Speedtest, por favor, aguarde...")

    st = speedtest.Speedtest()
    download_speed = st.download() / 1_000_000  # Mbps
    upload_speed = st.upload() / 1_000_000  # Mbps
    ping = st.results.ping

    response_message = (
        f"**Resultados do Speedtest:**\n"
        f"Download: {download_speed:.2f} Mbps\n"
        f"Upload: {upload_speed:.2f} Mbps\n"
        f"Ping: {ping:.2f} ms"
    )

    await update.message.reply_text(response_message, parse_mode='Markdown')

# Função para extrair e truncar o nome do arquivo a partir do arquivo torrent
def get_file_name_from_torrent(torrent_path):
    try:
        info = lt.torrent_info(torrent_path)
        file_name = info.name()
        if len(file_name) > MAX_FILE_NAME_LENGTH:
            base, ext = os.path.splitext(file_name)
            truncated_base = base[:MAX_FILE_NAME_LENGTH - len(ext) - 3]  # -3 para "..."
            file_name = f"{truncated_base}...{ext}"
        return file_name
    except Exception as e:
        print(f"Erro ao obter o nome do arquivo do torrent: {e}")
        return None

# Comando para iniciar o download e fazer o upload após completar (usando o arquivo .torrent)
async def start_download(update: Update, context: CallbackContext) -> None:
    if len(context.args) == 0:
        await update.message.reply_text("Por favor, forneça o caminho do arquivo torrent para iniciar o download.")
        return
    
    torrent_path = context.args[0]  # Caminho do arquivo .torrent
    await update.message.reply_text(f'Download a partir do torrent `{torrent_path}` iniciado! Monitorando progresso...')

    # Pegar o nome do arquivo a partir do .torrent
    file_name = get_file_name_from_torrent(torrent_path)

    if file_name is None:
        await update.message.reply_text("Falha ao obter o nome do arquivo do torrent.")
        return

    await update.message.reply_text(f"Nome do arquivo extraído: `{file_name}`")

    # Simulação de download (substitua isso por sua lógica de download real se necessário)
    time.sleep(10)  # Simulando 10 segundos de download

    # Simulação de caminho de arquivo baixado
    file_path = os.path.join("/home", file_name)

    # Upload para GoFile após o download simulado
    gofile_link = upload_file(file_path)

    if gofile_link:
        await update.message.reply_text(f"Download concluído! Arquivo enviado: {gofile_link}")
        
        # Simulando a deleção do arquivo após o upload
        try:
            os.remove(file_path)
            await update.message.reply_text(f"Arquivo `{file_path}` deletado com sucesso!")
        except Exception as e:
            await update.message.reply_text(f"Erro ao deletar o arquivo: {e}")
    else:
        await update.message.reply_text("Falha ao fazer upload do arquivo.")

# [O resto do código permanece o mesmo]

# Iniciar o bot
application.run_polling()
