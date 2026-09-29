from flask import Flask, render_template, request, redirect, url_for, session, jsonify
from blockchain_backup import solpay_chain
import time, qrcode, io, base64

app = Flask(__name__)
app.secret_key = "solpay_qr_2024"

# ── HELPERS ──────────────────────────────────────────────────

def make_qr_image(data):
    """Generate QR code as base64 PNG."""
    qr = qrcode.QRCode(box_size=8, border=3,
        error_correction=qrcode.constants.ERROR_CORRECT_H)
    qr.add_data(data)
    qr.make(fit=True)
    img = qr.make_image(fill_color="black", back_color="white")
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return base64.b64encode(buf.getvalue()).decode()

def short(addr):
    return addr[:6] + "..." + addr[-4:] if len(addr) > 12 else addr

def fmt_time(ts):
    return time.strftime("%d %b %Y, %I:%M %p", time.localtime(ts))

# ── AUTH API ─────────────────────────────────────────────────

@app.route("/api/connect-wallet", methods=["POST"])
def connect_wallet():
    data = request.get_json()
    address = data.get("address", "").strip()
    if not address:
        return jsonify({"success": False, "message": "No address!"})
    is_new = solpay_chain.register_wallet(address)
    session["wallet_address"] = address
    session["wallet_type"] = data.get("wallet_type", "Phantom")
    return jsonify({
        "success": True,
        "address": address,
        "balance": solpay_chain.get_balance(address),
        "is_new":  is_new,
        "message": "🎉Welcome to CryptoPay!" if is_new else "✅ Welcome back!"
    })

@app.route("/api/disconnect-wallet", methods=["POST"])
def disconnect_wallet():
    session.clear()
    return jsonify({"success": True})

# ── PAGES ────────────────────────────────────────────────────

@app.route("/")
def index():
    if "wallet_address" in session:
        return redirect(url_for("dashboard"))
    return render_template("index.html")

@app.route("/dashboard")
def dashboard():
    if "wallet_address" not in session:
        return redirect(url_for("index"))
    address = session["wallet_address"]
    history = solpay_chain.get_history(address)
    formatted = []
    for tx in history:
        is_send = tx["sender"] == address
        other   = tx.get("receiver") if is_send else tx.get("sender")
        formatted.append({
            "type":    "sent" if is_send else "received",
            "other":   short(other),
            "label":   tx.get("label", "Direct Transfer"),
            "amount":  tx["amount"],
            "tx_id":   tx["tx_id"],
            "time":    fmt_time(tx["timestamp"]),
            "is_qr":   tx.get("type") == "qr_payment"
        })
    return render_template("dashboard.html",
        address=address,
        addr_short=short(address),
        balance=round(solpay_chain.get_balance(address), 6),
        wallet_type=session.get("wallet_type", "Phantom"),
        history=formatted
    )

# ── QR PAYMENT ────────────────────────────────────────────────

@app.route("/create-qr", methods=["GET", "POST"])
def create_qr():
    """Merchant creates a payment QR."""
    if "wallet_address" not in session:
        return redirect(url_for("index"))
    qr_data = None
    qr_img  = None
    qr_id   = None
    error   = None

    if request.method == "POST":
        try:
            amount = float(request.form["amount"])
            label  = request.form["label"].strip() or "Payment"
        except ValueError:
            error = "Invalid amount!"
        else:
            merchant = session["wallet_address"]
            qr_id    = solpay_chain.create_qr_payment(merchant, amount, label)
            pay_url  = request.host_url + "pay/" + qr_id
            qr_img   = make_qr_image(pay_url)
            qr_data  = {"qr_id": qr_id, "url": pay_url, "amount": amount, "label": label}

    return render_template("create_qr.html",
        error=error, qr_img=qr_img, qr_data=qr_data,
        balance=round(solpay_chain.get_balance(session["wallet_address"]), 6)
    )

@app.route("/pay/<qr_id>")
def pay_page(qr_id):
    """Payer lands here after scanning QR."""
    qr = solpay_chain.get_qr_payment(qr_id)
    if not qr:
        return render_template("error.html", msg="QR payment not found!")
    return render_template("pay.html", qr=qr, qr_id=qr_id,
        logged_in="wallet_address" in session,
        payer_addr=session.get("wallet_address", ""),
        payer_balance=round(solpay_chain.get_balance(session.get("wallet_address", "")), 6)
    )

@app.route("/api/pay-qr", methods=["POST"])
def api_pay_qr():
    """Process QR payment."""
    if "wallet_address" not in session:
        return jsonify({"success": False, "message": "Please connect your wallet first!"})
    data   = request.get_json()
    qr_id  = data.get("qr_id")
    payer  = session["wallet_address"]
    success, result = solpay_chain.pay_via_qr(qr_id, payer)
    if success:
        return jsonify({
            "success": True,
            "tx_id":   result["tx_id"],
            "amount":  result["amount"],
            "message": f"✅ Payment of {result['amount']} SOL successful!"
        })
    return jsonify({"success": False, "message": result})

# ── SEND DIRECT ───────────────────────────────────────────────

@app.route("/send", methods=["GET", "POST"])
def send():
    if "wallet_address" not in session:
        return redirect(url_for("index"))
    message = error = None
    if request.method == "POST":
        receiver = request.form["receiver"].strip()
        tx_hash  = request.form.get("tx_hash", "").strip()  # real devnet tx hash
        try:
            amount = float(request.form["amount"])
        except ValueError:
            error = "Invalid amount!"
        else:
            ok, res = solpay_chain.send_sol(session["wallet_address"], receiver, amount)
            if ok:
                # If we have a real devnet tx hash, show it
                if tx_hash:
                    message = f"✅ Sent {amount} SOL on Devnet! TX Hash: {tx_hash[:20]}... | Internal TX: {res['tx_id']}"
                else:
                    message = f"✅ Sent {amount} SOL! TX: {res['tx_id']}"
            else:
                error = res
    return render_template("send.html",
        error=error, message=message,
        balance=round(solpay_chain.get_balance(session["wallet_address"]), 6)
    )

# ── EXPLORER ──────────────────────────────────────────────────

@app.route("/explorer")
def explorer():
    if "wallet_address" not in session:
        return redirect(url_for("index"))
    return render_template("explorer.html",
        blocks=solpay_chain.get_all_blocks(),
        is_valid=solpay_chain.is_chain_valid()
    )

if __name__ == "__main__":
    app.run(debug=True)
