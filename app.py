import subprocess
import threading
import os
from flask import Flask, render_template, request, jsonify, redirect, url_for

app = Flask(__name__)

# Global variables to track running processes
running_processes = {}
process_status = {}

@app.route('/')
def home():
    return render_template('index.html', status=process_status)

@app.route('/run/<algorithm>')
def run_algorithm(algorithm):
    """Execute the specified federated learning algorithm"""
    script_map = {
        'fedshare': './start-fedshare.sh',
        'fedavg': './start-fedavg.sh', 
        'scotch': './start-scotch.sh'
    }
    
    if algorithm not in script_map:
        return jsonify({'error': 'Invalid algorithm'}), 400
    
    # Check if already running
    if algorithm in running_processes and running_processes[algorithm].poll() is None:
        return jsonify({'message': f'{algorithm.upper()} is already running'}), 200
    
    try:
        # Start the script in the background
        script_path = script_map[algorithm]
        process = subprocess.Popen(
            [script_path], 
            stdout=subprocess.PIPE, 
            stderr=subprocess.PIPE,
            cwd='.',
            shell=True
        )
        
        running_processes[algorithm] = process
        process_status[algorithm] = 'running'
        
        return redirect(url_for('home'))
        
    except Exception as e:
        process_status[algorithm] = f'error: {str(e)}'
        return jsonify({'error': str(e)}), 500

@app.route('/status/<algorithm>')
def get_status(algorithm):
    """Get the status of a running algorithm"""
    if algorithm in running_processes:
        process = running_processes[algorithm]
        if process.poll() is None:
            return jsonify({'status': 'running'})
        else:
            return jsonify({'status': 'completed', 'returncode': process.returncode})
    return jsonify({'status': 'not_started'})

@app.route('/logs/<algorithm>')
def view_logs(algorithm):
    """View logs for the specified algorithm"""
    log_directories = {
        'fedshare': 'fedshare-mnist-client-5-server-2',
        'fedavg': 'fedavg-mnist-client-5',
        'scotch': 'scotch-mnist-client-5-server-2'
    }
    
    if algorithm not in log_directories:
        return "Invalid algorithm", 404
        
    log_dir = f"logs/{log_directories[algorithm]}"
    if not os.path.exists(log_dir):
        return f"No logs found for {algorithm.upper()}", 404
    
    # Read the latest log files
    log_files = []
    try:
        for filename in os.listdir(log_dir):
            if filename.endswith('.log'):
                filepath = os.path.join(log_dir, filename)
                with open(filepath, 'r') as f:
                    content = f.read()
                log_files.append({'name': filename, 'content': content})
    except Exception as e:
        return f"Error reading logs: {str(e)}", 500
    
    return render_template('logs.html', algorithm=algorithm, log_files=log_files)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)