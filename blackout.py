import requests
from bs4 import BeautifulSoup
import telebot
import os
import json
from datetime import datetime, timedelta
from dotenv import load_dotenv

import config

load_dotenv()

TELEGRAM_BOT_TOKEN = os.environ.get('TELEGRAM_BOT_TOKEN')
CHAT_ID = os.environ.get('CHAT_ID')

bot = telebot.TeleBot(TELEGRAM_BOT_TOKEN)

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


def get_filtered_data(file):
    # Load JSON file
    with open(file, 'r', encoding='utf-8') as json_file:
        table_data = json.load(json_file)

    today = datetime.now()
    current_date = today.strftime('%d.%m.%Y')
    tomorrow_date = (today + timedelta(days=1)).strftime('%d.%m.%Y')

    # Filter rows for current and tomorrow's dates
    filtered_data = {
        row_key: {k: v for k, v in row_data.items() if k in {"5", "6"}}
        for row_key, row_data in table_data.items()
        if row_key in {current_date, tomorrow_date}
    }
    
    return filtered_data


if __name__ == "__main__":
    data = scrape_website(config.URL)

    if data:
        # Save to JSON file
        with open(config.DATA_FILE, 'w', encoding='utf-8') as json_file:
            json.dump(data, json_file, ensure_ascii=False, indent=4)

        # Print data to console
        print(json.dumps(data, ensure_ascii=False, indent=4))

        filtered_data = get_filtered_data(config.DATA_FILE)
        filtered_data_string = json.dumps(filtered_data, ensure_ascii=False, indent=4)

        # Print the filtered data in JSON format
        print('\n === FILTERED DATA === \n')
        print(filtered_data_string)
        
        bot.send_message(CHAT_ID, filtered_data_string)

        