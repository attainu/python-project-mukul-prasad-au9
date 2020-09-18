from __future__ import print_function
import requests
from requests import Request, Session
from requests.exceptions import ConnectionError, Timeout, TooManyRedirects
import json
from datetime import datetime
import time
import pickle
import os.path
from googleapiclient.discovery import build
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from twilio.rest import Client
import optparse


class Links:
    # link of bitcoin site to retrive price
    bitcoin_url = 'https://pro-api.coinmarketcap.com/v1/cryptocurrency/listings/latest'
    # link to trigger action
    trigger_url = "https://maker.ifttt.com/trigger/{}/with/key/c6zUjiRVi9e0sNig8RDfAG"


# price class created
class BitcoinPrice:

    links = Links()

    # function to extract price from bitcoin site
    def bitcoin_price(self, curr):
        parameters = {
          'start': '1',
          'limit': '1',
          'convert': curr
        }
        headers = {
          'Accepts': 'application/json',
          'X-CMC_PRO_API_KEY': '69a4dff4-fdac-45bb-8add-fb0af04881d6',
        }

        session = Session()
        session.headers.update(headers)

        try:

            response = session.get(self.links.bitcoin_url, params=parameters)
            data = json.loads(response.text)
            price = data["data"][0]["quote"][curr]["price"]
            return price
        # exceptional cases are provided for errors
        except (ConnectionError, Timeout, TooManyRedirects) as e:
            print(e)


# notification class
class notification:
    price_value = BitcoinPrice()  # getting price from other class
    links = Links()  # getting link from link class

    def post_ifttt_webhook(self, event, value):  # function to trigger events
        data = {'value1': value}
        ifttt_event_url = self.links.trigger_url.format(event)
        requests.post(ifttt_event_url, json=data)

    def output_format(self, list1):  # function to correct data format
        rows = []
        for bitcoin_price in list1:
            date = bitcoin_price['date'].strftime('%d.%m.%Y %H:%M')
            price = bitcoin_price['price']
            row = '{}: $<b>{}<b>'.format(date, price)
            rows.append(row)
        return '<br>'.join(rows)

    def whatsapp(self, v):  # function for whatsapp messages
        account_sid = 'ACddcece8518eef133d35eaf0f68451acc'
        auth_token = 'c9d9ed2d4c6b48cb25cee0fad76114c2'
        client = Client(account_sid, auth_token)
        data_whatsapp = "price $"+str(v)
        message = client.messages.create(
            body = data_whatsapp,
            from_ = 'whatsapp:+14155238886',
            to = 'whatsapp:+918668438294'
        )

    def gmail(self):  # function for retriving messages from gmail inbox

        creds = None
        # The file token.pickle stores the user's access and refresh tokens, and is
        # created automatically when the authorization flow completes for the first
        # time.
        if os.path.exists('token.pickle'):
            with open('token.pickle', 'rb') as token:
                creds = pickle.load(token)
        # If there are no (valid) credentials available, let the user log in.
        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                creds.refresh(Request())
            else:
                flow = InstalledAppFlow.from_client_secrets_file(
                    'credentials.json', self.price_value.SCOPES)
                creds = flow.run_local_server(port=0)
            # Save the credentials for the next run
            with open('token.pickle', 'wb') as token:
                pickle.dump(creds, token)

        service = build('gmail', 'v1', credentials=creds)

        results = service.users().messages().list(userId="me", labelIds=["INBOX"]).execute()
        messages = results.get("messages", [])

        if not messages:
            print('No labels found.')
        else:
            for message in messages[:1]:
                msg = service.users().messages().get(userId="me", id=message["id"]).execute()
                value = int(msg['snippet'])
                return value

    def main(self, curr, time1, threshold):  # main function for calling other
        list_of_price = []                   # functions and triggering action
        while True:
            price = self.price_value.bitcoin_price(curr)
            value = self.gmail()
            date = datetime.now()
            list_of_price.append({'date': date, 'price': price})

            if value == threshold:
                pass
            else:
                if type(value) == str:
                    pass
                else:
                    threshold = value

            if price < threshold:
                val = ("emergency", price)
                self.post_ifttt_webhook("bitcoin_telegram", val)

            if len(list_of_price) == 5:
                self.whatsapp(price)
                self.post_ifttt_webhook('bitcoin_telegram', self.output_format(list_of_price))
                self.post_ifttt_webhook('bitcoin_email', self.output_format(list_of_price))
                self.post_ifttt_webhook('bitcoin_sms', price)
                list_of_price = []
                time.sleep(time1 * 10)

    def user_input(self):  # getting users data

        parser = optparse.OptionParser()
        parser.add_option('-t', '--threshold', type='int', dest='limit', action="store", default=10000,
                          help='threshold price')
        parser.add_option('-i', '--time', dest='time', type='int', action="store",
                          help='Time interval to send message in seconds', default=1)
        parser.add_option('-c', '--currency', action="store", type="string", dest='curr',
                          default="USD", help='default is in USD ----Currency you want the price in AUD,BRL,CNY,GBP,INR,JPY,KRW,RUB----')

        (options, args) = parser.parse_args()
        print(options)

        self.main(options.curr, options.time, options.limit)


if __name__ == '__main__':
    call = notification()
    call.user_input()
