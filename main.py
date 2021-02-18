import datetime
import os
import random
import re
import uuid

import matplotlib.pyplot as plt
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
		url = "https://api.exchangeratesapi.io/latest?base={}".format(currency)
		raw_data = requests.get(url)
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


def extract_history_data(msg_text: str) -> dict:
	result_two_currency = re.search(r"[A-Z]{3}/[A-Z]{3}", msg_text).group(0)
	if result_two_currency:
		base, second = result_two_currency.split("/")
	else:
		result_second_currency = re.search(r"[A-Z]{3}", msg_text).group(0)
		base, second = "USD", result_second_currency

	days_str = re.search(r"[\d]+", msg_text).group(0)
	days = int(days_str)

	return {
		"days": days,
		"base": base,
		"second": second
	}


def get_rates_history(data_for_history: dict) -> dict:
	end_at = datetime.datetime.now().date()
	start_at = end_at - datetime.timedelta(data_for_history["days"])

	url = "https://api.exchangeratesapi.io/history"
	params = {
		"start_at": start_at,
		"end_at": end_at,
		"base": data_for_history["base"],
		"symbols": data_for_history["second"]
	}
	req = requests.get(url, params=params)
	if req.status_code != 200:
		raise ConnectionError("Server unavailable")

	raw_history_data = req.json()
	history_data = raw_history_data["rates"]

	return history_data


def visualize_history(history: dict, msg_data: dict) -> str:
	second = msg_data["second"]
	list_of_date = list(history.keys())
	list_of_date.sort()

	rate_values = [round(history[date][second], 5) for date in list_of_date]
	list_of_date = [date[5:] for date in list_of_date]

	plt.figure(random.randint(1, 100000))
	plt.plot(list_of_date, rate_values)
	plt.grid()

	filename = str(uuid.uuid1()) + ".png"
	plt.savefig(filename)

	return filename


@bot.message_handler(commands=["list", "lst"])
def send_rates_list(msg):
	try:
		rates = get_rates_list("USD")
	except ConnectionError:
		bot.send_message(msg.chat.id, "Server unavailable")
		return

	reply_text = ""
	for key in rates:
		reply_text += "{}: {}\n".format(key, round(rates[key], 2))

	bot.send_message(msg.chat.id, reply_text)


@bot.message_handler(commands=["exchange"])
def send_converted_currency(msg):
	msg_text = msg.text.split(" ", 1)[1]

	msg_data = extract_exchange_data(msg_text)

	try:
		rates = get_rates_list("USD")
	except ConnectionError:
		bot.send_message(msg.chat.id, "Server unavailable")
		return

	result = convert_currency(rates, msg_data)

	reply_text = "{} {}".format(result["value"], result["currency"])

	bot.send_message(msg.chat.id, reply_text)


@bot.message_handler(commands=["history"])
def send_history(msg):
	msg_text = msg.text.split(" ", 1)[1]

	data_for_history = extract_history_data(msg_text)

	# Try load data from API
	try:
		history = get_rates_history(data_for_history)
	except ConnectionError:
		bot.send_message(msg.chat.id, "Server unavailable")
		return

	# If history data not available - inform user and stop function
	if not history:
		reply = "No exchange rate data is available for the selected currency"
		bot.send_message(msg.chat.id, reply)
		return

	bot.send_chat_action(msg.chat.id, "upload_photo")

	filename = visualize_history(history, data_for_history)

	# Send user graph, if available
	try:
		photo = open(filename, "rb")
	except FileNotFoundError:
		bot.send_message(msg.chat.id, "Failed to send image")
	else:
		bot.send_photo(msg.chat.id, photo)
		photo.close()
	finally:
		os.remove(filename)


if __name__ == '__main__':
	bot.polling()
