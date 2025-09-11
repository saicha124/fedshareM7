#!/usr/bin/env python3
import http.server
import socketserver
import subprocess
import urllib.parse
import os
import threading
import json
import time
import re
from datetime import datetime

PORT = 5000

# Track running processes and their progress
running_processes = {}
progress_data = {}

def parse_logs_for_progress(algorithm):
    """Parse log files to extract training progress"""
    log_directories = {
        'fedshare': 'fedshare-mnist-client-3-server-2',
        'fedavg': 'fedavg-mnist-client-1',  # Updated for current config
        'scotch': 'scotch-mnist-client-3-server-2'
    }
    
    if algorithm not in log_directories:
        return {}
    
    log_dir = f"logs/{log_directories[algorithm]}"
    
    # Get current config values
    if algorithm == 'fedavg':
        total_clients = 1  # Current simplified config
        total_rounds = 1
    else:
        total_clients = 3  # Default for other algorithms
        total_rounds = 2
        
    progress = {
        'clients_started': 0,
        'total_clients': total_clients,
        'current_round': 0,
        'total_rounds': total_rounds,
        'training_progress': 0,
        'status': 'not_started',
        'results': [],
        'metrics': {}
    }
    
    if not os.path.exists(log_dir):
        return progress
    
    # Check client logs for training progress
    for i in range(total_clients):
        client_log = f"{log_dir}/{algorithm}client-{i}.log"
        if os.path.exists(client_log):
            progress['clients_started'] += 1
            try:
                with open(client_log, 'r') as f:
                    content = f.read()
                    
                # Extract round information
                rounds = re.findall(r'Round: (\d+)/(\d+)', content)
                if rounds:
                    latest_round = max([int(r[0]) for r in rounds])
                    progress['current_round'] = max(progress['current_round'], latest_round)
                
                # Extract training completion
                completed_rounds = content.count('completed')
                training_finished = content.count('Training finished')
                
                # If training is finished, set to 100%, otherwise count completed rounds
                if training_finished > 0:
                    progress['training_progress'] = 100
                else:
                    progress['training_progress'] = max(progress['training_progress'], 
                                                      completed_rounds * 20)  # Each round = 20%
                
                # Extract accuracy/loss if available
                accuracy_matches = re.findall(r'accuracy: ([\d.]+)', content)
                loss_matches = re.findall(r'loss: ([\d.]+)', content)
                if accuracy_matches:
                    progress['metrics'][f'client_{i}_accuracy'] = float(accuracy_matches[-1])
                if loss_matches:
                    progress['metrics'][f'client_{i}_loss'] = float(loss_matches[-1])
                    
            except Exception as e:
                print(f"Error reading client log {client_log}: {e}")
    
    # Check server logs for completion
    server_log = f"{log_dir}/{algorithm}server.log" if algorithm == 'fedavg' else f"{log_dir}/{algorithm}server-0.log"
    if os.path.exists(server_log):
        try:
            with open(server_log, 'r') as f:
                content = f.read()
                
            # Check for final round completion
            final_round_completed = f"Round {progress['total_rounds']} completed" in content
            if final_round_completed:
                progress['training_progress'] = 100
            else:
                # Extract server aggregation info
                aggregations = content.count('Round completed')
                progress['training_progress'] = max(progress['training_progress'], 
                                                  aggregations * 50)  # Server aggregation progress
                
        except Exception as e:
            print(f"Error reading server log: {e}")
    
    # Check lead server for completion
    lead_server_log = f"{log_dir}/{algorithm}leadserver.log"
    if os.path.exists(lead_server_log):
        try:
            with open(lead_server_log, 'r') as f:
                content = f.read()
                
            # Check for successful aggregation completion
            if 'Model aggregation completed successfully' in content:
                progress['training_progress'] = 100
                
        except Exception as e:
            print(f"Error reading lead server log: {e}")
    
    # Determine overall status - check completion FIRST
    if progress['clients_started'] == 0:
        progress['status'] = 'not_started'
    elif progress['training_progress'] >= 100:
        progress['status'] = 'completed'
    elif progress['clients_started'] < progress['total_clients']:
        progress['status'] = 'starting_clients'
    elif progress['current_round'] < progress['total_rounds']:
        progress['status'] = 'training'
    else:
        progress['status'] = 'training'
    
    return progress

class EnhancedFedShareHandler(http.server.SimpleHTTPRequestHandler):
    def do_GET(self):
        if self.path == '/':
            self.serve_homepage()
        elif self.path.startswith('/run/'):
            algorithm = self.path.split('/')[-1]
            self.run_algorithm(algorithm)
        elif self.path.startswith('/progress/'):
            algorithm = self.path.split('/')[-1]
            self.get_progress(algorithm)
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
    <title>FedShare - Enhanced Federated Learning Framework</title>
    <style>
        body {
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            max-width: 1000px;
            margin: 0 auto;
            padding: 20px;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            min-height: 100vh;
        }
        .container {
            background: white;
            padding: 30px;
            border-radius: 15px;
            box-shadow: 0 8px 25px rgba(0,0,0,0.15);
        }
        h1 {
            color: #2c3e50;
            text-align: center;
            margin-bottom: 10px;
            font-size: 2.5em;
        }
        .subtitle {
            text-align: center;
            color: #7f8c8d;
            margin-bottom: 30px;
            font-size: 1.2em;
        }
        .algorithm-section {
            margin: 25px 0;
            padding: 25px;
            border: 2px solid #ecf0f1;
            border-radius: 12px;
            background: linear-gradient(145deg, #f8f9fa, #ffffff);
            transition: all 0.3s ease;
        }
        .algorithm-section:hover {
            border-color: #3498db;
            transform: translateY(-2px);
            box-shadow: 0 5px 15px rgba(52, 152, 219, 0.1);
        }
        .algorithm-title {
            font-size: 20px;
            font-weight: bold;
            margin-bottom: 15px;
            color: #2c3e50;
            display: flex;
            align-items: center;
        }
        .algorithm-title .emoji {
            margin-right: 10px;
            font-size: 24px;
        }
        .algorithm-description {
            color: #666;
            margin-bottom: 20px;
            line-height: 1.6;
        }
        .controls {
            display: flex;
            gap: 10px;
            margin-bottom: 15px;
            flex-wrap: wrap;
        }
        .btn {
            background: linear-gradient(145deg, #3498db, #2980b9);
            color: white;
            padding: 12px 24px;
            border: none;
            border-radius: 8px;
            cursor: pointer;
            font-size: 16px;
            font-weight: 500;
            text-decoration: none;
            display: inline-block;
            transition: all 0.3s ease;
            min-width: 120px;
            text-align: center;
        }
        .btn:hover {
            transform: translateY(-2px);
            box-shadow: 0 5px 15px rgba(52, 152, 219, 0.3);
        }
        .btn-success {
            background: linear-gradient(145deg, #27ae60, #219a52);
        }
        .btn-running {
            background: linear-gradient(145deg, #e67e22, #d35400);
        }
        .btn:disabled {
            opacity: 0.6;
            cursor: not-allowed;
            transform: none;
        }
        .progress-container {
            margin-top: 15px;
            padding: 15px;
            background: #f8f9fa;
            border-radius: 8px;
            display: none;
        }
        .progress-bar {
            width: 100%;
            height: 20px;
            background-color: #ecf0f1;
            border-radius: 10px;
            overflow: hidden;
            margin: 10px 0;
        }
        .progress-fill {
            height: 100%;
            background: linear-gradient(90deg, #3498db, #2ecc71);
            border-radius: 10px;
            width: 0%;
            transition: width 0.5s ease;
            position: relative;
        }
        .progress-text {
            position: absolute;
            top: 50%;
            left: 50%;
            transform: translate(-50%, -50%);
            color: white;
            font-weight: bold;
            font-size: 12px;
        }
        .status-info {
            margin: 10px 0;
            padding: 10px;
            border-radius: 6px;
            font-size: 14px;
        }
        .status-running {
            background-color: #fff3cd;
            border: 1px solid #ffeaa7;
            color: #856404;
        }
        .status-completed {
            background-color: #d4edda;
            border: 1px solid #c3e6cb;
            color: #155724;
        }
        .status-error {
            background-color: #f8d7da;
            border: 1px solid #f5c6cb;
            color: #721c24;
        }
        .metrics {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 10px;
            margin-top: 10px;
        }
        .metric-item {
            background: white;
            padding: 10px;
            border-radius: 6px;
            border: 1px solid #dee2e6;
            text-align: center;
        }
        .metric-label {
            font-size: 12px;
            color: #666;
            margin-bottom: 5px;
        }
        .metric-value {
            font-size: 18px;
            font-weight: bold;
            color: #2c3e50;
        }
        .info-box {
            background: linear-gradient(145deg, #e8f4fd, #ffffff);
            border-left: 4px solid #3498db;
            padding: 20px;
            margin: 25px 0;
            border-radius: 8px;
        }
        .optimization-note {
            background: linear-gradient(145deg, #fff7e6, #ffffff);
            border-left: 4px solid #f39c12;
            padding: 15px;
            margin: 20px 0;
            border-radius: 8px;
        }
        .refresh-btn {
            position: fixed;
            top: 20px;
            right: 20px;
            background: linear-gradient(145deg, #9b59b6, #8e44ad);
            color: white;
            border: none;
            padding: 10px 20px;
            border-radius: 25px;
            cursor: pointer;
            font-weight: bold;
            box-shadow: 0 4px 15px rgba(155, 89, 182, 0.3);
        }
    </style>
    <script>
        let updateIntervals = {};
        
        function runAlgorithm(algorithm) {
            const button = document.getElementById(algorithm + '-run-btn');
            const progressContainer = document.getElementById(algorithm + '-progress');
            
            button.style.background = 'linear-gradient(145deg, #e67e22, #d35400)';
            button.textContent = 'Starting...';
            button.disabled = true;
            
            fetch('/run/' + algorithm)
                .then(response => response.text())
                .then(data => {
                    progressContainer.style.display = 'block';
                    startProgressTracking(algorithm);
                })
                .catch(error => {
                    console.error('Error:', error);
                    button.textContent = 'Error';
                    button.style.background = 'linear-gradient(145deg, #c0392b, #a93226)';
                });
        }
        
        function startProgressTracking(algorithm) {
            if (updateIntervals[algorithm]) {
                clearInterval(updateIntervals[algorithm]);
            }
            
            updateIntervals[algorithm] = setInterval(() => {
                updateProgress(algorithm);
            }, 2000);
            
            updateProgress(algorithm);
        }
        
        function updateProgress(algorithm) {
            fetch('/progress/' + algorithm)
                .then(response => response.json())
                .then(data => {
                    updateProgressUI(algorithm, data);
                })
                .catch(error => console.error('Progress update error:', error));
        }
        
        function updateProgressUI(algorithm, data) {
            const progressFill = document.getElementById(algorithm + '-progress-fill');
            const progressText = document.getElementById(algorithm + '-progress-text');
            const statusInfo = document.getElementById(algorithm + '-status');
            const metricsContainer = document.getElementById(algorithm + '-metrics');
            const runBtn = document.getElementById(algorithm + '-run-btn');
            
            // Update progress bar
            const totalProgress = Math.min(100, 
                (data.clients_started / data.total_clients * 25) +
                (data.current_round / data.total_rounds * 50) +
                (data.training_progress * 0.25)
            );
            
            progressFill.style.width = totalProgress + '%';
            progressText.textContent = Math.round(totalProgress) + '%';
            
            // Update status
            let statusMessage = '';
            let statusClass = 'status-running';
            
            switch(data.status) {
                case 'not_started':
                    statusMessage = '⏳ Waiting to start...';
                    break;
                case 'starting_clients':
                    statusMessage = `🚀 Starting clients (${data.clients_started}/${data.total_clients})`;
                    break;
                case 'training':
                    statusMessage = `🧠 Training round ${data.current_round}/${data.total_rounds}`;
                    break;
                case 'completed':
                    statusMessage = '✅ Training completed successfully!';
                    statusClass = 'status-completed';
                    clearInterval(updateIntervals[algorithm]);
                    runBtn.textContent = 'Run ' + algorithm.charAt(0).toUpperCase() + algorithm.slice(1);
                    runBtn.style.background = 'linear-gradient(145deg, #3498db, #2980b9)';
                    runBtn.disabled = false;
                    break;
            }
            
            statusInfo.innerHTML = `<div class="${statusClass}">${statusMessage}</div>`;
            
            // Update metrics
            if (Object.keys(data.metrics).length > 0) {
                let metricsHTML = '<div class="metrics">';
                for (const [key, value] of Object.entries(data.metrics)) {
                    const label = key.replace('_', ' ').toUpperCase();
                    metricsHTML += `
                        <div class="metric-item">
                            <div class="metric-label">${label}</div>
                            <div class="metric-value">${typeof value === 'number' ? value.toFixed(4) : value}</div>
                        </div>
                    `;
                }
                metricsHTML += '</div>';
                metricsContainer.innerHTML = metricsHTML;
            }
        }
        
        function refreshPage() {
            location.reload();
        }
        
        // Removed automatic page refresh to prevent interrupting training progress
    </script>
</head>
<body>
    <button class="refresh-btn" onclick="refreshPage()">🔄 Refresh</button>
    
    <div class="container">
        <h1>🚀 FedShare Framework</h1>
        <p class="subtitle">Enhanced Federated Learning with Real-Time Progress</p>
        
        <div class="optimization-note">
            <strong>⚡ Performance Optimized:</strong> 
            Reduced to 3 clients, 2 rounds, and 6K dataset samples for faster training and demonstration.
            Training typically completes in 2-3 minutes per algorithm.
        </div>
        
        <div class="info-box">
            <strong>🔬 About Federated Learning:</strong> 
            Train machine learning models across distributed clients while preserving privacy. 
            Each algorithm demonstrates different approaches to aggregation and security.
        </div>

        <div class="algorithm-section">
            <div class="algorithm-title">
                <span class="emoji">🔐</span>FedShare Algorithm
            </div>
            <div class="algorithm-description">
                Privacy-preserving federated learning with secret sharing techniques.
                Uses cryptographic methods to protect individual client updates during aggregation.
            </div>
            <div class="controls">
                <button id="fedshare-run-btn" class="btn" onclick="runAlgorithm('fedshare')">Run FedShare</button>
                <a href="/logs/fedshare" class="btn btn-success">View Logs</a>
            </div>
            <div id="fedshare-progress" class="progress-container">
                <div class="progress-bar">
                    <div id="fedshare-progress-fill" class="progress-fill">
                        <div id="fedshare-progress-text" class="progress-text">0%</div>
                    </div>
                </div>
                <div id="fedshare-status"></div>
                <div id="fedshare-metrics"></div>
            </div>
        </div>

        <div class="algorithm-section">
            <div class="algorithm-title">
                <span class="emoji">📊</span>FedAvg Algorithm
            </div>
            <div class="algorithm-description">
                Classical federated averaging algorithm. Simple weighted averaging of model parameters
                based on local dataset sizes. The foundational approach for federated learning.
            </div>
            <div class="controls">
                <button id="fedavg-run-btn" class="btn" onclick="runAlgorithm('fedavg')">Run FedAvg</button>
                <a href="/logs/fedavg" class="btn btn-success">View Logs</a>
            </div>
            <div id="fedavg-progress" class="progress-container">
                <div class="progress-bar">
                    <div id="fedavg-progress-fill" class="progress-fill">
                        <div id="fedavg-progress-text" class="progress-text">0%</div>
                    </div>
                </div>
                <div id="fedavg-status"></div>
                <div id="fedavg-metrics"></div>
            </div>
        </div>

        <div class="algorithm-section">
            <div class="algorithm-title">
                <span class="emoji">🎯</span>SCOTCH Algorithm
            </div>
            <div class="algorithm-description">
                Secure aggregation for federated learning with advanced cryptographic guarantees.
                Provides strong privacy protection against both honest-but-curious and malicious adversaries.
            </div>
            <div class="controls">
                <button id="scotch-run-btn" class="btn" onclick="runAlgorithm('scotch')">Run SCOTCH</button>
                <a href="/logs/scotch" class="btn btn-success">View Logs</a>
            </div>
            <div id="scotch-progress" class="progress-container">
                <div class="progress-bar">
                    <div id="scotch-progress-fill" class="progress-fill">
                        <div id="scotch-progress-text" class="progress-text">0%</div>
                    </div>
                </div>
                <div id="scotch-status"></div>
                <div id="scotch-metrics"></div>
            </div>
        </div>

        <div class="info-box">
            <strong>📋 Training Configuration:</strong>
            <ul style="margin: 10px 0;">
                <li><strong>Clients:</strong> 3 distributed nodes</li>
                <li><strong>Dataset:</strong> MNIST (6,000 samples total)</li>
                <li><strong>Rounds:</strong> 2 training rounds</li>
                <li><strong>Batch Size:</strong> 32 (optimized for speed)</li>
                <li><strong>Results:</strong> Automatic accuracy and loss tracking</li>
            </ul>
        </div>
    </div>
</body>
</html>"""
        
        self.send_response(200)
        self.send_header('Content-type', 'text/html')
        self.send_header('Cache-Control', 'no-cache, no-store, must-revalidate')
        self.send_header('Pragma', 'no-cache')
        self.send_header('Expires', '0')
        self.end_headers()
        self.wfile.write(html.encode())
    
    def get_progress(self, algorithm):
        """Get real-time progress for an algorithm"""
        progress = parse_logs_for_progress(algorithm)
        
        self.send_response(200)
        self.send_header('Content-type', 'application/json')
        self.send_header('Cache-Control', 'no-cache')
        self.end_headers()
        self.wfile.write(json.dumps(progress).encode())
    
    def run_algorithm(self, algorithm):
        script_map = {
            'fedshare': './start-fedshare.sh',
            'fedavg': './start-fedavg.sh', 
            'scotch': './start-scotch.sh'
        }
        
        if algorithm not in script_map:
            self.send_error(400, "Invalid algorithm")
            return
        
        # Kill any existing processes first
        subprocess.run(['pkill', '-f', f'{algorithm}'], capture_output=True)
        time.sleep(1)
        
        # Clean up old logs
        log_dirs = {
            'fedshare': 'logs/fedshare-mnist-client-3-server-2',
            'fedavg': 'logs/fedavg-mnist-client-3',
            'scotch': 'logs/scotch-mnist-client-3-server-2'
        }
        
        if algorithm in log_dirs:
            subprocess.run(['rm', '-rf', log_dirs[algorithm]], capture_output=True)
        
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
            progress_data[algorithm] = {'status': 'starting', 'start_time': time.time()}
            print(f"Started {algorithm} with PID: {process.pid}")
            
            self.send_response(200)
            self.send_header('Content-type', 'text/plain')
            self.end_headers()
            self.wfile.write(f"{algorithm.upper()} started successfully!".encode())
            
        except Exception as e:
            print(f"Error starting {algorithm}: {str(e)}")
            self.send_error(500, str(e))
    
    def show_logs(self, algorithm):
        """Enhanced log viewer with better formatting"""
        log_directories = {
            'fedshare': 'fedshare-mnist-client-3-server-2',
            'fedavg': 'fedavg-mnist-client-3',
            'scotch': 'scotch-mnist-client-3-server-2'
        }
        
        if algorithm not in log_directories:
            self.send_error(404, "Invalid algorithm")
            return
        
        log_dir = f"logs/{log_directories[algorithm]}"
        
        html = f"""<!DOCTYPE html>
<html>
<head>
    <title>{algorithm.upper()} Training Logs</title>
    <style>
        body {{ font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; margin: 20px; background-color: #f5f5f5; }}
        .container {{ background: white; padding: 30px; border-radius: 15px; box-shadow: 0 5px 15px rgba(0,0,0,0.1); }}
        .back-btn {{ background: linear-gradient(145deg, #95a5a6, #7f8c8d); color: white; padding: 12px 24px; 
                     border: none; border-radius: 8px; text-decoration: none; display: inline-block; margin-bottom: 20px; }}
        .log-file {{ margin: 20px 0; border: 1px solid #ddd; border-radius: 10px; overflow: hidden; }}
        .log-header {{ background: linear-gradient(145deg, #34495e, #2c3e50); color: white; padding: 15px; font-weight: bold; }}
        .log-content {{ background-color: #2c3e50; color: #ecf0f1; padding: 20px; 
                        font-family: 'Courier New', monospace; font-size: 13px; max-height: 400px; 
                        overflow-y: auto; white-space: pre-wrap; line-height: 1.4; }}
        .refresh-btn {{ float: right; background: linear-gradient(145deg, #3498db, #2980b9); color: white; 
                       padding: 8px 16px; border: none; border-radius: 6px; cursor: pointer; }}
    </style>
    <script>
        function refreshLogs() {{ location.reload(); }}
        setInterval(refreshLogs, 15000); // Auto-refresh every 15 seconds (less aggressive)
    </script>
</head>
<body>
    <div class="container">
        <a href="/" class="back-btn">← Back to Main</a>
        <button class="refresh-btn" onclick="refreshLogs()">🔄 Refresh</button>
        <h1>📋 {algorithm.upper()} Training Logs</h1>"""
        
        if os.path.exists(log_dir):
            log_files = [f for f in os.listdir(log_dir) if f.endswith('.log')]
            log_files.sort()
            
            for filename in log_files:
                filepath = os.path.join(log_dir, filename)
                try:
                    with open(filepath, 'r') as f:
                        content = f.read()
                        if content.strip():  # Only show non-empty logs
                            # Highlight important information
                            content = content.replace('Round:', '<strong>Round:</strong>')
                            content = content.replace('accuracy:', '<span style="color: #2ecc71;"><strong>accuracy:</strong></span>')
                            content = content.replace('loss:', '<span style="color: #e74c3c;"><strong>loss:</strong></span>')
                            content = content.replace('completed', '<span style="color: #f39c12;"><strong>completed</strong></span>')
                            
                    html += f"""
        <div class="log-file">
            <div class="log-header">📄 {filename}</div>
            <div class="log-content">{content}</div>
        </div>"""
                except Exception as e:
                    html += f"<p style='color: red;'>Error reading {filename}: {str(e)}</p>"
        else:
            html += f"""<div style="text-align: center; color: #666; padding: 40px; font-style: italic;">
                No logs found for {algorithm.upper()}.<br>
                <strong>Run the algorithm first to generate training logs.</strong>
            </div>"""
        
        html += """
    </div>
</body>
</html>"""
        
        self.send_response(200)
        self.send_header('Content-type', 'text/html')
        self.send_header('Cache-Control', 'no-cache')
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

class ReusableTCPServer(socketserver.TCPServer):
    allow_reuse_address = True

def start_server():
    with ReusableTCPServer(("0.0.0.0", PORT), EnhancedFedShareHandler) as httpd:
        print(f"🚀 Enhanced FedShare server running on http://0.0.0.0:{PORT}")
        print("Enhanced interface with real-time progress tracking!")
        httpd.serve_forever()

if __name__ == "__main__":
    start_server()