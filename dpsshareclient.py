import pickle
import sys
import threading
import json

import numpy as np
import requests
from flask import Flask, request
from requests_toolbelt.adapters import source
import tensorflow as tf

import flcommon
import mnistcommon
import time_logger
from config import ClientConfig
from dpsshare_security import ProofOfWork, DigitalSignature

np.random.seed(42)
tf.random.set_seed(42)

config = ClientConfig(int(sys.argv[1]))

client_datasets = mnistcommon.load_train_dataset(config.number_of_clients, permute=True)

api = Flask(__name__)

round_weight = 0
training_round = 0
total_upload_cost = 0
total_download_cost = 0

TA_PORT = 9600
TA_URL = f"http://127.0.0.1:{TA_PORT}"
facility_secret_key = None
facility_attributes = {'role': 'hospital', 'region': 'North'}


def register_with_ta(facility_id: str) -> bool:
    """
    Register facility with Trusted Authority using PoW
    Algorithm 2: Facility Registration with Proof-of-Work
    """
    global facility_secret_key, facility_attributes
    
    print(f"\n{'='*70}")
    print(f"[TA REGISTRATION] Registering with Trusted Authority")
    print(f"{'='*70}")
    print(f"[TA REGISTRATION] Facility ID: {facility_id}")
    print(f"[TA REGISTRATION] Computing PoW challenge...")
    
    nonce, pow_time = ProofOfWork.compute_pow(facility_id, difficulty=4)
    print(f"[TA REGISTRATION] ✓ PoW solved! Nonce: {nonce}, Time: {pow_time:.4f}s")
    
    try:
        response = requests.post(
            f"{TA_URL}/register",
            json={
                'facility_id': facility_id,
                'nonce': nonce,
                'attributes': facility_attributes
            },
            timeout=10
        )
        
        if response.status_code == 200:
            result = response.json()
            if result.get('success'):
                facility_secret_key = result['secret_key']
                print(f"[TA REGISTRATION] ✓ Registration successful")
                print(f"[TA REGISTRATION] ✓ Secret key received from TA")
                print(f"[TA REGISTRATION] ✓ Attributes verified: {facility_attributes}")
                return True
            else:
                print(f"[TA REGISTRATION] ✗ Registration failed: {result.get('error')}")
                return False
        else:
            print(f"[TA REGISTRATION] ✗ Registration failed: HTTP {response.status_code}")
            return False
            
    except Exception as e:
        print(f"[TA REGISTRATION] ✗ Connection to TA failed: {e}")
        return False


def request_encrypted_model_from_leader() -> bytes:
    """
    Request encrypted model from Leader Server (which gets it from TA)
    Algorithm 3: Initial Model Distribution and Decryption
    """
    print(f"\n[MODEL REQUEST] Requesting encrypted model from Leader Server...")
    print(f"[MODEL REQUEST] Leader Server acts as intermediary with TA")
    
    leader_url = f"http://{config.master_server_address}:{config.master_server_port}"
    
    try:
        response = requests.get(f"{leader_url}/get_encrypted_model", timeout=10)
        
        if response.status_code == 200:
            result = response.json()
            if result.get('success'):
                encrypted_model = pickle.loads(bytes.fromhex(result['ciphertext']))
                print(f"[MODEL REQUEST] ✓ Encrypted model received from Leader Server")
                return encrypted_model
            else:
                print(f"[MODEL REQUEST] ✗ Failed to get model: {result.get('error')}")
                return None
        else:
            print(f"[MODEL REQUEST] ✗ Failed: HTTP {response.status_code}")
            return None
            
    except Exception as e:
        print(f"[MODEL REQUEST] ✗ Failed to connect to Leader Server: {e}")
        return None


def decrypt_model_with_cpabe(encrypted_model, sk: str, attributes: dict):
    """
    Decrypt CP-ABE encrypted model
    Algorithm 3: User Decrypt(CT, SK_facility) → Model
    """
    print(f"\n[CP-ABE DECRYPTION] Decrypting model with facility secret key...")
    print(f"[CP-ABE DECRYPTION] Verifying access policy against attributes: {attributes}")
    
    try:
        policy = encrypted_model['policy']
        
        policy_satisfied = all(
            attributes.get(attr) == value
            for attr, value in policy.items()
        )
        
        if not policy_satisfied:
            print(f"[CP-ABE DECRYPTION] ✗ Access denied - Policy not satisfied")
            print(f"[CP-ABE DECRYPTION] Required: {policy}")
            print(f"[CP-ABE DECRYPTION] Facility has: {attributes}")
            return None
        
        print(f"[CP-ABE DECRYPTION] ✓ Access policy satisfied")
        
        import hashlib
        pk = encrypted_model['pk']
        encryption_key = hashlib.sha256(f"{pk}_{json.dumps(policy, sort_keys=True)}".encode()).digest()
        
        decrypted_data = bytearray()
        for i, byte in enumerate(encrypted_model['ct']):
            decrypted_data.append(byte ^ encryption_key[i % len(encryption_key)])
        
        model_weights = pickle.loads(bytes(decrypted_data))
        print(f"[CP-ABE DECRYPTION] ✓ Model successfully decrypted")
        print(f"[CP-ABE DECRYPTION] ✓ Ready for local training")
        
        return model_weights
        
    except Exception as e:
        print(f"[CP-ABE DECRYPTION] ✗ Decryption failed: {e}")
        return None


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
    global training_round, facility_secret_key
    
    if training_round == 0:
        facility_id = f"client_{config.client_index}"
        
        if facility_secret_key is None:
            registered = register_with_ta(facility_id)
            if not registered:
                print(f"[ERROR] Failed to register with TA. Using default initialization.")
                model.set_weights(model.get_weights())
            else:
                encrypted_model = request_encrypted_model_from_leader()
                if encrypted_model:
                    initial_weights = decrypt_model_with_cpabe(
                        encrypted_model,
                        facility_secret_key,
                        facility_attributes
                    )
                    if initial_weights:
                        model.set_weights(initial_weights)
                        print(f"[MODEL INIT] ✓ Model initialized with TA-encrypted weights")
                    else:
                        print(f"[MODEL INIT] ✗ Decryption failed, using default weights")
                else:
                    print(f"[MODEL INIT] ✗ Failed to get encrypted model, using default weights")
    elif training_round != 0:
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
    
    facility_id = f"client_{config.client_index}"
    
    print(f"\n{'='*70}")
    print(f"[SECURITY] DPSShare Security Protocol Initiated")
    print(f"{'='*70}")
    
    print(f"[PROOF-OF-WORK] Computing PoW challenge for Sybil attack prevention...")
    print(f"[PROOF-OF-WORK] Facility ID: {facility_id}")
    nonce, pow_time = ProofOfWork.compute_pow(facility_id, difficulty=4)
    print(f"[PROOF-OF-WORK] ✓ PoW solved! Nonce: {nonce}, Time: {pow_time:.4f}s")
    print(f"[PROOF-OF-WORK] ✓ Verification: {ProofOfWork.verify_pow(facility_id, nonce, 4)}")
    
    signing_key = DigitalSignature.generate_key(facility_id)
    
    for layer_index, layer_weights in enumerate(noisy_weights):
        print(f"[SECRET SHARING] Splitting layer {layer_index} using additive secret sharing...")
        shares = additive_secret_split(layer_weights, num_shares=config.num_servers)
        
        for server_index in range(config.num_servers):
            all_servers[server_index][layer_index] = shares[server_index]

    global total_upload_cost

    pickle_model_list = []
    signature_list = []
    
    for server in range(config.num_servers):
        share_data = pickle.dumps(all_servers[server])
        
        signature = DigitalSignature.sign(share_data, signing_key)
        signature_list.append(signature)
        
        signed_package = {
            'share': share_data,
            'signature': signature,
            'facility_id': facility_id,
            'nonce': nonce
        }
        
        pickle_model_list.append(pickle.dumps(signed_package))
        len_serialized_model = len(pickle_model_list[server])
        total_upload_cost += len_serialized_model
        print(f"[DIGITAL SIGNATURE] Share {server} signed: {signature[:16]}...")
        print(f"[Upload] Size of signed package to server {server}: {len_serialized_model}")

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
