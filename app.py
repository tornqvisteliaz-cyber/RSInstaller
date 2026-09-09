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