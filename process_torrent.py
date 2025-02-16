from telegram.ext import Updater, MessageHandler, Filters, CommandHandler
import transmissionrpc
import os
import time
import subprocess

def get_rclone_folders():
    result = subprocess.run(['rclone', 'lsf', 'remote:', '--dirs-only'], capture_output=True, text=True)
    folders = result.stdout.strip().split('\n')
    return folders

def create_folder_keyboard(folders):
    keyboard = [[f"📁 {folder}"] for folder in folders]
    return {"keyboard": keyboard, "one_time_keyboard": True, "resize_keyboard": True}

def start(update, context):
    folders = get_rclone_folders()
    reply_markup = create_folder_keyboard(folders)
    update.message.reply_text(
        "Selecione a pasta para download:",
        reply_markup=reply_markup
    )
    context.user_data['waiting_for_folder'] = True

def handle_message(update, context):
    if context.user_data.get('waiting_for_folder'):
        selected_folder = update.message.text.replace("📁 ", "")
        download_path = f"/mnt/drive/{selected_folder}"
        context.user_data['download_path'] = download_path
        context.user_data['waiting_for_folder'] = False
        update.message.reply_text(f"Pasta selecionada: {selected_folder}\nEnvie o link magnet ou arquivo torrent.")
        return

    try:
        magnet_link = update.message.text
        if magnet_link.startswith('magnet:') or magnet_link.endswith('.torrent'):
            update.message.reply_text("⬇️ Iniciando download...")
            
            download_path = context.user_data.get('download_path', '/mnt/drive')
            tc = transmissionrpc.Client('localhost', port=9091)
            torrent = tc.add_torrent(magnet_link, download_dir=download_path)
            
            while True:
                t = tc.get_torrent(torrent.id)
                if t.status == 'downloading':
                    progress = t.progress
                    update.message.reply_text(f"📥 Download: {progress:.1f}%")
                elif t.status == 'seeding':
                    update.message.reply_text("✅ Download completo!")
                    break
                time.sleep(30)
                
    except Exception as e:
        update.message.reply_text(f"❌ Erro: {str(e)}")

def main():
    updater = Updater(token=os.environ['TELEGRAM_TOKEN'])
    dp = updater.dispatcher
    
    dp.add_handler(CommandHandler("start", start))
    dp.add_handler(MessageHandler(Filters.text, handle_message))
    
    updater.start_polling()
    updater.idle()

if __name__ == '__main__':
    main()
