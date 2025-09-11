#!/bin/bash

export PYTHONUNBUFFERED=1
export OMP_NUM_THREADS=1
export TF_NUM_INTRAOP_THREADS=1
export TF_NUM_INTEROP_THREADS=1

PYTHON=$(command -v python)
M=1

DEST_DIRECTORY="logs/fedavg-mnist-client-${M}"
echo "$DEST_DIRECTORY"
mkdir -p ${DEST_DIRECTORY}

nohup $PYTHON logger_server.py > ${DEST_DIRECTORY}/logger_server.log 2>&1 &
sleep 2

echo "Running server"
nohup $PYTHON fedavgserver.py > ${DEST_DIRECTORY}/fedavgserver.log 2>&1 &
sleep 2

for ((CLIENT = 0; CLIENT < M; CLIENT++)); do
  echo "Running client ${CLIENT}"
  nohup $PYTHON fedavgclient.py "${CLIENT}" > "${DEST_DIRECTORY}/fedavgclient-${CLIENT}.log" 2>&1 &
  sleep 5
done

$PYTHON flask_starter.py