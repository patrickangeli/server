import os
import requests
import speedtest
import time
import libtorrent as lt
from telegram import Update, Bot, ReplyKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackContext, MessageHandler, filters
import hashlib

# Configurações
GOFILE_API_KEY = "KIxsOddlMz2Iy9Bbng0e3Yke2QsUEr3j"
bot_token = '7259838966:AAE69fL3BJKVXclATA8n6wYCKI0OmqStKrM'
MAX_FILE_NAME_LENGTH = 64  # Reduzindo para um valor bem seguro

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

# Função para gerar um nome de arquivo curto e único
def generate_short_filename(original_name):
    _, ext = os.path.splitext(original_name)
    hash_object = hashlib.md5(original_name.encode())
    hash_str = hash_object.hexdigest()[:8]
    new_name = f"file_{hash_str}{ext}"
    if len(new_name) > MAX_FILE_NAME_LENGTH:
        new_name = new_name[:MAX_FILE_NAME_LENGTH - len(ext)] + ext
    return new_name

# Função para extrair e processar o nome do arquivo a partir do arquivo torrent
def get_file_name_from_torrent(torrent_path):
    try:
        info = lt.torrent_info(torrent_path)
        original_name = info.name()
        return generate_short_filename(original_name)
    except Exception as e:
        print(f"Erro ao obter o nome do arquivo do torrent: {e}")
        return generate_short_filename("unknown_file")

# Comando para iniciar o download e fazer o upload após completar (usando o arquivo .torrent)
async def start_download(update: Update, context: CallbackContext) -> None:
    if len(context.args) == 0:
        await update.message.reply_text("Por favor, forneça o caminho do arquivo torrent para iniciar o download.")
        return
    
    torrent_path = context.args[0]  # Caminho do arquivo .torrent
    await update.message.reply_text(f'Download a partir do torrent `{torrent_path}` iniciado! Monitorando progresso...')

    file_name = get_file_name_from_torrent(torrent_path)
    await update.message.reply_text(f"Nome do arquivo gerado: `{file_name}`")

    time.sleep(10)  # Simulando 10 segundos de download
    file_path = os.path.join("/home", file_name)

    gofile_link = upload_file(file_path)

    if gofile_link:
        await update.message.reply_text(f"Download concluído! Arquivo enviado: {gofile_link}")
        try:
            os.remove(file_path)
            await update.message.reply_text(f"Arquivo `{file_path}` deletado com sucesso!")
        except Exception as e:
            await update.message.reply_text(f"Erro ao deletar o arquivo: {e}")
    else:
        await update.message.reply_text("Falha ao fazer upload do arquivo.")

# Função para mostrar o menu de instruções
async def show_menu(update: Update, context: CallbackContext) -> None:
    menu_message = (
        "Bem-vindo! Aqui estão os comandos disponíveis:\n\n"
        "/start_download <caminho_arquivo_torrent> - Inicia o download a partir do arquivo torrent.\n"
        "/speedtest - Executa um teste de velocidade de internet.\n"
        "/help - Mostra este menu de ajuda.\n"
    )
    await update.message.reply_text(menu_message)

# Criação de um menu flutuante com as opções
def get_reply_keyboard():
    custom_keyboard = [
        ['/start_download', '/speedtest'],
        ['/help']
    ]
    return ReplyKeyboardMarkup(custom_keyboard, resize_keyboard=True)

# Configurar o menu flutuante
async def show_floating_menu(update: Update, context: CallbackContext) -> None:
    reply_markup = get_reply_keyboard()
    await update.message.reply_text("Escolha uma opção:", reply_markup=reply_markup)

def main() -> None:
    # Inicializar o bot
    application = Application.builder().token(bot_token).build()

    # Configurar comandos do bot
    application.add_handler(CommandHandler('start_download', start_download))
    application.add_handler(CommandHandler('speedtest', run_speedtest))
    application.add_handler(CommandHandler('help', show_menu))

    # Adicionar o handler do menu flutuante
    application.add_handler(MessageHandler(filters.Regex('^/$'), show_floating_menu))

    # Iniciar o bot
    application.run_polling()

if __name__ == '__main__':
    main()
