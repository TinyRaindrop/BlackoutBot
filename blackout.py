import requests
from bs4 import BeautifulSoup
from telebot import TeleBot
from telebot import formatting
import os
import json
from datetime import datetime, timedelta
from dotenv import load_dotenv

import config

load_dotenv()

TELEGRAM_BOT_TOKEN = os.environ.get('TELEGRAM_BOT_TOKEN')
CHAT_ID = os.environ.get('CHAT_ID')

bot = TeleBot(TELEGRAM_BOT_TOKEN)

@bot.message_handler(commands=['start', 'hello'])
def send_welcome(message):
    bot.send_message(message.chat.id, "HELLO !")


@bot.message_handler(func=lambda msg: True)
def echo_all(message):
    schedule = json.dumps(get_filtered_data(config.DATA_FILE), ensure_ascii=False, indent=4)
    # bot.reply_to(message, message.text)
    bot.send_message(message.chat.id, schedule)


# Upon calling this function, TeleBot starts polling the Telegram servers for new messages.
# - interval: int (default 0) - The interval between polling requests
# - timeout: integer (default 20) - Timeout in seconds for long polling.
#bot.infinity_polling(interval=1, timeout=0)

def scrape_website(url):
    response = requests.get(url, verify=False)
    if response.status_code != 200:
        print(f"Failed to retrieve the webpage. Status code: {response.status_code}")
        return False
        
    soup = BeautifulSoup(response.text, 'html.parser')
    table = soup.select_one('div#fetched-data-container > table')
    if not table:
        print("Table not found on the page.")
        return False
    
    rows = table.find_all('tr')[3:]  # Skip header rows (first 3)

    table_data = {}
    for row in rows:
        cells = row.find_all('td')
        if not cells:
            continue

        # Get the key from the first column
        row_key = cells[0].get_text(strip=True)

        row_data = {}
        cell_counter = 1 

        for cell in cells[1:]:
            # Extract text from all <p> tags in the cell
            paragraphs = [p.get_text(strip=True) for p in cell.find_all('p')]
            cell_content = paragraphs if paragraphs else cell.get_text(strip=True)
            row_data[str(cell_counter)] = cell_content
            cell_counter += 1

        table_data[row_key] = row_data

    return table_data


def get_filtered_data(data):
    today = datetime.now()
    current_date = today.strftime('%d.%m.%Y')
    tomorrow_date = (today + timedelta(days=1)).strftime('%d.%m.%Y')

    # Filter rows for current and tomorrow's dates
    try:
        filtered_data = {
            row_key: {k: v for k, v in row_data.items() if k in {"5", "6"}}
            for row_key, row_data in data.items()
            if row_key in {current_date, tomorrow_date}
        }
    except Exception as e:
        print(f"An error occurred: {e}")
        return False
    
    return filtered_data


def read_file():
    file = config.DATA_FILE
    if not os.path.exists(file):
        print ('config.DATA_FILE does not exist')
        return False
    with open(file, 'r', encoding='utf-8') as json_file: 
        return json.load(json_file)


def write_file(data):
    data["timestamp"] = datetime.now().strftime('%d.%m.%Y %H:%M')
    with open(config.DATA_FILE, 'w', encoding='utf-8') as json_file:
        json.dump(data, json_file, ensure_ascii=False, indent=4)


def format_message(json_data):
    message = ""
    for date, shifts in json_data.items():
        if not isinstance(shifts, dict):
            continue

        # Ensure all values in shifts are lists
        print(shifts)
        shifts = {k: v if isinstance(v, list) else [v] for k, v in shifts.items()}

        # Check if all shifts are "expected"
        all_expected = all(times == ["Очікується"] for times in shifts.values())

        # Check if all shifts are empty
        all_empty = all(
            not times or (isinstance(times, list) and not any(times))
            for times in shifts.values()
            )
        
        message += f"⚡ {formatting.hbold(date)}"
        if all_expected:
            message += ": Очікується\n"
        elif all_empty:
            message += ": Немає відключень\n"
        else:
            message += "\n"
            for shift, times in shifts.items():
                shift_title = formatting.hitalic('Черга '  + shift + ':')
                if times:
                    if all(not t.strip() for t in times):  # lists with only empty strings
                        times_str = " Немає відключень"
                    else:
                        times_str = "\n " + "\n".join(filter(None, times))
                else:
                    times_str = " Немає відключень"
                message += f"{shift_title}{times_str}\n\n"

    return message.strip()


def publish(data):       
    print('\n === NEW MESSAGE === \n')

    message = format_message(data)
    print(message)
    bot.send_message(CHAT_ID, message, parse_mode='HTML')
    
    #data_json = json.dumps(data, ensure_ascii=False, indent=4)
    #print(data_json)
    #bot.send_message(CHAT_ID, data_json)


if __name__ == "__main__":
    data = scrape_website(config.URL)

    if data:
        print('=== DATA ===')
        # print(json.dumps(data, ensure_ascii=False, indent=4))
        print(data)
        print(json.dumps(data, ensure_ascii=False))

        # Read from JSON file
        old_data = read_file()
        if not old_data: 
            write_file(data)
            print('No previous data was found.')
            publish(data)
            exit(1)
        
        # Filter data
        #filtered_old_data = get_filtered_data(old_data)
        #filtered_data = get_filtered_data(data)
        
        #if not filtered_data:
        #    print('Failed to filter new data!')
        #    exit(0)

        # If data has changed
        if data != old_data:
            # Checks passed, save with current timestamp
            write_file(data)
            publish(data)
