import json
import shutil
import zipfile
from pathlib import Path

import requests
import webview

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


class Api:
    def __init__(self):
        self.config = load_config()
        if not self.config.get("community_folder"):
            self.config["community_folder"] = default_community_folder()
            save_config(self.config)

    def get_state(self):
        return {
            "name": self.config.get("name", ""),
            "logged_in": bool(self.config.get("token")),
            "community_folder": self.config.get("community_folder", ""),
            "setup_done": bool(self.config.get("setup_done")),
        }

    def login(self, email, password):
        try:
            response = requests.post(
                f"{API_URL}/login",
                json={"email": email, "password": password},
                timeout=20,
            )
            data = response.json()
            if response.status_code != 200:
                return {"ok": False, "error": data.get("error", "Login failed")}
            self.config["token"] = data["token"]
            self.config["name"] = data.get("name")
            self.config["setup_done"] = True
            save_config(self.config)
            return {"ok": True, "name": data.get("name")}
        except Exception as exc:
            return {"ok": False, "error": str(exc)}

    def logout(self):
        self.config.pop("token", None)
        self.config["setup_done"] = False
        save_config(self.config)
        return {"ok": True}

    def browse_folder(self):
        result = webview.windows[0].create_file_dialog(webview.FOLDER_DIALOG)
        if result:
            folder = result[0]
            self.config["community_folder"] = folder
            save_config(self.config)
            return {"ok": True, "folder": folder}
        return {"ok": False, "folder": self.config.get("community_folder", "")}

    def set_folder(self, folder):
        self.config["community_folder"] = folder
        save_config(self.config)
        return {"ok": True}

    def products(self):
        token = self.config.get("token")
        if not token:
            return {"ok": False, "error": "Not logged in"}
        try:
            response = requests.get(
                f"{API_URL}/products",
                headers={"Authorization": f"Bearer {token}"},
                timeout=20,
            )
            if response.status_code == 401:
                return {"ok": False, "error": "Unauthorized"}
            data = response.json()
            folder = Path(self.config.get("community_folder") or "")
            items = []
            for product in data.get("products", []):
                product["installed"] = (folder / product["folder_name"]).exists()
                items.append(product)
            return {"ok": True, "products": items}
        except Exception as exc:
            return {"ok": False, "error": str(exc)}

    def install(self, product):
        folder = Path(self.config.get("community_folder") or "")
        if not folder.exists():
            return {"ok": False, "error": "Choose a valid Community folder first."}
        url = product.get("download_url")
        if not url:
            return {"ok": False, "error": "The aircraft file is not uploaded yet."}
        try:
            target_zip = folder / f"{product['id']}.zip"
            with requests.get(
                url,
                headers={"Authorization": f"Bearer {self.config.get('token')}"},
                stream=True,
                timeout=120,
            ) as response:
                response.raise_for_status()
                with open(target_zip, "wb") as handle:
                    for chunk in response.iter_content(chunk_size=1024 * 256):
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
    api = Api()
    html_path = Path(__file__).with_name("index.html")
    html = html_path.read_text(encoding="utf-8")
    webview.create_window(
        "RSInstaller",
        html=html,
        js_api=api,
        width=980,
        height=640,
        background_color="#ffffff",
    )
    webview.start()


if __name__ == "__main__":
    start()