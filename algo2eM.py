import requests  # for HTTP to talk to RIT
import time  # apparently sleep is pretty accurate
import multiprocessing as mp

# variables that are not changing while the case is running, and may appear in multiple spots - one change in the variable here applies to every instance, otherwise I would have to go through the code to change every instance; these are not inside a function which makes them "global" instead of "local" and they can be used by any function
MAX_LONG_EXPOSURE = 25000
MAX_SHORT_EXPOSURE = -25000
ORDER_LIMIT = 5000
# these are what I play with
# so far more trading volume meant more profit
# so far best is 5k max pos and 5k max trade
# MAX_POSITION_ABS = 3000
MAX_POSITION_ABS = {"CNR": 10000, "RY": 15000, "AC": 5000}
MAX_TRADE = {"CNR": 10000, "RY": 15000, "AC": 5000} #AC 15k
# TICK_DELAY = 0.2
TICK_DELAY = {"CNR":1, "RY": 1, "AC": 1}#upped from 0.5
MIN_SPREAD = {"CNR": 0.21, "RY": 0.12, "AC": 0.25}
SPREAD_DENOM = {"CNR": 1, "RY": 0.4, "AC": 1}
BIG_LIMIT_WAIT = {"CNR": 0, "RY": 0, "AC": 0}
TIMEOUT = {"CNR": 1, "RY": 1, "AC": 1} #upped from 0.5


def get_tick(s):  # this function queries the status of the case ("ACTIVE", "STOPPED", "PAUSED") which we will use in our "while" loop
    resp = s.get('http://localhost:9999/v1/case')
    if resp.ok:
        case = resp.json()
        return case['tick'], case['status']  # this code does not use the "tick" value, but may be useful if the code is modified


def get_bid_ask(ticker, s):  # this function queries the order book for price data, specifically finds the best bid and offer (BBO) prices; the same get request has additional information, like quantity (see the dictionary output of a query); the decision-making of the code depends on the bid-ask quote
    payload = {'ticker': ticker}
    resp = s.get('http://localhost:9999/v1/securities/book', params=payload)
    if resp.ok:
        book = resp.json()
        bid_side_book = book['bids']
        ask_side_book = book['asks']
        #
        # bid_prices_book = [item["price"] for item in bid_side_book]
        # ask_prices_book = [item['price'] for item in ask_side_book]
        #
        bid_quantity_book = [item["quantity"] for item in bid_side_book]
        ask_quantity_book = [item['quantity'] for item in ask_side_book]
        #
        # best_bid_price = bid_prices_book[0]
        # best_ask_price = ask_prices_book[0]
        #
        # best_bid_quantity = bid_quantity_book[0]
        # best_ask_quantity = ask_quantity_book[0]

        best_bid_price = bid_side_book[0]["price"]
        best_ask_price = ask_side_book[0]["price"]

        best_bid_quantity = sum(bid_quantity_book)/len(bid_quantity_book)
        best_ask_quantity = sum(ask_quantity_book)/len(ask_quantity_book)
        # print("%d, %d" % (best_bid_quantity, best_ask_quantity))

        return best_bid_price, best_ask_price, best_bid_quantity, best_ask_quantity


def get_position(ticker, s):
    resp = s.get('http://localhost:9999/v1/securities')
    if resp.ok:
        book = resp.json()
        for i in range(3):
            if book[i]['ticker'] == ticker:
                return book[i]['position']
        return abs(book[0]['position']) + abs(book[1]['position']) + abs(book[2]['position'])


# return 1 if buying for balance_order_buy_or_sell, -1 for selling, return 0 for no pre-existing position
def order_count_last_buy_sell(position, max_profit_size, ticker_symbol):
    balance_order_buy_or_sell = 0
    # in this case no extra trades, try to get order down to 0, limit market risk
    if abs(position) > MAX_POSITION_ABS[ticker_symbol]:
        order_count = 0
        order_size = 0
        # determine balance to sell or not
        if position > 0:
            balance_order_buy_or_sell = -1
        elif position < 0:
            balance_order_buy_or_sell = 1
            position = abs(position)

        balance_order_count, balance_order_size = divmod(position, ORDER_LIMIT)
    # in case we go for profit and clear position
    else:
        order_count, order_size = divmod(max_profit_size, ORDER_LIMIT)

        # determine balance to sell or not
        if position > 0:
            balance_order_buy_or_sell = -1
        elif position < 0:
            balance_order_buy_or_sell = 1
            position = abs(position)

        balance_order_count, balance_order_size = divmod(position, ORDER_LIMIT)

    return int(order_count), order_size, int(balance_order_count), balance_order_size, balance_order_buy_or_sell


def trade_process(ticker_symbol):
    s = requests.Session()
    s.headers.update({'X-API-key': 'davidbian'})

    tick, status = get_tick(s)
    while status != 'ACTIVE':
        time.sleep(0.5)
        tick, status = get_tick(s)

    while status == 'ACTIVE':
        best_bid_price, best_ask_price, best_bid_quantity, best_ask_quantity = get_bid_ask(ticker_symbol, s)
        position = get_position(ticker_symbol, s)
        max_profit_size = min(min(best_bid_quantity, best_ask_quantity), MAX_TRADE[ticker_symbol])
        # print("%3s: %d" % (ticker_symbol, max_profit_size))

        order_count, order_size, balance_order_count, balance_order_size, balance_order_buy_or_sell = order_count_last_buy_sell(position, max_profit_size, ticker_symbol)
        # print("%d, %d" % (order_count, balance_order_count))

        spread = best_ask_price - best_bid_price
        diff = spread - MIN_SPREAD[ticker_symbol]
        # storing all the order ids
        order_id = []
        # if spread not enough
        if diff < 0:
            diff = abs(diff)
            best_ask_price = best_ask_price + min((diff / 2), spread / SPREAD_DENOM[ticker_symbol])
            best_bid_price = best_bid_price - min((diff / 2), spread / SPREAD_DENOM[ticker_symbol])
            # print(min((diff / 2), spread / SPREAD_DENOM[ticker_symbol]))
            # best_ask_price = best_ask_price + min((diff/2), max(spread/SPREAD_DENOM[ticker_symbol], 0.015))
            # best_bid_price = best_bid_price - min((diff/2), max(spread/SPREAD_DENOM[ticker_symbol], 0.015))

        # if making big order
        if order_count != 0:
            for j in range(order_count):
                resp = s.post('http://localhost:9999/v1/orders', params={'ticker': ticker_symbol, 'type': 'LIMIT', 'quantity': ORDER_LIMIT, 'price': best_bid_price, 'action': 'BUY'})
                if resp.ok:
                    order_id.append(resp.json()["order_id"])
                resp = s.post('http://localhost:9999/v1/orders', params={'ticker': ticker_symbol, 'type': 'LIMIT', 'quantity': ORDER_LIMIT, 'price': best_ask_price, 'action': 'SELL'})
                if resp.ok:
                    order_id.append(resp.json()["order_id"])

        # else should mostly just be this
        if order_size != 0:
            resp = s.post('http://localhost:9999/v1/orders', params={'ticker': ticker_symbol, 'type': 'LIMIT', 'quantity': order_size, 'price': best_bid_price, 'action': 'BUY'})
            if resp.ok:
                order_id.append(resp.json()["order_id"])
            resp = s.post('http://localhost:9999/v1/orders', params={'ticker': ticker_symbol, 'type': 'LIMIT', 'quantity': order_size, 'price': best_ask_price, 'action': 'SELL'})
            if resp.ok:
                order_id.append(resp.json()["order_id"])

        # now clear the balance
        if balance_order_buy_or_sell == 1:
            if balance_order_count != 0:
                for j in range(balance_order_count):
                    resp = s.post('http://localhost:9999/v1/orders', params={'ticker': ticker_symbol, 'type': 'LIMIT', 'quantity': ORDER_LIMIT, 'price': best_bid_price, 'action': 'BUY'})
                    if resp.ok:
                        order_id.append(resp.json()["order_id"])
            if balance_order_size != 0:
                resp = s.post('http://localhost:9999/v1/orders', params={'ticker': ticker_symbol, 'type': 'LIMIT', 'quantity': balance_order_size, 'price': best_bid_price, 'action': 'BUY'})
                if resp.ok:
                    order_id.append(resp.json()["order_id"])
        else:
            if balance_order_count != 0:
                for j in range(balance_order_count):
                    resp = s.post('http://localhost:9999/v1/orders', params={'ticker': ticker_symbol, 'type': 'LIMIT', 'quantity': ORDER_LIMIT, 'price': best_ask_price, 'action': 'SELL'})
                    if resp.ok:
                        order_id.append(resp.json()["order_id"])
            if balance_order_size != 0:
                resp = s.post('http://localhost:9999/v1/orders', params={'ticker': ticker_symbol, 'type': 'LIMIT', 'quantity': balance_order_size, 'price': best_ask_price, 'action': 'SELL'})
                if resp.ok:
                    order_id.append(resp.json()["order_id"])

        # boolean to check whether order is executed, used to break while loop
        executed = False
        # copy of list used to check whether order is cancelled
        cancelled = order_id.copy()
        # if len(order_id) != 0:
        #     print(order_id)
        # timer to break if needed
        begin = time.time()
        while not executed and len(order_id) > 0:
            # loop through ids in order id and check status of that trade
            for oid in order_id:
                resp = s.get("http://localhost:9999/v1/orders/" + str(oid), params={"id": oid})
                if resp.ok:
                    # if transacted remove from list
                    if resp.json()["status"] == "TRANSACTED":
                        order_id.remove(oid)
                    # if quantity filled then also remove it
                    elif resp.json()["quantity"] == resp.json()["quantity_filled"]:
                        order_id.remove(oid)
                # check time
                passed = time.time() - begin
                # print(passed)
                # if time limit up leave
                if passed > TIMEOUT[ticker_symbol]:
                    executed = True
                    # print("exiting with timeout")
                    break

        # cancel existing order we submitted
        s.post('http://localhost:9999/v1/commands/cancel', params={'ticker': ticker_symbol})
        while len(cancelled) > 0:
            for oid in cancelled:
                resp = s.get("http://localhost:9999/v1/orders/" + str(oid), params={"id": oid})
                if resp.ok and resp.json()["status"] != "OPEN":
                    cancelled.remove(oid)
        tick, status = get_tick(s)


def main():
    # #create threads
    # t1 = threading.Thread(target=trade_thread, args=("CNR",))
    # t2 = threading.Thread(target=trade_thread, args=("RY",))
    # t3 = threading.Thread(target=trade_thread, args=("AC",))
    #
    # #start threads
    # t1.start()
    # t2.start()
    # t3.start()

    # fuck multithread we going multiprocess
    print("setup start")
    print(TICK_DELAY)
    # mp.set_start_method('spawn')
    p1 = mp.Process(target=trade_process, args=("CNR",), name="CNR")
    p2 = mp.Process(target=trade_process, args=("RY",), name="RY")
    p3 = mp.Process(target=trade_process, args=("AC",), name="AC")

    # start
    p1.start()
    p2.start()
    p3.start()

    # join
    p1.join()
    p2.join()
    p3.join()


if __name__ == '__main__':  # convenience to make it easier to run the code
    main()
