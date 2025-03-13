import tkinter as tk
from tkinter import filedialog, messagebox
import serial
import serial.tools.list_ports
import matplotlib.pyplot as plt
from mpl_toolkits.mplot3d import Axes3D
import threading

# Global variables
ser = None
gcode_commands = []
serial_lock = threading.Lock()  # To ensure thread-safe serial communication

def connect_to_arduino():
    """Connect to the Arduino using the selected COM port."""
    global ser
    port = port_var.get()
    if not port or port == "No ports available":
        messagebox.showwarning("Oops!", "Please select a valid COM port first!")
        return
    try:
        with serial_lock:
            ser = serial.Serial(port, baudrate=9600, timeout=1)
        status_label.config(text=f"Connected to {port} 🎉", fg="green")
        connect_button.config(state=tk.DISABLED)
        disconnect_button.config(state=tk.NORMAL)
    except serial.SerialException as e:
        messagebox.showerror("Connection Failed", f"Couldn't connect to {port}. Error: {e}")

def disconnect_arduino():
    """Disconnect from the Arduino."""
    global ser
    if ser and ser.is_open:
        with serial_lock:
            ser.close()
        status_label.config(text="Not Connected 😢", fg="red")
        connect_button.config(state=tk.NORMAL)
        disconnect_button.config(state=tk.DISABLED)

def import_gcode():
    """Load a G-code file for printing."""
    global gcode_commands
    file_path = filedialog.askopenfilename(filetypes=[("G-code Files", "*.gcode")])
    if file_path:
        try:
            with open(file_path, "r") as file:
                gcode_lines = file.readlines()
            gcode_commands = parse_gcode(gcode_lines)
            messagebox.showinfo("Success!", "G-code file loaded successfully! 🚀")
        except Exception as e:
            messagebox.showerror("File Error", f"Couldn't read the G-code file. Error: {e}")

def parse_gcode(gcode_lines):
    """Clean up and extract G-code commands from the file."""
    return [line.strip() for line in gcode_lines if line.strip() and not line.startswith(";")]

def send_gcode(commands):
    """Send G-code commands to the Arduino in a separate thread to keep the UI responsive."""
    if not ser or not ser.is_open:
        messagebox.showerror("Not Connected", "Please connect to the Arduino first!")
        return

    def send():
        for command in commands:
            try:
                with serial_lock:
                    ser.write(f"{command}\n".encode())
                    response = ser.readline().decode().strip()
                print(f"Sent: {command}, Arduino says: {response}")
            except Exception as e:
                print(f"Oops! Something went wrong: {e}")
                break
        messagebox.showinfo("Done!", "All G-code commands have been sent! 🎉")

    threading.Thread(target=send, daemon=True).start()

def visualize_gcode(commands):
    """Show a 3D visualization of the G-code path."""
    x, y, z = [], [], []
    last_x, last_y, last_z = 0, 0, 0  # Start from the origin

    for command in commands:
        if "G1" in command:  # Only look at movement commands
            parts = command.split()
            for part in parts:
                if part.startswith("X"):
                    last_x = float(part[1:])
                elif part.startswith("Y"):
                    last_y = float(part[1:])
                elif part.startswith("Z"):
                    last_z = float(part[1:])
            x.append(last_x)
            y.append(last_y)
            z.append(last_z)

    if not x or not y or not z:
        messagebox.showerror("No Data", "No valid movement commands found in the G-code. 🤔")
        return

    fig = plt.figure()
    ax = fig.add_subplot(111, projection="3d")
    ax.plot(x, y, z, marker='o')

    ax.set_xlabel("X Axis")
    ax.set_ylabel("Y Axis")
    ax.set_zlabel("Z Axis")
    ax.set_title("G-code Path Visualization 🖨️")
    plt.show()

def refresh_ports():
    """Update the list of available COM ports."""
    ports = [port.device for port in serial.tools.list_ports.comports()]
    
    if not ports:
        ports = ["No ports available"]

    port_var.set(ports[0])  # Set the default selection
    port_dropdown['menu'].delete(0, 'end')
    
    for port in ports:
        port_dropdown['menu'].add_command(label=port, command=tk._setit(port_var, port))

def create_ui():
    """Set up the main user interface."""
    global port_var, port_dropdown, status_label, connect_button, disconnect_button

    root = tk.Tk()
    root.title("3D Printer Controller 🖨️")

    # COM Port Selection
    tk.Label(root, text="Select COM Port:").grid(row=0, column=0, padx=10, pady=10)
    port_var = tk.StringVar()
    
    # Get available ports or show a message if none are found
    ports = [port.device for port in serial.tools.list_ports.comports()]
    if not ports:
        ports = ["No ports available"]
    
    port_var.set(ports[0])
    port_dropdown = tk.OptionMenu(root, port_var, *ports)
    port_dropdown.grid(row=0, column=1, padx=10, pady=10)

    # Refresh Button for COM ports
    tk.Button(root, text="Refresh 🔄", command=refresh_ports).grid(row=0, column=2, padx=10, pady=10)

    # Connect Button
    connect_button = tk.Button(root, text="Connect 🚀", command=connect_to_arduino)
    connect_button.grid(row=0, column=3, padx=10, pady=10)

    # Disconnect Button
    disconnect_button = tk.Button(root, text="Disconnect 🛑", command=disconnect_arduino, state=tk.DISABLED)
    disconnect_button.grid(row=0, column=4, padx=10, pady=10)

    # G-code Import Button
    tk.Button(root, text="Import G-code 📂", command=import_gcode).grid(row=1, column=0, padx=10, pady=10)

    # Visualize Button
    tk.Button(root, text="Visualize 🎨", command=lambda: visualize_gcode(gcode_commands)).grid(row=1, column=1, padx=10, pady=10)

    # Start Print Button
    tk.Button(root, text="Start Print 🖨️", command=lambda: send_gcode(gcode_commands)).grid(row=1, column=2, padx=10, pady=10)

    # Status Label
    status_label = tk.Label(root, text="Not Connected 😢", fg="red")
    status_label.grid(row=2, column=0, columnspan=5, pady=10)

    root.mainloop()

if __name__ == "__main__":
    create_ui()