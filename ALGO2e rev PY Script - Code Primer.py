# indentation in Python is functional (i.e. it is an instruction to Python) and not a matter of style
# functions, if statements, loops, are defined by indentation (other languages, like VBA or R use explicit code to define clause)
# all of the lines of code that start at the left margin (i.e. column 1) will be read/run by Python when you run the file (hit F5 or the sideways triangle button under "Source"), all the lines that are indented to the right of the first column will be read/run by Python if the clause containing the lines are activated (depending on the clause, this would require calling a function, a true "if" statement, continuing "while" loop)
# all lines in a clause at the same level of indentation are considered to be in that clause, other levels of indentation are in different clauses
# for example:

#This level of indentation could define function
    #This level of indentation is inside the function
    #This level of indentation is inside the function
    #This level of indentation is inside the function and contains if satement A
        #This level of indentation is inside if statement A, which is inside the function
        #This level of indentation is inside if statement A, which is inside the function
    #This level of indentation is inside the function (but not if statement A - the indentation moving to the right of the indentation in the previous line ends the if statement)
    #This level of indentation is inside the function and contains if statement B
        #This level of indentation is inside if statement B, which is inside the function
        #This level of indentation is inside if statement B, which is inside the function
    #This level of indentation is inside the function (but not if statement B - the indentation moving to the right of the indentation in the previous line ends the if statement)
    
#This level of indentation could define another function (and end the preceding function)

import requests # loads the REQUESTS package, allows us to use the get, post, and Session functions
from time import sleep # loads the SLEEP function from the TIME package

s = requests.Session() # assigns the SESSION() function from REQUESTS to the variable "s"
s.headers.update({'X-API-key': 'W9OPB2TD'}) # assigns the API key "W9OPB2TD" to the header of "s", so every message we send to RIT contains the API key ; you will use the API key for your RIT

MAX_LONG_EXPOSURE = 25000 # assign the variable MAX_LONG_EXPOSURE a value of 25,000 - the maximum number of shares I want to be long at any point in time
MAX_SHORT_EXPOSURE = -25000 # assign the variable MAX_SHORT_EXPOSURE a value of -25,000 - the maximum number of shares I want to be short at any point in time
ORDER_LIMIT = 500 # assign the variable ORDER_LIMIT a value of 500 - this will set the size of the orders entereed into the market

def get_tick_status(): # defines a function called "get_tick_status" when defining a function the brackets () and colon : must be included. Any values you send to the function "get_tick_status" would be stored in the variable names in the brackets, which we will not use in this function. The colon tells Python that the definition statement is done and the function's code is next
    resp = s.get('http://localhost:9999/v1/case') # uses the "get" function from REQUESTS, in combination with the variable "s" - hence the "s.get" - to send a request (i.e. get information from) to http://localhost:9999/v1/case and store the information that comes back in the variable "resp"
    if resp.ok: # uses the IF statement and the "ok" function from REQUESTS to check IF the status code of the variable "resp" is ok (meaning the status code is 200); if the status code is 200, go to the next line, otherwise skip 
        case = resp.json() # uses the "json" function from REQUESTS to parse or reformat the data in "resp" using the JSON format, then storing the parsed/reformatted data in the variable "case"
        return case['tick'], case['status'] # return two separate pieces of information, separated by commas, to the variables that called "get_tick_status" - see line 47 - the variable "case" contains a "dictionary" of variables, each of which has a "key" (or name) and a value; this line is returning the value of the variable called "tick" and the value of the variable called "status" from the dictionary called "case"; the value of case['tick'] will be assigned to the variable "tick" on line 47, the value of case['status'] will be assigned to the variable "status" on line 47

def get_bid_ask(ticker): # defines a function called "get_bid_ask" that expects a piece of information that is assigned the variable name "ticker" which is used inside the function "get_bid_ask". The value of ticker comes from the value in the brackets of the function call on line 94, which is the value contained in "ticker_symbol"
    payload = {'ticker': ticker} # assigns the value of "ticker" to the key (or name) "ticker" in the dictionary "payload" - note the curly brackets surrounding the dictionary
    resp = s.get ('http://localhost:9999/v1/securities/book', params = payload) # attaches the dictionary "payload" to the parameters ("params") that are included in the "get" request sent to RIT; in this case "params" includes the ticker symbol that tells RIT which order book to retrieve
    if resp.ok:
        book = resp.json() # stores the parsed data from "resp" in a variable named "book"; "book" is a list that contains two lists (one called "bids" and one called "asks") - similar to a folder called "book" that has two sub-folders, one called "bids" and the other called "asks" - and each of the "bids" and "asks" lists are made up of a list of items, with each item in the list being a dictionary that contains the information for each order in the order book
        bid_side_book = book['bids'] # creates a new list called "bid_side_book" composed of all the items/dictionaries from the "bids" list in "book"
        ask_side_book = book['asks'] # creates a new list called "ask_side_book" composed of all the items/dictionaries from the "asks" list in "book"
        
        bid_prices_book = [item["price"] for item in bid_side_book] # assigns the list "bid_prices_book" the "price" values for all bids in bid_side_book
        ask_prices_book = [item['price'] for item in ask_side_book] # assigns the list "ask_prices_book" the "price" values for all asks in ask_side_book
        
        best_bid_price_fn = bid_prices_book[0] # assigns the variable "best_bid_price_fn" the value of the first item in the "bid_prices_book" list (this is the highest bid price, or the "top of the book"; note that counting in Python starts at 0, so the first item in a list is item 0, the second item in a list is item 1, the third item in a list is item 2, etc. 
        best_ask_price_fn = ask_prices_book[0] # assigns the variable "best_ask_price_fn" the value of the first item in the "ask_prices_book" list (this is the lowest ask price, or the "top of the book")
  
        return best_bid_price_fn, best_ask_price_fn # returns the values from the function to the variables on line 94: the value of "best_bid_price_fn" will be assigned to variable "best_bid_price" on line 94, the value of "best_ask_price_fn" will be assigned to variable "best_ask_price" on line 94

def get_time_sales(ticker):
    payload = {'ticker': ticker}
    resp = s.get ('http://localhost:9999/v1/securities/tas', params = payload)
    if resp.ok:
        book = resp.json()
        time_sales_book = [item["quantity"] for item in book]
        return time_sales_book # returns the list "time_sales_book"; the variable that is assigned this value when calling the function must be able to hold a list of values

def get_position():
    resp = s.get ('http://localhost:9999/v1/securities')
    if resp.ok:
        book = resp.json()
        return abs(book[0]['position']) + abs(book[1]['position']) + abs(book[2]['position']) # sum of absolute position values for all three tradeable stocks; alternatively, can include a ticker symbol in the query to return the data for a particular stock

def get_open_orders(ticker):
    payload = {'ticker': ticker}
    resp = s.get ('http://localhost:9999/v1/orders', params = payload)
    if resp.ok:
        orders = resp.json()
        buy_orders = [item for item in orders if item["action"] == "BUY"] # creates a list in "buy_orders" of all buy orders -> for each dictionary in the list that has a value of "BUY" for the "action" key
        sell_orders = [item for item in orders if item["action"] == "SELL"] # creates a list in "buy_orders" of all buy orders -> for each dictionary in the list that has a value of "SELL" for the "action" key
        return buy_orders, sell_orders # returns two lists of dictionaries, the variables being assigned these value must be able to hold lists of dictionaries

def get_order_status(order_id):
    resp = s.get ('http://localhost:9999/v1/orders' + '/' + str(order_id)) # requests the order details for a specific order defined by "order_id" - each order entered into the market has a unique ID
    if resp.ok:
        order = resp.json()
        return order['status'] # returns the status of "order_id" - either "OPEN", "CANCELLED", or "TRANSACTED"


def main():
    tick, status = get_tick_status() # calls the function "get_tick_status" - the brackets must be included when calling the function, and the brackets are empty because no information is being sent to "get_tick_status" - and assigns the first piece of information returned by "get_tick_status" to "tick" and the second piece of information returned by "get_tick_status" to "status"
    ticker_list = ['CNR','RY','AC'] # creates a list of ticker symbols that are traded in the case which will be cycled in the for loop below

    while status == 'ACTIVE': # continues to loop as long as (or "while") the value of the variable "status" is "ACTIVE" - when checking the equality (==) the test is case sensitive (i.e. "ACTIVE" is not the same as "active" or "Active" or "aCtive", etc.); in Python, "==" checks for equality, "=" assigns a value; "!=" checks for not-equal-to     

        for i in range(3): # a loop that lasts for a specific number of iterations; the range() function will count starting at 0, but excluding the last number (the number 3 in this example); the variable "i" will take on the values 0, 1, 2 and then the loop will ext
            
            ticker_symbol = ticker_list[i] # assigns the "ith" item in ticker_list to the variable "ticker_symbol"; when i = 0, ticker_list[0] = 'CNR', for example
            position = get_position() # calls the get_position() function and assigns the return value to the variable "position"; note that this is the total position overall, not the position for ticker_symbol
            best_bid_price, best_ask_price = get_bid_ask(ticker_symbol) # calls the get_bid_ask() function to find the best bid and ask prices for ticker_symbol
       
            if position < MAX_LONG_EXPOSURE: # if statement that checks if the value in "position" is less than MAX_LONG_EXPOSURE, if the condition is true, goes to the next indented line; if the condition is not true, goes to the next line at the same level of indentation (in this example, the "elif" statement)
                resp = s.post('http://localhost:9999/v1/orders', params = {'ticker': ticker_symbol, 'type': 'LIMIT', 'quantity': ORDER_LIMIT, 'price': best_bid_price, 'action': 'BUY'}) # uses the "post" function from "REQUESTS" in conjunction with "s" - hence the "s.post" - to send a message (or "post" a message) to RIT; this is the trade message that enters an order in RIT. The message includes the destination where the message is being sent ("http://localhost:9999/v1/orders") and a dictionary of parameters ("params") with necessary information about the order: the key/name for the ticker symbol for the order is "ticker" and the value is the variable "ticker_symbold", the type of order (Market or Limit) key/name is "type" and the value is "LIMIT" (note: all caps), the number of shares in the order key/name is "quantity" and the value is the variable "ORDER_LIMIT", the limit price for the order (all limit orders require a limit price) key/name is "price" and the value is the variable "best_bid_price", and the direction of the order (buy or sell) key/name is "action" and the value is "BUY" (selling a long position and shorting both use "SELL"); note the use of brackets - the "post" function encloses its inputs with round brackets () and the dictionary "params", which is an input into "post", encloses its inputs with curly brackets {}; RIT sends back a response (including the status code) when the message is received by the RIT server, which must be assigned to a variable name (in this example the variable "resp") or an error will result
              
            if position > MAX_SHORT_EXPOSURE:
                resp = s.post('http://localhost:9999/v1/orders', params = {'ticker': ticker_symbol, 'type': 'LIMIT', 'quantity': ORDER_LIMIT, 'price': best_ask_price, 'action': 'SELL'})

            sleep(0.5) # uses the "sleep" function to pause for half a second (0.5 seconds) - i.e. Python waits at this line for half a second and then proceeds with the next line of code

            s.post('http://localhost:9999/v1/commands/cancel', params = {'ticker': ticker_symbol}) # use the "post" function from "REQUESTS", in conjunction with "s" - hence the "s.post" - to send a message to the RIT server to cancel all outstanding orders that match the criteria in "params"; in this case, cancel all orders that match the ticker symbol in "ticker_symbol"

        tick, status = get_tick_status() # calls the function "get_tick_status" to update the value of "status" inside the "while" loop

if __name__ == '__main__': # "if" statement that check if the embedded/reserved variable "__name__" is equal to "__main__", which is always true
    main() # calls the "main" function; since the if statement is always true, this means you can call your "main" function by running all of the code in the window using the Run File command (pressing sideways triange butting or F5); since all lines of the file are read by Python before the "main" function is called, any changes in the code are incorporated



