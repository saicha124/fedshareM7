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


def shamir_reconstruct(shares, threshold):
    """
    Reconstruct secret from Shamir Secret Shares using Lagrange interpolation.
    shares: list of (x, y) pairs where x is the share index and y is the share value
    threshold: number of shares needed (unused but kept for compatibility)
    """
    shape = shares[0][1].shape
    flat_shares = [(x, y.flatten().astype(np.float64)) for x, y in shares]
    
    reconstructed = np.zeros_like(flat_shares[0][1])
    
    for idx in range(len(reconstructed)):
        points = [(x, y[idx]) for x, y in flat_shares]
        
        result = 0.0
        for i, (xi, yi) in enumerate(points):
            term = yi
            for j, (xj, _) in enumerate(points):
                if i != j:
                    term *= (0 - xj) / (xi - xj)
            result += term
        
        reconstructed[idx] = result
    
    return reconstructed.reshape(shape)


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

    print("[RECONSTRUCTION] Reconstructing secret using Shamir Secret Sharing...")
    
    dpsshare_weights = []
    
    for layer_index in range(len(servers_secret[0])):
        shares_with_indices = []
        for server_index in range(config.num_servers):
            x = server_index + 1
            y = servers_secret[server_index][layer_index]
            shares_with_indices.append((x, y))
        
        reconstructed_layer = shamir_reconstruct(shares_with_indices, threshold=config.num_servers)
        dpsshare_weights.append(reconstructed_layer)

    servers_secret.clear()

    pickle_model = pickle.dumps(dpsshare_weights)
    flcommon.broadcast_to_clients(pickle_model, config, lead_server=True)

    global total_upload_cost
    total_upload_cost += len(pickle_model) * config.number_of_clients

    print(f"[DOWNLOAD] Total download cost so far: {total_download_cost}")
    print(f"[UPLOAD] Total upload cost so far: {total_upload_cost}")

    print("[AGGREGATION] Model aggregation with Shamir reconstruction completed successfully.")

    time_logger.lead_server_idle()


api.run(host=config.master_server_address, port=int(config.master_server_port), debug=False, threaded=True)
