from translations.translations import vocabulary
from datetime import datetime, timedelta
from telebot.types import Message
from bot_redis import redis_db
from loguru import logger
import re


steps = {
    '1': 'destination_id',
    '2min': 'min_price',
    '2max': 'max_price',
    '3': 'distance',
    '4': 'quantity',
}
currencies = {
    "ru": "RUB",
    "en": "USD"
}
locales = {
    "ru": "ru_RU",
    "en": "en_US"
}

logger_config = {
    "handlers": [
        {
            "sink": "logs/bot.log",
            "format": "{time} | {level} | {message}",
            "encoding": "utf-8",
            "level": "DEBUG",
            "rotation": "5 MB",
            "compression": "zip"
        },
    ],
}


def internationalize(key: str, msg: Message) -> str:
    lang = redis_db.hget(msg.chat.id, 'language')

    return vocabulary[key][lang]


_ = internationalize


def is_input_correct(msg: Message) -> bool:
    state = redis_db.hget(msg.chat.id, 'state')
    msg = msg.text.strip()

    if state == '4' and ' ' not in msg and msg.isdigit() and 0 < int(msg) <= 20: return True
    elif state == '3' and ' ' not in msg and msg.replace('.', '').isdigit(): return True
    elif state == '2' and msg.replace(' ', '').isdigit() and len(msg.split()) == 2: return True
    elif state == '1' and msg.replace(' ', '').replace('-', '').isalpha(): return True


def get_parameters_information(msg: Message) -> str:
    logger.info(f'Function {get_parameters_information.__name__} called with argument: {msg}')
    parameters = redis_db.hgetall(msg.chat.id)
    sort_order = parameters['order']
    city = parameters['destination_name']
    currency = parameters['currency']
    message = (
        f"<b>{_('parameters', msg)}</b>\n"
        f"{_('city', msg)}: {city}\n"
    )

    if sort_order == "DISTANCE_FROM_LANDMARK":
        price_min = parameters['min_price']
        price_max = parameters['max_price']
        distance = parameters['distance']
        message += f"{_('price', msg)}: {price_min} - {price_max} {currency}\n" \
                   f"{_('max_distance', msg)}: {distance} {_('dis_unit', msg)}"
        
    logger.info(f'Search parameters: {message}')
    return message


def make_message(msg: Message, prefix: str) -> str:
    state = redis_db.hget(msg.chat.id, 'state')
    message = _(prefix + state, msg)

    if state == '2':
        message += f" ({redis_db.hget(msg.chat.id, 'currency')})"

    return message


def hotel_price(hotel: dict) -> int:

    price = 0

    try:
        if hotel.get('ratePlan').get('price').get('exactCurrent'):
            price = hotel.get('ratePlan').get('price').get('exactCurrent')
        else:
            price = hotel.get('ratePlan').get('price').get('current')
            price = int(re.sub(r'[^0-9]', '', price))

    except Exception as e: logger.warning(f'Hotel price getting error {e}')
    
    return price


def hotel_address(hotel: dict, msg: Message) -> str:

    message = _('no_information', msg)

    if hotel.get('address'):
        message = hotel.get('address').get('streetAddress', message)
    return message


def hotel_rating(rating: float, msg: Message) -> str:
    if not rating:
        return _('no_information', msg)
    
    return '⭐' * int(rating)


def check_in_n_out_dates(check_in: datetime = None, check_out: datetime = None) -> dict:
    dates = {}

    if not check_in:
        check_in = datetime.now()

    if not check_out:
        check_out = check_in + timedelta(1)

    dates['check_in'] = check_in.strftime("%Y-%m-%d")
    dates['check_out'] = check_out.strftime("%Y-%m-%d")

    return dates


def add_user(msg: Message) -> None:
    logger.info("add_user called")
    chat_id = msg.chat.id
    lang = msg.from_user.language_code

    if lang != 'ru': lang = 'en'

    redis_db.hset(chat_id, mapping={
        "language": lang,
        "state": 0,
        "locale": locales[lang],
        "currency": currencies[lang]
    })


def is_user_in_db(msg: Message) -> bool:
    logger.info('is_user_in_db called')
    chat_id = msg.chat.id

    return redis_db.hget(chat_id, 'state') and redis_db.hget(chat_id, 'language')


def extract_search_parameters(msg: Message) -> dict:
    logger.info(f"Function {extract_search_parameters.__name__} called")
    params = redis_db.hgetall(msg.chat.id)
    logger.info(f"parameters: {params}")

    return params