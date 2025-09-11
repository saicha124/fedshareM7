#!/bin/bash

# Kill any existing scotch processes first
pkill -f "scotch" || true
sleep 2

export PYTHONUNBUFFERED=1
export OMP_NUM_THREADS=1
export TF_NUM_INTRAOP_THREADS=1
export TF_NUM_INTEROP_THREADS=1

N=2
M=3

DEST_DIRECTORY="scotch-mnist-client-${M}-server-${N}"
echo "$DEST_DIRECTORY"
mkdir -p logs/${DEST_DIRECTORY}

# Use consistent Python interpreter
PYTHON_EXEC="/home/runner/workspace/.pythonlibs/bin/python"

nohup $PYTHON_EXEC logger_server.py &>logs/${DEST_DIRECTORY}/logger_server.log &
sleep 3

for ((SERVER = 0; SERVER < N; SERVER++)); do
  echo "Running server ${SERVER}"
  nohup $PYTHON_EXEC scotchserver.py "${SERVER}" &>"logs/${DEST_DIRECTORY}/scotchserver-${SERVER}.log" &
  sleep 2
done

for ((CLIENT = 0; CLIENT < M; CLIENT++)); do
  echo "Running client ${CLIENT}"
  nohup $PYTHON_EXEC scotchclient.py "${CLIENT}" &>"logs/${DEST_DIRECTORY}/scotchclient-${CLIENT}.log" &
  sleep 2
done

$PYTHON_EXEC flask_starter.py
