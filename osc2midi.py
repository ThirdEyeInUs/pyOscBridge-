import tkinter as tk
from tkinter import ttk, messagebox
from pythonosc import dispatcher, osc_server, udp_client
import mido
from mido import Message
import threading
import socket
import json
import os
from PIL import Image, ImageTk
import re
import time

class OSCMIDIApp:
    CONFIG_FILE = "config.json"

    def __init__(self, master):
        self.master = master
        self.master.title("OSC2MIDI")

        # Charger l'icône
        self.load_icon()

        # Charger les paramètres sauvegardés
        self.load_config()

        # Configuration de l'interface
        self.setup_ui()

        # Variables pour stocker l'état
        self.midi_out = None
        self.osc_client = None
        self.midi_in_thread = None
        self.osc_server_thread = None
        self.active_notes = {}

    def load_icon(self):
        try:
            icon_path = os.path.join(os.path.dirname(__file__), "icon.png")
            self.master.iconphoto(False, ImageTk.PhotoImage(Image.open(icon_path)))
        except Exception as e:
            print(f"Erreur lors du chargement de l'icône : {e}")

    def load_config(self):
        if os.path.exists(self.CONFIG_FILE):
            with open(self.CONFIG_FILE, 'r') as f:
                config = json.load(f)
                self.saved_port = config.get("osc_in_port", "")
                self.saved_midi_port = config.get("midi_input_port", "")
                self.saved_midi_out_port = config.get("midi_output_port", "")
                self.saved_out_ip = config.get("osc_out_ip", "192.168.0.0")
                self.saved_out_port = config.get("osc_out_port", "")
        else:
            self.saved_port = ""
            self.saved_midi_port = ""
            self.saved_midi_out_port = ""
            self.saved_out_ip = "192.168.0.0"
            self.saved_out_port = ""

        self.saved_ip = self.get_local_ip()

    def save_config(self):
        config = {
            "osc_in_port": self.saved_port,
            "midi_input_port": self.saved_midi_port,
            "midi_output_port": self.saved_midi_out_port,
            "osc_out_ip": self.saved_out_ip,
            "osc_out_port": self.saved_out_port,
        }
        with open(self.CONFIG_FILE, 'w') as f:
            json.dump(config, f)

    def setup_ui(self):
        self.ip_label = tk.Label(self.master, text="IP pour OSC In:")
        self.ip_label.pack()

        self.ip_entry = tk.Entry(self.master)
        self.ip_entry.insert(0, self.saved_ip)
        self.ip_entry.config(state='readonly')
        self.ip_entry.pack()

        self.port_label = tk.Label(self.master, text="Port pour OSC In:")
        self.port_label.pack()

        self.port_entry = tk.Entry(self.master)
        self.port_entry.insert(0, self.saved_port)
        self.port_entry.pack()

        self.midi_label = tk.Label(self.master, text="Choisir MIDI Input:")
        self.midi_label.pack()

        self.midi_input_combo = ttk.Combobox(self.master, values=self.get_midi_ports())
        self.midi_input_combo.set(self.saved_midi_port)
        self.midi_input_combo.pack()

        self.midi_out_label = tk.Label(self.master, text="Choisir MIDI Output:")
        self.midi_out_label.pack()

        self.midi_out_combo = ttk.Combobox(self.master, values=self.get_midi_output_ports())
        self.midi_out_combo.set(self.saved_midi_out_port)
        self.midi_out_combo.pack()

        self.output_ip_label = tk.Label(self.master, text="IP pour OSC Out:")
        self.output_ip_label.pack()

        self.output_ip_entry = tk.Entry(self.master)
        self.output_ip_entry.insert(0, self.saved_out_ip)
        self.output_ip_entry.pack()

        self.output_port_label = tk.Label(self.master, text="Port pour OSC Out:")
        self.output_port_label.pack()

        self.output_port_entry = tk.Entry(self.master)
        self.output_port_entry.insert(0, self.saved_out_port)
        self.output_port_entry.pack()

        self.start_button = tk.Button(self.master, text="Démarrer", command=self.start)
        self.start_button.pack()

        # Log area
        self.log_label = tk.Label(self.master, text="Messages de Log:")
        self.log_label.pack()

        self.log_text = tk.Text(self.master, height=10, width=50)
        self.log_text.pack()

        # Scrollbar for the log
        self.log_scroll = tk.Scrollbar(self.master, command=self.log_text.yview)
        self.log_text.config(yscrollcommand=self.log_scroll.set)
        self.log_scroll.pack(side=tk.RIGHT, fill=tk.Y)

    def get_local_ip(self):
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip

    def get_midi_ports(self):
        return mido.get_input_names()

    def get_midi_output_ports(self):
        return mido.get_output_names()

    def start(self):
        if self.start_button['text'] == "Démarrer":
            midi_input_port_name = self.midi_input_combo.get()
            midi_output_port_name = self.midi_out_combo.get()
            osc_out_ip = self.output_ip_entry.get()
            osc_out_port = int(self.output_port_entry.get())
            osc_in_port = int(self.port_entry.get())

            if not midi_input_port_name:
                messagebox.showerror("Erreur", "Veuillez sélectionner un port MIDI d'entrée.")
                return

            if not midi_output_port_name:
                messagebox.showerror("Erreur", "Veuillez sélectionner un port MIDI de sortie.")
                return

            if self.is_port_in_use(osc_in_port):
                messagebox.showerror("Erreur", f"Le port {osc_in_port} est déjà utilisé. Veuillez en choisir un autre.")
                return

            try:
                self.midi_out = mido.open_output(midi_output_port_name)
            except (IOError, ValueError) as e:
                messagebox.showerror("Erreur MIDI", f"Impossible d'ouvrir le port MIDI de sortie : {e}")
                return

            try:
                midi_in = mido.open_input(midi_input_port_name)
            except (IOError, ValueError) as e:
                messagebox.showerror("Erreur MIDI", f"Impossible d'ouvrir le port MIDI d'entrée : {e}")
                return

            self.osc_client = udp_client.SimpleUDPClient(osc_out_ip, osc_out_port)

            self.osc_server_thread = threading.Thread(target=self.start_osc_server, args=(osc_in_port,), daemon=True)
            self.osc_server_thread.start()
            self.midi_in_thread = threading.Thread(target=self.midi_to_osc, args=(midi_in,), daemon=True)
            self.midi_in_thread.start()

            self.saved_out_ip = osc_out_ip
            self.saved_out_port = osc_out_port
            self.saved_port = osc_in_port
            self.saved_midi_port = midi_input_port_name
            self.saved_midi_out_port = midi_output_port_name
            self.save_config()

            self.start_button.config(text="Arrêter et Quitter")
        else:
            self.quit_app()

    def quit_app(self):
        self.master.quit()

    def is_port_in_use(self, port):
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
            try:
                s.bind(('0.0.0.0', port))
                return False
            except OSError:
                return True

    def start_osc_server(self, osc_in_port):
        self.dispatcher = dispatcher.Dispatcher()
        self.dispatcher.map("/*", self.handle_osc_message)

        self.server = osc_server.BlockingOSCUDPServer((self.get_local_ip(), osc_in_port), self.dispatcher)
        print(f"Listening for OSC messages on {self.get_local_ip()}:{osc_in_port}")
        self.server.serve_forever()

    def handle_osc_message(self, address, *args):
        match = re.match(r"/ch(\d+)", address)
        if match:
            channel = int(match.group(1)) - 1

            if "cc" in address:
                control = int(address.split("cc")[1])
                value = int(args[0])
                midi_message = Message('control_change', channel=channel, control=control, value=value)
                self.midi_out.send(midi_message)
                self.log_message(f"OUT: {midi_message}")

            elif "n" in address:
                note = int(address.split("n")[1])
                velocity = int(args[0])
                midi_message = Message('note_on' if velocity > 0 else 'note_off', channel=channel, note=note, velocity=velocity)
                self.midi_out.send(midi_message)
                self.log_message(f"OUT: {midi_message}")

            elif "pressure" in address:
                value = int(args[0])
                value = max(0, min(value, 127))
                midi_message = Message('aftertouch', channel=channel, value=value)
                self.midi_out.send(midi_message)
                self.log_message(f"OUT: {midi_message}")

            elif "pitch" in address:
                pitch = int(args[0])
                midi_message = Message('pitchwheel', channel=channel, pitch=pitch)
                self.midi_out.send(midi_message)
                self.log_message(f"OUT: {midi_message}")

    def midi_to_osc(self, midi_in):
        while True:
            message = midi_in.receive()

            note_id = int(time.time() * 1000)

            if message.type == 'note_on':
                osc_address = f"/ch{message.channel + 1}n{message.note}"
                self.osc_client.send_message(osc_address, message.velocity)
                self.log_message(f"IN: {osc_address} {message.velocity}")

                self.osc_client.send_message(f"/ch{message.channel + 1}note", message.note)
                self.osc_client.send_message(f"/ch{message.channel + 1}nvalue", message.velocity)

            elif message.type == 'note_off':
                self.osc_client.send_message(f"/ch{message.channel + 1}noteoff", message.note)
                self.osc_client.send_message(f"/ch{message.channel + 1}noffvalue", 0)
                self.log_message(f"IN: /ch{message.channel + 1}noteoff {message.note}")

            elif message.type == 'control_change':
                osc_address = f"/ch{message.channel + 1}cc{message.control}"
                self.osc_client.send_message(osc_address, message.value)
                self.log_message(f"IN: {osc_address} {message.value}")
                self.osc_client.send_message(f"/ch{message.channel + 1}cc", message.control)
                self.osc_client.send_message(f"/ch{message.channel + 1}ccvalue", message.value)

            elif message.type == 'aftertouch':
                osc_address = f"/ch{message.channel + 1}pressure"
                self.osc_client.send_message(osc_address, message.value)
                self.log_message(f"IN: {osc_address} {message.value}")

            elif message.type == 'pitchwheel':
                osc_address = f"/ch{message.channel + 1}pitch"
                self.osc_client.send_message(osc_address, message.pitch)
                self.log_message(f"IN: {osc_address} {message.pitch}")

    def log_message(self, message):
        self.log_text.insert(tk.END, f"{message}\n")
        self.log_text.yview(tk.END)  # Scroll to the latest message
        self.log_text.update_idletasks()  # Ensure the GUI updates

if __name__ == "__main__":
    root = tk.Tk()
    app = OSCMIDIApp(root)
    root.mainloop()
