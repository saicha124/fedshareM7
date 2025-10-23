class Config:
    number_of_clients = 5  # Number of federated learning clients - optimized for reliability
    train_dataset_size = 6000  # Reduced dataset size for faster training
    clients_dataset_size = [train_dataset_size/number_of_clients] * number_of_clients
    total_dataset_size = sum(clients_dataset_size)
    num_servers = 3  # Number of servers (can be modified as needed)
    training_rounds = 3  # Multiple rounds for proper convergence
    epochs = 1
    batch_size = 16  # Larger batch size for faster training
    verbose = 1
    validation_split = 0.1
    server_base_port = 8500
    master_server_index = 0
    master_server_port = 7501
    client_address = '127.0.0.1'
    server_address = '127.0.0.1'
    master_server_address = '127.0.0.1'
    buffer_size = 4096
    client_base_port = 9500
    fedavg_server_port = 3500
    logger_address = '127.0.0.1'
    logger_port = 8778
    delay = 10
    
    # DPSShare-specific: Differential Privacy configuration
    dp_epsilon = 5.0  # Privacy budget (smaller = more privacy, more noise)
    dp_sensitivity = 0.01  # Sensitivity of the query (max change in output)
    
    # DPSShare-specific: Secret Sharing configuration
    num_shares = 3  # Number of shares to split the model into
    threshold = 2  # Minimum shares needed to reconstruct


class ClientConfig(Config):
    def __init__(self, client_index):
        self.client_index = client_index


class ServerConfig(Config):
    def __init__(self, server_index):
        self.server_index = server_index


class LeadConfig(Config):
    def __init__(self):
        pass


class FedAvgServerConfig(Config):
    def __init__(self):
        pass
