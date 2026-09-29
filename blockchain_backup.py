import hashlib
import time
import json
import os

class Block:
    def __init__(self, index, transactions, previous_hash):
        self.index = index
        self.timestamp = time.time()
        self.transactions = transactions
        self.previous_hash = previous_hash
        self.nonce = 0
        self.hash = self.calculate_hash()

    def calculate_hash(self):
        data = json.dumps({
            "index": self.index,
            "timestamp": self.timestamp,
            "transactions": self.transactions,
            "previous_hash": self.previous_hash,
            "nonce": self.nonce
        }, sort_keys=True)
        return hashlib.sha256(data.encode()).hexdigest()

    def mine_block(self, difficulty=2):
        target = "0" * difficulty
        while not self.hash.startswith(target):
            self.nonce += 1
            self.hash = self.calculate_hash()

    def to_dict(self):
        return {
            "index": self.index,
            "timestamp": self.timestamp,
            "transactions": self.transactions,
            "previous_hash": self.previous_hash,
            "nonce": self.nonce,
            "hash": self.hash
        }


class SolanaBlockchain:
    def __init__(self):
        self.chain = []
        self.pending_transactions = []
        self.wallets = {}   # address -> { balance, merchant_name, is_merchant }
        self.difficulty = 2
        self.qr_payments = {}

        if os.path.exists("blockchain_data.json"):
            self.load_data()
        else:
            self._create_genesis_block()
            self.save_data()

    def _create_genesis_block(self):
        g = Block(0, [{"type": "genesis", "message": "SolanaPay Genesis 🌟"}], "0")
        g.mine_block(self.difficulty)
        self.chain.append(g)

    def save_data(self):
        data = {
             "chain": [b.to_dict() for b in self.chain],
             "wallets": self.wallets,
             "qr_payments": self.qr_payments
    }

        with open("blockchain_data.json", "w") as f:
            json.dump(data, f, indent=4)


    def load_data(self):
        with open("blockchain_data.json", "r") as f:
            data = json.load(f)

        self.wallets = data.get("wallets", {})
        self.qr_payments = data.get("qr_payments", {})

        self.chain = []

        for block_data in data.get("chain", []):
            block = Block(
                block_data["index"],
                block_data["transactions"],
                block_data["previous_hash"]
            )

            block.timestamp = block_data["timestamp"]
            block.nonce = block_data["nonce"]
            block.hash = block_data["hash"]

            self.chain.append(block)
    def get_latest_block(self):
            return self.chain[-1]
    # ── WALLETS ──────────────────────────────────────────────

    def register_wallet(self, address, is_merchant=False, merchant_name=None):
        if address not in self.wallets:
            self.wallets[address] = {
                "balance": 100.0,
                "is_merchant": is_merchant,
                "merchant_name": merchant_name or (address[:8] + "...")
            }
            self.save_data()
            return True
        return False

    def get_balance(self, address):
        return self.wallets.get(address, {}).get("balance", 0.0)

    def wallet_exists(self, address):
        return address in self.wallets

    # ── QR PAYMENT ───────────────────────────────────────────

    def create_qr_payment(self, merchant_address, amount, label):
        """Merchant creates a QR code payment request."""
        qr_id = "QR_" + hashlib.sha256(
            f"{merchant_address}{amount}{label}{time.time()}".encode()
        ).hexdigest()[:16].upper()

        self.qr_payments[qr_id] = {
            "merchant_address": merchant_address,
            "merchant_name": self.wallets.get(merchant_address, {}).get("merchant_name", "Unknown"),
            "amount": amount,
            "label": label,
            "status": "pending",
            "created_at": time.time()
        }
        return qr_id

    def get_qr_payment(self, qr_id):
        return self.qr_payments.get(qr_id)

    def pay_via_qr(self, qr_id, payer_address):
        """Payer scans QR and pays."""
        qr = self.qr_payments.get(qr_id)
        if not qr:
            return False, "❌ QR payment not found!"
        if qr["status"] != "pending":
            return False, "❌ This QR has already been paid!"
        if not self.wallet_exists(payer_address):
            return False, "❌ Your wallet is not registered!"

        merchant_address = qr["merchant_address"]
        amount = qr["amount"]
        FEE = 0.000005

        if self.wallets[payer_address]["balance"] < amount + FEE:
            return False, f"❌ Insufficient balance! Need {amount + FEE:.6f} SOL"
        if payer_address == merchant_address:
            return False, "❌ Cannot pay yourself!"

        self.wallets[payer_address]["balance"]   -= (amount + FEE)
        self.wallets[merchant_address]["balance"] += amount
        self.qr_payments[qr_id]["status"] = "paid"

        tx_id = "TX_" + hashlib.sha256(
            f"{payer_address}{merchant_address}{amount}{time.time()}".encode()
        ).hexdigest()[:20].upper()

        transaction = {
            "type":             "qr_payment",
            "tx_id":            tx_id,
            "qr_id":            qr_id,
            "sender":           payer_address,
            "receiver":         merchant_address,
            "merchant_name":    qr["merchant_name"],
            "label":            qr["label"],
            "amount":           amount,
            "fee":              FEE,
            "timestamp":        time.time()
        }
        self.pending_transactions.append(transaction)
        self._mine_pending()
        return True, transaction

    # ── DIRECT SEND ──────────────────────────────────────────

    def send_sol(self, sender, receiver, amount):
        FEE = 0.000005

        if sender not in self.wallets:
            return False, "❌ Sender not registered!"
        if sender == receiver:
            return False, "❌ Cannot send to yourself!"
        if amount <= 0:
            return False, "❌ Invalid amount!"
        if self.wallets[sender]["balance"] < amount + FEE:
            return False, f"❌ Insufficient balance! Need {amount + FEE:.6f} SOL"

        # ── If receiver is external (Solflare, any wallet) auto-register with 0 balance ──
        if receiver not in self.wallets:
            self.wallets[receiver] = {
                "balance": 0.0,
                "is_merchant": False,
                "merchant_name": receiver[:8] + "...",
                "is_external": True   # flag: external wallet
            }

        self.wallets[sender]["balance"]   -= (amount + FEE)
        self.wallets[receiver]["balance"] += amount

        tx_id = "TX_" + hashlib.sha256(
            f"{sender}{receiver}{amount}{time.time()}".encode()
        ).hexdigest()[:20].upper()

        tx = {
            "type":        "transfer",
            "tx_id":       tx_id,
            "sender":      sender,
            "receiver":    receiver,
            "amount":      amount,
            "fee":         FEE,
            "timestamp":   time.time(),
            "is_external": receiver not in self.wallets or
                           self.wallets[receiver].get("is_external", False)
        }
        self.pending_transactions.append(tx)
        self._mine_pending()
        return True, tx

    def _mine_pending(self):
        if not self.pending_transactions:
            return
        block = Block(len(self.chain), self.pending_transactions.copy(), self.get_latest_block().hash)
        block.mine_block(self.difficulty)
        self.chain.append(block)
        self.pending_transactions = []
        self.save_data()

    # ── HISTORY ──────────────────────────────────────────────

    def get_history(self, address):
        history = []
        for block in self.chain:
            for tx in block.transactions:
                if tx.get("type") in ("transfer", "qr_payment"):
                    if tx.get("sender") == address or tx.get("receiver") == address:
                        history.append(tx)
        return sorted(history, key=lambda x: x["timestamp"], reverse=True)

    def is_chain_valid(self):
        for i in range(1, len(self.chain)):
            c, p = self.chain[i], self.chain[i-1]
            if c.hash != c.calculate_hash(): return False
            if c.previous_hash != p.hash:    return False
        return True

    def get_all_blocks(self):
        return [b.to_dict() for b in self.chain]


solpay_chain = SolanaBlockchain()
