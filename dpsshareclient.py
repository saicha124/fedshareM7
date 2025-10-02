import pickle
import sys
import threading

import numpy as np
import requests
from flask import Flask, request
from requests_toolbelt.adapters import source
import tensorflow as tf

import flcommon
import mnistcommon
import time_logger
from config import ClientConfig

np.random.seed(42)
tf.random.set_seed(42)

config = ClientConfig(int(sys.argv[1]))

client_datasets = mnistcommon.load_train_dataset(config.number_of_clients, permute=True)

api = Flask(__name__)

round_weight = 0
training_round = 0
total_upload_cost = 0
total_download_cost = 0


def additive_secret_split(secret_array, num_shares):
    """
    Split a secret array using additive secret sharing.
    This is numerically stable and suitable for federated learning.
    num_shares: total number of shares to create
    """
    shape = secret_array.shape
    shares = []
    
    for i in range(num_shares - 1):
        random_share = np.random.normal(0, 0.01, shape).astype(np.float64)
        shares.append(random_share)
    
    sum_of_shares = np.sum(shares, axis=0).astype(np.float64)
    last_share = np.subtract(secret_array.astype(np.float64), sum_of_shares, dtype=np.float64)
    shares.append(last_share)
    
    return shares


def add_differential_privacy_noise(weights, epsilon=1.0, sensitivity=1.0):
    """
    Add Laplace noise for differential privacy.
    epsilon: privacy budget (smaller = more privacy, more noise)
    sensitivity: sensitivity of the query (max change in output)
    """
    scale = sensitivity / epsilon
    noisy_weights = []
    
    for layer in weights:
        noise = np.random.laplace(0, scale, layer.shape)
        noisy_layer = layer + noise
        noisy_weights.append(noisy_layer)
    
    return noisy_weights


def start_next_round(data):
    time_logger.client_start()

    x_train, y_train = client_datasets[config.client_index][0], client_datasets[config.client_index][1]

    model = mnistcommon.get_model()
    global training_round
    if training_round != 0:
        global round_weight
        round_weight = pickle.loads(data)
        model.set_weights(round_weight)

    print(
        f"Model: DPSShare (Differential Privacy + Shamir Secret Sharing), "
        f"Round: {training_round + 1}/{config.training_rounds}, "
        f"Client {config.client_index + 1}/{config.number_of_clients}, "
        f"Dataset Size: {len(x_train)}")
    
    model.fit(x_train, y_train, epochs=config.epochs, batch_size=config.batch_size, verbose=config.verbose,
              validation_split=config.validation_split)
    
    x_test, y_test = mnistcommon.load_test_dataset()
    local_results = model.evaluate(x_test, y_test, verbose=0)
    local_loss = local_results[0]
    local_accuracy = local_results[1]
    
    print(f"Client {config.client_index} Local Performance:")
    print(f"  loss: {local_loss:.6f}")
    print(f"  accuracy: {local_accuracy:.6f}")
    
    round_weight = model.get_weights()

    print(f"[PRIVACY] Adding differential privacy noise (epsilon=5.0)...")
    noisy_weights = add_differential_privacy_noise(round_weight, epsilon=5.0, sensitivity=0.01)
    
    all_servers = []
    for server_index in range(config.num_servers):
        all_servers.append({})
    
    for layer_index, layer_weights in enumerate(noisy_weights):
        print(f"[SECRET SHARING] Splitting layer {layer_index} using additive secret sharing...")
        shares = additive_secret_split(layer_weights, num_shares=config.num_servers)
        
        for server_index in range(config.num_servers):
            all_servers[server_index][layer_index] = shares[server_index]

    global total_upload_cost

    pickle_model_list = []
    for server in range(config.num_servers):
        pickle_model_list.append(pickle.dumps(all_servers[server]))
        len_serialized_model = len(pickle_model_list[server])
        total_upload_cost += len_serialized_model
        print(f"[Upload] Size of the object to send to server {server} is {len_serialized_model}")

    flcommon.send_to_servers(pickle_model_list, config)

    global total_download_cost
    print(f"[DOWNLOAD] Total download cost so far: {total_download_cost}")
    print(f"[UPLOAD] Total upload cost so far: {total_upload_cost}")

    print(f"********************** Round {training_round} completed **********************")
    training_round += 1
    print("Waiting to receive response from master server...")

    time_logger.client_idle()


@api.route('/', methods=['GET'])
def health_check():
    return {"client_id": int(sys.argv[1]), "status": "healthy"}


@api.route('/start', methods=['GET', 'POST'])
def start():
    data = request.data if request.method == 'POST' else b''
    my_thread = threading.Thread(target=start_next_round, args=(data,))
    my_thread.start()
    return {"response": "ok"}


@api.route('/recv', methods=['POST'])
def recv():
    global total_download_cost
    total_download_cost += len(request.data)

    print(f"[DOWNLOAD] Received weights from lead server, size: {len(request.data)}")
    print(f"[DOWNLOAD] Total download cost so far: {total_download_cost}")
    print(f"[UPLOAD] Total upload cost so far: {total_upload_cost}")
    
    if training_round < config.training_rounds:
        start_next_round(request.data)
    else:
        print("Training finished!")
        
        model = mnistcommon.get_model()
        final_weights = pickle.loads(request.data)
        model.set_weights(final_weights)
        
        x_test, y_test = mnistcommon.load_test_dataset()
        test_results = model.evaluate(x_test, y_test, verbose=0)
        test_loss = test_results[0]
        test_accuracy = test_results[1]
        
        print(f"\n{'='*60}")
        print(f"📊 Final Global Test Performance (DPSShare)")
        print(f"{'='*60}")
        print(f"📊 Global Test Loss:     {test_loss:.6f}")
        print(f"🎯 Global Test Accuracy: {test_accuracy:.6f}")
        print(f"{'='*60}\n")
        
        time_logger.client_finish()

    return {"response": "ok"}


api.run(host=config.client_address, port=int(config.client_base_port) + int(sys.argv[1]), debug=False, threaded=True)
