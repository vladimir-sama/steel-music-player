import tkinter as tk
from tkinter import ttk
import yt_dlp
import mpv
import time
import threading
import json

class MusicPlayer:
    def __init__(self, root):
        self.root = root
        self.root.title("Steel Music Player")
        self.root.geometry("500x400")

        root.tk.call("source", "azure.tcl")
        root.tk.call("set_theme", "dark")

        # MPV Media Player
        self.player = mpv.MPV(ytdl=True, input_default_bindings=True, input_vo_keyboard=True, video=False)
        self.player.loop_file = 'inf'

        # Track and state variables
        self.track_url = None
        self.is_paused = False
        self.current_volume = 100
        self.is_playing = False
        self.track_length = 0
        self.is_user_dragging = False  # Flag to track when the user is dragging the slider

        # Playlist data and search
        self.playlist = {}  # Dictionary to hold playlist names and URLs
        self.playlist_titles = []  # List to hold playlist names
        self.tracks = []  # List to hold tracks from the selected playlist

        # Load playlists from JSON file
        self.load_playlists_from_json('playlists.json')

        # GUI Components
        self.create_widgets()

    def load_playlists_from_json(self, json_file):
        with open(json_file, 'r') as file:
            self.playlist = json.load(file)  # Load JSON into the playlist dictionary
            self.playlist_titles = list(self.playlist.keys())  # Extract keys for display in ComboBox

    def create_widgets(self):
        # Frame for Playlist selection
        playlist_frame = ttk.Frame(self.root)
        playlist_frame.pack(pady=10)

        self.playlist_combobox = ttk.Combobox(playlist_frame, values=self.playlist_titles, width=50)
        self.playlist_combobox.pack(side=tk.LEFT, padx=(5, 0))
        self.playlist_combobox.bind("<<ComboboxSelected>>", self.load_selected_playlist)

        # Search Bar for filtering tracks
        search_frame = ttk.Frame(self.root)
        search_frame.pack(pady=10)

        self.filter_entry = ttk.Entry(search_frame, width=50)
        self.filter_entry.pack(side=tk.LEFT, padx=(5, 0))
        self.filter_entry.bind("<KeyRelease>", self.filter_tracks)

        # Playlist Listbox
        playlist_box_frame = ttk.Frame(self.root)
        playlist_box_frame.pack(pady=10, fill=tk.Y, expand=True)
        self.playlist_box = tk.Listbox(playlist_box_frame, height=10, width=60, bg="#161616", fg="white", selectbackground="#007fff")
        self.playlist_box.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        self.playlist_box.bind("<Double-Button-1>", self.select_track)

        # Scrollbar
        self.scrollbar = ttk.Scrollbar(playlist_box_frame)
        self.scrollbar.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True)

        self.playlist_box.config(yscrollcommand = self.scrollbar.set)
        self.scrollbar.config(command = self.playlist_box.yview)

        # Control Frame for Play/Pause, Volume, and Seek
        controls_frame = tk.Frame(self.root)
        controls_frame.pack(pady=10)

        self.play_button = ttk.Button(controls_frame, text="Play", command=self.toggle_play)
        self.play_button.pack(side=tk.LEFT, padx=(5, 0))

        # Volume Slider
        self.volume_slider = ttk.Scale(controls_frame, from_=0, to=100, command=self.set_volume, orient='horizontal')
        self.volume_slider.set(self.current_volume)
        self.volume_slider.pack(side=tk.LEFT, padx=(10, 0))

        # Seek Slider
        self.seek_slider = ttk.Scale(controls_frame, from_=0, to=100, orient='horizontal', length=240)
        self.seek_slider.pack(side=tk.LEFT, padx=(10, 0), fill=tk.X, expand=True)

        # Bind seek slider events
        self.seek_slider.bind("<ButtonPress-1>", self.seek_start)
        self.seek_slider.bind("<ButtonRelease-1>", self.seek_end)

    def load_selected_playlist(self, event):
        selected_index = self.playlist_combobox.current()
        selected_playlist_name = self.playlist_titles[selected_index]
        self.track_url = self.playlist[selected_playlist_name]  # Get the URL from the dictionary
        self.load_playlist(self.track_url)

    def load_playlist(self, playlist_url):
        if not playlist_url:
            return

        # Scrape YouTube Music Playlist using yt-dlp
        def scrape_playlist():
            ydl_opts = {
                'extract_flat': True,  # Only fetch metadata, not the videos
                'skip_download': True,
            }
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(playlist_url, download=False)
                self.tracks = [{'title': entry['title'], 'url': entry['url']} for entry in info['entries']]
                self.update_playlist_box()

        # Run the scraping in a separate thread to avoid blocking the UI
        threading.Thread(target=scrape_playlist).start()

    def update_playlist_box(self):
        # Update the Listbox with playlist titles
        self.playlist_box.delete(0, tk.END)
        for idx, track in enumerate(self.tracks):
            self.playlist_box.insert(tk.END, str(idx + 1) + '. ' + track['title'])

    def filter_tracks(self, event=None):
        search_term = self.filter_entry.get().lower()
        filtered_tracks = [{'title': str(idx + 1) + '. ' + track['title'], 'url': track['url']} for idx, track in enumerate(self.tracks) if search_term in track['title'].lower()]
        self.update_filtered_playlist_box(filtered_tracks)

    def update_filtered_playlist_box(self, filtered_tracks):
        # Update the Listbox with filtered track titles
        self.playlist_box.delete(0, tk.END)
        for track in filtered_tracks:
            self.playlist_box.insert(tk.END, track['title'])

    def select_track(self, event):
        selected_index = int(self.playlist_box.get(self.playlist_box.curselection()[0]).split('.')[0]) - 1
        selected_track = self.tracks[selected_index]
        self.track_url = selected_track['url']
        self.play_track()

    def play_track(self):
        if self.track_url:
            if self.is_playing:
                self.is_playing = False
                time.sleep(0.55)
            self.is_playing = True

            # Set the media URL to the MPV player
            self.track_length = 0
            self.player.play(self.track_url)
            self.play_button.config(text="Pause")

            # Get the length of the track in milliseconds
            threading.Thread(target=self.update_seek_slider).start()

    def update_seek_slider(self):
        while self.is_playing:
            time.sleep(0.25)
            if not self.is_paused and not self.is_user_dragging:
                # MPV player provides track length, so we can update the slider
                if self.track_length == 0 and self.player.duration:
                    self.track_length = int(self.player.duration)  # Get track length in seconds
                    if self.track_length > 0:
                        self.seek_slider.config(to=self.track_length)  # Length in seconds

                # Update seek slider position without triggering slider events
                if self.player.time_pos:
                    current_time = int(self.player.time_pos)  # Time in seconds
                    self.seek_slider.set(current_time)

    def seek_start(self, event):
        """Disable auto-seek update when user interacts with the slider"""
        self.is_user_dragging = True

    def seek_end(self, event):
        """Enable the slider and jump to the selected track position"""
        self.is_user_dragging = False
        position = self.seek_slider.get()
        self.player.seek(position)  # Seek to the selected position in seconds

    def toggle_play(self):
        if self.is_playing:
            if self.is_paused:
                self.player.pause = False
                self.play_button.config(text="Pause")
                self.is_paused = False
            else:
                self.player.pause = True
                self.play_button.config(text="Play")
                self.is_paused = True
        else:
            self.play_track()

    def set_volume(self, volume_level):
        volume = int(float(volume_level))
        self.player.volume = volume

# Create and start the Tkinter app
if __name__ == "__main__":
    root = tk.Tk()
    app = MusicPlayer(root)
    root.mainloop()
