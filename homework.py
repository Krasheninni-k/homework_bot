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

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)
console_handler = logging.StreamHandler(stream=sys.stdout)
formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
console_handler.setFormatter(formatter)
logger.addHandler(console_handler)


def check_tokens():
    """Функция проверки доступности переменных окружения."""
    if not PRACTICUM_TOKEN:
        message = ('Отсутствует обязательная переменная окружения:'
                   '"PRACTICUM_TOKEN". Программа остановлена.')
        logger.critical(message)
        raise NameError(message)
    if not TELEGRAM_TOKEN:
        logger.critical('Отсутствует обязательная переменная окружения:'
                        '"TELEGRAM_TOKEN". Программа остановлена')
        raise NameError(message)
    if not TELEGRAM_CHAT_ID:
        logger.critical('Отсутствует обязательная переменная окружения:'
                        '"TELEGRAM_CHAT_ID". Программа остановлена')
        raise NameError(message)


def get_api_answer(timestamp):
    """Функция запроса ответа сервера Яндекс Практикум."""
    try:
        params = {'from_date': timestamp - RETRY_PERIOD}
        response = requests.get(ENDPOINT, headers=HEADERS, params=params)
    except Exception as error:
        message = (f'Сбой в работе программы: Эндпоинт {ENDPOINT} недоступен.'
                   f'{error}')
        logger.error(message)
        return message
    if response.status_code == HTTPStatus.OK:
        return response.json()
    else:
        raise ValueError('Неверный код ответа')


def check_response(response):
    """Функция для проверки ответа сервера Яндекс Практикум."""
    if isinstance(response, dict):
        try:
            homeworks = response.get('homeworks')
        except Exception as error:
            message = (f'Неожиданный ответ сервера {error}.')
            logger.error(message)
            return message
        if isinstance(homeworks, list):
            try:
                if homeworks:
                    homework = homeworks[0]
                    return homework
                else:
                    message = 'Новых домашних работ нет'
                    logger.debug(message)
            except Exception as error:
                message = f'Ошибка при обработке домашних работ: {error}'
                logger.error(message)
                return message
        else:
            raise TypeError('В ответе сервера под ключом'
                            '"homeworks" нет списка')
    else:
        raise TypeError('Ответ сервера не соответствует ожидаемому'
                        'типу данных (словарь)')


def parse_status(homework):
    """Функция для проверки статуса домашней работы."""
    if 'homework_name' not in homework or 'status' not in homework:
        message = 'В ответе сервера нет ключа homework_name или status'
        logger.error(message)
        raise ValueError(message)
    homework_name = homework.get('homework_name')
    status = homework.get('status')
    if status not in HOMEWORK_VERDICTS:
        message = ('Неожиданный статус домашней работы')
        logger.error(message)
        raise NameError(message)
    verdict = HOMEWORK_VERDICTS.get(status)
    message = ('Изменился статус проверки работы '
               f'"{homework_name}". {verdict}')
    return message


def send_message(bot, message):
    """Функция для отправки сообщения в Telegram."""
    try:
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
