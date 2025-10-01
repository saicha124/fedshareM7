import pickle
import threading

import numpy as np
from flask import Flask, request

import flcommon
import time_logger
from config import FedAvgServerConfig

api = Flask(__name__)

config = FedAvgServerConfig()

clients_secret = []
aggregation_lock = threading.Lock()

total_download_cost = 0
total_upload_cost = 0


@api.route('/recv', methods=['POST'])
def recv():
    my_thread = threading.Thread(target=recv_thread, args=(request.data, request.remote_addr, clients_secret))
    my_thread.start()
    return {"response": "ok"}


def recv_thread(data, address, clients_secret: list):
    time_logger.server_received()

    len_joined_data = len(data)
    print(f"[DOWNLOAD] Secret of {address} received. size: {len_joined_data}")

    global total_download_cost
    total_download_cost += len_joined_data

    secret = pickle.loads(data)
    
    # Critical section: protect shared state with lock
    with aggregation_lock:
        clients_secret.append(secret)
        
        print(f"[SECRET] Secret received successfully. Total received: {len(clients_secret)}/{config.number_of_clients}")

        if len(clients_secret) != config.number_of_clients:
            return

        time_logger.server_start()
        
        # Calculate correct normalization weights
        num_participating_clients = len(clients_secret)
        participating_dataset_sizes = config.clients_dataset_size[:num_participating_clients]
        total_participating_size = sum(participating_dataset_sizes)
        
        # Compute normalized weights that sum to 1.0
        normalized_weights = [size / total_participating_size for size in participating_dataset_sizes]
        
        # Log aggregation weights for debugging
        print(f"FedAvg Aggregation Details:")
        print(f"  Participating clients: {num_participating_clients}")
        print(f"  Dataset sizes: {participating_dataset_sizes}")
        print(f"  Total size: {total_participating_size}")
        print(f"  Normalized weights: {normalized_weights}")
        print(f"  Weights sum: {sum(normalized_weights):.6f}")
        
        # Perform weighted aggregation
        model = {}
        for layer_index in range(len(clients_secret[0])):
            alpha_list = []
            for client_index in range(num_participating_clients):
                alpha = clients_secret[client_index][layer_index] * normalized_weights[client_index]
                alpha_list.append(alpha)
            model[layer_index] = np.array(alpha_list).sum(axis=0, dtype=np.float32)

        # Convert dictionary back to list for Keras model.set_weights()
        model_weights_list = [model[i] for i in range(len(model))]
        
        clients_secret.clear()
        pickle_model = pickle.dumps(model_weights_list)
        flcommon.broadcast_to_clients(pickle_model, config, False)

        global total_upload_cost
        total_upload_cost += len(pickle_model) * config.number_of_clients

        print(f"[DOWNLOAD] Total download cost so far: {total_download_cost}")
        print(f"[UPLOAD] Total upload cost so far: {total_upload_cost}")

        print(f"********************** [ROUND] Round completed **********************")
        
    time_logger.server_idle()


api.run(host=config.server_address, port=config.fedavg_server_port, debug=False, threaded=True, use_reloader=False)
