from telebot.types import Message
from bot_redis import redis_db
from loguru import logger
import requests
import os
import re


X_RAPIDAPI_KEY = "d75c67d72emsh14ad5be705d05dcp1aece8jsn3b6fabf90458"


def exact_location(data: dict, loc_id: str) -> str:
    for loc in data['reply_markup']['inline_keyboard']:
        if loc[0]['callback_data'] == loc_id:
            return loc[0]['text']

def delete_tags(html_text):
    text = re.sub('<([^<>]*)>', '', html_text)
    return text


def request_locations(msg):
    url = "https://hotels4.p.rapidapi.com/locations/search"

    querystring = {
        "query": msg.text.strip(),
        "locale": redis_db.hget(msg.chat.id, 'locale'),
    }

    headers = {
        'x-rapidapi-key': X_RAPIDAPI_KEY,
        'x-rapidapi-host': "hotels4.p.rapidapi.com"
    }
    logger.info(f'Parameters for search locations: {querystring}')

    try:
        response = requests.request("GET", url, headers=headers, params=querystring, timeout=20)
        data = response.json()
        logger.info(f'Hotels api(locations) response received: {data}')

        if data.get('message'):
            logger.error(f'Problems with subscription to hotels api {data}')
            raise requests.exceptions.RequestException
        
        return data
    
    except requests.exceptions.RequestException as e: logger.error(f'Server error: {e}')
    except Exception as e: logger.error(f'Error: {e}')


def make_locations_list(msg: Message) -> dict:
    data = request_locations(msg)

    if not data: return {'bad_request': 'bad_request'}

    try:
        locations = dict()

        if len(data.get('suggestions')[0].get('entities')) > 0:
            for item in data.get('suggestions')[0].get('entities'):
                location_name = delete_tags(item['caption'])
                locations[location_name] = item['destinationId']
            logger.info(locations)

            return locations
        
    except Exception as e: logger.error(f'Could not parse hotel api response. {e}')
