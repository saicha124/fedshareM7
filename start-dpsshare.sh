#!/bin/bash

export PYTHONUNBUFFERED=1
export OMP_NUM_THREADS=1
export TF_NUM_INTRAOP_THREADS=1
export TF_NUM_INTEROP_THREADS=1

PYTHON=$(command -v python)

# Read configuration from config.py
M=$($PYTHON -c "from config import Config; print(Config.number_of_clients)")
N=$($PYTHON -c "from config import Config; print(Config.num_servers)")

echo "DPSShare Configuration: $M clients, $N servers (with Differential Privacy and Shamir Secret Sharing)"

DEST_DIRECTORY="logs/dpsshare-mnist-client-${M}-server-${N}"
echo "Log directory: $DEST_DIRECTORY"
mkdir -p ${DEST_DIRECTORY}

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
