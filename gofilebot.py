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

# Função para extrair o nome do arquivo a partir do arquivo torrent, com limite de tamanho de nome
def get_file_name_from_torrent(torrent_path, max_length=10):
    try:
        # Criar um objeto de informação do torrent a partir do arquivo torrent
        info = lt.torrent_info(torrent_path)
        # Pegar o nome do primeiro arquivo no torrent (ou o nome do diretório, se for uma pasta)
        if info.num_files() > 1:
            file_name = info.name()  # Retorna o nome da pasta principal se houver vários arquivos
        else:
            file_name = info.files().file_name(0)  # Retorna o nome do único arquivo no torrent

        # Limitar o comprimento do nome do arquivo
        if len(file_name) > max_length:
            file_name = file_name[:max_length]  # Cortar o nome para o tamanho máximo permitido
            print(f"Nome do arquivo truncado para: {file_name}")
        
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
    file_path = f"/home/{file_name}"

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

# Função para mostrar o menu de instruções
async def show_menu(update: Update, context: CallbackContext) -> None:
    menu_message = (
        "Bem-vindo! Aqui estão os comandos disponíveis:\n\n"
        "/start_download <caminho_arquivo_torrent> - Inicia o download a partir do arquivo torrent.\n"
        "/speedtest - Executa um teste de velocidade de internet.\n"
        "/upload_to_gofile <nome_arquivo> - Faz upload do arquivo para o GoFile.\n"
        "/toggle_bot - Ativa ou desativa o bot.\n"
    )
    await update.message.reply_text(menu_message)

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
