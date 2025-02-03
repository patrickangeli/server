import os
import telebot
import qbittorrentapi
import time
from pathlib import Path

def main():
    TELEGRAM_TOKEN = os.environ['TELEGRAM_TOKEN']
    TELEGRAM_CHAT_ID = os.environ['TELEGRAM_CHAT_ID']
    
    bot = telebot.TeleBot(TELEGRAM_TOKEN)
    
    # Envia mensagem de início
    bot.send_message(TELEGRAM_CHAT_ID, "🚀 Workflow iniciado!")
    
    try:
        # Processa o magnet link do evento
        magnet = os.environ.get('MAGNET_LINK')
        if not magnet:
            raise ValueError("Magnet link não fornecido")
            
        # Configura qBittorrent
        qbt_client = qbittorrentapi.Client(
            host='localhost',
            port=8080,
            username='admin',
            password='adminadmin'
        )
        
        # Inicia download
        qbt_client.torrents_add(urls=[magnet])
        bot.send_message(TELEGRAM_CHAT_ID, "⬇️ Download iniciado...")
        
        # Monitora progresso
        while True:
            torrents = qbt_client.torrents_info()
            if not torrents or all(t.progress == 100 for t in torrents):
                break
            time.sleep(30)
            
        bot.send_message(TELEGRAM_CHAT_ID, "✅ Download concluído!")
        
        # Move para pasta destino
        dest_type = os.environ.get('DEST_TYPE', 'filmes')
        dest_path = f"/mnt/{dest_type}"
        
        for torrent in qbt_client.torrents_info():
            source = Path(torrent.content_path)
            dest = Path(dest_path) / source.name
            source.rename(dest)
            
        bot.send_message(TELEGRAM_CHAT_ID, f"📦 Arquivos movidos para {dest_type}")
        
    except Exception as e:
        bot.send_message(TELEGRAM_CHAT_ID, f"❌ Erro: {str(e)}")

if __name__ == "__main__":
    main()
