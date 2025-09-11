# FedShare - Federated Learning Framework

## Overview
This is a federated learning research project implementing three algorithms:
- **FedShare**: The main algorithm with privacy-preserving features
- **FedAvg**: Classical federated averaging algorithm  
- **SCOTCH**: Another federated learning approach

The project is built with Python 3.11, TensorFlow 2.20.0, and Flask for the web interface.

## Usage
The project runs on port 5000 with an enhanced web interface featuring:
- Real-time training progress tracking
- Interactive algorithm execution
- Live log viewing
- Performance metrics visualization

Access the web interface at the main URL. Click buttons to run algorithms directly from the browser.

## Technical Setup
- **Frontend**: Enhanced Flask app (`enhanced_app.py`) on port 5000
- **Backend**: Distributed federated learning clients and servers
- **Configuration**: Optimized for Replit with 3 clients, 2 servers, 2 training rounds
- **Dataset**: MNIST (6,000 samples for faster training)
- **Deployment**: Configured for VM deployment target

## Files Structure
- `enhanced_app.py` - Main web interface with progress tracking
- `config.py` - Configuration for clients, servers, and training parameters
- `start-*.sh` - Shell scripts to launch federated learning algorithms
- `logs/` - Training logs and results storage

## Development Notes  
- **2025-09-11**: Successfully imported from GitHub and configured for Replit
- All dependencies installed via requirements.txt (TensorFlow 2.20.0, Flask 3.1.2, etc.)
- Scripts are executable and ready to run
- Enhanced Flask app running successfully on port 5000 with 0.0.0.0 binding
- Optimized for fast training iterations in development environment
- Production deployment configured for VM target
- Project fully functional with real-time web interface for federated learning algorithms
