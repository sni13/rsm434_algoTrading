import requests
from time import sleep

s = requests.Session()
s.headers.update({'X-API-key': '336UI8XK'}) # Desktop

MAX_LONG_EXPOSURE = 25000
MAX_SHORT_EXPOSURE = -25000
ORDER_LIMIT = 500

def get_tick():
    resp = s.get('http://localhost:9999/v1/case')
    if resp.ok:
        case = resp.json()
        return case['tick'], case['status']

def get_bid_ask(ticker):
    payload = {'ticker': ticker}
    resp = s.get ('http://localhost:9999/v1/securities/book', params = payload)
    if resp.ok:
        book = resp.json()
        bid_side_book = book['bids']
        ask_side_book = book['asks']
        
        bid_prices_book = [item["price"] for item in bid_side_book]
        ask_prices_book = [item['price'] for item in ask_side_book]
        
        best_bid_price = bid_prices_book[0]
        best_ask_price = ask_prices_book[0]
  
        return best_bid_price, best_ask_price

def get_time_sales(ticker):
    payload = {'ticker': ticker}
    resp = s.get ('http://localhost:9999/v1/securities/tas', params = payload)
    if resp.ok:
        book = resp.json()
        time_sales_book = [item["quantity"] for item in book]
        return time_sales_book

def get_position():
    resp = s.get ('http://localhost:9999/v1/securities')
    if resp.ok:
        book = resp.json()
        return abs(book[0]['position']) + abs(book[1]['position']) + abs(book[2]['position'])

def get_open_orders(ticker):
    payload = {'ticker': ticker}
    resp = s.get ('http://localhost:9999/v1/orders', params = payload)
    if resp.ok:
        orders = resp.json()
        buy_orders = [item for item in orders if item["action"] == "BUY"]
        sell_orders = [item for item in orders if item["action"] == "SELL"]
        return buy_orders, sell_orders

def get_order_status(order_id):
    resp = s.get ('http://localhost:9999/v1/orders' + '/' + str(order_id))
    if resp.ok:
        order = resp.json()
        return order['status']

def main():
    tick, status = get_tick()
    ticker_list = ['CNR','RY','AC']

    while status == 'ACTIVE':        

        for i in range(3):
            
            ticker_symbol = ticker_list[i]
            position = get_position()
            best_bid_price, best_ask_price = get_bid_ask(ticker_symbol)
            
            # Price Adjustment Stuff
            BID_ADJUSTMENT = 0
            ASK_ADJUSTMENT = 0

            ADJ_THRESHOLD_1 = 10000
            ADJ_THRESHOLD_2 = 15000

            # Volume Adjustment Stuff
            BID_VOLUME_ADJ = 0
            ASK_VOLUME_ADJ = 0

            VOL_THRESH_1 = 10000
            VOL_THRESH_2 = 15000

            # Price Adjustment Implementation
            if position > ADJ_THRESHOLD_2:
                BID_ADJUSTMENT = 0.2

            elif position > ADJ_THRESHOLD_1:
                BID_ADJUSTMENT = 0.1

            if position > ADJ_THRESHOLD_2:
                ASK_ADJUSTMENT = 0.2

            elif position > ADJ_THRESHOLD_1:
                ASK_ADJUSTMENT = 0.1

            # Volume Adjustment Implementation
            if position > VOL_THRESH_2:
                BID_VOLUME_ADJ = 200

            elif position > VOL_THRESH_1:
                BID_VOLUME_ADJ = 300

            if position > VOL_THRESH_2:
                ASK_VOLUME_ADJ = 200

            elif position > VOL_THRESH_1:
                ASK_VOLUME_ADJ = 300

            # Punching in Orders
            if position < MAX_LONG_EXPOSURE:
                resp = s.post('http://localhost:9999/v1/orders', params = {'ticker': ticker_symbol, 'type': 'LIMIT', 'quantity': min(ORDER_LIMIT - BID_VOLUME_ADJ, abs(MAX_LONG_EXPOSURE) - abs(position)), 'price': best_bid_price - BID_ADJUSTMENT, 'action': 'BUY'})
              
            if position > MAX_SHORT_EXPOSURE:
                resp = s.post('http://localhost:9999/v1/orders', params = {'ticker': ticker_symbol, 'type': 'LIMIT', 'quantity': min(ORDER_LIMIT + ASK_VOLUME_ADJ, abs(MAX_SHORT_EXPOSURE) - abs(position)), 'price': best_ask_price + ASK_ADJUSTMENT, 'action': 'SELL'})

            sleep(0.5) 

            s.post('http://localhost:9999/v1/commands/cancel', params = {'ticker': ticker_symbol})

        tick, status = get_tick()

if __name__ == '__main__':
    main()



