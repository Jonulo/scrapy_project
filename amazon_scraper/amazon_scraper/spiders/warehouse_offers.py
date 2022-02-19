import scrapy
import os, sys
import asyncio
import json
import time
import smtplib, ssl
# library for use env variables:
from decouple import config

from scrapy.mail import MailSender

from urllib.error import HTTPError
from scrapy.spidermiddlewares.httperror import HttpError

from scrapy.crawler import CrawlerProcess, CrawlerRunner
from twisted.internet import reactor
from twisted.python import log

# TODO:

    # Make a function ... ? xD
    # Manage especific errors in exceptions

class warehouse_offers(scrapy.Spider):
    name = 'warehouse'
    WEBSITE_URL = config('WAREHOUSE_URL')
    EMAIL_PASS = config('EMAIL_PASS')
    start_urls = [WEBSITE_URL]
    page_count = 1

    custom_settings = {
        # put fileName into the env file:
        'FEEDS': {
            "warehouse_products.json": { "format": "json" }
        },
        # 'FEED_URI': 'warehouse_products.json',
        # 'FEED_FORMAT': 'json',
        'FEED_EXPORT_ENCODING': 'utf-8',
        'ROBOTSTXT_OBEY': True,
        'CONCURRENT_REQUESTS': 24,
        'MEMUSAGE_LIMIT_MB': 2048,
        # put the email into the env file:
        'MEMUSAGE_NOTIFY_MAIL': ['georgenul@live.com']
    }



    def parse(self, response):
        try:
            print("response {}".format(response))
            warehouse_products_obj = {}
            list_of_prods = response.xpath('//div[@data-index and string-length(@data-asin)>0]')
            warehouse_products_obj = self.get_products_per_page(list_of_prods, self.page_count)
            print('===============')
            # print('total object: {}'.format(warehouse_products_obj))
            print('===============')

            # next_page_button = response.xpath('//div[@class="a-section a-spacing-none s-result-item s-flex-full-width s-widget s-widget-spacing-large"]/span')
            # print("button {}".format(next_page_button))


            self.page_count += 1
            yield response.follow(
                url=self.WEBSITE_URL + "&page=" + str(self.page_count),
                callback=self.parse_get_all_products,
                errback=self.handling_errors,
                cb_kwargs={
                    'prev_page_prods': warehouse_products_obj,
                    # 'page_count': 2
                }
            )

        except:
            print("Some error has ocurred 1")


    def parse_get_all_products(self, response, **kwargs):
        time.sleep(5)
        print("response -- {}".format(response))
        try:
            list_of_prods = response.xpath('//div[@data-index and string-length(@data-asin)>0]')
            if kwargs:
                warehouse_products_obj = kwargs['prev_page_prods']
                # page_count = kwargs['page_count']

                self.page_count += 1

                warehouse_products_obj.update(self.get_products_per_page(list_of_prods, self.page_count))

                print("+++++++++")
                # print("Next Object: {}".format(warehouse_products_obj))
                print("+++++++++")

                print("test0")
                if self.WEBSITE_URL and self.page_count < 7:
                    print("test1")
                    yield response.follow(
                        url=self.WEBSITE_URL + "&page=" + str(self.page_count),
                        callback=self.parse_get_all_products,
                        errback=self.handling_errors,
                        cb_kwargs={
                            'prev_page_prods': warehouse_products_obj,
                            # 'page_count': self.page_count
                        }
                    )
                else:
                    print("test2")
                    File_is_empty = os.stat("warehouse_products.json").st_size == 0
                    if File_is_empty is True:
                        print("Empty file")
                        yield warehouse_products_obj
                    else:
                        print("test3")
                        products_obj_to_send = []
                        with open('warehouse_products.json') as f:
                            read_products = f.read()
                            products_from_db = json.loads(read_products)

                            for key, value in warehouse_products_obj.items():
                                if key in products_from_db[0]:
                                    pass
                                else:
                                    print("New product incoming...")
                                    new_db_product = value
                                    print("new product: {}".format(new_db_product))
                                    products_from_db[0][new_db_product['id']] = new_db_product
                                    products_obj_to_send.append(new_db_product)
                                    # self.send_email(new_db_product)

                            with open('warehouse_products.json', 'w') as file:
                                print("updatind local DB...")
                                file.write(json.dumps(products_from_db))

                            # If program finishes successfuly, it will waits 30min and send an email.
                            self.send_email(products_obj_to_send)
                            print("wait until request again...")
                            time.sleep(1800)

        except:
            print("Error at next page 2")



    def send_email(self, products):
        try:
            if not len(products):
                pass
            else:
                final_message = ''
                port = 465
                password = self.EMAIL_PASS
                smtp_server = "smtp.gmail.com"
                sender_email = "jonulodev@gmail.com"
                receiver_email = "georgenul@live.com"
                SUBJECT = 'New warehouse products added!!'

                for prod in products:
                    message = f"""
                        Product: {prod['title']} \n
                        Normal price: {prod['current_price']} - new lower price: {prod['warehouse_price']}. \n
                        Link: {prod['link']} \n
                        ============= \n
                    """
                    final_message = final_message + message

                message_with_subject = 'Subject: {}\n\n{}'.format(SUBJECT, final_message)


                # Trying to handle error when email can't be sended
                for x in range(0, 6):
                    try:
                        context = ssl.create_default_context()
                        with smtplib.SMTP_SSL(smtp_server, port, context=context) as server:
                            print("sending email ... {}".format(server.login(sender_email, password)))
                            server.login(sender_email, password)
                            server.sendmail(sender_email, receiver_email, message_with_subject.encode('utf-8'))
                            error_sending_email = None
                    except smtplib.SMTPException as e:
                        print("error sending email", e)
                        error_sending_email = "email error"

                    if error_sending_email == "email error":
                        print("error sending email, retrying...")
                        time.sleep(3)
                    else:
                        break

        except Exception as e:
            print("Error sending email first {}".format(e))


    def get_products_per_page(self, list_of_prods, num_page):
        # Put main_web into env file:
        main_web = 'https://www.amazon.com.mx'
        warehouse_products_obj = {}

        for idx, product in enumerate(list_of_prods):
            new_warehouse_product = {}

            new_warehouse_product['title'] = product.xpath('.//span[@class="a-size-base-plus a-color-base a-text-normal"]/text()').get(default="No Title")
            new_warehouse_product['id'] = product.xpath('./@data-asin').get(default="No Asin")
            new_warehouse_product['link'] = main_web + product.xpath('.//a[@class="a-link-normal s-no-outline"]/@href').get()
            new_warehouse_product['current_price'] = product.xpath('.//span[@class="a-price"]/span[@class="a-offscreen"]/text()').get(default="No Price")
            new_warehouse_product['warehouse_price'] = product.xpath('.//div[@class="a-section a-spacing-none a-spacing-top-mini"]//span[@class="a-color-base"]/text()').get(default="No price")
            new_warehouse_product['page'] = num_page

            # print(new_warehouse_product)
            warehouse_products_obj[new_warehouse_product['id']] = new_warehouse_product

        return warehouse_products_obj


    def handling_errors(self, failure):

        print("hanling error {}".format(failure))
        self.logger.error(repr(failure))

        # print("show response from last failure", failure.value.response)
        if failure.check(HttpError):
            error_response = failure.value.response
            print("http error: {}".format(error_response))
            print("requesting page {} again".format(self.page_count))


async def main():
    while True:
        try:
            print("starting spider warehouse...")
            time.sleep(180)
            # probando = warehouse_offers()
            # log.addObserver(probando.parse)
            # log.addObserver(probando.parse_get_all_products)
            runner = CrawlerRunner()
            d = runner.crawl(warehouse_offers)
            print("probando 1")
            d.addBoth(lambda _: reactor.stop())
            print("probando 2")
            reactor.run()
            print("probando 3")
            os.execl(sys.executable, sys.executable, *sys.argv)

        except:
            print("error at the begining")


asyncio.run(main())

# =========
# Tests:
# probando_obj = [
#     {
#         'name': 'name1',
#         'price': '$200',
#         'warehouse': '$100'
#     },
#     {
#         'name': 'name2',
#         'price': '$300',
#         'warehouse': '$50'
#     },
#     {
#         'name': 'name3',
#         'price': '$400',
#         'warehouse': '$100'
#     },
# ]
# probandoo = warehouse_offers()
# probandoo.send_email(probando_obj)
