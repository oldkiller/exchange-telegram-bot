import datetime

import peewee

# Create connection with database. Can be changed to PostgreSQL
sqlite_db = peewee.SqliteDatabase("cur_rates.db")
sqlite_db.connect()


# Classes for working with the database
class BaseModel(peewee.Model):

	class Meta:
		database = sqlite_db


class CurrencyRate(BaseModel):
	currency = peewee.TextField(null=False)
	rate = peewee.FloatField(null=False)


class RequestTime(BaseModel):
	ids = peewee.IntegerField(primary_key=True)
	last_request = peewee.DateTimeField()


# Creating table if not exists
if not CurrencyRate.table_exists():
	CurrencyRate.create_table()

if not RequestTime.table_exists():
	RequestTime.create_table()
	create_query = RequestTime.insert(
		ids=1,
		last_request=datetime.datetime(1, 1, 1)
	)
	create_query.execute()


# Function for working with the database
def save_new_rates(rates: dict) -> None:
	existed = CurrencyRate.select()
	existed_currency = [c.currency for c in existed]

	for currency in rates:
		if currency in existed_currency:
			query = CurrencyRate.update(
				{CurrencyRate.rate: rates[currency]}
				).where(
				CurrencyRate.currency == currency
			)
		else:
			query = CurrencyRate.insert(
				currency=currency,
				rate=rates[currency]
			)

		query.execute()

	q = RequestTime.update({RequestTime.last_request: datetime.datetime.now()})
	q.execute()


def get_old_rates() -> dict:
	old_rates_query = CurrencyRate.select()

	currency_rates = {}
	for currency in old_rates_query:
		currency_rates.update({currency.currency: currency.rate})

	return currency_rates


def check_data_out_of_date() -> bool:
	old_request_time = [r.last_request for r in RequestTime.select()][0]
	now_time = datetime.datetime.now()

	diff = now_time - old_request_time
	if diff < datetime.timedelta(0, 600):
		return False
	else:
		return True
