#!/bin/bash

export PYTHONUNBUFFERED=1
export OMP_NUM_THREADS=1
export TF_NUM_INTRAOP_THREADS=1
export TF_NUM_INTEROP_THREADS=1

PYTHON=$(command -v python)

# Read configuration from config.py
M=$($PYTHON -c "from config import Config; print(Config.number_of_clients)")
N=$($PYTHON -c "from config import Config; print(Config.num_servers)")

echo "DPSShare Configuration: $M clients, $N servers (with Differential Privacy and Shamir Secret Sharing + TA)"

DEST_DIRECTORY="logs/dpsshare-mnist-client-${M}-server-${N}"
echo "Log directory: $DEST_DIRECTORY"
mkdir -p ${DEST_DIRECTORY}

echo "=========================================="
echo "PHASE 1: Starting Trusted Authority (TA)"
echo "=========================================="
echo "Starting TA server on port 9600..."
nohup $PYTHON trusted_authority.py 9600 > ${DEST_DIRECTORY}/trusted_authority.log 2>&1 &
TA_PID=$!
sleep 3

echo "Initializing TA system (CP-ABE setup)..."
$PYTHON -c "
import requests
import pickle
import mnistcommon
import json

# Initialize TA system
response = requests.post('http://127.0.0.1:9600/setup', json={
    'num_facilities': ${M},
    'pow_difficulty': 4,
    'security_param': 256
})

if response.status_code == 200:
    print('[TA INIT] ✓ TA system initialized successfully')
    
    # Create initial model and encrypt it
    model = mnistcommon.get_model()
    initial_weights = model.get_weights()
    
    # Encrypt model with CP-ABE
    response = requests.post('http://127.0.0.1:9600/encrypt_model', json={
        'model_hex': pickle.dumps(initial_weights).hex(),
        'policy': {'role': 'hospital', 'region': 'North'}
    })
    
    if response.status_code == 200:
        print('[TA INIT] ✓ Initial model encrypted with CP-ABE')
        print('[TA INIT] ✓ Access policy: role=hospital, region=North')
    else:
        print('[TA INIT] ✗ Model encryption failed')
else:
    print('[TA INIT] ✗ TA initialization failed')
"

sleep 2

echo ""
echo "=========================================="
echo "PHASE 2: Starting Federated Infrastructure"
echo "=========================================="

echo "Starting logger server..."
nohup $PYTHON logger_server.py > ${DEST_DIRECTORY}/logger_server.log 2>&1 &
sleep 2

echo "Starting lead server (master)..."
nohup $PYTHON dpsshareleadserver.py > ${DEST_DIRECTORY}/dpsshareleadserver.log 2>&1 &
sleep 2

for ((SERVER = 0; SERVER < N; SERVER++)); do
  echo "Starting server ${SERVER}..."
  nohup $PYTHON dpsshareserver.py "${SERVER}" > "${DEST_DIRECTORY}/dpsshareserver-${SERVER}.log" 2>&1 &
  sleep 2
done

for ((CLIENT = 0; CLIENT < M; CLIENT++)); do
  echo "Starting client ${CLIENT}..."
  nohup $PYTHON dpsshareclient.py "${CLIENT}" > "${DEST_DIRECTORY}/dpsshareclient-${CLIENT}.log" 2>&1 &
  sleep 5
done

echo "DPSShare training started. Check logs in ${DEST_DIRECTORY}/"
echo "All processes running. Training in progress..."

$PYTHON flask_starter.py
