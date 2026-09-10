import json
import shutil
import sys
import webbrowser
import zipfile
from pathlib import Path

import requests
import webview

API_URL = "https://rsg-website.onrender.com/api"
CONFIG_PATH = Path.home() / ".rsinstaller.json"


def resource_path(name):
    if getattr(sys, "frozen", False):
        return Path(sys._MEIPASS) / name
    return Path(__file__).with_name(name)


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


class Api:
    def __init__(self):
        self.config = load_config()
        if not self.config.get("community_folder"):
            self.config["community_folder"] = default_community_folder()
            save_config(self.config)

    def headers(self):
        return {"Authorization": f"Bearer {self.config.get('token')}"}

    def get_state(self):
        return {
            "name": self.config.get("name", ""),
            "role": self.config.get("role", "Customer"),
            "is_admin": bool(self.config.get("is_admin")),
            "logged_in": bool(self.config.get("token")),
            "community_folder": self.config.get("community_folder", ""),
        }

    def login(self, email, password):
        email = (email or "").strip()
        password = password or ""
        if not email or not password:
            return {"ok": False, "error": "Enter email and password."}
        try:
            response = requests.post(
                f"{API_URL}/login",
                json={"email": email, "password": password},
                timeout=20,
            )
            data = response.json() if "json" in response.headers.get("content-type", "") else {}
            if response.status_code != 200:
                return {"ok": False, "error": data.get("error", f"Login failed ({response.status_code})")}
            is_admin = bool(data.get("is_admin")) or data.get("role") in ("Owner", "Admin", "Support")
            self.config.update({
                "token": data.get("token"),
                "name": data.get("name"),
                "role": data.get("role", "Customer"),
                "is_admin": is_admin,
            })
            save_config(self.config)
            return {"ok": True, "name": data.get("name"), "is_admin": is_admin}
        except Exception as exc:
            return {"ok": False, "error": str(exc)}

    def logout(self):
        self.config.pop("token", None)
        self.config["is_admin"] = False
        save_config(self.config)
        return {"ok": True}

    def browse_folder(self):
        result = webview.windows[0].create_file_dialog(webview.FOLDER_DIALOG)
        if result:
            self.config["community_folder"] = result[0]
            save_config(self.config)
            return {"ok": True, "folder": result[0]}
        return {"ok": False, "folder": self.config.get("community_folder", "")}

    def _with_installed(self, items):
        folder = Path(self.config.get("community_folder") or "")
        for item in items:
            item["installed"] = (folder / item.get("folder_name", "")).exists()
        return items

    def products(self):
        try:
            response = requests.get(f"{API_URL}/products", headers=self.headers(), timeout=20)
            if response.status_code == 401:
                return {"ok": False, "error": "Unauthorized"}
            return {"ok": True, "products": self._with_installed(response.json().get("products", []))}
        except Exception as exc:
            return {"ok": False, "error": str(exc)}

    def liveries(self):
        try:
            response = requests.get(f"{API_URL}/liveries", headers=self.headers(), timeout=20)
            if response.status_code == 401:
                return {"ok": False, "error": "Unauthorized"}
            return {"ok": True, "liveries": self._with_installed(response.json().get("liveries", []))}
        except Exception as exc:
            return {"ok": False, "error": str(exc)}

    def add_product(self, name, version, folder_name, download_url, image_url, price, buy_url, description):
        try:
            response = requests.post(
                f"{API_URL}/admin/products",
                headers=self.headers(),
                json={
                    "name": name,
                    "version": version,
                    "folder_name": folder_name,
                    "download_url": download_url,
                    "image_url": image_url,
                    "price": price,
                    "buy_url": buy_url,
                    "description": description,
                },
                timeout=20,
            )
            data = response.json() if "json" in response.headers.get("content-type", "") else {}
            if response.status_code != 200:
                return {"ok": False, "error": data.get("error", "Could not save aircraft")}
            return {"ok": True}
        except Exception as exc:
            return {"ok": False, "error": str(exc)}

    def add_livery(self, name, aircraft, folder_name, download_url, image_url):
        try:
            response = requests.post(
                f"{API_URL}/admin/liveries",
                headers=self.headers(),
                json={
                    "name": name,
                    "aircraft": aircraft,
                    "folder_name": folder_name,
                    "download_url": download_url,
                    "image_url": image_url,
                },
                timeout=20,
            )
            data = response.json() if "json" in response.headers.get("content-type", "") else {}
            if response.status_code != 200:
                return {"ok": False, "error": data.get("error", "Could not save livery")}
            return {"ok": True}
        except Exception as exc:
            return {"ok": False, "error": str(exc)}

    def open_url(self, url):
        if url:
            webbrowser.open(url)
        return {"ok": True}

    def install(self, product):
        folder = Path(self.config.get("community_folder") or "")
        if not folder.exists():
            return {"ok": False, "error": "Choose a valid Community folder first."}
        url = product.get("download_url")
        if not url:
            return {"ok": False, "error": "No download file yet."}
        try:
            target_zip = folder / f"{product['id']}.zip"
            with requests.get(url, headers=self.headers(), stream=True, timeout=120) as response:
                response.raise_for_status()
                with open(target_zip, "wb") as handle:
                    for chunk in response.iter_content(1024 * 256):
                        if chunk:
                            handle.write(chunk)
            dest = folder / product["folder_name"]
            if dest.exists():
                shutil.rmtree(dest)
            dest.mkdir(parents=True, exist_ok=True)
            with zipfile.ZipFile(target_zip, "r") as archive:
                archive.extractall(dest)
            target_zip.unlink(missing_ok=True)
            return {"ok": True}
        except Exception as exc:
            return {"ok": False, "error": str(exc)}

    def uninstall(self, product):
        dest = Path(self.config.get("community_folder") or "") / product["folder_name"]
        if dest.exists():
            shutil.rmtree(dest)
        return {"ok": True}


def start():
    html = resource_path("index.html").read_text(encoding="utf-8")
    webview.create_window(
        "RSInstaller",
        html=html,
        js_api=Api(),
        width=1360,
        height=860,
        background_color="#2b3038",
    )
    webview.start()


if __name__ == "__main__":
    start()