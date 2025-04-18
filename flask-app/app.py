from flask import Flask, request, render_template, jsonify, url_for
import serial
import serial.tools.list_ports
import threading
import os
from werkzeug.utils import secure_filename

app = Flask(__name__)
app.config.update({
    'UPLOAD_FOLDER': 'static/uploads',
    'ALLOWED_EXTENSIONS': {'gcode', 'txt'},
    'MAX_CONTENT_LENGTH': 16 * 1024 * 1024
})

# Shared state
serial_lock = threading.Lock()
ser = None
gcode_commands = []
printer_status = {
    'connected': False,
    'printing': False,
    'progress': 0
}

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in app.config['ALLOWED_EXTENSIONS']

@app.route("/")
def index():
    ports = [port.device for port in serial.tools.list_ports.comports()]
    return render_template('index.html', ports=ports, status=printer_status)

@app.route("/connect", methods=["POST"])
def connect():
    global ser, printer_status
    port = request.form.get("port")
    
    try:
        with serial_lock:
            if ser and ser.is_open:
                ser.close()
            ser = serial.Serial(port, baudrate=115200, timeout=1)
            printer_status['connected'] = True
            
            return jsonify({
                'status': 'success',
                'message': f'Connected to {port}',
                'port': port,
                'connected': True
            })
            
    except Exception as e:
        printer_status['connected'] = False
        return jsonify({
            'status': 'error',
            'message': str(e),
            'connected': False
        }), 400

@app.after_request
def add_security_headers(response):
    response.headers['X-Content-Type-Options'] = 'nosniff'
    response.headers['X-Frame-Options'] = 'SAMEORIGIN'
    return response

@app.route("/upload", methods=["POST"])
def upload():
    if 'gcode' not in request.files:
        return jsonify({'status': 'error', 'message': 'No file part'}), 400
        
    file = request.files['gcode']
    if file.filename == '':
        return jsonify({'status': 'error', 'message': 'No selected file'}), 400

    if not allowed_file(file.filename):
        return jsonify({'status': 'error', 'message': 'Invalid file type'}), 400

    try:
        filename = secure_filename(file.filename)
        os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        file.save(filepath)
        
        with open(filepath, 'r') as f:
            global gcode_commands
            gcode_commands = [
                line.strip() for line in f 
                if line.strip() and not line.startswith(";")
            ]
            
        return jsonify({
            'status': 'success',
            'filename': filename,
            'count': len(gcode_commands),
            'message': f'Uploaded {len(gcode_commands)} commands'
        })
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500

@app.route("/visualize")
def visualize():
    if not gcode_commands:
        return "No G-code loaded", 400

    # Basic example: plot number of commands vs line index
    import matplotlib.pyplot as plt
    from matplotlib.figure import Figure

    # Create a simple plot (e.g. number of commands)
    fig = Figure()
    ax = fig.subplots()
    ax.plot(range(len(gcode_commands)), [1]*len(gcode_commands), label="G-code lines")
    ax.set_title("G-code Command Preview")
    ax.set_xlabel("Line")
    ax.set_ylabel("Command Presence")
    fig.tight_layout()

    # Save to static file
    image_path = os.path.join(app.static_folder, "gcode_plot.png")
    fig.savefig(image_path)

    return render_template("index.html", ports=[p.device for p in serial.tools.list_ports.comports()],
                           status=printer_status, gcode_commands=gcode_commands,
                           image_url=url_for('static', filename='gcode_plot.png'))


if __name__ == "__main__":
    os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
    app.run(debug=True, host='0.0.0.0')