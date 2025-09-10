#!/usr/bin/env python3
import http.server
import socketserver
import subprocess
import urllib.parse
import os
import threading
import json
from datetime import datetime

PORT = 5000

# Track running processes
running_processes = {}

class FedShareHandler(http.server.SimpleHTTPRequestHandler):
    def do_GET(self):
        if self.path == '/':
            self.serve_homepage()
        elif self.path.startswith('/run/'):
            algorithm = self.path.split('/')[-1]
            self.run_algorithm(algorithm)
        elif self.path.startswith('/logs/'):
            algorithm = self.path.split('/')[-1]
            self.show_logs(algorithm)
        elif self.path.startswith('/status/'):
            algorithm = self.path.split('/')[-1]
            self.get_status(algorithm)
        else:
            super().do_GET()
    
    def serve_homepage(self):
        html = """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>FedShare - Federated Learning Framework</title>
    <style>
        body {
            font-family: Arial, sans-serif;
            max-width: 800px;
            margin: 0 auto;
            padding: 20px;
            background-color: #f5f5f5;
        }
        .container {
            background: white;
            padding: 30px;
            border-radius: 10px;
            box-shadow: 0 2px 10px rgba(0,0,0,0.1);
        }
        h1 {
            color: #333;
            text-align: center;
            margin-bottom: 10px;
        }
        .subtitle {
            text-align: center;
            color: #666;
            margin-bottom: 30px;
        }
        .algorithm-section {
            margin: 20px 0;
            padding: 20px;
            border: 1px solid #ddd;
            border-radius: 8px;
            background-color: #fafafa;
        }
        .algorithm-title {
            font-size: 18px;
            font-weight: bold;
            margin-bottom: 10px;
            color: #2c3e50;
        }
        .algorithm-description {
            color: #666;
            margin-bottom: 15px;
        }
        .btn {
            background-color: #3498db;
            color: white;
            padding: 12px 24px;
            border: none;
            border-radius: 5px;
            cursor: pointer;
            font-size: 16px;
            margin-right: 10px;
            text-decoration: none;
            display: inline-block;
        }
        .btn:hover {
            background-color: #2980b9;
        }
        .btn-success {
            background-color: #27ae60;
        }
        .btn-success:hover {
            background-color: #219a52;
        }
        .btn-running {
            background-color: #e67e22;
        }
        .status-info {
            margin-top: 10px;
            padding: 8px;
            background-color: #d4edda;
            border-radius: 4px;
            font-size: 14px;
            color: #155724;
        }
        .info-box {
            background-color: #e8f4fd;
            border-left: 4px solid #3498db;
            padding: 15px;
            margin: 20px 0;
        }
    </style>
    <script>
        function runAlgorithm(algorithm) {
            const button = event.target;
            button.style.backgroundColor = '#e67e22';
            button.textContent = 'Starting...';
            button.disabled = true;
            
            fetch('/run/' + algorithm)
                .then(response => response.text())
                .then(data => {
                    setTimeout(() => {
                        button.textContent = 'Run ' + algorithm.charAt(0).toUpperCase() + algorithm.slice(1);
                        button.style.backgroundColor = '#3498db';
                        button.disabled = false;
                        checkStatus(algorithm);
                    }, 2000);
                })
                .catch(error => {
                    console.error('Error:', error);
                    button.textContent = 'Error';
                    button.style.backgroundColor = '#c0392b';
                });
        }
        
        function checkStatus(algorithm) {
            const statusDiv = document.getElementById(algorithm + '-status');
            if (statusDiv) {
                statusDiv.innerHTML = '<div class="status-info">✅ ' + algorithm.toUpperCase() + ' algorithm started! Check logs for progress.</div>';
            }
        }
    </script>
</head>
<body>
    <div class="container">
        <h1>🤖 FedShare Framework</h1>
        <p class="subtitle">Federated Learning Algorithms Playground</p>
        
        <div class="info-box">
            <strong>About this framework:</strong> Run federated learning experiments with multiple algorithms. 
            Each algorithm trains machine learning models across distributed clients while preserving privacy.
        </div>

        <div class="algorithm-section">
            <div class="algorithm-title">🔐 FedShare Algorithm</div>
            <div class="algorithm-description">
                Privacy-preserving federated learning with secret sharing techniques.
                Trains models across 5 clients with 2 servers.
            </div>
            <button class="btn" onclick="runAlgorithm('fedshare')">Run FedShare</button>
            <a href="/logs/fedshare" class="btn btn-success">View Logs</a>
            <div id="fedshare-status"></div>
        </div>

        <div class="algorithm-section">
            <div class="algorithm-title">📊 FedAvg Algorithm</div>
            <div class="algorithm-description">
                Classical federated averaging algorithm. Simple and efficient approach
                that averages model weights across distributed clients.
            </div>
            <button class="btn" onclick="runAlgorithm('fedavg')">Run FedAvg</button>
            <a href="/logs/fedavg" class="btn btn-success">View Logs</a>
            <div id="fedavg-status"></div>
        </div>

        <div class="algorithm-section">
            <div class="algorithm-title">🎯 SCOTCH Algorithm</div>
            <div class="algorithm-description">
                Secure aggregation for federated learning with cryptographic guarantees.
                Advanced privacy protection for sensitive datasets.
            </div>
            <button class="btn" onclick="runAlgorithm('scotch')">Run SCOTCH</button>
            <a href="/logs/scotch" class="btn btn-success">View Logs</a>
            <div id="scotch-status"></div>
        </div>

        <div class="info-box">
            <strong>Default Configuration:</strong>
            <ul>
                <li>5 clients per experiment</li>
                <li>MNIST dataset (28x28 handwritten digits)</li>
                <li>3 training rounds, 1 epoch per round</li>
                <li>Results saved automatically to logs/ directory</li>
            </ul>
        </div>
    </div>
</body>
</html>"""
        
        self.send_response(200)
        self.send_header('Content-type', 'text/html')
        self.end_headers()
        self.wfile.write(html.encode())
    
    def run_algorithm(self, algorithm):
        script_map = {
            'fedshare': './start-fedshare.sh',
            'fedavg': './start-fedavg.sh', 
            'scotch': './start-scotch.sh'
        }
        
        if algorithm not in script_map:
            self.send_error(400, "Invalid algorithm")
            return
        
        # Check if already running
        if algorithm in running_processes:
            if running_processes[algorithm].poll() is None:
                self.send_response(200)
                self.send_header('Content-type', 'text/plain')
                self.end_headers()
                self.wfile.write(f"{algorithm.upper()} is already running".encode())
                return
        
        try:
            script_path = script_map[algorithm]
            print(f"Starting {algorithm}: {script_path}")
            
            # Start the script
            process = subprocess.Popen(
                ['/bin/bash', script_path],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                cwd='.'
            )
            
            running_processes[algorithm] = process
            print(f"Started {algorithm} with PID: {process.pid}")
            
            self.send_response(200)
            self.send_header('Content-type', 'text/plain')
            self.end_headers()
            self.wfile.write(f"{algorithm.upper()} started successfully!".encode())
            
        except Exception as e:
            print(f"Error starting {algorithm}: {str(e)}")
            self.send_error(500, str(e))
    
    def show_logs(self, algorithm):
        log_directories = {
            'fedshare': 'fedshare-mnist-client-5-server-2',
            'fedavg': 'fedavg-mnist-client-5',
            'scotch': 'scotch-mnist-client-5-server-2'
        }
        
        if algorithm not in log_directories:
            self.send_error(404, "Invalid algorithm")
            return
        
        log_dir = f"logs/{log_directories[algorithm]}"
        
        html = f"""<!DOCTYPE html>
<html>
<head>
    <title>{algorithm.upper()} Logs</title>
    <style>
        body {{ font-family: Arial, sans-serif; margin: 20px; background-color: #f5f5f5; }}
        .container {{ background: white; padding: 30px; border-radius: 10px; }}
        .back-btn {{ background-color: #95a5a6; color: white; padding: 10px 20px; 
                     border: none; border-radius: 5px; text-decoration: none; display: inline-block; margin-bottom: 20px; }}
        .log-file {{ margin: 20px 0; border: 1px solid #ddd; border-radius: 5px; }}
        .log-header {{ background-color: #34495e; color: white; padding: 10px 15px; font-weight: bold; }}
        .log-content {{ background-color: #2c3e50; color: #ecf0f1; padding: 15px; 
                        font-family: 'Courier New', monospace; font-size: 12px; max-height: 300px; 
                        overflow-y: auto; white-space: pre-wrap; }}
    </style>
</head>
<body>
    <div class="container">
        <a href="/" class="back-btn">← Back to Main</a>
        <h1>📋 {algorithm.upper()} Training Logs</h1>"""
        
        if os.path.exists(log_dir):
            for filename in os.listdir(log_dir):
                if filename.endswith('.log'):
                    filepath = os.path.join(log_dir, filename)
                    try:
                        with open(filepath, 'r') as f:
                            content = f.read()
                        html += f"""
        <div class="log-file">
            <div class="log-header">📄 {filename}</div>
            <div class="log-content">{content}</div>
        </div>"""
                    except Exception as e:
                        html += f"<p>Error reading {filename}: {str(e)}</p>"
        else:
            html += f"""<div style="text-align: center; color: #666; padding: 40px; font-style: italic;">
                No logs found for {algorithm.upper()}.<br>
                Run the algorithm first to generate training logs.
            </div>"""
        
        html += """
    </div>
</body>
</html>"""
        
        self.send_response(200)
        self.send_header('Content-type', 'text/html')
        self.end_headers()
        self.wfile.write(html.encode())
    
    def get_status(self, algorithm):
        if algorithm in running_processes:
            process = running_processes[algorithm]
            if process.poll() is None:
                status = {'status': 'running', 'pid': process.pid}
            else:
                status = {'status': 'completed', 'returncode': process.returncode}
        else:
            status = {'status': 'not_started'}
        
        self.send_response(200)
        self.send_header('Content-type', 'application/json')
        self.end_headers()
        self.wfile.write(json.dumps(status).encode())

def start_server():
    with socketserver.TCPServer(("0.0.0.0", PORT), FedShareHandler) as httpd:
        print(f"🚀 FedShare server running on http://0.0.0.0:{PORT}")
        print("Click the buttons in your web browser to run federated learning algorithms!")
        httpd.serve_forever()

if __name__ == "__main__":
    start_server()