import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import threading
import requests
import os
import zipfile
import io
import re
import subprocess

VERSION = "0.4"
OWNER = "coltonsr77"
API_BASE = f"https://api.github.com/users/{OWNER}/repos"


class InstallerReadyApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title(f"InstallerReady v{VERSION}")
        self.geometry("750x550")
        self.resizable(False, False)
        self.install_path = os.getcwd()
        self.projects = []
        self.create_tabs()
        self.load_projects()

    def create_tabs(self):
        notebook = ttk.Notebook(self)
        notebook.pack(fill="both", expand=True, padx=10, pady=10)

        # Tabs
        self.tab_github = ttk.Frame(notebook)
        self.tab_myprojects = ttk.Frame(notebook)
        self.tab_about = ttk.Frame(notebook)

        notebook.add(self.tab_github, text="Install from GitHub")
        notebook.add(self.tab_myprojects, text="My Projects")
        notebook.add(self.tab_about, text="About")

        self.create_github_tab()
        self.create_myprojects_tab()
        self.create_about_tab()

    def create_github_tab(self):
        tk.Label(self.tab_github, text="Install from GitHub URL", font=("Arial", 16, "bold")).pack(pady=10)
        self.repo_entry = tk.Entry(self.tab_github, width=60)
        self.repo_entry.insert(0, "Enter GitHub repository URL...")
        self.repo_entry.pack(padx=20, pady=10)

        tk.Button(self.tab_github, text="Select Install Folder", command=self.select_folder).pack(pady=5)
        self.folder_label = tk.Label(self.tab_github, text=f"Install Path: {self.install_path}")
        self.folder_label.pack()

        # Progress bar
        self.progress = ttk.Progressbar(self.tab_github, length=400, mode='determinate')
        self.progress.pack(pady=20)
        self.progress_label = tk.Label(self.tab_github, text="Ready")
        self.progress_label.pack()

        tk.Button(self.tab_github, text="Install", command=self.start_install_from_url).pack(pady=10)

    def create_myprojects_tab(self):
        tk.Label(self.tab_myprojects, text="My GitHub Projects", font=("Arial", 16, "bold")).pack(pady=10)
        self.canvas = tk.Canvas(self.tab_myprojects)
        self.scrollbar = ttk.Scrollbar(self.tab_myprojects, orient="vertical", command=self.canvas.yview)
        self.scrollable_frame = tk.Frame(self.canvas)

        self.scrollable_frame.bind(
            "<Configure>",
            lambda e: self.canvas.configure(scrollregion=self.canvas.bbox("all"))
        )

        self.canvas.create_window((0, 0), window=self.scrollable_frame, anchor="nw")
        self.canvas.configure(yscrollcommand=self.scrollbar.set)

        self.canvas.pack(side="left", fill="both", expand=True)
        self.scrollbar.pack(side="right", fill="y")

        tk.Button(self.tab_myprojects, text="Refresh List", command=self.load_projects).pack(pady=5)

    def create_about_tab(self):
        text = (
            f"InstallerReady v{VERSION}\n\n"
            "Created by Coltonsr77\n\n"
            "Use this tool to install GitHub projects easily.\n"
            "You can install any repository via URL or from my own projects list."
        )
        tk.Label(self.tab_about, text=text, justify="left", wraplength=700).pack(padx=20, pady=20)

    def select_folder(self):
        path = filedialog.askdirectory()
        if path:
            self.install_path = path
            self.folder_label.configure(text=f"Install Path: {self.install_path}")

    def update_progress(self, value, text):
        self.progress["value"] = value * 100
        self.progress_label.configure(text=text)
        self.update_idletasks()

    def start_install_from_url(self):
        url = self.repo_entry.get().strip()
        if not url or url.lower().startswith("enter github"):
            messagebox.showwarning("Missing URL", "Please enter a valid GitHub repository URL.")
            return
        threading.Thread(target=self.download_and_extract, args=(url,), daemon=True).start()

    def start_install_project(self, repo_name):
        url = f"https://github.com/{OWNER}/{repo_name}"
        threading.Thread(target=self.download_and_extract, args=(url,), daemon=True).start()

    def download_and_extract(self, repo_url):
        try:
            self.update_progress(0.05, "Downloading repository...")
            repo_name = self.get_repo_name(repo_url)
            zip_url = f"{repo_url}/archive/refs/heads/main.zip"
            r = requests.get(zip_url, stream=True)
            r.raise_for_status()

            total = int(r.headers.get("content-length", 0))
            downloaded = 0
            buffer = io.BytesIO()

            for chunk in r.iter_content(chunk_size=8192):
                if chunk:
                    buffer.write(chunk)
                    downloaded += len(chunk)
                    if total:
                        self.update_progress(min(0.8, downloaded / total * 0.8), f"Downloading {repo_name}...")

            buffer.seek(0)
            with zipfile.ZipFile(buffer) as zip_ref:
                zip_ref.extractall(self.install_path)

            self.update_progress(1.0, "Done!")
            messagebox.showinfo("Installed", f"{repo_name} installed successfully!")
        except Exception as e:
            messagebox.showerror("Error", f"Failed to install project:\n{e}")
            self.update_progress(0, "Error")

    def load_projects(self):
        for widget in self.scrollable_frame.winfo_children():
            widget.destroy()

        tk.Label(self.scrollable_frame, text="Loading projects...", font=("Arial", 14)).pack(pady=20)
        threading.Thread(target=self.fetch_projects, daemon=True).start()

    def fetch_projects(self):
        try:
            r = requests.get(API_BASE)
            r.raise_for_status()
            self.projects = r.json()
            self.display_projects()
        except Exception as e:
            for widget in self.scrollable_frame.winfo_children():
                widget.destroy()
            tk.Label(self.scrollable_frame, text=f"Error loading projects: {e}", fg="red").pack(pady=20)

    def display_projects(self):
        for widget in self.scrollable_frame.winfo_children():
            widget.destroy()

        for project in self.projects:
            frame = tk.Frame(self.scrollable_frame, relief="ridge", borderwidth=2)
            frame.pack(fill="x", padx=10, pady=5)

            name = project.get("name", "Unnamed")
            desc = project.get("description", "No description provided.")
            tk.Label(frame, text=name, font=("Arial", 14, "bold")).pack(anchor="w", padx=10, pady=2)
            tk.Label(frame, text=desc, wraplength=650, justify="left").pack(anchor="w", padx=10)
            tk.Button(frame, text="Install", command=lambda n=name: self.start_install_project(n)).pack(pady=5)

    def get_repo_name(self, repo_url):
        match = re.search(r"github\.com/[^/]+/([^/]+)", repo_url)
        if match:
            return match.group(1).replace(".git", "")
        return "repository"


if __name__ == "__main__":
    app = InstallerReadyApp()
    app.mainloop()
