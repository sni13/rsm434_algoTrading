import requests # we need a package to access RIT via API, there may be other packages that can perform the same role (we are using requests to make an HTTP connection)
from time import sleep # to slow the Python loop we will want to be able to pause the code; the purpose is to correct for different processing speeds in this Python code vs. the RIT server; this is NOT the best way to accomplish this task, ideally the code would have a more exacting way of control the flow of the Python code...

s = requests.Session() # necessary to keep Python from having socket connection errors; not using Session() means Python would keep opening and closing the socket connection to RIT which causes errors as the connection may not have completed closing when the next opening is attempted
s.headers.update({'X-API-key': 'W9OPB2TD'}) # convenience, so we do not need to separately include the API Key in our messages to RIT as it is already included when we use "s"

# variables that are not changing while the case is running, and may appear in multiple spots - one change in the variable here applies to every instance, otherwise I would have to go through the code to change every instance; these are not inside a function which makes them "global" instead of "local" and they can be used by any function
MAX_LONG_EXPOSURE = 25000
MAX_SHORT_EXPOSURE = -25000
ORDER_LIMIT = 500

def get_tick(): # this function queries the status of the case ("ACTIVE", "STOPPED", "PAUSED") which we will use in our "while" loop
    resp = s.get('http://localhost:9999/v1/case')
    if resp.ok:
        case = resp.json()
        return case['tick'], case['status'] # this code does not use the "tick" value, but may be useful if the code is modified

def get_bid_ask(ticker): # this function queries the order book for price data, specifically finds the best bid and offer (BBO) prices; the same get request has additional information, like quantity (see the dictionary output of a query); the decision-making of the code depends on the bid-ask quote
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

def get_time_sales(ticker): # not used in the body of the code, but provides a history of the trades for the selected stock, possibly something that could be used in a strategy
    payload = {'ticker': ticker}
    resp = s.get ('http://localhost:9999/v1/securities/tas', params = payload)
    if resp.ok:
        book = resp.json()
        time_sales_book = [item["quantity"] for item in book]
        return time_sales_book

def get_position(): # this function queries my position and calcualtes the gross position across all stocks in the case; the case has 2 limits, net and gross, with separate fines for each - this function is NOT returning the net position, which might be useful in some cases...
    resp = s.get ('http://localhost:9999/v1/securities')
    if resp.ok:
        book = resp.json()
        return abs(book[0]['position']) + abs(book[1]['position']) + abs(book[2]['position']) # summing without the abs() functions would produce the net position

def get_open_orders(ticker): # this function gets all open orders for a particular ticker symbol (can be used without the ticker symbol and would return all outstanding orders for all stocks in the case); since the market making strategy in this code uses limit orders, it may be useful to have information about existing orders to control the amount of exposure; not used in this code, but could provide more granular control of the strategy...
    payload = {'ticker': ticker}
    resp = s.get ('http://localhost:9999/v1/orders', params = payload)
    if resp.ok:
        orders = resp.json()
        buy_orders = [item for item in orders if item["action"] == "BUY"]
        sell_orders = [item for item in orders if item["action"] == "SELL"]
        return buy_orders, sell_orders

def get_order_status(order_id): # this function finds the order status for a specific order, a complementary function to get_open_orders()
    resp = s.get ('http://localhost:9999/v1/orders' + '/' + str(order_id))
    if resp.ok:
        order = resp.json()
        return order['status']

def main(): # function that contains the decision-making portion of the algo, can be called by the final if statement (line 88) or invoking main() or hitting the "play" butting (F5)
    tick, status = get_tick() # this function call queries the case status and establishes whether the loop will start
    ticker_list = ['CNR','RY','AC'] # list of ticker symbols that will be traded by the algo; no logic/analytics are applied, all ticker symbols are traded by this algo

    while status == 'ACTIVE': # this loop is the algo - the loop contains the set of instructions (including calls to the functions we define above) that execute our trading strategy; we want these instructions to be repeatedly executed over the duration of the case and use the "while" loop to implement this repetition - there are other types of loops that can be used, such as a "for" loop below; the loop is necessary to re-query the market to check on the current quotes which are used in the if conditions (the decision-making part of the algo)       

        for i in range(3): # for loop that repeats the following code for each ticker symbol in "tick_list"; the code is acting as a market maker for all the stocks in the case, and is dealing with each stock sequentially
            
            ticker_symbol = ticker_list[i]
            # these two lines get the data to establish the current state of affairs (my position, BBO prices) that feed into the calculations; before we decide anything we first need the data... any data that you think is important for decision-making needs to be queried FIRST (i.e. you need to gather the data before you run any calculations)
            position = get_position()
            best_bid_price, best_ask_price = get_bid_ask(ticker_symbol)
       
            if position < MAX_LONG_EXPOSURE: # "if statements are common triggers for launching orders - the order will be sent if the condition(s) are true; in this case we are identifying that we are entering a buy order ('action' = 'BUY') at the current best bid price (i.e. we are joining the bid) if we have not yet reached our maximum long exposure of 25,000; this condition is flawed/incomplete, and will cause errors... a key skill in coding is figuring out what breaks the strategy/code (i.e. there is no use in figuring out how the code works when everything goes right, the trick is finding the opposite... trial and error will be helpful, but frustrating, to find what can go wrong, which is the algo's risk - one of your jobs is to think of all the things that could go wrong, and prevent them)
                resp = s.post('http://localhost:9999/v1/orders', params = {'ticker': ticker_symbol, 'type': 'LIMIT', 'quantity': ORDER_LIMIT, 'price': best_bid_price, 'action': 'BUY'})
              
            if position > MAX_SHORT_EXPOSURE:
                resp = s.post('http://localhost:9999/v1/orders', params = {'ticker': ticker_symbol, 'type': 'LIMIT', 'quantity': ORDER_LIMIT, 'price': best_ask_price, 'action': 'SELL'})

            sleep(0.5) # pauses the code to give the passive orders a chance to trade before being cancelled; this is NOT optimal...

            s.post('http://localhost:9999/v1/commands/cancel', params = {'ticker': ticker_symbol}) # cancels any unfilled orders that were just placed in this for loop - prevents a proliferation of passive orders that can cause the position to exceed the limits; this is NOT optimal...

        tick, status = get_tick() # updates the status of the case for our "while" loop - if we do not update the status the loop will continue forever once it starts (unless an error breaks the execution)

if __name__ == '__main__': # convenience to make it easier to run the code
    main()



