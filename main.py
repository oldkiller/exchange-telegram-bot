import os

import telebot
import requests

# load telegram token from .env file
from dotenv import load_dotenv
load_dotenv()


telegram_token = os.environ["TELEGRAM_TOKEN"]
bot = telebot.TeleBot(telegram_token)


def get_rates_list(currency: str) -> dict:
	root = "https://api.exchangeratesapi.io/latest?base={}".format(currency)
	raw_data = requests.get(root)
	if raw_data.status_code != 200:
		raise ConnectionError("Server unavailable")

	raw_data = raw_data.json()

	rates = raw_data["rates"]
	rates.pop(currency, None)  # Delete base currency

	return rates


@bot.message_handler(commands=["list", "lst"])
def send_rates_list(msg):
	rates = get_rates_list("USD")

	reply_text = ""
	for key in rates:
		reply_text += "{}: {}\n".format(key, round(rates[key], 2))

	bot.send_message(msg.chat.id, reply_text)


if __name__ == '__main__':
	bot.polling()
