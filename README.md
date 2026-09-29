# SolanaPay – Blockchain Payment System

A blockchain-based cryptocurrency payment system developed using Solana, Flask, and Phantom Wallet. The system supports direct SOL transfers and QR-code-based payments with transaction validation and blockchain-based record keeping.

## 📌 Project Overview

SolanaPay is a web-based cryptocurrency payment system designed to provide a simple and secure way to perform SOL transactions.

The system allows users to connect their Phantom Wallet, view their SOL balance, send SOL directly to another wallet address, and make payments using QR codes. Transactions are validated and recorded using blockchain-based data structures, with transaction records maintained using local JSON storage.

## ✨ Features

- 🔐 Connect and manage Phantom Wallet
- 💰 View SOL wallet balance
- 💸 Send SOL directly to a wallet address
- 📱 Generate QR codes for payments
- 📷 Process QR-code-based SOL payments
- 🔗 Validate blockchain transactions
- ⛓️ Maintain blockchain blocks with previous-hash linking
- 🔍 View transaction and blockchain history
- 🧮 Generate SHA-256 hashes for blocks
- 💾 Store blockchain data using JSON backup
- 🌐 Use Solana Devnet for transaction processing

## 🛠️ Technologies Used

### Frontend
- HTML5
- CSS3
- JavaScript

### Backend
- Python
- Flask

### Blockchain & Wallet
- Solana Devnet
- Phantom Wallet

### Other Technologies
- QR Code
- SHA-256 Hashing
- JSON Data Storage

## ⚙️ System Workflow

1. The user opens the SolanaPay web application.
2. The user connects their Phantom Wallet.
3. The system retrieves the wallet address and SOL balance.
4. The user selects either direct SOL transfer or QR-code payment.
5. The transaction is authorized through Phantom Wallet.
6. The transaction is processed through Solana Devnet.
7. The transaction is validated.
8. A blockchain record is created and linked with the previous block using its hash.
9. Transaction and blockchain information can be viewed through the application.

## 📂 Project Structure

```text
SolanaPay/
│
├── app.py
├── blockchain_backup.py
├── templates/
│   ├── base.html
│   ├── create_qr.html
│   ├── dashboard.html
│   ├── error.html
│   ├── explorer.html
│   ├── index.html
│   ├── pay.html
│   └── send.html
│
└── README.md
