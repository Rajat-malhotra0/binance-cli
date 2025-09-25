from binance.client import Client


def test():
    client = Client()
    client.API_URL = 'https://testnet.binancefuture.com'
    
    try:
        symbol = ""
        exchange_info = client.futures_exchange_info()
        symbols = [s['symbol'] for s in exchange_info['symbols']
                  if s['status'] == 'TRADING']
        return symbols
    except Exception as e:
        return False


print(test())