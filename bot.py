import requests
from geopy.distance import geodesic
from time import sleep
import asyncio
from telegram import Update
from telegram.ext import Application, CommandHandler, CallbackContext
from telegram.ext import Updater
import threading

# Substitua pelo seu token do Telegram
BOT_TOKEN = "7839021746:AAE9rR_jFzAy1Hw8_puCNzwg1vQpyjjaCxg"
chat_id = "7839021746"  # Substitua pelo seu chat ID real

# Função para obter dados de voos da OpenSky Network
def get_opensky_data():
    url = "https://opensky-network.org/api/states/all"
    response = requests.get(url)

    if response.status_code == 200:
        return response.json()
    return None

# Função para calcular a distância restante até o destino
def calcular_distancia(lat_atual, lon_atual, lat_dest, lon_dest):
    if None in [lat_atual, lon_atual, lat_dest, lon_dest]:
        return None
    return round(geodesic((lat_atual, lon_atual), (lat_dest, lon_dest)).km, 2)

# Comando /voos - Lista os primeiros 10 voos ativos
async def send_flight_info(update: Update, context: CallbackContext):
    flights = get_opensky_data()
    if not flights:
        await update.message.reply_text("⚠️ Erro ao obter dados dos voos.")
        return

    reply = "✈️ **Voos em tempo real:**\n\n"
    count = 0

    for flight in flights["states"]:
        if count >= 10:
            break

        flight_id = flight[1] if flight[1] else "Desconhecido"
        origin = flight[2] if flight[2] else "Desconhecida"
        destination = flight[3] if flight[3] else "Desconhecido"
        lat = flight[6]  # Latitude
        lon = flight[5]  # Longitude
        altitude = flight[7]  # Altitude em metros
        velocidade = flight[9]  # Velocidade em m/s

        # Calcular distância restante (se houver coordenadas do destino)
        distancia_restante = calcular_distancia(lat, lon, None, None)  # Adicione coordenadas do destino aqui

        # Estimativa de chegada (se houver velocidade)
        tempo_chegada = "Indisponível"
        if distancia_restante and velocidade:
            tempo_est = (distancia_restante * 1000) / velocidade / 60  # Tempo em minutos
            tempo_chegada = f"{int(tempo_est)} min"

        reply += f"🛫 **Voo {flight_id}**\n"
        reply += f"- Origem: {origin}\n"
        reply += f"- Destino: {destination}\n"
        reply += f"- 📍 Localização: {lat}, {lon}\n"
        reply += f"- 📏 Distância restante: {distancia_restante} km\n" if distancia_restante else ""
        reply += f"- ⏳ Previsão de chegada: {tempo_chegada}\n" if tempo_chegada != "Indisponível" else ""
        reply += f"- 🛬 Altitude: {altitude} m\n\n"

        count += 1

    await update.message.reply_text(reply, parse_mode="Markdown")

# Monitoramento de voos para pouso
async def monitorar_pouso():
    voos_pousados = set()
    while True:
        flights = get_opensky_data()
        if flights:
            for flight in flights["states"]:
                flight_id = flight[1] if flight[1] else "Desconhecido"
                altitude = flight[7]

                if altitude == 0 and flight_id not in voos_pousados:
                    voos_pousados.add(flight_id)
                    mensagem = f"🛬 **O voo {flight_id} acaba de pousar!**"
                    # Aqui usamos a variável chat_id
                    await bot.send_message(chat_id, mensagem)

        await asyncio.sleep(60)  # Verifica a cada minuto

async def start(update: Update, context: CallbackContext):
    await update.message.reply_text("Olá! Eu sou o Flight Tracker Bot. Use o comando /voos para obter informações de voos.")

async def main():
    # Cria a aplicação do bot
    application = Application.builder().token(BOT_TOKEN).build()

    # Adiciona o comando /start
    application.add_handler(CommandHandler("start", start))
    
    # Adiciona o comando /voos
    application.add_handler(CommandHandler("voos", send_flight_info))
    
    # Inicia a monitoração de pouso em uma thread separada
    asyncio.create_task(monitorar_pouso())

    # Inicia o bot
    print("Bot iniciado...")
    await application.run_polling()

if __name__ == '__main__':
    # Rodando o bot com o asyncio
    asyncio.run(main())
