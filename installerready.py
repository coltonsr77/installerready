import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import threading
import requests
import os
import zipfile
import io
import shutil
import re
import subprocess
import traceback
from datetime import datetime
import sys
import time

VERSION = "0.5-Beta"
OWNER = "coltonsr77"
API_BASE = f"https://api.github.com/users/{OWNER}/repos"


class InstallerReady(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title(f"InstallerReady v{VERSION}")
        self.geometry("750x550")
        self.resizable(False, False)
        self.install_path = os.getcwd()
        # Optional: read GitHub token from environment to increase rate limits
        self.gh_token = os.environ.get("GITHUB_TOKEN")
        self.project_buttons = []
        self.projects = []
        self.create_tabs()
        self.load_projects()

    def api_request(self, method, url, **kwargs):
        """Wrapper around requests.request that adds GitHub token and handles rate limits.

        Raises RuntimeError on auth/rate-limit conditions.
        """
        headers = kwargs.pop("headers", {}) or {}
        headers.setdefault("Accept", "application/vnd.github.v3+json")
        if self.gh_token:
            headers["Authorization"] = f"token {self.gh_token}"

        timeout = kwargs.pop("timeout", 10)
        try:
            resp = requests.request(method, url, headers=headers, timeout=timeout, **kwargs)
        except Exception as e:
            raise

        if resp.status_code == 401:
            msg = "GitHub API authentication failed (401). Set GITHUB_TOKEN environment variable."
            try:
                self.log_error("api_request_401", Exception(msg))
            except Exception:
                pass
            raise RuntimeError(msg)

        if resp.status_code == 403 and resp.headers.get("X-RateLimit-Remaining") == "0":
            reset = resp.headers.get("X-RateLimit-Reset")
            wait = None
            if reset:
                try:
                    wait = int(reset) - int(time.time())
                except Exception:
                    wait = None
            msg = f"GitHub API rate limit exceeded. Reset in {max(wait,0)}s" if wait is not None else "GitHub API rate limit exceeded."
            try:
                self.log_error("api_request_rate_limit", Exception(msg))
            except Exception:
                pass
            raise RuntimeError(msg)

        resp.raise_for_status()
        return resp

    def create_tabs(self):
        notebook = ttk.Notebook(self)
        notebook.pack(fill="both", expand=True, padx=10, pady=10)

        # Tabs
        self.tab_github = ttk.Frame(notebook)
        self.tab_myprojects = ttk.Frame(notebook)
        self.tab_about = ttk.Frame(notebook)

        notebook.add(self.tab_github, text="Download from GitHub")
        notebook.add(self.tab_myprojects, text="coltonsr77`s Projects")
        notebook.add(self.tab_about, text="About InstallerReady")

        self.create_github_tab()
        self.create_myprojects_tab()
        self.create_about_tab()

    def create_github_tab(self):
        tk.Label(self.tab_github, text="Download from GitHub", font=("Arial", 16, "bold")).pack(pady=10)
        self.repo_entry = tk.Entry(self.tab_github, width=60)
        self.repo_entry.insert(0, "Enter GitHub repository URL...")
        self.repo_entry.pack(padx=20, pady=10)
        self.select_folder_button = tk.Button(self.tab_github, text="Select Download Folder", command=self.select_folder)
        self.select_folder_button.pack(pady=5)
        self.folder_label = tk.Label(self.tab_github, text=f"Download Path: {self.install_path}")
        self.folder_label.pack()

        # Progress bar
        self.progress = ttk.Progressbar(self.tab_github, length=400, mode='determinate')
        self.progress.pack(pady=20)
        self.progress["maximum"] = 100
        self.progress["value"] = 0
        self.progress_label = tk.Label(self.tab_github, text="Ready")
        self.progress_label.pack()

        self.download_button = tk.Button(self.tab_github, text="Download", command=self.start_install_from_url)
        self.download_button.pack(pady=10)

    def create_myprojects_tab(self):
        tk.Label(self.tab_myprojects, text="coltonsr77`s GitHub Projects", font=("Arial", 16, "bold")).pack(pady=10)
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

        self.refresh_button = tk.Button(self.tab_myprojects, text="Refresh List", command=self.load_projects)
        self.refresh_button.pack(pady=5)

    def create_about_tab(self):
        text = (
            f"InstallerReady v{VERSION}\n\n"
            "Created by coltonsr77\n\n"
            "Use this tool to download GitHub projects easily.\n\n"
            "You can download any repository via URL or from coltonsr77`s projects list."
        )
        tk.Label(self.tab_about, text=text, justify="left", wraplength=700).pack(padx=20, pady=20)
        # View Log button to open the local log file if it exists
        def _open_log_if_exists():
            log_path = os.path.expanduser("~/.installerready.log")
            if os.path.exists(log_path):
                try:
                    self.open_log(log_path)
                except Exception:
                    messagebox.showerror("Open Log", "Failed to open log file. See console for details.")
            else:
                messagebox.showinfo("View Log", "No log file found at ~/.installerready.log")

        tk.Button(self.tab_about, text="View Log", command=_open_log_if_exists).pack(pady=5)

    def set_ui_enabled(self, enabled: bool):
        """Enable or disable UI controls during downloads."""
        state = "normal" if enabled else "disabled"
        try:
            if hasattr(self, "download_button"):
                self.download_button.configure(state=state)
            if hasattr(self, "select_folder_button"):
                self.select_folder_button.configure(state=state)
            if hasattr(self, "refresh_button"):
                self.refresh_button.configure(state=state)
            # repo entry
            try:
                self.repo_entry.configure(state=state)
            except Exception:
                pass
            # per-project buttons
            for b in getattr(self, "project_buttons", []):
                try:
                    b.configure(state=state)
                except Exception:
                    pass
        except Exception:
            pass

    def select_folder(self):
        path = filedialog.askdirectory()
        if path:
            self.install_path = path
            self.folder_label.configure(text=f"Install Path: {self.install_path}")

    def update_progress(self, value, text):
        # value expected in range 0.0 - 1.0
        try:
            frac = float(value)
        except Exception:
            frac = 0.0
        frac = max(0.0, min(1.0, frac))
        percent = int(frac * 100)
        self.progress["value"] = percent
        self.progress_label.configure(text=f"{text} ({percent}%)")
        self.update_idletasks()

    def start_install_from_url(self):
        url = self.repo_entry.get().strip()
        if not url or url.lower().startswith("Enter github"):
            messagebox.showwarning("Missing URL", "Please enter a valid GitHub repository URL.")
            return
        threading.Thread(target=self.download_and_extract, args=(url,), daemon=True).start()

    def start_install_project(self, repo_name):
        url = f"https://github.com/{OWNER}/{repo_name}"
        threading.Thread(target=self.download_and_extract, args=(url,), daemon=True).start()

    def get_default_branch(self, repo_url):
        """Return the default branch name for a GitHub repository URL.

        Returns the branch name (e.g. 'main') or None on failure.
        """
        try:
            if repo_url.startswith("http"):
                parts = repo_url.rstrip("/").split("/")
                owner, repo = parts[-2], parts[-1]
            elif repo_url.startswith("git@"):
                parts = repo_url.split(":")[-1].replace(".git", "").split("/")
                owner, repo = parts[0], parts[1]
            else:
                return None

            repo = repo.replace(".git", "")
            api_url = f"https://api.github.com/repos/{owner}/{repo}"
            resp = self.api_request('GET', api_url, timeout=10)
            data = resp.json()
            return data.get("default_branch")
        except Exception:
            return None

    def parse_owner_repo(self, repo_url):
        """Return (owner, repo) from a GitHub URL or None on failure."""
        try:
            if repo_url.startswith("http"):
                parts = repo_url.rstrip("/").split("/")
                owner, repo = parts[-2], parts[-1]
            elif repo_url.startswith("git@"):
                parts = repo_url.split(":")[-1].replace(".git", "").split("/")
                owner, repo = parts[0], parts[1]
            else:
                return None, None
            repo = repo.replace(".git", "")
            return owner, repo
        except Exception:
            return None, None

    def get_archive_url(self, repo_url):
        """Return (archive_url, label) for a repo URL. Label is branch or tag used for naming.

        Supports:
        - releases/latest
        - releases/tag/<tag> or releases/<tag>
        - fallback to default branch archive
        """
        owner, repo = self.parse_owner_repo(repo_url)
        if not owner or not repo:
            return None, None

        # If user supplied a releases/tag URL, try to extract tag
        m = re.search(r"/releases/(?:tag/)?([^/]+)$", repo_url)
        try:
            if "/releases/latest" in repo_url:
                # latest release
                api = f"https://api.github.com/repos/{owner}/{repo}/releases/latest"
                resp = self.api_request('GET', api, timeout=10)
                data = resp.json()
                tag = data.get("tag_name")
                if tag:
                    return f"https://github.com/{owner}/{repo}/archive/refs/tags/{tag}.zip", tag
                # fallback to zipball_url
                zipball = data.get("zipball_url")
                return (zipball, data.get("tag_name") if data else None)
            elif m:
                tag = m.group(1)
                # try release by tag
                api = f"https://api.github.com/repos/{owner}/{repo}/releases/tags/{tag}"
                try:
                    resp = self.api_request('GET', api, timeout=10)
                    data = resp.json()
                    return (data.get("zipball_url") or f"https://github.com/{owner}/{repo}/archive/refs/tags/{tag}.zip", tag)
                except Exception:
                    # fallback to github tag archive
                    return (f"https://github.com/{owner}/{repo}/archive/refs/tags/{tag}.zip", tag)
            else:
                # Not a release URL — return None so caller falls back to branch archives
                return None, None
        except Exception:
            return None, None

    def download_and_extract(self, repo_url):
        try:
            self.update_progress(0.05, "Preparing download...")
            repo_name = self.get_repo_name(repo_url)

            # Prefer release/tag archives when URL indicates releases or tag
            # Disable UI controls while downloading
            self.after(0, lambda: self.set_ui_enabled(False))

            archive_url, label = self.get_archive_url(repo_url)
            if archive_url:
                zip_url = archive_url
                label_text = label or "release"
                r = self.api_request('GET', zip_url, stream=True, timeout=30)
            else:
                branch = self.get_default_branch(repo_url) or None

                # If we couldn't determine the default branch, try common names
                if not branch:
                    for try_branch in ("main", "master"):
                        check_url = f"{repo_url}/archive/refs/heads/{try_branch}.zip"
                        try:
                            head = self.api_request('HEAD', check_url, timeout=8)
                            if head.status_code == 200:
                                branch = try_branch
                                break
                        except Exception:
                            continue

                branch = branch or "master"
                label_text = branch
                zip_url = f"{repo_url}/archive/refs/heads/{branch}.zip"
                r = self.api_request('GET', zip_url, stream=True, timeout=30)
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
            # Safely extract zip contents to avoid path traversal and avoid overwriting
            with zipfile.ZipFile(buffer) as zip_ref:
                members = [m for m in zip_ref.namelist() if m and not m.endswith('/')]

                # Determine a unique base directory for extraction to prevent overwriting
                top_level = None
                if members:
                    first = members[0]
                    top_level = first.split('/')[0]

                base_dir_name = f"{repo_name}-{label_text}" if repo_name else (top_level or f"repo-{int(datetime.utcnow().timestamp())}")
                target_base = os.path.join(self.install_path, base_dir_name)
                counter = 1
                while os.path.exists(target_base):
                    target_base = os.path.join(self.install_path, f"{base_dir_name}_{counter}")
                    counter += 1
                os.makedirs(target_base, exist_ok=True)

                total_members = len(members) or 1
                for idx, member in enumerate(members, start=1):
                    member_path = os.path.normpath(member)
                    if member_path.startswith("..") or os.path.isabs(member_path):
                        # skip suspicious paths
                        continue
                    # strip top-level folder from member path if present
                    parts = member_path.split('/')
                    if parts and parts[0] == top_level:
                        relative_path = os.path.join(*parts[1:]) if len(parts) > 1 else ""
                    else:
                        relative_path = member_path

                    target_path = os.path.join(target_base, relative_path)
                    target_dir = os.path.dirname(target_path)
                    if target_dir:
                        os.makedirs(target_dir, exist_ok=True)
                    with zip_ref.open(member) as source, open(target_path, "wb") as target:
                        shutil.copyfileobj(source, target)

                    # update extraction progress between 80% and 98%
                    extract_frac = 0.8 + 0.18 * (idx / total_members)
                    self.update_progress(extract_frac, f"Extracting {repo_name}...")

            # finalize progress
            self.update_progress(0.99, "Finalizing...")

            self.update_progress(1.0, "Done!")
            self.after(0, lambda: messagebox.showinfo("Downloaded", f"{repo_name} has downloaded successfully!"))
        except Exception as e:
            log_path = self.log_error("download_and_extract", e)
            # Ensure UI interactions happen on the main thread
            self.after(0, lambda: messagebox.showerror("Error", f"Failed to download project. Details saved to {log_path}"))
            self.after(0, lambda: self.prompt_open_log(log_path))
            self.update_progress(0, "Error")
        finally:
            # Re-enable UI controls
            self.after(0, lambda: self.set_ui_enabled(True))

    def load_projects(self):
        for widget in self.scrollable_frame.winfo_children():
            widget.destroy()

        tk.Label(self.scrollable_frame, text="Loading projects...", font=("Arial", 14)).pack(pady=20)
        threading.Thread(target=self.fetch_projects, daemon=True).start()

    def fetch_projects(self):
        try:
            r = self.api_request('GET', API_BASE, timeout=10)
            self.projects = r.json()
            self.display_projects()
        except Exception as e:
            for widget in self.scrollable_frame.winfo_children():
                widget.destroy()
            log_path = self.log_error("fetch_projects", e)
            tk.Label(self.scrollable_frame, text=f"Error loading projects. Details saved to {log_path}", fg="red").pack(pady=20)
            self.after(0, lambda: self.prompt_open_log(log_path))

    def log_error(self, context, exc):
        """Append detailed exception information to a log file in the user's home directory.

        Returns the path to the log file.
        """
        try:
            log_path = os.path.join(os.path.expanduser("~"), ".installerready.log")
            with open(log_path, "a", encoding="utf-8") as f:
                f.write("-----\n")
                f.write(f"{datetime.utcnow().isoformat()}Z - {context}\n")
                f.write(traceback.format_exc())
                f.write("\n")
            return log_path
        except Exception:
            return "(failed to write log)"

    def open_log(self, path):
        """Try to open the given file path with the system default application."""
        try:
            if not path or path.startswith("(failed"):
                return False
            # Windows
            if os.name == "nt":
                os.startfile(path)
                return True
            # macOS
            if sys.platform == "darwin":
                subprocess.run(["open", path], check=False)
                return True
            # Linux and other POSIX
            subprocess.run(["xdg-open", path], check=False)
            return True
        except Exception:
            return False

    def prompt_open_log(self, log_path):
        try:
            if not log_path or log_path.startswith("(failed"):
                return
            if messagebox.askyesno("Open Log", f"Open the log file at {log_path}?"):
                self.open_log(log_path)
        except Exception:
            pass

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
            tk.Button(frame, text="Download", command=lambda n=name: self.start_install_project(n)).pack(pady=5)

    def get_repo_name(self, repo_url):
        # Try to parse owner/repo using the central helper which
        # supports both HTTP and SSH (git@) URL forms.
        owner, repo = self.parse_owner_repo(repo_url)
        if owner and repo:
            return repo.replace('.git', '')

        # Fallback: try a broader regex that handles either / or : separators
        match = re.search(r"github\.com[:/][^/]+/([^/]+)", repo_url)
        if match:
            return match.group(1).replace('.git', '')

        return "repository"


if __name__ == "__main__":
    app = InstallerReady()
    app.mainloop()
