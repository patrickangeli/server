import io
import os
import sqlite3
import sys
from datetime import datetime, timezone

import folium
import matplotlib.pyplot as plt
import numpy as np
import telebot
from flightradar24 import FlightRadar24API
from PIL import Image
from telebot.types import InputMediaPhoto

# Initialize bot and API with environment variables
BOT_TOKEN = os.getenv('BOT_TOKEN')
if not BOT_TOKEN:
    print("No BOT_TOKEN provided")
    sys.exit(1)

bot = telebot.TeleBot(BOT_TOKEN)
fr_api = FlightRadar24API()

def setup_database():
    """Initialize SQLite database with required tables"""
    conn = sqlite3.connect('flights.db')
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS tracked_flights
                 (id INTEGER PRIMARY KEY AUTOINCREMENT,
                  flight_number TEXT,
                  registration TEXT,
                  last_status TEXT,
                  last_altitude INTEGER,
                  last_speed INTEGER,
                  last_update TIMESTAMP,
                  origin TEXT,
                  destination TEXT,
                  chat_id INTEGER,
                  is_active BOOLEAN)''')
    conn.commit()
    conn.close()

def save_flight_data(flight_details, current_flight, chat_id):
    """Save or update flight data in database"""
    conn = sqlite3.connect('flights.db')
    c = conn.cursor()
    
    try:
        flight_number = flight_details['identification']['number']['default']
        registration = flight_details['aircraft']['registration']
        status = "In Flight" if current_flight.altitude > 100 else "On Ground"
        origin = flight_details['airport']['origin']['code']['icao']
        destination = flight_details['airport']['destination']['code']['icao']
        
        c.execute('''INSERT OR REPLACE INTO tracked_flights 
                     (flight_number, registration, last_status, last_altitude, 
                      last_speed, last_update, origin, destination, chat_id, is_active)
                     VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)''',
                     (flight_number, registration, status, current_flight.altitude,
                      current_flight.ground_speed, datetime.now(), origin, 
                      destination, chat_id, True))
        conn.commit()
        return True
    except Exception as e:
        print(f"Error saving flight data: {e}")
        return False
    finally:
        conn.close()

def check_status_changes():
    """Check for status changes of tracked flights"""
    conn = sqlite3.connect('flights.db')
    c = conn.cursor()
    
    try:
        c.execute('SELECT * FROM tracked_flights WHERE is_active = True')
        active_flights = c.fetchall()
        
        for flight in active_flights:
            try:
                registration = flight[2]
                last_status = flight[3]
                chat_id = flight[9]
                
                current_flights = fr_api.get_flights(registration=registration, details=True)
                if current_flights:
                    current_flight = current_flights[0]
                    flight_details = fr_api.get_flight_details(current_flight)
                    new_status = "In Flight" if current_flight.altitude > 100 else "On Ground"
                    
                    if new_status != last_status:
                        message = (f"✈️ Status Update for {flight[1]}\n"
                                 f"Registration: {registration}\n"
                                 f"Previous Status: {last_status}\n"
                                 f"New Status: {new_status}\n"
                                 f"Current Altitude: {current_flight.altitude} ft\n"
                                 f"Ground Speed: {current_flight.ground_speed} knots")
                        
                        bot.send_message(chat_id=chat_id, text=message, parse_mode='HTML')
                        update_flight_status(current_flight, new_status, flight[0])
                        
                        # Generate and send updated flight map
                        create_flight_map(flight_details, current_flight)
                        with open('flight_map.png', 'rb') as map_file:
                            bot.send_photo(chat_id, map_file, caption="Updated Flight Path")
            
            except Exception as e:
                print(f"Error checking flight {registration}: {e}")
                continue
    
    finally:
        conn.close()

def update_flight_status(current_flight, new_status, flight_id):
    """Update flight status in database"""
    conn = sqlite3.connect('flights.db')
    c = conn.cursor()
    
    try:
        c.execute('''UPDATE tracked_flights 
                     SET last_status = ?, last_altitude = ?, 
                         last_speed = ?, last_update = ?
                     WHERE id = ?''',
                     (new_status, current_flight.altitude,
                      current_flight.ground_speed, datetime.now(),
                      flight_id))
        conn.commit()
    finally:
        conn.close()

def create_flight_map(flight_details, current_flight):
    """Create a map with the flight path"""
    trail_coordinates = [(point['lat'], point['lng']) 
                        for point in flight_details['trail']]
    
    if not trail_coordinates:
        return None
    
    flight_map = folium.Map(location=trail_coordinates[0], zoom_start=6)
    
    # Draw flight path
    folium.PolyLine(
        trail_coordinates,
        weight=2,
        color='blue',
        opacity=0.8
    ).add_to(flight_map)
    
    # Add markers for airports
    try:
        origin = (flight_details['airport']['origin']['position']['latitude'],
                 flight_details['airport']['origin']['position']['longitude'])
        destination = (flight_details['airport']['destination']['position']['latitude'],
                      flight_details['airport']['destination']['position']['longitude'])
        
        folium.Marker(
            origin,
            popup=flight_details['airport']['origin']['code']['icao'],
            icon=folium.Icon(color='green')
        ).add_to(flight_map)
        
        folium.Marker(
            destination,
            popup=flight_details['airport']['destination']['code']['icao'],
            icon=folium.Icon(color='red')
        ).add_to(flight_map)
    except Exception as e:
        print(f"Error adding airport markers: {e}")
    
    # Save map as PNG
    img_data = flight_map._to_png()
    img = Image.open(io.BytesIO(img_data))
    img.save('flight_map.png')

def create_flight_graph(flight_details):
    """Create a graph showing altitude and speed over time"""
    timestamps = [datetime.fromtimestamp(point['ts']) 
                 for point in flight_details['trail']]
    altitudes = [point['alt'] for point in flight_details['trail']]
    speeds = [point['spd'] for point in flight_details['trail']]
    
    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(10, 8))
    
    # Plot altitude
    ax1.plot(timestamps, altitudes, 'b-')
    ax1.set_ylabel('Altitude (ft)')
    ax1.grid(True)
    
    # Plot speed
    ax2.plot(timestamps, speeds, 'r-')
    ax2.set_ylabel('Ground Speed (knots)')
    ax2.grid(True)
    
    plt.tight_layout()
    plt.savefig('flight_graph.png')
    plt.close()

@bot.message_handler(commands=['start'])
def send_welcome(message):
    """Handle /start command"""
    welcome_text = (
        "👋 Welcome to Flight Tracker!\n\n"
        "Commands:\n"
        "/track <flight_number> - Track a flight\n"
        "/list - Show tracked flights\n"
        "/stop - Stop tracking all flights\n"
        "/help - Show this message"
    )
    bot.reply_to(message, welcome_text)

@bot.message_handler(commands=['track'])
def track_flight(message):
    """Handle /track command"""
    try:
        flight_num = message.text.split()[1]
    except IndexError:
        bot.reply_to(message, "❌ Please provide a flight number: /track <flight_number>")
        return
    
    try:
        flight_tracker = fr_api.search(flight_num)
        
        if 'live' in flight_tracker and flight_tracker['live']:
            registration = flight_tracker['live'][0]['detail']['reg']
            current_flight = next(fr_api.get_flights(registration=registration, details=True))
            flight_details = fr_api.get_flight_details(current_flight)
            
            if save_flight_data(flight_details, current_flight, message.chat.id):
                create_flight_map(flight_details, current_flight)
                create_flight_graph(flight_details)
                
                # Send initial flight information
                with open('flight_map.png', 'rb') as map_file:
                    bot.send_photo(message.chat.id, map_file, caption="Current Flight Path")
                
                with open('flight_graph.png', 'rb') as graph_file:
                    bot.send_photo(message.chat.id, graph_file, caption="Flight Data")
                
                bot.reply_to(message, "✅ Flight is now being tracked!")
        else:
            bot.reply_to(message, "❌ Flight not found or not currently active")
    
    except Exception as e:
        bot.reply_to(message, f"❌ Error tracking flight: {str(e)}")

@bot.message_handler(commands=['list'])
def list_tracked(message):
    """Handle /list command"""
    conn = sqlite3.connect('flights.db')
    c = conn.cursor()
    
    try:
        c.execute('''SELECT flight_number, registration, last_status, 
                            last_update, origin, destination 
                     FROM tracked_flights 
                     WHERE chat_id = ? AND is_active = True''', 
                     (message.chat.id,))
        
        flights = c.fetchall()
        
        if flights:
            response = "📋 Tracked Flights:\n\n"
            for flight in flights:
                response += (f"Flight: {flight[0]}\n"
                           f"Registration: {flight[1]}\n"
                           f"Status: {flight[2]}\n"
                           f"Route: {flight[4]} ✈️ {flight[5]}\n"
                           f"Last Update: {flight[3]}\n\n")
        else:
            response = "No flights currently being tracked"
        
        bot.reply_to(message, response)
    finally:
        conn.close()

@bot.message_handler(commands=['stop'])
def stop_tracking(message):
    """Handle /stop command"""
    conn = sqlite3.connect('flights.db')
    c = conn.cursor()
    
    try:
        c.execute('''UPDATE tracked_flights 
                     SET is_active = False 
                     WHERE chat_id = ? AND is_active = True''', 
                     (message.chat.id,))
        conn.commit()
        bot.reply_to(message, "✅ Stopped tracking all flights")
    finally:
        conn.close()

if __name__ == "__main__":
    setup_database()
    check_status_changes()  # Check status on startup
    bot.polling(none_stop=True)
