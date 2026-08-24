import tkinter as tk
from tkinter import ttk
import paho.mqtt.client as mqtt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
import matplotlib.pyplot as plt
import threading
import queue
import json
from datetime import datetime

class NexusVizProStudio:
    def __init__(self, root):
        self.root = root
        self.root.title("Nexus VizPro Studio v2.0")
        self.root.geometry("1200x800")
        self.root.configure(bg='#2d2d2d')
        self.setup_ui()
        self.data_queue = queue.Queue()
        self.mqtt_client = None
        self.running = True
        self.update_interval = 100
        self.start_data_polling()

    def setup_ui(self):
        # Configure style
        style = ttk.Style()
        style.theme_use('clam')
        style.configure('.', background='#2d2d2d', foreground='white')
        style.configure('TFrame', background='#2d2d2d')
        style.configure('TLabel', background='#2d2d2d', foreground='white')
        style.map('TButton', background=[('active', '#3d3d3d')], foreground=[('active', 'white')])

        # Main frame
        main_frame = ttk.Frame(self.root, padding="10")
        main_frame.pack(fill=tk.BOTH, expand=True)

        # Connection panel
        conn_frame = ttk.Labelframe(main_frame, text="Connection Manager", padding="10")
        conn_frame.grid(row=0, column=0, sticky="nsew", padx=5, pady=5)

        # Protocol selector
        ttk.Label(conn_frame, text="Protocol:").grid(row=0, column=0, sticky="w")
        self.protocol_var = tk.StringVar(value="MQTT")
        protocol_dropdown = ttk.Combobox(conn_frame, textvariable=self.protocol_var, values=["MQTT", "Kafka", "Database"], state="readonly")
        protocol_dropdown.grid(row=0, column=1, sticky="ew")

        # Connection parameters
        ttk.Label(conn_frame, text="Host:").grid(row=1, column=0, sticky="w")
        self.host_entry = ttk.Entry(conn_frame)
        self.host_entry.insert(0, "localhost")
        self.host_entry.grid(row=1, column=1, sticky="ew")

        ttk.Label(conn_frame, text="Port:").grid(row=2, column=0, sticky="w")
        self.port_entry = ttk.Entry(conn_frame)
        self.port_entry.insert(0, "1883")
        self.port_entry.grid(row=2, column=1, sticky="ew")

        ttk.Label(conn_frame, text="Topic/Table:").grid(row=3, column=0, sticky="w")
        self.topic_entry = ttk.Entry(conn_frame)
        self.topic_entry.insert(0, "sensors/#")
        self.topic_entry.grid(row=3, column=1, sticky="ew")

        # Connect button
        self.connect_button = ttk.Button(conn_frame, text="Connect", command=self.toggle_connection)
        self.connect_button.grid(row=4, columnspan=2, pady=10, sticky="ew")

        # Status indicator
        self.status_var = tk.StringVar(value="Disconnected")
        self.status_light = tk.Canvas(conn_frame, width=20, height=20, bg="red", bd=0, highlightthickness=0)
        self.status_light.grid(row=5, column=0, sticky="w", pady=5)
        ttk.Label(conn_frame, textvariable=self.status_var).grid(row=5, column=1, sticky="w")

        # Dashboard frame
        dashboard_frame = ttk.Frame(main_frame)
        dashboard_frame.grid(row=0, column=1, rowspan=2, sticky="nsew", padx=5, pady=5)

        # Notebook for multiple panels
        self.notebook = ttk.Notebook(dashboard_frame)
        self.notebook.pack(fill=tk.BOTH, expand=True)

        # Add default tabs
        self.add_dashboard_tab("Live Charts")
        self.add_dashboard_tab("Data Grid")

        # Configure grid weights
        main_frame.columnconfigure(0, weight=1)
        main_frame.columnconfigure(1, weight=3)
        main_frame.rowconfigure(0, weight=1)

        # Configure root weights
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(0, weight=1)

    def add_dashboard_tab(self, name):
        tab = ttk.Frame(self.notebook, padding="5")
        self.notebook.add(tab, text=name)

        # Figure for plotting
        fig, ax = plt.subplots(figsize=(8, 4), facecolor='#2d2d2d')
        ax.set_facecolor('#2d2d2d')
        ax.tick_params(colors='white')
        ax.xaxis.label.set_color('white')
        ax.yaxis.label.set_color('white')
        ax.title.set_color('white')

        # Canvas for the figure
        canvas = FigureCanvasTkAgg(fig, master=tab)
        canvas_widget = canvas.get_tk_widget()
        canvas_widget.pack(fill=tk.BOTH, expand=True)

        if "Chart" in name:
            ax.set_title("Live Data Chart", color="white")
            ax.grid(color='#3d3d3d', linestyle='--', linewidth=0.5)
            tab.figure = fig
            tab.canvas = canvas
            tab.ax = ax
            tab.data = []
        elif "Grid" in name:
            # Create a Treeview widget
            tree = ttk.Treeview(tab, columns=("timestamp", "source", "value"), show="headings")
            tree.heading("timestamp", text="Timestamp")
            tree.heading("source", text="Source")
            tree.heading("value", text="Value")
            tree.pack(fill=tk.BOTH, expand=True)
            tab.tree = tree

    def toggle_connection(self):
        if self.status_var.get() == "Disconnected":
            protocol = self.protocol_var.get()
            if protocol == "MQTT":
                self.connect_mqtt()
            elif protocol == "Kafka":
                # Kafka connection would go here
                self.status_var.set("Connected to Kafka")
                self.status_light.config(bg="green")
                self.connect_button.config(text="Disconnect")
            elif protocol == "Database":
                # Database connection would go here
                self.status_var.set("Connected to Database")
                self.status_light.config(bg="green")
                self.connect_button.config(text="Disconnect")
        else:
            self.disconnect()

    def connect_mqtt(self):
        host = self.host_entry.get()
        port = int(self.port_entry.get())
        topic = self.topic_entry.get()

        self.mqtt_client = mqtt.Client()
        self.mqtt_client.on_connect = self.on_mqtt_connect
        self.mqtt_client.on_message = self.on_mqtt_message

        try:
            self.mqtt_client.connect(host, port, 60)
            self.mqtt_client.subscribe(topic)
            self.mqtt_client.loop_start()
            self.status_var.set(f"Connected to {host}")
            self.status_light.config(bg="green")
            self.connect_button.config(text="Disconnect")
        except Exception as e:
            self.status_var.set(f"Connection failed: {str(e)}")
            self.status_light.config(bg="red")

    def disconnect(self):
        if self.mqtt_client:
            self.mqtt_client.loop_stop()
            self.mqtt_client.disconnect()
        self.status_var.set("Disconnected")
        self.status_light.config(bg="red")
        self.connect_button.config(text="Connect")

    def on_mqtt_connect(self, client, userdata, flags, rc):
        if rc == 0:
            self.data_queue.put(("status", f"Connected to MQTT broker"))

    def on_mqtt_message(self, client, userdata, msg):
        try:
            payload = msg.payload.decode("utf-8")
            data = json.loads(payload)
            timestamp = datetime.now().strftime("%H:%M:%S")
            self.data_queue.put(("data", {"timestamp": timestamp, "source": msg.topic, "value": data}))
        except Exception as e:
            self.data_queue.put(("error", f"Error processing message: {str(e)}"))

    def start_data_polling(self):
        def poll_data():
            while self.running:
                try:
                    item = self.data_queue.get_nowait()
                    item_type, content = item

                    if item_type == "data":
                        self.update_dashboard(content)
                    elif item_type == "status":
                        self.status_var.set(content)
                    elif item_type == "error":
                        print(f"Error: {content}")

                except queue.Empty:
                    pass

                self.root.after(self.update_interval, poll_data)

        self.root.after(0, poll_data)

    def update_dashboard(self, data):
        for tab_id in range(self.notebook.index("end")):
            tab = self.notebook.nametowidget(self.notebook.tabs()[tab_id])
            tab_name = self.notebook.tab(tab_id, "text")

            if "Live Charts" in tab_name:
                if not hasattr(tab, 'data'):
                    tab.data = []
                
                tab.data.append(float(data['value']))
                if len(tab.data) > 50:  # Keep only last 50 points
                    tab.data = tab.data[-50:]
                
                tab.ax.clear()
                tab.ax.plot(tab.data, color='cyan')
                tab.ax.set_title("Live Data Chart", color="white")
                tab.ax.set_xlabel("Time (samples)", color="white")
                tab.ax.set_ylabel("Value", color="white")
                tab.ax.grid(color='#3d3d3d', linestyle='--', linewidth=0.5)
                tab.canvas.draw()
                
            elif "Data Grid" in tab_name:
                tab.tree.insert("", "end", values=(data['timestamp'], data['source'], data['value']))
                if tab.tree.get_children():
                    tab.tree.yview_moveto(1)  # Auto-scroll to bottom

    def on_closing(self):
        self.running = False
        self.disconnect()
        self.root.destroy()

if __name__ == "__main__":
    root = tk.Tk()
    app = NexusVizProStudio(root)
    root.protocol("WM_DELETE_WINDOW", app.on_closing)
    root.mainloop()