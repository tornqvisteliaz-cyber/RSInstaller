import os
import secrets
from functools import wraps

from flask import Blueprint, jsonify, request

from . import db
from .extensions import bcrypt, limiter
from .models import AdminUser, Customer, Order

api = Blueprint("api", __name__, url_prefix="/api")

PRODUCTS = [
    {
        "id": "seabee",
        "name": "Republic RC-3 Seabee",
        "simulator": "MSFS 2024",
        "version": "0.1.0-dev",
        "folder_name": "rsg-seabee",
        "download_url": os.getenv("SEABEE_DOWNLOAD_URL", ""),
        "status": "in_development",
    }
]

LIVERIES = [
    {
        "id": "seabee-n87451",
        "name": "N87451",
        "aircraft": "Republic RC-3 Seabee",
        "folder_name": "rsg-seabee-n87451",
        "download_url": "",
    },
    {
        "id": "seabee-white",
        "name": "Classic White",
        "aircraft": "Republic RC-3 Seabee",
        "folder_name": "rsg-seabee-white",
        "download_url": "",
    },
]


def bearer_token():
    header = request.headers.get("Authorization", "")
    return header.replace("Bearer ", "").strip()


def get_account_from_token():
    token = bearer_token()
    if not token:
        return None, None
    admin = AdminUser.query.filter_by(api_token=token).first()
    if admin and admin.enabled:
        return admin, "admin"
    customer = Customer.query.filter_by(api_token=token).first()
    if customer and not customer.banned:
        return customer, "customer"
    return None, None


def require_account(fn):
    @wraps(fn)
    def wrapper(*args, **kwargs):
        account, kind = get_account_from_token()
        if not account:
            return jsonify({"error": "Unauthorized"}), 401
        return fn(account, kind, *args, **kwargs)
    return wrapper


def require_admin(fn):
    @wraps(fn)
    def wrapper(*args, **kwargs):
        account, kind = get_account_from_token()
        if not account:
            return jsonify({"error": "Unauthorized"}), 401
        if kind != "admin":
            return jsonify({"error": "Admin only"}), 403
        return fn(account, kind, *args, **kwargs)
    return wrapper


@api.route("/login", methods=["POST"])
@limiter.limit("8 per minute")
def api_login():
    data = request.get_json(silent=True) or {}
    raw_email = (data.get("email") or "").strip()
    email = raw_email.lower()
    password = data.get("password") or ""

    if not email or not password:
        return jsonify({"error": "Enter your email/username and password."}), 400

    admin = AdminUser.query.filter(
        (AdminUser.email == email) | (AdminUser.username == raw_email)
    ).first()
    if admin and admin.enabled and bcrypt.check_password_hash(admin.password_hash, password):
        if not admin.api_token:
            admin.api_token = secrets.token_urlsafe(32)
            db.session.commit()
        return jsonify({
            "token": admin.api_token,
            "name": admin.username,
            "email": admin.email,
            "role": admin.role,
            "is_admin": True,
        })

    customer = Customer.query.filter_by(email=email).first()
    if (
        not customer
        or customer.banned
        or not customer.password_hash
        or not bcrypt.check_password_hash(customer.password_hash, password)
    ):
        return jsonify({"error": "Invalid email or password"}), 401

    if not customer.api_token:
        customer.api_token = secrets.token_urlsafe(32)
        db.session.commit()

    return jsonify({
        "token": customer.api_token,
        "name": customer.name,
        "email": customer.email,
        "role": "Customer",
        "is_admin": False,
    })


@api.route("/logout", methods=["POST"])
@require_account
def api_logout(account, kind):
    account.api_token = None
    db.session.commit()
    return jsonify({"ok": True})


@api.route("/me")
@require_account
def api_me(account, kind):
    if kind == "admin":
        return jsonify({
            "name": account.username,
            "email": account.email,
            "role": account.role,
            "is_admin": True,
        })
    return jsonify({
        "name": account.name,
        "email": account.email,
        "role": "Customer",
        "is_admin": False,
    })


def owns_product(account, kind, product_id):
    if kind == "admin" or os.getenv("RSG_DEV_UNLOCK", "").lower() == "true":
        return True
    paid = Order.query.filter_by(
        customer_id=account.id,
        payment_status="Paid",
    ).count()
    return paid > 0 and product_id == "seabee"


@api.route("/products")
@require_account
def api_products(account, kind):
    items = []
    for product in PRODUCTS:
        item = dict(product)
        item["owned"] = owns_product(account, kind, product["id"])
        if not item["owned"]:
            item["download_url"] = ""
        items.append(item)
    return jsonify({"products": items})


@api.route("/liveries")
@require_account
def api_liveries(account, kind):
    items = []
    for livery in LIVERIES:
        item = dict(livery)
        item["owned"] = owns_product(account, kind, "seabee")
        if not item["owned"]:
            item["download_url"] = ""
        items.append(item)
    return jsonify({"liveries": items})


@api.route("/admin/products", methods=["POST"])
@require_admin
def api_admin_add_product(account, kind):
    data = request.get_json(silent=True) or {}
    name = (data.get("name") or "").strip()
    folder_name = (data.get("folder_name") or "").strip()
    if not name or not folder_name:
        return jsonify({"error": "Name and folder name are required."}), 400

    product_id = data.get("id") or name.lower().replace(" ", "-")
    existing = next((p for p in PRODUCTS if p["id"] == product_id), None)
    payload = {
        "id": product_id,
        "name": name,
        "simulator": data.get("simulator", "MSFS 2024"),
        "version": data.get("version", ""),
        "folder_name": folder_name,
        "download_url": data.get("download_url", ""),
        "image_url": data.get("image_url", ""),
        "price": data.get("price", ""),
        "buy_url": data.get("buy_url", ""),
        "description": data.get("description", ""),
        "status": data.get("status", "active"),
    }
    if existing:
        existing.update(payload)
    else:
        PRODUCTS.append(payload)
    return jsonify({"ok": True, "product": payload})


@api.route("/admin/liveries", methods=["POST"])
@require_admin
def api_admin_add_livery(account, kind):
    data = request.get_json(silent=True) or {}
    name = (data.get("name") or "").strip()
    folder_name = (data.get("folder_name") or "").strip()
    if not name or not folder_name:
        return jsonify({"error": "Name and folder name are required."}), 400

    livery_id = data.get("id") or name.lower().replace(" ", "-")
    existing = next((l for l in LIVERIES if l["id"] == livery_id), None)
    payload = {
        "id": livery_id,
        "name": name,
        "aircraft": data.get("aircraft", ""),
        "folder_name": folder_name,
        "download_url": data.get("download_url", ""),
        "image_url": data.get("image_url", ""),
    }
    if existing:
        existing.update(payload)
    else:
        LIVERIES.append(payload)
    return jsonify({"ok": True, "livery": payload})


@api.route("/admin/overview")
@require_admin
def api_admin_overview(account, kind):
    return jsonify({
        "name": account.username,
        "role": account.role,
        "customers": Customer.query.count(),
        "orders": Order.query.count(),
        "products": len(PRODUCTS),
        "liveries": len(LIVERIES),
        "dashboard_url": "https://rsg-website.onrender.com/admin/",
    })


@api.route("/newsletter")
def api_newsletter():
    from .models import NewsletterPost
    posts = NewsletterPost.query.order_by(NewsletterPost.date_posted.desc()).limit(20).all()
    return jsonify({
        "posts": [
            {
                "id": post.id,
                "title": post.title,
                "content": post.content,
                "author": post.author,
                "date": post.date_posted.strftime("%Y-%m-%d") if post.date_posted else "",
            }
            for post in posts
        ]
    })