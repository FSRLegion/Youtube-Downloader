import threading
import tkinter as tk
from tkinter import filedialog, messagebox
from pytube import YouTube, exceptions
from moviepy.video.io.ffmpeg_tools import ffmpeg_extract_subclip
from urllib.parse import urlparse, parse_qs
import re
import os
import queue
from ttkthemes import ThemedTk
from tkinter import ttk
import time

class VideoDownloader:
    def __init__(self, root):
        self.root = root
        self.download_directory = ''
        self.progress_queue = queue.Queue()
        self.stream = None
        self.start_time = None

        self.create_gui()

    def create_gui(self):
        self.root.configure(bg='lightgray')
        self.root.title('YouTube Video Downloader')
        self.root.geometry('700x500')

        main_frame = ttk.Frame(self.root, padding=20)
        main_frame.pack(expand=True)

        url_label = ttk.Label(main_frame, text="YouTube URL:")
        url_label.grid(row=0, column=0, sticky="w", pady=5)

        self.url_entry = ttk.Entry(main_frame)
        self.url_entry.grid(row=0, column=1, padx=10, pady=5, sticky="we")

        start_time_label = ttk.Label(main_frame, text="Start time (s):")
        start_time_label.grid(row=1, column=0, sticky="w", pady=5)

        self.start_time_entry = ttk.Entry(main_frame)
        self.start_time_entry.grid(row=1, column=1, padx=10, pady=5, sticky="we")

        end_time_label = ttk.Label(main_frame, text="End time (s):")
        end_time_label.grid(row=2, column=0, sticky="w", pady=5)

        self.end_time_entry = ttk.Entry(main_frame)
        self.end_time_entry.grid(row=2, column=1, padx=10, pady=5, sticky="we")

        filename_label = ttk.Label(main_frame, text="Output File Name:")
        filename_label.grid(row=3, column=0, sticky="w", pady=5)

        self.filename_entry = ttk.Entry(main_frame)
        self.filename_entry.grid(row=3, column=1, padx=10, pady=5, sticky="we")

        download_dir_label = ttk.Label(main_frame, text="Download Directory:")
        download_dir_label.grid(row=4, column=0, sticky="w", pady=5)

        self.download_dir_entry = ttk.Entry(main_frame)
        self.download_dir_entry.grid(row=4, column=1, padx=10, pady=5, sticky="we")

        download_dir_button = ttk.Button(main_frame, text="Set Download Directory", command=self.set_download_directory)
        download_dir_button.grid(row=5, column=0, columnspan=2, pady=10)

        self.progress_bar = ttk.Progressbar(main_frame, length=300, mode='determinate', style="CustomGreen.Horizontal.TProgressbar")
        self.progress_bar.grid(row=6, column=0, columnspan=2, pady=10)

        self.progress_status_label = ttk.Label(main_frame, text="", background='lightgray')
        self.progress_status_label.grid(row=7, column=0, columnspan=2, pady=5)

        download_button = ttk.Button(main_frame, text="Download and Crop", command=self.download_and_crop)
        download_button.grid(row=8, column=0, columnspan=2, pady=10)

        main_frame.columnconfigure(1, weight=1)
        main_frame.rowconfigure(8, weight=1)

        self.root.after(100, self.update_progress)

    def set_download_directory(self):
        self.download_directory = filedialog.askdirectory()
        self.download_dir_entry.delete(0, tk.END)
        self.download_dir_entry.insert(0, self.download_directory)

    def is_valid_url(self, url):
        youtube_regex = r"(https?://)?(www\.)?(youtube|youtu|youtube-nocookie)\.(com|be)/"
        youtube_url_format = re.match(youtube_regex, url)
        return bool(youtube_url_format)

    def download_youtube_video(self, youtube_url, on_progress):
        try:
            yt = YouTube(youtube_url, on_progress_callback=on_progress)
            self.stream = yt.streams.get_highest_resolution()
            return self.stream.download(output_path=self.download_directory)
        except exceptions.RegexMatchError:
            raise ValueError("The provided URL is not a valid YouTube URL")
        except Exception as e:
            raise RuntimeError(f"An error occurred while downloading: {str(e)}")

    def crop_video(self, video_path, start_time, end_time, output_path):
        try:
            ffmpeg_extract_subclip(video_path, start_time, end_time, targetname=output_path)
        except Exception as e:
            raise RuntimeError(f"An error occurred while cropping: {str(e)}")

    def update_progress(self):
        try:
            progress = self.progress_queue.get(0)
            self.progress_bar['value'] = progress

            total_size = self.stream.filesize
            bytes_downloaded = (progress / 100) * total_size
            elapsed_time = time.time() - self.start_time

            if elapsed_time > 0 and bytes_downloaded > 0:
                download_speed = bytes_downloaded / elapsed_time
                remaining_time = (total_size - bytes_downloaded) / download_speed

                minutes = int(remaining_time // 60)
                seconds = int(remaining_time % 60)

                self.progress_status_label['text'] = f"Time Remaining: {minutes} minutes {seconds} seconds"
            else:
                self.progress_status_label['text'] = "Calculating..."

        except queue.Empty:
            pass

        self.root.after(100, self.update_progress)

    def download_and_crop(self):
        youtube_url = self.url_entry.get()

        if not self.is_valid_url(youtube_url):
            messagebox.showerror("Error", "Please enter a valid YouTube URL.")
            return

        try:
            self.start_time = int(self.start_time_entry.get())
            end_time = int(self.end_time_entry.get())
        except ValueError:
            messagebox.showerror("Error", "Please enter valid start and end times.")
            return

        output_file_name = self.filename_entry.get()
        if not output_file_name:
            output_file_name = "output"

        download_directory = self.download_dir_entry.get()
        output_file = os.path.join(download_directory, output_file_name + '.mp4')

        download_button = self.root.focus_get()
        download_button['state'] = 'disabled'
        self.progress_bar['value'] = 0

        def on_progress(stream, chunk, bytes_remaining):
            total_size = stream.filesize
            bytes_downloaded = total_size - bytes_remaining
            percentage = (bytes_downloaded / total_size) * 100
            self.progress_queue.put(percentage)

        def run_in_thread():
            try:
                downloaded_video_path = self.download_youtube_video(youtube_url, on_progress)
                self.crop_video(downloaded_video_path, self.start_time, end_time, output_file)
                messagebox.showinfo("Success", "Video successfully downloaded and cropped")
            except Exception as e:
                messagebox.showerror("Error", str(e))
            finally:
                download_button['state'] = 'normal'

        thread = threading.Thread(target=run_in_thread)
        thread.start()

root = ThemedTk(theme="arc")
video_downloader = VideoDownloader(root)
root.mainloop()
