app.py — this is your PyWebView desktop app entry point (login, install/uninstall logic, config storage, safe zip extraction).
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
        try:
            return json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
        except Exception:
            return {}
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


def parse_payload(payload):
    if isinstance(payload, str):
        return json.loads(payload)
    return payload or {}


def safe_extract(archive: zipfile.ZipFile, dest: Path):
    """Extract a zip file while guarding against zip-slip path traversal."""
    dest = dest.resolve()
    for member in archive.infolist():
        member_path = (dest / member.filename).resolve()
        if not str(member_path).startswith(str(dest)):
            raise ValueError(f"Unsafe path in archive: {member.filename}")
    archive.extractall(dest)


class Api:
    def __init__(self):
        self.config = load_config()
        if not self.config.get("community_folder"):
            self.config["community_folder"] = default_community_folder()
            save_config(self.config)

    def headers(self):
        token = self.config.get("token")
        headers = {"Content-Type": "application/json"}
        if token:
            headers["Authorization"] = f"Bearer {token}"
        return headers

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
            return {"ok": False, "error": "Enter your email/username and password."}
        try:
            response = requests.post(
                f"{API_URL}/login",
                json={"email": email, "password": password},
                timeout=20,
            )
            data = {}
            if "json" in response.headers.get("content-type", ""):
                try:
                    data = response.json()
                except Exception:
                    data = {}
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
        except requests.exceptions.ConnectionError:
            return {"ok": False, "error": "Could not reach the server. Check your internet connection."}
        except requests.exceptions.Timeout:
            return {"ok": False, "error": "The server took too long to respond. Try again."}
        except Exception as exc:
            return {"ok": False, "error": str(exc)}

    def logout(self):
        token = self.config.get("token")
        if token:
            try:
                requests.post(f"{API_URL}/logout", headers=self.headers(), timeout=10)
            except Exception:
                pass  # best-effort server-side revoke; always clear locally regardless
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
            if response.status_code != 200:
                return {"ok": False, "error": f"Could not load products ({response.status_code})"}
            return {"ok": True, "products": self._with_installed(response.json().get("products", []))}
        except requests.exceptions.ConnectionError:
            return {"ok": False, "error": "Could not reach the server."}
        except Exception as exc:
            return {"ok": False, "error": str(exc)}

    def liveries(self):
        try:
            response = requests.get(f"{API_URL}/liveries", headers=self.headers(), timeout=20)
            if response.status_code != 200:
                return {"ok": False, "error": f"Could not load liveries ({response.status_code})"}
            return {"ok": True, "liveries": self._with_installed(response.json().get("liveries", []))}
        except requests.exceptions.ConnectionError:
            return {"ok": False, "error": "Could not reach the server."}
        except Exception as exc:
            return {"ok": False, "error": str(exc)}

    def add_product(self, payload):
        data = parse_payload(payload)
        try:
<<<<<<< HEAD
            response = requests.post(f"{API_URL}/admin/products", headers=self.headers(), json=data, timeout=20)
            body = {}
            if "json" in response.headers.get("content-type", ""):
                try:
                    body = response.json()
                except Exception:
                    body = {}
=======
            response = requests.post(f"{API_URL}/save-product", headers=self.headers(), json=data, timeout=20)
            body = response.json() if "json" in response.headers.get("content-type", "") else {}
>>>>>>> d7f06e573c0c3a94f9ed1f4de4eb24a7ec4e8a94
            if response.status_code != 200:
                return {"ok": False, "error": body.get("error", f"Save failed ({response.status_code})")}
            return {"ok": True}
        except Exception as exc:
            return {"ok": False, "error": str(exc)}

    def add_livery(self, payload):
        data = parse_payload(payload)
        try:
<<<<<<< HEAD
            response = requests.post(f"{API_URL}/admin/liveries", headers=self.headers(), json=data, timeout=20)
            body = {}
            if "json" in response.headers.get("content-type", ""):
                try:
                    body = response.json()
                except Exception:
                    body = {}
=======
            response = requests.post(f"{API_URL}/save-livery", headers=self.headers(), json=data, timeout=20)
            body = response.json() if "json" in response.headers.get("content-type", "") else {}
>>>>>>> d7f06e573c0c3a94f9ed1f4de4eb24a7ec4e8a94
            if response.status_code != 200:
                return {"ok": False, "error": body.get("error", f"Save failed ({response.status_code})")}
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
            return {"ok": False, "error": "No download file available yet."}
        if not product.get("folder_name"):
            return {"ok": False, "error": "This item is missing a folder name."}

        target_zip = folder / f"{product['id']}.zip"
        try:
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
                safe_extract(archive, dest)

            return {"ok": True}
        except zipfile.BadZipFile:
            return {"ok": False, "error": "The downloaded file was corrupted. Please try again."}
        except ValueError as exc:
            return {"ok": False, "error": f"Unsafe archive rejected: {exc}"}
        except requests.exceptions.ConnectionError:
            return {"ok": False, "error": "Download failed: could not reach the server."}
        except Exception as exc:
            return {"ok": False, "error": str(exc)}
        finally:
            if target_zip.exists():
                target_zip.unlink(missing_ok=True)

    def uninstall(self, product):
        folder_name = product.get("folder_name")
        if not folder_name:
            return {"ok": False, "error": "This item is missing a folder name."}
        dest = Path(self.config.get("community_folder") or "") / folder_name
        try:
            if dest.exists():
                shutil.rmtree(dest)
            return {"ok": True}
        except Exception as exc:
            return {"ok": False, "error": str(exc)}


def start():
    html = resource_path("index.html").read_text(encoding="utf-8")
    webview.create_window(
        "RSInstaller",
        html=html,
        js_api=Api(),
        width=1360,
        height=860,
        background_color="#0b1020",
    )
    webview.start()


if __name__ == "__main__":
    start()
