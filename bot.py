from telegram.ext import Application, CommandHandler, MessageHandler, filters
from qbittorrentapi import Client
import os
import time
from telegram import ReplyKeyboardMarkup

# Configurações
DOWNLOAD_BASE = "/mnt/drive"
FOLDERS = ["Filmes", "Séries"]

def create_folder_keyboard():
    keyboard = [[f"📁 {folder}"] for folder in FOLDERS]
    return ReplyKeyboardMarkup(keyboard, one_time_keyboard=True, resize_keyboard=True)

async def start(update, context):
    reply_markup = create_folder_keyboard()
    await update.message.reply_text(
        "Selecione a pasta para download:",
        reply_markup=reply_markup
    )
    context.user_data['waiting_for_folder'] = True

async def handle_message(update, context):
    if context.user_data.get('waiting_for_folder'):
        selected_folder = update.message.text.replace("📁 ", "")
        if selected_folder in FOLDERS:
            download_path = f"{DOWNLOAD_BASE}/{selected_folder}"
            context.user_data['download_path'] = download_path
            context.user_data['waiting_for_folder'] = False
            await update.message.reply_text(
                f"Pasta selecionada: {selected_folder}\n"
                "Envie o link magnet ou arquivo torrent."
            )
        else:
            await update.message.reply_text("Por favor, selecione uma pasta válida.")
        return

    try:
        magnet_link = update.message.text
        if magnet_link.startswith('magnet:') or magnet_link.endswith('.torrent'):
            await update.message.reply_text("⬇️ Iniciando download...")
            
            download_path = context.user_data.get('download_path', DOWNLOAD_BASE)
            
            # Conecta ao qBittorrent
            qb = Client('http://localhost:8080')
            qb.login('admin', 'adminadmin')  # Credenciais padrão
            
            # Adiciona o torrent
            qb.download_from_link(magnet_link, savepath=download_path)
            
            # Aguarda alguns segundos para o torrent ser adicionado
            time.sleep(5)
            
            # Obtém o hash do torrent mais recente
            torrents = qb.torrents()
            if torrents:
                torrent = torrents[0]  # Pega o torrent mais recente
                
                while True:
                    # Atualiza o status do torrent
                    torrent_info = qb.get_torrent(torrent['hash'])
                    
                    if torrent_info['state'] in ['downloading', 'stalledDL']:
                        progress = torrent_info['progress'] * 100
                        await update.message.reply_text(f"📥 Download: {progress:.1f}%")
                    elif torrent_info['state'] in ['uploading', 'stalledUP', 'completed']:
                        await update.message.reply_text("✅ Download completo!")
                        break
                    
                    time.sleep(30)
                
    except Exception as e:
        await update.message.reply_text(f"❌ Erro: {str(e)}")

def main():
    application = Application.builder().token(os.environ['TELEGRAM_TOKEN']).build()
    
    application.add_handler(CommandHandler("start", start))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    
    application.run_polling()

if __name__ == '__main__':
    main()
