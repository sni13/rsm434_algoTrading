import requests
from time import sleep
import numpy as np
import multiprocessing as mp
import threading

s = requests.Session()
api_key = 'KICKWUQE'                        # change api key here
s.headers.update({'X-API-key': api_key})    # Make sure you use YOUR API Key

# position limiters
MAX_EXPOSURE_GROSS = 452000 # 500k - 48k (one order max can be 48k, so to be safe)
ORDER_LIMIT = 12000         # 25k/2 around 12k so we don't go over the net limit

# the buy and sell margins (not including conversion fee, that another variable)
# reason for 0.03 for now is that 1 cent commission for both RGLD and RFIN with half cent
# for INDX, this means that we need at least 2.5 cents for profit (rock bottom), maybe do 4?
BUY_ETF_MARGIN = 0.04
SELL_ETF_MARGIN = 0.04

# stuff for the converter
creation_id = 0
redemption_id = 0
redemption_cost = 0.0375
PERCENT_START_CONVERT = 0.7 # at what percentage do we convert to free up position

# price update time (in seconds)
UPDATE_DELAY = 0.05

# round no for continuous rounds
round_num = 0

# price and quantity updated here
#           [bid price] [ask price] [bid quantity] [ask quantity]
# ['RGLD'] ____________|___________|______________|______________
# ['RFIN'] ____________|___________|______________|______________
# ['INDX'] ____________|___________|______________|______________
# format follows above, updated by threads so global
market = np.array([0., 0., 0., 0., 0., 0., 0., 0., 0., 0., 0., 0.])
market = market.reshape(3, 4)

# multithread ticker list
ticker_list = ['RGLD', 'RFIN', 'INDX']


def get_tick():
    resp = s.get('http://localhost:9999/v1/case')
    if resp.ok:
        case = resp.json()
        return case['tick'], case['status']
    print("API key probably not set")
    return 300, "STOPPED"


# again, also gives quantity now
def get_bid_ask(ticker):
    resp = s.get('http://localhost:9999/v1/securities/book', params={'ticker': ticker})
    if resp.ok:
        book = resp.json()
        bid_side_book = book['bids']
        ask_side_book = book['asks']
        try:
            best_bid_price = bid_side_book[0]["price"]
            best_ask_price = ask_side_book[0]["price"]

            best_bid_quantity = bid_side_book[0]["quantity"]
            best_ask_quantity = ask_side_book[0]["quantity"]
        except IndexError as error:
            print(error)
            return 0, 0, 0, 0

        return best_bid_price, best_ask_price, best_bid_quantity, best_ask_quantity


# also gives etf position to decide which way to convert
def get_position():
    resp = s.get('http://localhost:9999/v1/securities')
    if resp.ok:
        book = resp.json()
        gross_position = abs(book[1]['position']) + abs(book[2]['position']) + 2 * abs(book[3]['position'])
        net_position = book[1]['position'] + book[2]['position'] + 2 * book[3]['position']
        etf_position = book[3]['position']
        return gross_position, net_position, etf_position


# set up the lease to be used
def setup_lease():
    # mark them as global so we actually change them
    global creation_id
    global redemption_id
    global s
    # new request session for different process
    s = requests.Session()
    s.headers.update({'X-API-key': api_key})

    # get list of active leases
    resp = s.get('http://localhost:9999/v1/leases')
    if resp.ok:
        # if current one exist then register them
        if len(resp.json()) == 2:
            for i in range(2):
                if resp.json()[i]['ticker'] == 'ETF-Creation':
                    creation_id = resp.json()[i]['id']
                elif resp.json()[i]['ticker'] == 'ETF-Redemption':
                    redemption_id = resp.json()[i]['id']
        # else lease them
        else:
            resp = s.post('http://localhost:9999/v1/leases', params={'ticker': 'ETF-Creation'})
            creation_id = int(resp.json()['id'])
            resp = s.post('http://localhost:9999/v1/leases', params={'ticker': 'ETF-Redemption'})
            redemption_id = int(resp.json()['id'])

    # if lease id not updated
    if creation_id == 0 or redemption_id == 0:
        print("lease id not set, exit")
        exit(1)


# main function for the lease process, constantly polls to convert
def use_lease():
    while True:
        tick, status = get_tick()
        while status != 'ACTIVE':
            sleep(0.5)
            tick, status = get_tick()

        setup_lease()
        create_link = 'http://localhost:9999/v1/leases/' + str(creation_id)
        redeem_link = 'http://localhost:9999/v1/leases/' + str(redemption_id)

        # double check different session from main
        print(s)

        while status == 'ACTIVE':
            gross_position, net_position, etf_position = get_position()

            # if over certain percentage then convert
            if gross_position > (MAX_EXPOSURE_GROSS * PERCENT_START_CONVERT):
                # all these etf position checking to be divisible by 2000 is just what I think what contributed to the crash
                if etf_position < 0:
                    etf_position = -etf_position
                    etf_position = (etf_position//2000)*2000
                    convert_size = int(min(etf_position, 100000))
                    resp = s.post(create_link, params={'from1':'RGLD', 'quantity1': convert_size, 'from2': 'RFIN', 'quantity2': convert_size, 'id':creation_id})
                    if not resp.ok:
                        print(resp.json())
                    else:
                        # if successfully tried to convert then sleep
                        sleep(2)
                else:
                    etf_position = (etf_position // 2000) * 2000
                    convert_size = int(min(etf_position, 100000))
                    resp = s.post(redeem_link, params={'from1':'INDX', 'quantity1': convert_size, 'from2': 'CAD', 'quantity2': round(convert_size * redemption_cost),'id': redemption_id})
                    if not resp.ok:
                        print(resp.json())
                    else:
                        # if successfully tried to convert then sleep
                        sleep(2)

            # else poll the fuck out of it without sleep
            tick, status = get_tick()


# threads to update price to global numpy array
def update_price(index):
    while True:
        tick, status = get_tick()

        while status != 'ACTIVE':
            sleep(0.5)
            tick, status = get_tick()

        while status == 'ACTIVE':
            market[index, 0], market[index, 1], market[index, 2], market[index, 3] = get_bid_ask(ticker_list[index])
            sleep(UPDATE_DELAY)
            tick, status = get_tick()


# actual main thread that does the trading
def actual_trading():
    global round_num
    tick, status = get_tick()

    # threads to update the price
    t1 = threading.Thread(target=update_price, args=(0,), name="RGLD")
    t2 = threading.Thread(target=update_price, args=(1,), name="RFIN")
    t3 = threading.Thread(target=update_price, args=(2,), name="INDX")
    t1.start()
    t2.start()
    t3.start()

    while True:
        while status != 'ACTIVE':
            sleep(0.5)
            tick, status = get_tick()

        # check the session used is different from that other process for lease
        print(s)
        print("Round %d start" % round_num)

        while status == 'ACTIVE':
            # to track whether it went through or not
            order_id = []

            gross_position, net_position, etf_position = get_position()

            # don't trade if at limit, let the lease converter work
            if (gross_position < MAX_EXPOSURE_GROSS) or (etf_position < 0):
                # if RGLD bid + RFIN bid - INDX ask is greater than the margin, sell RGLD and RFIN for INDX
                if (market[0, 0] + market[1, 0] - market[2, 1]) > (BUY_ETF_MARGIN + redemption_cost):
                    # just so we don't overbuy just in case
                    size = min(ORDER_LIMIT, market[2, 3], market[0, 2], market[1, 2])
                    resp = s.post('http://localhost:9999/v1/orders', params={'ticker': 'RGLD', 'type': 'MARKET', 'quantity': size, 'action': 'SELL'})
                    if resp.ok:
                        order_id.append(resp.json()["order_id"])
                    resp = s.post('http://localhost:9999/v1/orders', params={'ticker': 'INDX', 'type': 'MARKET', 'quantity': size, 'action': 'BUY'})
                    if resp.ok:
                        order_id.append(resp.json()["order_id"])
                    resp = s.post('http://localhost:9999/v1/orders', params={'ticker': 'RFIN', 'type': 'MARKET', 'quantity': size, 'action': 'SELL'})
                    if resp.ok:
                        order_id.append(resp.json()["order_id"])

                # do the same if there are some etf_positions that we can cancel out this way
                elif ((market[0, 0] + market[1, 0] - market[2, 1]) > BUY_ETF_MARGIN) and (etf_position < 0):
                    # just so we don't overbuy just in case
                    size = min(ORDER_LIMIT, market[2, 3], market[0, 2], market[1, 2])
                    resp = s.post('http://localhost:9999/v1/orders', params={'ticker': 'RGLD', 'type': 'MARKET', 'quantity': size, 'action': 'SELL'})
                    if resp.ok:
                        order_id.append(resp.json()["order_id"])
                    resp = s.post('http://localhost:9999/v1/orders', params={'ticker': 'INDX', 'type': 'MARKET', 'quantity': size, 'action': 'BUY'})
                    if resp.ok:
                        order_id.append(resp.json()["order_id"])
                    resp = s.post('http://localhost:9999/v1/orders', params={'ticker': 'RFIN', 'type': 'MARKET', 'quantity': size, 'action': 'SELL'})
                    if resp.ok:
                        order_id.append(resp.json()["order_id"])

            # I mean there are chances that it goes both ways right? although slim
            if (gross_position < MAX_EXPOSURE_GROSS) or (etf_position > 0):
                # if INDX bid - RGLD ask - RFIN ask is greater than the margin, sell INDX for RGLD and RFIN
                if market[2, 0] - market[0, 1] - market[1, 1] > SELL_ETF_MARGIN:
                    # just so we don't overbuy just in case
                    size = min(ORDER_LIMIT, market[2, 2], market[0, 3], market[1, 3])
                    resp = s.post('http://localhost:9999/v1/orders', params={'ticker': 'RGLD', 'type': 'MARKET', 'quantity': size, 'action': 'BUY'})
                    if resp.ok:
                        order_id.append(resp.json()["order_id"])
                    resp = s.post('http://localhost:9999/v1/orders', params={'ticker': 'INDX', 'type': 'MARKET', 'quantity': size, 'action': 'SELL'})
                    if resp.ok:
                        order_id.append(resp.json()["order_id"])
                    resp = s.post('http://localhost:9999/v1/orders', params={'ticker': 'RFIN', 'type': 'MARKET', 'quantity': size, 'action': 'BUY'})
                    if resp.ok:
                        order_id.append(resp.json()["order_id"])

            while len(order_id) > 0:
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

            tick, status = get_tick()
        round_num = round_num + 1


def main():
    print("setup start thread")
    # mp.set_start_method('spawn')
    # one process for trading, one for converting
    p1 = mp.Process(target=actual_trading, args=(), name="Trade")
    p2 = mp.Process(target=use_lease, args=(), name="Convert")

    # start
    p1.start()
    p2.start()

    exit(0)


if __name__ == '__main__':
    main()
