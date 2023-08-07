"""Телеграмм бот для проверки статуса домашней работы."""
import logging
import os
import sys
import requests
import time
from telegram import Bot
from http import HTTPStatus
from dotenv import load_dotenv

load_dotenv()

PRACTICUM_TOKEN = os.getenv('PRACTICUM_TOKEN')
TELEGRAM_TOKEN = os.getenv('TELEGRAM_TOKEN')
TELEGRAM_CHAT_ID = os.getenv('TELEGRAM_CHAT_ID')

RETRY_PERIOD = 600
ENDPOINT = 'https://practicum.yandex.ru/api/user_api/homework_statuses/'
HEADERS = {'Authorization': f'OAuth {PRACTICUM_TOKEN}'}


HOMEWORK_VERDICTS = {
    'approved': 'Работа проверена: ревьюеру всё понравилось. Ура!',
    'reviewing': 'Работа взята на проверку ревьюером.',
    'rejected': 'Работа проверена: у ревьюера есть замечания.'
}

logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)
console_handler = logging.StreamHandler(stream=sys.stdout)
formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
console_handler.setFormatter(formatter)
logger.addHandler(console_handler)


def check_tokens():
    """Функция проверки доступности переменных окружения."""
    tokens = {'PRACTICUM_TOKEN': PRACTICUM_TOKEN,
              'TELEGRAM_TOKEN': TELEGRAM_TOKEN,
              'TELEGRAM_CHAT_ID': TELEGRAM_CHAT_ID}

    for token_name, token_value in tokens.items():
        if not token_value:
            message = ('Отсутствует обязательная переменная окружения:'
                       f'{token_name}. Программа остановлена.')
            logger.critical(message)
            raise NameError(message)


def get_api_answer(timestamp):
    """Функция запроса ответа сервера Яндекс Практикум."""
    try:
        params = {'from_date': timestamp - RETRY_PERIOD}
        response = requests.get(ENDPOINT, headers=HEADERS, params=params)
        logger.debug(f'Сделан запрос к API {ENDPOINT}. Параметры {params}')
    except Exception as error:
        message = (f'Сбой в работе программы: Эндпоинт {ENDPOINT} недоступен.'
                   f'Параметры {params}. Ошибка {error}')
        logger.error(message)
        return message
    if response.status_code == HTTPStatus.OK:
        return response.json()
    else:
        raise ValueError('Неверный код ответа')


def check_response(response):
    """Функция для проверки ответа сервера Яндекс Практикум."""
    if not isinstance(response, dict):
        raise TypeError('Ответ сервера не соответствует ожидаемому'
                        'типу данных (словарь)')
    try:
        homeworks = response.get('homeworks')
    except Exception as error:
        message = (f'Неожиданный ответ сервера {error}.')
        logger.error(message)
        return message
    if not isinstance(homeworks, list):
        raise TypeError('В ответе сервера под ключом "homeworks" нет списка')
    try:
        if homeworks:
            homework = homeworks[0]
            return homework
        message = 'Новых домашних работ нет'
        logger.debug(message)
    except Exception as error:
        message = f'Ошибка при обработке домашних работ: {error}'
        logger.error(message)
        return message


def parse_status(homework):
    """Функция для проверки статуса домашней работы."""
    homework_name = homework.get('homework_name')
    status = homework.get('status')
    if not status or not homework_name:
        message = 'В ответе сервера нет ключа homework_name или status'
        logger.error(message)
        raise ValueError(message)
    verdict = HOMEWORK_VERDICTS.get(status)
    if not verdict:
        message = ('Неожиданный статус домашней работы')
        logger.error(message)
        raise NameError(message)
    message = ('Изменился статус проверки работы '
               f'"{homework_name}". {verdict}')
    return message


def send_message(bot, message):
    """Функция для отправки сообщения в Telegram."""
    try:
        logger.debug(f'Начинаем отпрвку сообщения {message} в телеграм')
        bot.send_message(TELEGRAM_CHAT_ID, message)
        logger.debug(f'Бот отправил сообщение {message}')
    except Exception as error:
        message = (f'Сбой при отправке сообщения {error}')
        logger.error(message)


def main():
    """Основная функция для выполнения задачи."""
    try:
        check_tokens()
    except Exception:
        sys.exit()
    bot = Bot(token=TELEGRAM_TOKEN)
    while True:
        try:
            timestamp = int(time.time())
            response = get_api_answer(timestamp)
            if response:
                homework = check_response(response)
                if homework:
                    message = parse_status(homework)
                    send_message(bot, message)
        except Exception as error:
            message = f'Сбой в работе программы: {error}'
            logger.error(message)
            send_message(bot, message)
        time.sleep(RETRY_PERIOD)


if __name__ == '__main__':
    main()
