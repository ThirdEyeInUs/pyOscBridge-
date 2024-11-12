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
import re  # Importation de re pour l'expression régulière

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

    def load_icon(self):
        try:
            icon_path = os.path.join(os.path.dirname(__file__), "icon.png")
            self.master.iconphoto(False, ImageTk.PhotoImage(Image.open(icon_path)))
        except Exception as e:
            print(f"Erreur lors du chargement de l'icône : {e}")

    def load_config(self):
        # Charger les paramètres sauvegardés sans l'adresse IP locale
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

        # Récupérer dynamiquement l'IP locale de l'hôte à chaque lancement
        self.saved_ip = self.get_local_ip()

    def save_config(self):
        # Sauvegarder les paramètres, sans l'adresse IP locale
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
        self.ip_entry.insert(0, self.saved_ip)  # L'adresse IP locale est affichée ici
        self.ip_entry.config(state='readonly')  # L'IP est en lecture seule
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

    def get_local_ip(self):
        # Fonction pour obtenir l'IP locale de l'hôte
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))  # Connexion à un serveur DNS public
        ip = s.getsockname()[0]
        s.close()
        return ip

    def get_midi_ports(self):
        return mido.get_input_names()

    def get_midi_output_ports(self):
        return mido.get_output_names()  # Liste des périphériques MIDI sortants

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
        # Utilisation d'une expression régulière pour extraire le numéro de canal
        match = re.match(r"/ch(\d+)", address)
        if match:
            channel = int(match.group(1)) - 1  # Ajuste le canal pour MIDI (0-15)

            if "cc" in address:
                control = int(address.split("cc")[1])
                value = int(args[0])
                midi_message = Message('control_change', channel=channel, control=control, value=value)
                self.midi_out.send(midi_message)

            elif "n" in address:
                note = int(address.split("n")[1])
                velocity = int(args[0])
                midi_message = Message('note_on' if velocity > 0 else 'note_off', channel=channel, note=note, velocity=velocity)
                self.midi_out.send(midi_message)

            elif "pressure" in address:
                value = int(args[0])
                value = max(0, min(value, 127))  # Limiter la valeur entre 0 et 127
                midi_message = Message('aftertouch', channel=channel, value=value)
                self.midi_out.send(midi_message)

            elif "pitch" in address:
                value = int(args[0])
                value = max(-8192, min(value, 8191))  # Limiter la valeur entre -8192 et 8191
                midi_message = Message('pitchwheel', channel=channel, pitch=value)
                self.midi_out.send(midi_message)

    def midi_to_osc(self, midi_in):
        while True:
            message = midi_in.receive()
            if message.type == 'note_on':
                # Ancien format OSC : /chXnY Z
                osc_address = f"/ch{message.channel + 1}n{message.note}"
                self.osc_client.send_message(osc_address, message.velocity)

                # Nouveau format OSC détaillé : /channel X, /note Y, /value Z
                self.osc_client.send_message(f"/channel", message.channel + 1)
                self.osc_client.send_message(f"/note", message.note)
                self.osc_client.send_message(f"/value", message.velocity)

            elif message.type == 'note_off':
                # Ancien format OSC : /chXnY 0
                osc_address = f"/ch{message.channel + 1}n{message.note}"
                self.osc_client.send_message(osc_address, 0)

                # Nouveau format OSC détaillé : /channel X, /note Y, /value 0
                self.osc_client.send_message(f"/channel", message.channel + 1)
                self.osc_client.send_message(f"/note", message.note)
                self.osc_client.send_message(f"/value", 0)

            elif message.type == 'control_change':
                # Ancien format OSC : /chXccY Z
                osc_address = f"/ch{message.channel + 1}cc{message.control}"
                self.osc_client.send_message(osc_address, message.value)

                # Nouveau format OSC détaillé : /channel X, /cc Y, /value Z
                self.osc_client.send_message(f"/channel", message.channel + 1)
                self.osc_client.send_message(f"/cc", message.control)
                self.osc_client.send_message(f"/value", message.value)

            elif message.type == 'aftertouch':
                # Ancien format OSC : /chXpressure Z
                osc_address = f"/ch{message.channel + 1}pressure"
                self.osc_client.send_message(osc_address, message.value)

                # Nouveau format OSC détaillé : /channel X, /pressure, /value Z
                self.osc_client.send_message(f"/channel", message.channel + 1)
                self.osc_client.send_message(f"/pressure", message.value)
                self.osc_client.send_message(f"/value", message.value)

            elif message.type == 'pitchwheel':
                # Ancien format OSC : /chXpitch Z
                osc_address = f"/ch{message.channel + 1}pitch"
                self.osc_client.send_message(osc_address, message.pitch)

                # Nouveau format OSC détaillé : /channel X, /pitch, /value Z
                self.osc_client.send_message(f"/channel", message.channel + 1)
                self.osc_client.send_message(f"/pitch", message.pitch)
                self.osc_client.send_message(f"/value", message.pitch)

if __name__ == "__main__":
    root = tk.Tk()
    app = OSCMIDIApp(root)
    root.mainloop()
