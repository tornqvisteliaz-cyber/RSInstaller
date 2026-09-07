import json
import shutil
import zipfile
from pathlib import Path
from tkinter import filedialog, messagebox

import customtkinter as ctk
import requests

API_URL = "https://rsg-website.onrender.com/api"
CONFIG_PATH = Path.home() / ".rsinstaller.json"


def load_config():
    if CONFIG_PATH.exists():
        return json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
    return {}


def save_config(data):
    CONFIG_PATH.write_text(json.dumps(data, indent=2), encoding="utf-8")


def default_community_folder():
    candidates = [
        Path.home() / "AppData/Roaming/Microsoft Flight Simulator 2024/Packages/Community",
        Path.home() / "AppData/Local/Packages/Microsoft.Limitless_8wekyb3d8bbwe/LocalCache/Packages/Community",
        Path.home() / "AppData/Roaming/Microsoft Flight Simulator/Packages/Community",
    ]
    for path in candidates:
        if path.exists():
            return str(path)
    return ""


class RSInstaller(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("RSInstaller")
        self.geometry("780x520")
        ctk.set_appearance_mode("dark")
        ctk.set_default_color_theme("dark-blue")

        self.config_data = load_config()
        self.token = self.config_data.get("token")
        self.community = self.config_data.get("community_folder") or default_community_folder()
        self.wizard_step = 0

        self.container = ctk.CTkFrame(self)
        self.container.pack(fill="both", expand=True)

        if self.config_data.get("setup_done") and self.token:
            self.show_library()
        else:
            self.show_wizard()

    def clear(self):
        for child in self.container.winfo_children():
            child.destroy()

    def show_wizard(self):
        self.clear()
        steps = [
            self.wizard_welcome,
            self.wizard_login,
            self.wizard_folder,
            self.wizard_done,
        ]
        steps[self.wizard_step]()

    def wizard_nav(self, back=False, next_step=False):
        if back:
            self.wizard_step = max(0, self.wizard_step - 1)
        if next_step:
            self.wizard_step = min(3, self.wizard_step + 1)
        self.show_wizard()

    def footer(self, parent, show_back=True, next_text="Next", next_cmd=None):
        bar = ctk.CTkFrame(parent, fg_color="transparent")
        bar.pack(fill="x", pady=20)
        if show_back:
            ctk.CTkButton(bar, text="Back", width=100, command=lambda: self.wizard_nav(back=True)).pack(side="left")
        ctk.CTkButton(bar, text=next_text, width=140, command=next_cmd).pack(side="right")

    def wizard_welcome(self):
        box = ctk.CTkFrame(self.container)
        box.pack(expand=True, fill="both", padx=40, pady=40)
        ctk.CTkLabel(box, text="RSInstaller", font=("Segoe UI", 28, "bold")).pack(anchor="w", pady=(10, 8))
        ctk.CTkLabel(
            box,
            text="Install and update RSG Software products for Microsoft Flight Simulator.\nThis setup will connect your account and find your Community folder.",
            justify="left",
        ).pack(anchor="w", pady=(0, 20))
        self.footer(box, show_back=False, next_text="Next", next_cmd=lambda: self.wizard_nav(next_step=True))

    def wizard_login(self):
        box = ctk.CTkFrame(self.container)
        box.pack(expand=True, fill="both", padx=40, pady=40)
        ctk.CTkLabel(box, text="Account", font=("Segoe UI", 24, "bold")).pack(anchor="w", pady=(10, 8))
        ctk.CTkLabel(box, text="Log in with the same email and password as on the RSG website.").pack(anchor="w", pady=(0, 16))

        self.email = ctk.CTkEntry(box, width=320, placeholder_text="Email")
        self.email.pack(anchor="w", pady=6)
        self.password = ctk.CTkEntry(box, width=320, placeholder_text="Password", show="*")
        self.password.pack(anchor="w", pady=6)
        self.login_error = ctk.CTkLabel(box, text="", text_color="#f87171")
        self.login_error.pack(anchor="w", pady=8)

        self.footer(box, next_text="Log in", next_cmd=self.wizard_do_login)

    def wizard_do_login(self):
        try:
            response = requests.post(
                f"{API_URL}/login",
                json={"email": self.email.get().strip(), "password": self.password.get()},
                timeout=20,
            )
            data = response.json()
            if response.status_code != 200:
                self.login_error.configure(text=data.get("error", "Login failed"))
                return
            self.token = data["token"]
            self.config_data["token"] = self.token
            self.config_data["name"] = data.get("name")
            save_config(self.config_data)
            self.wizard_nav(next_step=True)
        except Exception as exc:
            self.login_error.configure(text=str(exc))

    def wizard_folder(self):
        box = ctk.CTkFrame(self.container)
        box.pack(expand=True, fill="both", padx=40, pady=40)
        ctk.CTkLabel(box, text="Community folder", font=("Segoe UI", 24, "bold")).pack(anchor="w", pady=(10, 8))
        ctk.CTkLabel(box, text="Select the folder where Microsoft Flight Simulator loads addons.").pack(anchor="w", pady=(0, 16))

        row = ctk.CTkFrame(box, fg_color="transparent")
        row.pack(fill="x")
        self.path_entry = ctk.CTkEntry(row)
        self.path_entry.pack(side="left", fill="x", expand=True, padx=(0, 8))
        self.path_entry.insert(0, self.community)
        ctk.CTkButton(row, text="Browse", width=90, command=self.browse_folder).pack(side="right")
        self.folder_error = ctk.CTkLabel(box, text="", text_color="#f87171")
        self.folder_error.pack(anchor="w", pady=8)

        self.footer(box, next_text="Next", next_cmd=self.wizard_save_folder)

    def browse_folder(self):
        chosen = filedialog.askdirectory()
        if chosen:
            self.path_entry.delete(0, "end")
            self.path_entry.insert(0, chosen)

    def wizard_save_folder(self):
        folder = self.path_entry.get().strip()
        if not folder or not Path(folder).exists():
            self.folder_error.configure(text="Select a valid folder.")
            return
        self.community = folder
        self.config_data["community_folder"] = folder
        save_config(self.config_data)
        self.wizard_nav(next_step=True)

    def wizard_done(self):
        box = ctk.CTkFrame(self.container)
        box.pack(expand=True, fill="both", padx=40, pady=40)
        ctk.CTkLabel(box, text="Ready", font=("Segoe UI", 24, "bold")).pack(anchor="w", pady=(10, 8))
        ctk.CTkLabel(box, text="RSInstaller is set up. You can now install RSG products.").pack(anchor="w")
        self.config_data["setup_done"] = True
        save_config(self.config_data)
        self.footer(box, next_text="Open library", next_cmd=self.show_library)

    def headers(self):
        return {"Authorization": f"Bearer {self.token}"}

    def show_library(self):
        self.clear()
        top = ctk.CTkFrame(self.container)
        top.pack(fill="x", padx=16, pady=16)
        name = self.config_data.get("name") or "Pilot"
        ctk.CTkLabel(top, text=f"RSInstaller  ·  {name}", font=("Segoe UI", 18, "bold")).pack(side="left")
        ctk.CTkButton(top, text="Log out", width=90, command=self.logout).pack(side="right")

        path_row = ctk.CTkFrame(self.container)
        path_row.pack(fill="x", padx=16)
        ctk.CTkLabel(path_row, text="Community folder").pack(anchor="w")
        inner = ctk.CTkFrame(path_row, fg_color="transparent")
        inner.pack(fill="x", pady=6)
        self.path_entry = ctk.CTkEntry(inner)
        self.path_entry.pack(side="left", fill="x", expand=True, padx=(0, 8))
        self.path_entry.insert(0, self.community)
        ctk.CTkButton(inner, text="Browse", width=90, command=self.browse_folder).pack(side="right")

        self.list_frame = ctk.CTkScrollableFrame(self.container)
        self.list_frame.pack(fill="both", expand=True, padx=16, pady=16)
        self.refresh_products()

    def refresh_products(self):
        for child in self.list_frame.winfo_children():
            child.destroy()
        try:
            response = requests.get(f"{API_URL}/products", headers=self.headers(), timeout=20)
            if response.status_code == 401:
                self.logout()
                return
            products = response.json().get("products", [])
        except Exception as exc:
            ctk.CTkLabel(self.list_frame, text=f"Could not load products: {exc}").pack()
            return

        if not products:
            ctk.CTkLabel(self.list_frame, text="No products available yet.").pack(anchor="w")
            return

        for product in products:
            card = ctk.CTkFrame(self.list_frame)
            card.pack(fill="x", pady=8)
            text = f"{product['name']}\n{product['simulator']}  ·  v{product['version']}"
            if not product.get("owned"):
                text += "\nNot owned"
            ctk.CTkLabel(card, text=text, justify="left", anchor="w").pack(side="left", padx=16, pady=16)
            if product.get("owned"):
                label = "Update" if self.is_installed(product) else "Install"
                ctk.CTkButton(card, text=label, width=110, command=lambda p=product: self.install_product(p)).pack(side="right", padx=8, pady=16)
                if self.is_installed(product):
                    ctk.CTkButton(
                        card, text="Uninstall", width=110, fg_color="#7f1d1d",
                        command=lambda p=product: self.uninstall_product(p)
                    ).pack(side="right", padx=8, pady=16)

    def product_path(self, product):
        return Path(self.path_entry.get().strip()) / product["folder_name"]

    def is_installed(self, product):
        return self.product_path(product).exists()

    def install_product(self, product):
        folder = self.path_entry.get().strip()
        if not folder or not Path(folder).exists():
            messagebox.showerror("RSInstaller", "Choose a valid Community folder first.")
            return
        url = product.get("download_url")
        if not url:
            messagebox.showinfo("RSInstaller", "The aircraft file is not uploaded yet.")
            return
        try:
            target_zip = Path(folder) / f"{product['id']}.zip"
            with requests.get(url, headers=self.headers(), stream=True, timeout=120) as response:
                response.raise_for_status()
                with open(target_zip, "wb") as handle:
                    for chunk in response.iter_content(chunk_size=1024 * 256):
                        if chunk:
                            handle.write(chunk)
            dest = self.product_path(product)
            if dest.exists():
                shutil.rmtree(dest)
            dest.mkdir(parents=True, exist_ok=True)
            with zipfile.ZipFile(target_zip, "r") as archive:
                archive.extractall(dest)
            target_zip.unlink(missing_ok=True)
            messagebox.showinfo("RSInstaller", f"{product['name']} installed.")
            self.refresh_products()
        except Exception as exc:
            messagebox.showerror("RSInstaller", str(exc))

    def uninstall_product(self, product):
        dest = self.product_path(product)
        if dest.exists():
            shutil.rmtree(dest)
        self.refresh_products()

    def logout(self):
        self.token = None
        self.config_data.pop("token", None)
        self.config_data["setup_done"] = False
        save_config(self.config_data)
        self.wizard_step = 0
        self.show_wizard()


if __name__ == "__main__":
    RSInstaller().mainloop()