import os
import telebot
import qbittorrentapi
from pathlib import Path

TELEGRAM_TOKEN = os.environ['TELEGRAM_TOKEN']
bot = telebot.TeleBot(TELEGRAM_TOKEN)

# Configuração do qBittorrent
qbt_client = qbittorrentapi.Client(
    host='localhost',
    port=8080,
    username='admin',
    password='adminadmin'
)

@bot.message_handler(commands=['torrent'])
def handle_torrent(message):
    try:
        magnet = message.text.split(' ')[1]
        bot.reply_to(message, "Iniciando download do torrent...")
        
        # Adiciona torrent ao qBittorrent
        qbt_client.torrents_add(urls=[magnet])
        
        # Aguarda download completar
        while any(torrent.progress < 100 for torrent in qbt_client.torrents_info()):
            time.sleep(10)
            
        bot.reply_to(message, "Download concluído! Para qual pasta deseja enviar?\n/filmes\n/series")
        
    except Exception as e:
        bot.reply_to(message, f"Erro: {str(e)}")

@bot.message_handler(commands=['filmes', 'series'])
def handle_destination(message):
    command = message.text[1:]
    if command == 'filmes':
        dest_path = Path('~/mnt/filmes')
    else:
        dest_path = Path('~/mnt/series')
        
    try:
        # Move arquivos para pasta destino
        for torrent in qbt_client.torrents_info():
            source = Path(torrent.content_path)
            dest = dest_path / source.name
            source.rename(dest)
            
        bot.reply_to(message, f"Arquivos movidos para pasta {command}")
        
    except Exception as e:
        bot.reply_to(message, f"Erro ao mover arquivos: {str(e)}")

bot.polling()
