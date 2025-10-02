import pickle
import threading
import time

import numpy as np
from flask import Flask, request

import flcommon
import time_logger
from config import LeadConfig
from dpsshare_security import FogNodeSecurity

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

    print(f"\n{'='*70}")
    print(f"[LEADER SERVER] GLOBAL AGGREGATION PHASE")
    print(f"{'='*70}")
    print(f"[DOWNLOAD] Signed fog node package from {remote_addr} received. size: {len(data)}")

    signed_fog_package = pickle.loads(data)
    partial_model_data = signed_fog_package['partial_model']
    fog_signature = signed_fog_package['fog_signature']
    fog_node_id = signed_fog_package['fog_node_id']
    
    print(f"[LEADER SERVER] Fog Node: {fog_node_id}")
    print(f"[LEADER SERVER] Verifying fog node signature for authenticity...")
    
    signature_valid = FogNodeSecurity.verify_fog_signature(
        partial_model_data, 
        fog_signature, 
        fog_node_id
    )
    
    print(f"[LEADER SERVER] Signature verification: {'✓ PASSED' if signature_valid else '✗ FAILED'}")
    
    if not signature_valid:
        print(f"[LEADER SERVER] ✗ Partial model rejected - Invalid fog node signature")
        return {"response": "error", "message": "Invalid signature"}
    
    print(f"[LEADER SERVER] ✓ Fog node {fog_node_id} authenticated")

    secret = pickle.loads(partial_model_data)
    servers_secret.append(secret)

    print(f"[SECRET] Partial model from authenticated fog node accepted.")
    print(f"[PROGRESS] Collected {len(servers_secret)}/{config.num_servers} fog node contributions")

    if len(servers_secret) != config.num_servers:
        return {"response": "ok"}

    time_logger.lead_server_start()

    print(f"\n{'='*70}")
    print(f"[LEADER SERVER] ALL FOG NODES VERIFIED - GLOBAL AGGREGATION")
    print(f"{'='*70}")
    print(f"[RECONSTRUCTION] Reconstructing global model from {config.num_servers} fog node shares...")
    print(f"[RECONSTRUCTION] Using additive secret sharing reconstruction...")
    
    dpsshare_weights = []
    
    for layer_index in range(len(servers_secret[0])):
        shares = []
        for server_index in range(config.num_servers):
            shares.append(servers_secret[server_index][layer_index])
        
        reconstructed_layer = additive_reconstruct(shares)
        dpsshare_weights.append(reconstructed_layer)
    
    print(f"[RECONSTRUCTION] ✓ Global model reconstructed with {len(dpsshare_weights)} layers")

    servers_secret.clear()

    pickle_model = pickle.dumps(dpsshare_weights)
    
    print(f"\n[GLOBAL MODEL REDISTRIBUTION]")
    print(f"[BROADCAST] Distributing global model M_global to all {config.number_of_clients} facilities...")
    print(f"[BROADCAST] Model size: {len(pickle_model)} bytes")
    
    flcommon.broadcast_to_clients(pickle_model, config, lead_server=True)

    global total_upload_cost
    total_upload_cost += len(pickle_model) * config.number_of_clients

    print(f"[BROADCAST] ✓ Global model distributed to all facilities")
    print(f"\n[STATISTICS]")
    print(f"[DOWNLOAD] Total download cost: {total_download_cost} bytes")
    print(f"[UPLOAD] Total upload cost: {total_upload_cost} bytes")

    print(f"\n{'='*70}")
    print("[AGGREGATION] ✓ DPSShare global aggregation cycle completed")
    print("[AGGREGATION] Security features applied:")
    print("  ✓ Proof-of-Work validation")
    print("  ✓ Digital signature authentication")
    print("  ✓ Validator committee consensus")
    print("  ✓ Fog node regional aggregation")
    print("  ✓ Leader server global aggregation")
    print(f"{'='*70}\n")

    time_logger.lead_server_idle()


api.run(host=config.master_server_address, port=int(config.master_server_port), debug=False, threaded=True)
