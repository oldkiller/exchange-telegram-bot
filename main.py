import os
import re

import telebot
import requests

import database as db

# load telegram token from .env file
from dotenv import load_dotenv
load_dotenv()


telegram_token = os.environ["TELEGRAM_TOKEN"]
bot = telebot.TeleBot(telegram_token)


def get_rates_list(currency: str) -> dict:
	if db.check_data_out_of_date():
		root = "https://api.exchangeratesapi.io/latest?base={}".format(currency)
		raw_data = requests.get(root)
		if raw_data.status_code != 200:
			raise ConnectionError("Server unavailable")

		raw_data = raw_data.json()

		rates = raw_data["rates"]
		rates.pop(currency, None)  # Delete base currency

		db.save_new_rates(rates)

	else:
		rates = db.get_old_rates()

	return rates


def extract_exchange_data(msg_text: str) -> dict:
	result_value = re.search(r"[\d]+", msg_text).group(0)
	result_currency = re.findall(r"[A-Z]{3}", msg_text)

	if msg_text.startswith("$"):
		base, second = "USD", result_currency[0]
	else:
		base, second = result_currency[0], result_currency[1]

	return {
		"value": float(result_value),
		"base": base,
		"second": second
	}


def convert_currency(rates: dict, currency_to_convert: dict) -> dict:
	base_value = currency_to_convert["value"]
	second_currency = currency_to_convert["second"]
	multiplier = rates[second_currency]

	result = round(base_value * multiplier, 2)

	return {"value": result, "currency": second_currency}


@bot.message_handler(commands=["list", "lst"])
def send_rates_list(msg):
	rates = get_rates_list("USD")

	reply_text = ""
	for key in rates:
		reply_text += "{}: {}\n".format(key, round(rates[key], 2))

	bot.send_message(msg.chat.id, reply_text)


@bot.message_handler(commands=["exchange"])
def send_converted_currency(msg):
	msg_text = msg.text.split(" ", 1)[1]

	msg_data = extract_exchange_data(msg_text)
	rates = get_rates_list("USD")
	result = convert_currency(rates, msg_data)

	reply_text = "{} {}".format(result["value"], result["currency"])

	bot.send_message(msg.chat.id, reply_text)


if __name__ == '__main__':
	bot.polling()
