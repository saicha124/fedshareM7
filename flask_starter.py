import ipaddress
import threading

import requests
import time
from config import LeadConfig

config = LeadConfig()

print(f"Waiting {config.delay} seconds.")
time.sleep(config.delay)


def call(client):
    print(f"Starting client {client}")
    port = config.client_base_port + client
    url = f'http://{config.client_address}:{port}/start'
    print(requests.get(url).json())


for client in range(config.number_of_clients):
    my_thread = threading.Thread(target=call, args=(client,))
    my_thread.start()
