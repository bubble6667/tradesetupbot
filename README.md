Intro -

This is a trading helper, basicaly this program will automate getting in and out of posistion 
using the Kraken Futures trading platform, if you want to use it on Regular Kraken you'd have to
modify some value in the code, the JSON key are different.. along with some url's

Setup - 

First you'll need to insert your API public and private key in the config file where specified, 
with that your almost good to start trading just need to understand how to use it

Usage -

So first you'll need to setup a pairing that you want to trade with, in the config.txt file the 
defaul is eth/usd, called PI_ETHUSD, if you want to trade bitcoin juste change that value to 
PI_XBTUSD, so this program will allow you to trade 2 different ways, if you use the value "now" 
for the "action" key value in the config file the bot will take position directly, btw you'll have
to specify a prefered_side value that would be "short" or "long" so if you have a prefered_side 
value and "now" for "action" the bot will automaticaly take position(after the market moves in the
way of your prefered position by 0.1%). The other way will trigger after a price is attained, 
to use it that way you'll have to remove "now" from the value of "action" and leave it empty, 
like so "". In this case the trigger will be the "entry_price" value, change it accordingly, the 
"bid_size" value will be size of the bid the bot will take, default is 50.

I'll be uploading a video to explain howto use it on youtube soon !
