import json
import logging

import requests
from flask import Flask, request, Response
from viberbot import Api
from viberbot.api.bot_configuration import BotConfiguration
from viberbot.api.messages.text_message import TextMessage
from viberbot.api.messages.url_message import URLMessage
from viberbot.api.viber_requests import ViberFailedRequest, ViberConversationStartedRequest
from viberbot.api.viber_requests import ViberMessageRequest
from viberbot.api.viber_requests import ViberSubscribedRequest

app = Flask(__name__)
viber = Api(BotConfiguration(
    name='Smyt Career\'s Bot',
    avatar='',
    auth_token=''
))

logger = logging.getLogger()
logger.setLevel(logging.DEBUG)

COUNTRIES = (
    ('belarus', 'Беларусь'),
    ('rossiya', 'Россия'),
    ('ukraina', 'Украина'),
    ('udalennaya-rabota', 'Удаленная работа'),
)

PROFILES = (
    ('hr', 'Hr'),
    ('marketing', 'Маркетинг'),
    ('otdel-prodazh', 'Отдел продаж'),
    ('razrabotka', 'Разработка'),
    ('testirovanie', 'Тестирование'),
    ('upravlenie-i-analitika', 'Управление и аналитика'),
)

LEVELS = (
    ('junior', 'Junior'),
    ('middle', 'Middle'),
    ('senior', 'Senior'),
    ('bez-opyita', 'Без опыта'),
    ('', 'Неважно'),
)

VACANCIES_URL = 'https://careers.smyt.ru/api/vacancies/'


def get_buttons(action_type, items):
    return [{
        "Columns": 3,
        "Rows": 1,
        "BgColor": "#e6f5ff",
        # "BgMedia": "http://link.to.button.image",
        # "BgMediaType": "picture",
        "BgLoop": True,
        "ActionType": 'reply',
        "ActionBody": "{action_type}|{value}".format(action_type=action_type, value=item[0]),
        "ReplyType": "message",
        "Text": item[1]
    } for item in items]


careers_actions = ('select_country', 'select_profile', 'select_level')


@app.route('/', methods=['POST'])
def incoming():
    # print("received request. post data: {0}".format(request.get_data()))
    # every viber message is signed, you can verify the signature using this method
    if not viber.verify_signature(request.get_data(), request.headers.get('X-Viber-Content-Signature')):
        return Response(status=403)

    # this library supplies a simple way to receive a request object
    viber_request = viber.parse_request(request.get_data())

    if isinstance(viber_request, ViberMessageRequest):
        message = viber_request.message
        text = message.text
        text = text.split('|')
        text_type = text[0]
        text_message = ''

        tracking_data = message.tracking_data
        if tracking_data is None:
            tracking_data = {}
        else:
            tracking_data = json.loads(tracking_data)

        keyboard = {
            "DefaultHeight": True,
            "BgColor": "#FFFFFF",
            "Type": "keyboard",
            "Buttons": [
                {
                    "Columns": 6,
                    "Rows": 1,
                    "BgColor": "#e6f5ff",
                    "BgLoop": True,
                    "ActionType": "reply",
                    "ActionBody": "search_vacancies",
                    "ReplyType": "message",
                    "Text": "Поиск вакансий"
                }
            ]
        }
        is_finished = False
        buttons = {}

        if text_type == 'search_vacancies':
            tracking_data = {}
            countries = [country[1] for country in COUNTRIES]
            text_message = 'Доступны вакансии в следующих странах: {countries}. Пожалуйста, выберите одну из них.'\
                .format(countries=', '.join(countries))
            buttons = get_buttons('select_country', COUNTRIES)
        elif text_type == 'select_country':
            tracking_data['country'] = text[1]
            items = [item[1] for item in PROFILES]
            text_message = 'Доступны вакансии по следующим профилям: {profiles}. Пожалуйста, выберите один из них.'\
                .format(profiles=', '.join(items))
            buttons = get_buttons('select_profile', PROFILES)
        elif text_type == 'select_profile':
            tracking_data['profile'] = text[1]
            items = [item[1] for item in LEVELS]
            text_message = 'Укажите пожалуйста какой у вас опыт в этой области: {items}. Пожалуйста, выберите один из них.'\
                .format(
                items=', '.join(items))
            buttons = get_buttons('select_level', LEVELS)
        elif text_type == 'select_level':
            is_finished = True
            tracking_data['level'] = text[1]
        else:
            text_message = "Выберите опцию"

        messages = []
        if is_finished:
            response = requests.get(VACANCIES_URL, params=tracking_data)
            json_response = response.json()
            items = json_response.get('results', [])
            for item in items:
                messages.append(URLMessage(media=item.get('url'),
                                           keyboard=keyboard,
                                           tracking_data={}))

            if not messages:
                messages.append(TextMessage(text='Извините, по выбранным критериям, вакансий не найдено.',
                                            keyboard=keyboard,
                                            tracking_data={}))
        else:
            keyboard_buttons = keyboard.get('Buttons', [])
            keyboard_buttons.extend(buttons)
            keyboard['Buttons'] = keyboard_buttons
            keyboard = keyboard if keyboard.get('Buttons') else None
            tracking_data = json.dumps(tracking_data)
            messages.append(TextMessage(text=text_message,
                                        keyboard=keyboard,
                                        tracking_data=tracking_data))

        viber.send_messages(viber_request.sender.id, messages)

    elif isinstance(viber_request, ViberSubscribedRequest):
        viber.send_messages(viber_request.user.id, [
            TextMessage(text="thanks for subscribing!")
        ])
    elif isinstance(viber_request, ViberFailedRequest):
        logger.warn("client failed receiving message. failure: {0}".format(viber_request))
    elif isinstance(viber_request, ViberConversationStartedRequest):
        keyboard = {
            "DefaultHeight": True,
            "BgColor": "#FFFFFF",
            "Type": "keyboard",
            "Buttons": [
                {
                    "Columns": 6,
                    "Rows": 1,
                    "BgColor": "#e6f5ff",
                    "BgLoop": True,
                    "ActionType": "reply",
                    "ActionBody": "search_vacancies",
                    "ReplyType": "message",
                    "Text": "Поиск вакансий"
                }
            ]
        }
        viber.send_messages(viber_request.user.id, [
            TextMessage(text="Здравствуйте!", keyboard=keyboard)
        ])

    return Response(status=200)


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8443, debug=True, )
