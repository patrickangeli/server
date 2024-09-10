import os
import requests
import speedtest
import time
import libtorrent as lt
import datetime
from telegram import Update, Bot
from telegram.ext import Application, CommandHandler, CallbackContext
from telegram.ext import MessageHandler, filters
from telegram import ReplyKeyboardMarkup

# Configurações
GOFILE_API_KEY = "KIxsOddlMz2Iy9Bbng0e3Yke2QsUEr3j"
bot_token = '7259838966:AAE69fL3BJKVXclATA8n6wYCKI0OmqStKrM'

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

# Comando para realizar o Speedtest
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

# Função para mostrar o menu de instruções
async def show_menu(update: Update, context: CallbackContext) -> None:
    menu_message = (
        "Bem-vindo! Aqui estão os comandos disponíveis:\n\n"
        "/start_download <magnet_link ou .torrent URL> - Inicia o download a partir de um link magnet ou torrent.\n"
        "/speedtest - Executa um teste de velocidade de internet.\n"
        "/upload_to_gofile <nome_arquivo> - Faz upload do arquivo para o GoFile.\n"
        "/toggle_bot - Ativa ou desativa o bot.\n"
    )
    await update.message.reply_text(menu_message)

# Função para baixar torrent usando libtorrent e fazer upload para GoFile
async def start_download(update: Update, context: CallbackContext) -> None:
    if len(context.args) == 0:
        await update.message.reply_text("Por favor, forneça um link magnet ou um URL de arquivo torrent.")
        return
    
    link = context.args[0]
    params = {
        'save_path': './Torrent/',  # Caminho de salvamento do arquivo
        'storage_mode': lt.storage_mode_t(2),
    }

    # Configura sessão de libtorrent
    ses = lt.session()
    ses.listen_on(6881, 6891)

    # Se for um arquivo .torrent
    if link.endswith('.torrent'):
        import wget
        from torf import Torrent

        if os.path.exists('torrent.torrent'):
            os.remove('torrent.torrent')

        # Baixar arquivo torrent
        wget.download(link, 'torrent.torrent')
        t = Torrent.read('torrent.torrent')
        link = str(t.magnet(name=True, size=False, trackers=False, tracker=False))

    await update.message.reply_text(f'Baixando `{link}`... Monitorando progresso.')

    # Iniciar o download
    handle = lt.add_magnet_uri(ses, link, params)
    handle.set_sequential_download(0)
    ses.start_dht()

    # Aguarda até que os metadados sejam baixados
    while not handle.has_metadata():
        await update.message.reply_text('Baixando Metadados...')
        time.sleep(1)

    await update.message.reply_text('Metadados baixados! Iniciando download...')

    # Baixar o arquivo
    while handle.status().state != lt.torrent_status.seeding:
        s = handle.status()
        state_str = ['queued', 'checking', 'downloading metadata',
                     'downloading', 'finished', 'seeding', 'allocating']
        progress_message = (
            f'{handle.name()} - {s.progress * 100:.2f}% completo\n'
            f'Download: {s.download_rate / 1000:.1f} kB/s\n'
            f'Upload: {s.upload_rate / 1000:.1f} kB/s\n'
            f'Peers: {s.num_peers}\n'
            f'Estado: {state_str[s.state]}'
        )
        await update.message.reply_text(progress_message)
        time.sleep(5)

    await update.message.reply_text(f'Download concluído: {handle.name()}')

    # Caminho do arquivo baixado
    file_path = os.path.join(params['save_path'], handle.name())

    # Upload para GoFile
    gofile_link = upload_file(file_path)
    if gofile_link:
        await update.message.reply_text(f"Arquivo enviado para GoFile: {gofile_link}")
        
        # Deletar arquivo após upload
        try:
            os.remove(file_path)
            await update.message.reply_text(f"Arquivo `{file_path}` deletado com sucesso.")
        except Exception as e:
            await update.message.reply_text(f"Erro ao deletar o arquivo: {e}")
    else:
        await update.message.reply_text("Erro ao fazer upload do arquivo.")

# Criação de um menu flutuante com as opções
def get_reply_keyboard():
    custom_keyboard = [
        ['/start_download', '/speedtest'],
        ['/upload_to_gofile', '/toggle_bot'],
        ['/help']
    ]
    return ReplyKeyboardMarkup(custom_keyboard, resize_keyboard=True)

# Inicializar o bot com a nova forma de construção
application = Application.builder().token(bot_token).build()

# Configurar comandos do bot
application.add_handler(CommandHandler('start_download', start_download))
application.add_handler(CommandHandler('speedtest', run_speedtest))
application.add_handler(CommandHandler('help', show_menu))

# Configurar o menu flutuante (usando um MessageHandler para capturar a digitação de '/')
async def show_floating_menu(update: Update, context: CallbackContext) -> None:
    reply_markup = get_reply_keyboard()
    await update.message.reply_text("Escolha uma opção:", reply_markup=reply_markup)

# Adicionando o handler do menu flutuante
application.add_handler(MessageHandler(filters.Regex('^/$'), show_floating_menu))

# Iniciar o bot
application.run_polling()
