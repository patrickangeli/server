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

def sanitize_filename(filename):
    # Remove invalid characters and truncate if necessary
    invalid_chars = '<>:"/\\|?*'
    filename = ''.join(c for c in filename if c not in invalid_chars)
    filename = filename.strip()
    if len(filename) > MAX_FILE_NAME_LENGTH:
        base, ext = os.path.splitext(filename)
        filename = base[:MAX_FILE_NAME_LENGTH - len(ext)] + ext
    return filename

def generate_short_filename(original_name):
    base, ext = os.path.splitext(original_name)
    hash_object = hashlib.md5(base.encode())
    hash_str = hash_object.hexdigest()[:8]
    new_name = f"{hash_str}{ext}"
    return new_name

def get_file_name_from_torrent(torrent_path):
  try:
    info = lt.torrent_info(torrent_path)
    # Get the first filename from the list (adjust if needed)
    original_name = info.files().name()[0]
    return sanitize_filename(original_name)
  except Exception as e:
    print(f"Erro ao obter o nome do arquivo do torrent: {e}")
    return "unknown_file"

async def start_download(update: Update, context: CallbackContext) -> None:
    if len(context.args) == 0:
        await update.message.reply_text("Por favor, forneça o caminho do arquivo torrent para iniciar o download.")
        return
    
    torrent_path = context.args[0]  # Caminho do arquivo .torrent
    await update.message.reply_text(f'Processando torrent: `{torrent_path}`')

    try:
        file_name = get_file_name_from_torrent(torrent_path)
        await update.message.reply_text(f"Nome do arquivo: `{file_name}`")

        # Simulação de download (substitua isso por sua lógica de download real se necessário)
        time.sleep(10)  # Simulando 10 segundos de download

        # Caminho de arquivo baixado
        download_dir = "/home/downloads"  # Defina um diretório de download fixo
        os.makedirs(download_dir, exist_ok=True)  # Garante que o diretório existe
        file_path = os.path.join(download_dir, file_name)

        # Simule a criação do arquivo
        with open(file_path, 'w') as f:
            f.write("Conteúdo simulado do arquivo")

        # Upload para GoFile
        gofile_link = upload_file(file_path)

        if gofile_link:
            await update.message.reply_text(f"Download concluído! Arquivo enviado: {gofile_link}")
            os.remove(file_path)
            await update.message.reply_text(f"Arquivo `{file_path}` deletado com sucesso!")
        else:
            await update.message.reply_text("Falha ao fazer upload do arquivo.")
    except Exception as e:
        await update.message.reply_text(f"Erro durante o processamento: {str(e)}")
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
