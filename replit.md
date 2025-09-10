# FedShare - Federated Learning Framework

## Overview
This is a federated learning research project implementing three algorithms:
- **FedShare**: The main algorithm with privacy-preserving features
- **FedAvg**: Classical federated averaging algorithm  
- **SCOTCH**: Another federated learning approach

The project is built with Python 3.11, TensorFlow 2.9.1, and Flask for the web interface.

## Usage
The project runs on port 5000 with a web interface. Use the terminal scripts:
- `./start-fedshare.sh` - Run FedShare algorithm
- `./start-fedavg.sh` - Run FedAvg algorithm  
- `./start-scotch.sh` - Run SCOTCH algorithm

Training results are saved in the `logs/` directory.

## Configuration
- 5 clients by default (configurable in config.py)
- 2 servers for multi-server algorithms
- MNIST dataset (replaceable with other datasets)
- 3 training rounds, 1 epoch per round
