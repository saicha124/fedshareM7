import pickle
import sys
import threading

import numpy as np
import requests
from flask import Flask, request
from requests_toolbelt.adapters import source

import time_logger
from config import ServerConfig
from dpsshare_security import ProofOfWork, DigitalSignature, ValidatorCommittee, FogNodeSecurity

config = ServerConfig(int(sys.argv[1]))

api = Flask(__name__)

training_round = 0

clients_secret = []
clients_duration = []

total_download_cost = 0
total_upload_cost = 0

validator_committee = ValidatorCommittee(num_validators=3)


def recv_thread(clients_secret, data, remote_addr):
    time_logger.server_received()

    global total_download_cost
    total_download_cost += len(data)

    print(f"\n{'='*70}")
    print(f"[FOG NODE {config.server_index}] VALIDATOR COMMITTEE PROCESSING")
    print(f"{'='*70}")
    print(f"[DOWNLOAD] Signed package from {remote_addr} received. size: {len(data)}")
    
    signed_package = pickle.loads(data)
    share_data = signed_package['share']
    signature = signed_package['signature']
    facility_id = signed_package['facility_id']
    nonce = signed_package['nonce']
    
    print(f"[VALIDATOR] Facility ID: {facility_id}")
    print(f"[VALIDATOR] Verifying PoW challenge...")
    pow_valid = ProofOfWork.verify_pow(facility_id, nonce, difficulty=4)
    print(f"[VALIDATOR] PoW verification: {'✓ PASSED' if pow_valid else '✗ FAILED'}")
    
    if not pow_valid:
        print(f"[VALIDATOR] ✗ Share rejected - Invalid PoW")
        return
    
    print(f"[VALIDATOR] Committee consensus voting initiated...")
    validation_result = validator_committee.validate_share(share_data, signature, facility_id)
    
    print(f"[VALIDATOR] Committee votes: {validation_result['total_votes']}/{validation_result['required_votes']} required")
    print(f"[VALIDATOR] Decision: {'✓ APPROVED' if validation_result['approved'] else '✗ REJECTED'}")
    print(f"[VALIDATOR] Reason: {validation_result['reason']}")
    
    if not validation_result['approved']:
        print(f"[VALIDATOR] ✗ Share rejected by committee")
        return
    
    committee_signature = validator_committee.sign_approved_share(share_data)
    print(f"[VALIDATOR] ✓ Committee signature applied: {committee_signature[:16]}...")
    
    print(f"\n[BROADCAST] Broadcasting approved share to fog node {config.server_index}")
    print(f"[BROADCAST] After validation, fog nodes assume the role of regional aggregators.")
    print(f"{'='*70}\n")
    
    secret = pickle.loads(share_data)
    clients_secret.append(secret)
    print(f"[SECRET] Secret share verified and accepted.")

    if len(clients_secret) != config.number_of_clients:
        return

    time_logger.server_start()
    
    print(f"\n{'='*70}")
    print(f"[FOG NODE {config.server_index}] REGIONAL AGGREGATOR ROLE ACTIVATED")
    print(f"{'='*70}")
    print(f"[AGGREGATION] Performing FedAvg on {len(clients_secret)} verified shares...")

    model = {}
    for layer_index in range(len(clients_secret[0])):
        alpha_list = []
        for client_index in range(config.number_of_clients):
            alpha = clients_secret[client_index][layer_index] * \
                    (config.clients_dataset_size[client_index] / config.total_dataset_size)
            alpha_list.append(alpha)
        model[layer_index] = np.array(alpha_list).sum(axis=0, dtype=np.float64)
    
    print(f"[AGGREGATION] ✓ Regional aggregation completed for {len(model)} layers")

    pickle_model = pickle.dumps(model)
    
    fog_node_id = f"fog_server_{config.server_index}"
    fog_signature = FogNodeSecurity.sign_partial_model(pickle_model, fog_node_id)
    
    signed_fog_package = {
        'partial_model': pickle_model,
        'fog_signature': fog_signature,
        'fog_node_id': fog_node_id
    }
    
    signed_package_data = pickle.dumps(signed_fog_package)
    len_dumped_model = len(signed_package_data)

    print(f"[FOG SECURITY] Signing partial aggregated model...")
    print(f"[FOG SECURITY] Fog signature: {fog_signature[:16]}...")
    print(f"[FOG SECURITY] ✓ Partial model authenticated")
    print(f"{'='*70}\n")

    time_logger.server_start_upload()

    global total_upload_cost
    total_upload_cost += len(signed_package_data)

    url = f'http://{config.master_server_address}:{config.master_server_port}/recv'
    s = requests.Session()
    new_source = source.SourceAddressAdapter(config.server_address)
    s.mount('http://', new_source)
    print(s.post(url, signed_package_data).json())

    clients_secret.clear()

    global training_round
    training_round += 1

    print(f"[UPLOAD] Sent aggregated shares to the master, size: {len_dumped_model}")

    print(f"[DOWNLOAD] Total download cost so far: {total_download_cost}")
    print(f"[UPLOAD] Total upload cost so far: {total_upload_cost}")

    print(f"********************** [ROUND] Round {training_round} completed **********************")

    time_logger.server_idle()


@api.route('/', methods=['GET'])
def health_check():
    return {"server_id": int(sys.argv[1]), "status": "healthy"}


@api.route('/recv', methods=['POST'])
def recv():
    my_thread = threading.Thread(target=recv_thread, args=(clients_secret,
                                                           request.data, request.remote_addr))
    my_thread.start()
    return {"response": "ok"}


api.run(host=config.server_address, port=int(config.server_base_port) + int(sys.argv[1]), debug=False, threaded=True)
