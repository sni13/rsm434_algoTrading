import requests
from time import sleep

s = requests.Session()
s.headers.update({'X-API-key': '6PXNU7YM'}) # Desktop

MAX_LONG_EXPOSURE = 25000
MAX_SHORT_EXPOSURE = -25000
ORDER_LIMIT = 3000

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

def test_compelete(resps):
    for resp in resps:
        resp.json()
        order_id = resp.json()['order_id']
        resp2 = None
        while not resp2:
            resp2 = s.get ('http://localhost:9999/v1/orders' + '/' + str(order_id))

def get_ticker_position(ticker):
    ticker_dict = {'CNR': 0,'RY': 1,'AC': 2}
    index = ticker_dict[ticker]
    resp = s.get ('http://localhost:9999/v1/securities')
    if resp.ok:
        book = resp.json()
        return book[index]['position']

def rank_sd(market_prices):
    """return the ranks of 0, 1, 2"""
    ranks = {}
    for i in range(3):
        test_list = market_prices[i]
        mean = sum(test_list) / len(test_list)
        variance = sum([((x - mean) ** 2) for x in test_list]) / len(test_list)
        sd = variance ** 0.5
        ranks[sd] = i
    sds = sorted(list(ranks.keys()))
    res = []
    for sd in sds:
        res.append(ranks[sd])
    return res

def main():
    tick, status = get_tick()
    ticker_list = ['CNR','RY','AC']
    market_prices = [[0.0] * 10] * 3

    while status == 'ACTIVE':   
        # rank all sd of the three; not trading on the first one      
        ranks = rank_sd(market_prices)

        for i in range(3):
            
            ticker_symbol = ticker_list[i]
            sum_position = get_position() #sum of abs position for three stocks
            net_position = get_ticker_position(ticker_symbol) # net position for particular ticker
            best_bid_price, best_ask_price = get_bid_ask(ticker_symbol)
            
            # update market prices
            mid_price = (best_bid_price + best_ask_price)/2.0
            market_prices[i] = market_prices[i][1:].append(mid_price) 

            # TODO: seletively enter the following lines
            if i == ranks[0]:
                continue

            # SET PRICE ADJUSTMENTS
            PRICE_ADJUSTMENT = 0

            ADJ_THRESHOLD_1 = 2000
            ADJ_THRESHOLD_2 = 3500
            ADJ_THRESHOLD_3 = 4000
            ADJ_THRESHOLD_4 = 6000

            if abs(net_position) > ADJ_THRESHOLD_4:
                PRICE_ADJUSTMENT = 0.12

            elif abs(net_position) > ADJ_THRESHOLD_3:
                PRICE_ADJUSTMENT = 0.08

            elif abs(net_position) > ADJ_THRESHOLD_2:
                PRICE_ADJUSTMENT = 0.05

            elif abs(net_position) > ADJ_THRESHOLD_1:
                PRICE_ADJUSTMENT = 0.03

            LONG_PRICE, SHORT_PRICE = best_bid_price, best_ask_price

            # SET VOLUME ADJUSTMENTS
            VOLUME_ADJUSTMENT = 0
            LONG_VOLUME, SHORT_VOLUME = ORDER_LIMIT, ORDER_LIMIT
            VOLUME_ADJUSTMENT = min(abs(net_position) // 15, ORDER_LIMIT)
        
            # make adjustment on only 1 side
            if net_position > 0: # long position
                LONG_PRICE -= PRICE_ADJUSTMENT
                LONG_VOLUME -= VOLUME_ADJUSTMENT
            elif net_position < 0: # short position
                SHORT_PRICE += PRICE_ADJUSTMENT
                SHORT_VOLUME -= VOLUME_ADJUSTMENT

            if sum_position < MAX_LONG_EXPOSURE:
                resp1 = s.post('http://localhost:9999/v1/orders', params = {'ticker': ticker_symbol, 'type': 'LIMIT', 'quantity': min(MAX_LONG_EXPOSURE-sum_position, LONG_VOLUME), 'price': LONG_PRICE, 'action': 'BUY'})
                sum_position = get_position()

            if sum_position > MAX_SHORT_EXPOSURE:
                resp2 = s.post('http://localhost:9999/v1/orders', params = {'ticker': ticker_symbol, 'type': 'LIMIT', 'quantity': min(sum_position-MAX_SHORT_EXPOSURE, SHORT_VOLUME), 'price': SHORT_PRICE, 'action': 'SELL'})
            
            test_compelete([resp1, resp2])

            s.post('http://localhost:9999/v1/commands/cancel', params = {'ticker': ticker_symbol})

        tick, status = get_tick()

if __name__ == '__main__':
    main()



