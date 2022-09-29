# Permission is hereby granted, free of charge, to any person obtaining
# a copy of this software and associated documentation files (the "Software"),
# to deal in the Software without restriction, including without limitation
# the rights to use, copy, modify, merge, publish, distribute, sublicense,
# and/or sell copies of the Software, and to permit persons to whom the
# Software is furnished to do so, subject to the following conditions:

# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY,
# WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR
# IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.



import time, datetime, ta, socket, json, _thread, websocket
import pandas as pd
import cfRestApiV3 as cfApi

last_time = 0
first_time = 0
minute_list = []
last_mark = 0
config = {}


def get_config():
    global config
    with open('config.txt', 'r') as f:
        config = json.loads(f.read())
        f.close()


def check_internet():  # checking if internet is available
    try:
        host = socket.gethostbyname('futures.kraken.com')  # sets up address in socket
        con = socket.create_connection((host, 80), 2)  # try to connect to address
        return True
    except Exception:  # if con trows exception, check_internet returns false
        return False


def send_auto_order(side, product_id, bid_size):  # send order function
    global config
    api_public_key = config['api_public_key']
    api_private_key = config['api_private_key']
    api_path = config['api_path']
    timeout = 20
    check_certificate = True  # when using the test environment, this must be set to "False"
    use_nonce = False  # nonce is optional
    cf_private = cfApi.cfApiMethods(api_path, timeout=timeout, apiPublicKey=api_public_key,
                                   apiPrivateKey=api_private_key, checkCertificate=check_certificate, useNonce=use_nonce)
    limit_order = {
        "orderType": "mkt",
        "symbol": product_id,
        "side": side,
        "size": bid_size,
        "reduceOnly": "false"
    }
    while not check_internet():
        print("no internet connection pausing for 30sec")
        time.sleep(30)
    result = cf_private.send_order_1(limit_order)
    return result


def ws_message(ws, message):
    global last_time
    global first_time
    global minute_list
    global last_mark
    message_json = json.loads(message)
    if message_json.get("feed", "") == "ticker":
        last_time = int(message_json["time"])
        if first_time == 0:
            first_time = last_time
            minute_list = [float(message_json["markPrice"])]
        elif first_time + 60000 < last_time:
            minute_list.append(float(message_json["markPrice"]))
            first_time += 60000
        last_mark = float(message_json["markPrice"])
    #print(message_json)


def ws_open(ws):
    global config
    product_id = config['product_id']
    ws.send('{"event":"subscribe", "feed":"ticker", "product_ids":["' + product_id + '"]}')


def ws_thread(*args):
    ws = websocket.WebSocketApp("wss://futures.kraken.com/ws/v1", on_open=ws_open, on_message=ws_message)
    ws.run_forever(ping_interval=30)


def data_generator():  # data generator function
    global last_mark
    global minute_list
    _thread.start_new_thread(ws_thread, ())
    first_run = True
    side = ""
    rise_lvl = 0
    dump_lvl = 0
    ema5_last = 0
    ema11_last = 0
    minimum_list_len = 11
    volatility = 0
    volatility_reset = 0
    time.sleep(1)  # waiting 1sec for the socket to get value
    bid = last_mark  # setting bid to current price
    while True:
        ts = time.time()
        st = datetime.datetime.fromtimestamp(ts).strftime('%H:%M:%S')
        bid1 = last_mark  # setting new bid for price side indicator
        if (time.time() * 1000) > last_time + 15000:  # after 15sec without new message restarting socket
            while not check_internet():  # making sure we have internet connection
                print("no internet connection pausing for 30sec")
                time.sleep(30)
            _thread.start_new_thread(ws_thread, ())
        if len(minute_list) > minimum_list_len:  # if we have enough data time to generate some indicators
            if not first_run:
                del dfonemin  # trying to fix: ValueError: could not broadcast input array from shape (7728,) into shape (7727,)
            else:
                first_run = False
            dfonemin = pd.DataFrame(data=minute_list)
            ema5 = ta.trend.EMAIndicator(dfonemin[0], window=5).ema_indicator()
            ema11 = ta.trend.EMAIndicator(dfonemin[0], window=11).ema_indicator()
            ema5_last = ema5.get(ema5.last_valid_index())
            ema11_last = ema11.get(ema11.last_valid_index())
            minimum_list_len += 1
        if bid1 > bid:
            percentage = ((float(bid1) - float(bid)) / float(bid1)) * 100
            bid = bid1
            rise_lvl += percentage
            if dump_lvl > 0:
                dump_lvl -= percentage
                if dump_lvl < 0:
                    dump_lvl = 0
            if rise_lvl > .1:
                rise_lvl = 0
                side = "up"
                volatility += 1
                volatility_reset = 0
        elif bid1 < bid:
            percentage = ((float(bid) - float(bid1)) / float(bid)) * 100
            bid = bid1
            dump_lvl += percentage
            if rise_lvl > 0:
                rise_lvl -= percentage
                if rise_lvl < 0:
                    rise_lvl = 0
            if dump_lvl > .1:
                dump_lvl = 0
                side = "down"
                volatility -= 1
                volatility_reset = 0
        else:
            if volatility != 0:
                volatility_reset += 1
            if volatility_reset > 60:
                volatility_reset = 0
                if volatility > 0:
                    volatility -= 1
                if volatility < 0:
                    volatility += 1
        data_dict = {'time': st, 'minute_list': len(minute_list), 'volatility': volatility,
            'price': bid1, 'side': side, 'ema5': ema5_last, 'ema11': ema11_last}
        yield data_dict


def main():
    get_config()
    global config
    data_dict = data_generator()
    time.sleep(1)
    long_setup = False
    short_setup = False
    above = False
    below = False
    time_val = -1
    product_id = config['product_id']
    bid_size = config['bid_size']
    preferred_side = config['preferred_side']
    entry_price = config['entry_price']
    stop_loss = config['stop_loss']
    adj_trigger = config['adj_trigger']
    adj_trigger_value = config['adj_trigger_value']
    if config['action'] == 'now':
        if preferred_side == 'short':
            short_setup = True
        elif preferred_side == 'long':
            long_setup = True
    else:
        mydict = next(data_dict)
        if adj_trigger > 0:
            ts = time.time()
            time_val = int(datetime.datetime.fromtimestamp(ts).strftime('%M'))
        if mydict['price'] > entry_price:
            above = True
        else:
            below = True
    while True:
        mydict = next(data_dict)
        if long_setup and mydict['side'] == 'up':
            loop_b = True
            ts = time.time()
            st = datetime.datetime.fromtimestamp(ts).strftime('%H:%M:%S')
            breakeven = False
            trailing = False
            lockprofit = False
            bid = mydict['price']
            result = send_auto_order("buy", product_id, bid_size)
            print("buy  " + str(bid_size) + " entry " + str(bid) + " time " + st)
            print(mydict)
            entrybid = bid
            stopprice = entrybid - (stop_loss * entrybid)
            while loop_b:
                time.sleep(.25)
                mydict = next(data_dict)
                ts = time.time()
                st = datetime.datetime.fromtimestamp(ts).strftime('%H:%M:%S')
                bid = mydict['price']
                if time_val != -1:
                    st2 = int(datetime.datetime.fromtimestamp(ts).strftime('%M'))
                    if st2 > time_val:
                        time_val = st2
                        entry_price += adj_trigger_value
                    elif st2 == 0 and time_val == 59:
                        time_val = st2
                        entry_price += adj_trigger_value
                if trailing:
                    if lockprofit:
                        if (bid - (.006 * entrybid)) > stopprice:
                            stopprice = bid - (.006 * entrybid)
                        if mydict['minute_list'] > 11:
                            if mydict['ema5'] < mydict['ema11']:
                                stopprice = bid + 20
                                print("ema stop")
                                print(mydict)
                    else:
                        if (bid - (.0035 * entrybid)) > stopprice:
                            stopprice = (bid - (.0035 * entrybid))
                            if (entrybid + (.016 * entrybid)) < stopprice:
                                lockprofit = True
                                print("lockprofit " + str(stopprice) + " time " + st)
                                print(mydict)
                if bid > (entrybid + (.009 * entrybid)) and not breakeven:
                    stopprice = entrybid + (.007 * entrybid)
                    breakeven = True
                    print("breakeven " + str(stopprice) + " time " + st)
                    print(mydict)
                elif bid > (entrybid + (.011 * entrybid)) and not trailing:
                    stopprice = entrybid + (.0076 * entrybid)
                    trailing = True
                    print("trailing " + str(stopprice) + " time " + st)
                    print(mydict)
                else:
                    if bid < stopprice:
                        result = send_auto_order("sell", product_id, bid_size)
                        print(mydict)
                        preferred_side = 'none'
                        if breakeven:
                            if time_val != -1:
                                preferred_side = 'long'
                                above = True
                                below = False
                            print(st + " : win, entry was :" + str(entrybid) + " close was :" + str(bid))
                            print("-------------------------------------------------------------------")
                        else:
                            print(st + " : lose, entry was :" + str(entrybid) + " close was :" + str(bid))
                            print("-------------------------------------------------------------------")
                        loop_b = False
                        long_setup = False

        elif short_setup and mydict['side'] == 'down':
            ts = time.time()
            st = datetime.datetime.fromtimestamp(ts).strftime('%H:%M:%S')
            loop_b = True
            breakeven = False
            trailing = False
            lockprofit = False
            bid = mydict['price']
            result = send_auto_order("sell", product_id, bid_size)
            print("sell  " + str(bid_size) + " entry " + str(bid) + " time " + st)
            print(mydict)
            entrybid = bid
            stopprice = entrybid + (stop_loss * entrybid)
            while loop_b:
                time.sleep(.25)
                mydict = next(data_dict)
                ts = time.time()
                st = datetime.datetime.fromtimestamp(ts).strftime('%H:%M:%S')
                bid = mydict['price']
                if time_val != -1:
                    st2 = int(datetime.datetime.fromtimestamp(ts).strftime('%M'))
                    if st2 > time_val:
                        time_val = st2
                        entry_price += adj_trigger_value
                    elif st2 == 0 and time_val == 59:
                        time_val = st2
                        entry_price += adj_trigger_value
                if trailing:
                    if lockprofit:
                        if (bid + (.006 * entrybid)) < stopprice:
                            stopprice = bid + (.006 * entrybid)
                        if mydict['minute_list'] > 11:
                            if mydict['ema5'] > mydict['ema11']:
                                stopprice = bid - 20
                                print("ema stop")
                                print(mydict)
                    else:
                        if (bid + (.0035 * entrybid)) < stopprice:
                            stopprice = (bid + (.0035 * entrybid))
                            if (entrybid - (.016 * entrybid)) > stopprice:
                                lockprofit = True
                                print("lockprofit " + str(stopprice) + " time " + st)
                                print(mydict)
                if bid < (entrybid - (.009 * entrybid)) and not breakeven:
                    stopprice = entrybid - (.007 * entrybid)
                    breakeven = True
                    print("breakeven " + str(stopprice) + " time " + st)
                    print(mydict)
                elif bid < (entrybid - (.011 * entrybid)) and not trailing:
                    stopprice = entrybid - (.0076 * entrybid)
                    trailing = True
                    print("trailing " + str(stopprice) + " time " + st)
                    print(mydict)
                else:
                    if bid > stopprice:
                        result = send_auto_order("buy", product_id, bid_size)
                        print(mydict)
                        preferred_side = 'none'
                        if breakeven:
                            if time_val != -1:
                                preferred_side = 'short'
                                below = True
                                above = False
                            print(st + " : win, entry was :" + str(entrybid) + " close was :" + str(bid))
                            print("-------------------------------------------------------------------")
                        else:
                            print(st + " : lose, entry was :" + str(entrybid) + " close was :" + str(bid))
                            print("-------------------------------------------------------------------")
                        loop_b = False
                        short_setup = False
        elif not short_setup and not long_setup:  # trying to find a trade setup
            if time_val != -1:
                ts = time.time()
                st = int(datetime.datetime.fromtimestamp(ts).strftime('%M'))
                if st > time_val:
                    time_val = st
                    entry_price += adj_trigger_value
                elif st == 0 and time_val == 59:
                    time_val = st
                    entry_price += adj_trigger_value
                    print(mydict)
                    print('current entry price: ' + str(entry_price))
            if preferred_side == 'short':
                if mydict['price'] > entry_price and below:
                    short_setup = True
                    print(mydict)
                    print('shortsetup')
                if mydict['price'] < entry_price and above:
                    short_setup = True
                    print(mydict)
                    print('shortsetup')
            if preferred_side == 'long':
                if mydict['price'] < entry_price and above:
                    long_setup = True
                    print(mydict)
                    print('longsetup')
                if mydict['price'] > entry_price and below:
                    long_setup = True
                    print(mydict)
                    print('longsetup')
        time.sleep(.25)


main()
