import scrapy
import os
import json
import time
import smtplib, ssl

class spider_razer(scrapy.Spider):
    name = 'razer'
    start_urls = [
        'https://www.amazon.com.mx/s?k=razer&rh=n%3A9482640011%2Cp_89%3ARazer&dc&__mk_es_MX=%C3%85M%C3%85%25'
        # 'https://www.amazon.com.mx/s?k=razer&i=videogames&rh=n%3A9482640011%2Cp_89%3ARazer&dc&page=3&__mk_es_MX=%C3%85M%C3%85%25&qid=1619130862&ref=sr_pg_3'
    ]

    custom_settings = {
        'FEED_URI': 'razer_products.json',
        'FEED_FORMAT': 'json',
        'FEED_EXPORT_ENCODING': 'utf-8',
        'ROBOTSTXT_OBEY': True,
        'CONCURRENT_REQUESTS': 24,
        'MEMUSAGE_LIMIT_MB': 2048,
        'MEMUSAGE_NOTIFY_MAIL': ['georgenul@live.com']
    }

    def parse(self, response):
        time.sleep(5)
        prod_div = response.xpath('//div[@class="s-result-item s-asin sg-col-0-of-12 sg-col-16-of-20 sg-col sg-col-12-of-16"]')
        razer_products_obj = {}
        main_web = 'https://www.amazon.com.mx'

        for idx, prod in enumerate(prod_div):
            new_razer_product = {}
            current_prod = '//div[@class="s-result-item s-asin sg-col-0-of-12 sg-col-16-of-20 sg-col sg-col-12-of-16"]['+str(idx)+']'

            new_razer_product['product_id'] = prod.xpath(current_prod+'/@data-asin').get(default="000000")
            new_razer_product['product_title'] = prod.xpath(current_prod+'//span[@class="a-size-medium a-color-base a-text-normal"]/text()').get(default="NoTitle")
            new_razer_product['product_price'] = prod.xpath(current_prod+'//span[@class="a-price-whole"]/text()').get(default="00")
            new_razer_product['product_link'] = main_web+prod.xpath(current_prod+'//a[@class="a-link-normal a-text-normal"]/@href').get(default="NoLink")
            new_razer_product['page'] = 1

            razer_products_obj[new_razer_product['product_id']] = new_razer_product

        next_page_button = response.xpath('//ul[@class="a-pagination"]//li[@class="a-last"]/a/@href').get()

        time.sleep(5)
        yield response.follow(next_page_button, callback=self.parse_get_all_products, cb_kwargs={'prev_page_prods': razer_products_obj, 'page_count': 1})

        # yield razer_products_obj

    def parse_get_all_products(self, response, **kwargs):
        print('*' * 10)
        print('*' * 10)
        main_web = 'https://www.amazon.com.mx'
        prod_div = response.xpath('//div[@class="s-result-item s-asin sg-col-0-of-12 sg-col-16-of-20 sg-col sg-col-12-of-16"]')

        if kwargs:
            razer_products_obj = kwargs['prev_page_prods']
            page_count = kwargs['page_count']

        print('*' * 10)
        print(page_count)
        page_count += 1

        for idx, prod in enumerate(prod_div):
            new_razer_product = {}
            current_prod = '//div[@class="s-result-item s-asin sg-col-0-of-12 sg-col-16-of-20 sg-col sg-col-12-of-16"]['+str(idx)+']'

            new_razer_product['product_id'] = prod.xpath(current_prod+'/@data-asin').get(default="000000")
            new_razer_product['product_title'] = prod.xpath(current_prod+'//span[@class="a-size-medium a-color-base a-text-normal"]/text()').get(default="NoTitle")
            new_razer_product['product_price'] = prod.xpath(current_prod+'//span[@class="a-price-whole"]/text()').get(default="00")
            new_razer_product['product_link'] = main_web+prod.xpath(current_prod+'//a[@class="a-link-normal a-text-normal"]/@href').get(default="NoLink")
            new_razer_product['page'] = page_count

            razer_products_obj[new_razer_product['product_id']] = new_razer_product

        next_page_button = response.xpath('//ul[@class="a-pagination"]//li[@class="a-last"]/a/@href').get()

        if next_page_button and page_count < 2:
            time.sleep(5)
            yield response.follow(next_page_button, callback=self.parse_get_all_products, cb_kwargs={'prev_page_prods': razer_products_obj, 'page_count': page_count})
        else:
            File_is_empty = os.stat("razer_products.json").st_size == 0
            if File_is_empty is True:
                print('file is EMPTY!!')
                yield razer_products_obj
            else:
                self.compare_prices(razer_products_obj)

    def compare_prices(self, razer_products_obj):
        print('file is not EMPTY!!!')
        with open('razer_products.json') as f:
            print('reading file...')
            read_products = f.read()
            products_from_db = json.loads(read_products)

            for key, value in razer_products_obj.items():
                current_product_price = int(value['product_price'].replace(',', ''))

                if key in products_from_db[0]:
                    db_product = products_from_db[0].get(key)
                    db_product_price = int(db_product['product_price'].replace(',', ''))

                    offer_price = db_product_price - ((db_product_price * 10) / 100)

                    if current_product_price < offer_price:
                        if 'lower_price' in db_product:
                            lower_prod_price = int(db_product['lower_price'].replace(',', ''))
                            if current_product_price < lower_prod_price:
                                print('product: '+db_product['product_id']+' has a new lower price!')
                                db_product['lower_price'] = value['product_price']
                                self.send_email(db_product['product_title'], db_product['product_price'], db_product['product_link'], value['product_price'])
                        else:
                            print('product: '+db_product['product_id']+' has a new lower price!')
                            db_product['lower_price'] = value['product_price']
                            self.send_email(db_product['product_title'], db_product['product_price'], db_product['product_link'], value['product_price'])
                else:
                    print("this product was not register: \n")
                    print(value)
                    products_from_db[0][value['product_id']] = value

            with open('razer_products.json', 'w') as file:
                file.write(json.dumps(products_from_db))

    def send_email(self, product_title, product_price, product_link, lower_price):
        port = 465
        # password = input("Type your password: ")
        password = "Jonulodev274."
        smtp_server = "smtp.gmail.com"
        sender_email = "jonulodev@gmail.com"
        receiver_email = "georgenul@live.com"
        message = f"""
            Subject: subject test

            Product: {product_title} \n
            Normal price: ${product_price} - new lower price: ${lower_price}. \n
            Link: {product_link}"""

        context = ssl.create_default_context()
        with smtplib.SMTP_SSL(smtp_server, port, context=context) as server:
            server.login(sender_email, password)
            server.sendmail(sender_email, receiver_email, message)

