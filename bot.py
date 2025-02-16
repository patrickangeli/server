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
            
            # Conecta ao qBittorrent com autenticação correta
            qb = Client(
                host='localhost',
                port=8080,
                username='admin',
                password='adminadmin'
            )
            
            try:
                qb.auth_log_in()  # Autenticação correta
                
                # Adiciona o torrent corretamente
                qb.torrents_add(
                    urls=magnet_link,
                    save_path=download_path,
                    is_paused=False
                )
                
                # Aguarda a adição do torrent
                time.sleep(2)
                
                # Obtém o torrent mais recente
                torrents = qb.torrents_info(sort='added_on', reverse=True)
                if torrents:
                    torrent = torrents[0]
                    
                    while True:
                        torrent.refresh()
                        if torrent.state_enum.is_downloading:
                            progress = torrent.progress * 100
                            await update.message.reply_text(f"📥 Download: {progress:.1f}%")
                        elif torrent.state_enum.is_complete:
                            await update.message.reply_text("✅ Download completo!")
                            break
                        time.sleep(30)
                            
            except Exception as e:
                await update.message.reply_text(f"❌ Erro no qBittorrent: {str(e)}")
                
    except Exception as e:
        await update.message.reply_text(f"❌ Erro geral: {str(e)}")

def main():
    application = Application.builder().token(os.environ['TELEGRAM_TOKEN']).build()
    
    application.add_handler(CommandHandler("start", start))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    
    application.run_polling()

if __name__ == '__main__':
    main()
