import csv
import datetime
import requests
from bs4 import BeautifulSoup
from fake_useragent import UserAgent
import telebot
from config import tg_token
from time import sleep

last_call = datetime.datetime(2022, 1, 1, 1, 1, 1, 1)


def collect_data(city_code='2398'):
    global last_call
    time_diff = last_call - datetime.datetime.now()
    time_diff = time_diff.total_seconds()
    if time_diff < -300: # условие, чтобы не запрашивать новые данные с сайте чаще, чем раз в 5 минут
        last_call = datetime.datetime.now()
        ua = UserAgent()
        headers = {
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8',
            'User-Agent': ua.random
        }
        cookies = {
            'mg_geo_id': f'{city_code}'
        }
        response = requests.get(url='https://magnit.ru/promo/', headers=headers, cookies=cookies)
        with open(f'magnit.html', 'w') as file:
            file.write(response.text)

    with open('magnit.html') as file:
        src = file.read()
    soup = BeautifulSoup(src, 'lxml')
    # city = soup.find('a', class_='header__contacts-link_city').text.strip()
    cards = soup.find_all('a', class_='card-sale_catalogue')
    cards_list = []
    print(len(cards_list))
    for card in cards:
        try:
            card_discount = card.find('div', class_='card-sale__discount').text.strip()
        except AttributeError:
            continue
        # Название
        card_title = card.find('div', class_='card-sale__title').text.strip()
        # старая цена
        card_price_old_integer = card.find('div', class_='label__price_old').find('span', class_='label__price-integer').text.strip()
        card_price_old_decimal = card.find('div', class_='label__price_old').find('span', class_='label__price-decimal').text.strip()
        card_old_price = f'{card_price_old_integer}.{card_price_old_decimal}'
        # новая цена
        card_price_integer = card.find('div', class_='label__price_new').find('span', class_='label__price-integer').text.strip()
        card_price_decimal = card.find('div', class_='label__price_new').find('span', class_='label__price-decimal').text.strip()
        card_price = f'{card_price_integer}.{card_price_decimal}'
        # срок акции
        card_sale_date = card.find('div', class_='card-sale__date').text.strip().replace('\n', ' ')
        cards_list.append(f'{card_title}\n{card_old_price}р.->{card_price}р.({card_discount})\n{card_sale_date}')
    # очистка от дубликатов
    cards_set = set(cards_list)
    return cards_set


def save_to_csv(cards_set):
    with open('sale.csv', 'w') as file:
        writer = csv.writer(file)
        writer.writerow(
            (
                'Продукт',
                'Старая цена',
                'Новая цена',
                'Скидка',
                'Время акции',
            )
        )


def telegram_bot(token):
    bot = telebot.TeleBot(token)

    @bot.message_handler(commands=["start"])
    def start_message(message):
        bot.send_message(message.chat.id, 'Привет!')

    @bot.message_handler(content_types=['text'])
    def handle_text(message):
        user_input = message.text.lower().replace('ё', 'е').strip()
        if len(user_input) > 2:
            bot.send_message(message.chat.id, 'Пожалуйста немного подождите. Собираю информацию.')
            cards_set = collect_data(city_code='2398')
            send_text = ''
            cards_count = 0
            for card in cards_set:
                if user_input in card.lower():
                    cards_count += 1
                    send_text += '🤑 ' + card + '\n\n'
                    if cards_count >= 40: # в одном сообщении макс 40 товаров
                        bot.send_message(message.chat.id, '💲💲Скидочки!💲💲\n\n' + send_text)
                        send_text = ''
                        cards_count = 0
            if cards_count == 0:
                bot.send_message(message.chat.id, 'Ничего не найдено 😭')
            else:
                bot.send_message(message.chat.id, '💲💲Скидочки!💲💲\n\n' + send_text)
        else:
            bot.send_message(message.chat.id, 'Слишком короткий запрос.')

    try:
        bot.infinity_polling()
    except Exception as e:
        print(f'{datetime.datetime.now()}: Связь с Телегой отсутствует! {e}')
        bot.stop_polling()
        sleep(30)
        telegram_bot(tg_token)


def main():
    telegram_bot(tg_token)


if __name__ == '__main__':
    main()
