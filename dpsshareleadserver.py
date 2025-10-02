import pickle
import threading
import time

import numpy as np
from flask import Flask, request

import flcommon
import time_logger
from config import LeadConfig

api = Flask(__name__)

config = LeadConfig()

run_start_time = time.time()

total_upload_cost = 0
total_download_cost = 0

servers_secret = []


def additive_reconstruct(shares):
    """
    Reconstruct secret from additive secret shares by summing them.
    shares: list of share arrays
    """
    reconstructed = np.sum(shares, axis=0).astype(np.float64)
    return reconstructed


@api.route('/', methods=['GET'])
def health_check():
    return {"server_id": "lead", "status": "healthy"}


@api.route('/recv', methods=['POST'])
def recv():
    my_thread = threading.Thread(target=recv_thread, args=(servers_secret, request.data, request.remote_addr))
    my_thread.start()
    return {"response": "ok"}


def recv_thread(servers_secret, data, remote_addr):
    global total_download_cost
    total_download_cost += len(data)

    time_logger.lead_server_received()

    print(f"[DOWNLOAD] Secret share of {remote_addr} received. size: {len(data)}")

    secret = pickle.loads(data)
    servers_secret.append(secret)

    print(f"[SECRET] Secret share opened successfully.")

    if len(servers_secret) != config.num_servers:
        return {"response": "ok"}

    time_logger.lead_server_start()

    print("[RECONSTRUCTION] Reconstructing secret using additive secret sharing...")
    
    dpsshare_weights = []
    
    for layer_index in range(len(servers_secret[0])):
        shares = []
        for server_index in range(config.num_servers):
            shares.append(servers_secret[server_index][layer_index])
        
        reconstructed_layer = additive_reconstruct(shares)
        dpsshare_weights.append(reconstructed_layer)

    servers_secret.clear()

    pickle_model = pickle.dumps(dpsshare_weights)
    flcommon.broadcast_to_clients(pickle_model, config, lead_server=True)

    global total_upload_cost
    total_upload_cost += len(pickle_model) * config.number_of_clients

    print(f"[DOWNLOAD] Total download cost so far: {total_download_cost}")
    print(f"[UPLOAD] Total upload cost so far: {total_upload_cost}")

    print("[AGGREGATION] Model aggregation with additive secret sharing completed successfully.")

    time_logger.lead_server_idle()


api.run(host=config.master_server_address, port=int(config.master_server_port), debug=False, threaded=True)
