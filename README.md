# 🏠 CSE471 Lab Project: Freelance Home Service Marketplace

A full-stack **Flask-based web application** for connecting users who need home services with freelance service providers. Users can browse, request, and offer services — all within a secure and admin-managed environment.

---

## 🚀 Project Overview

This project is an **e-commerce-style marketplace** where:

- Users can **register and request services** (e.g., plumbing, electrical, cleaning).
- Freelancers can **offer their own services** after registration.
- Admins have control over **user approval** before service providers can go live.
- The platform fosters a decentralized, peer-to-peer exchange of home services.

---

## 🛠️ Built With

- **Python 3.8+**
- **Flask** (web framework)
- **SQLite** (default DB, configurable)
- **HTML/CSS + Bootstrap** (frontend)
- **Jinja2** (templating engine)

---

## 📂 Project Structure

```bash
.
├── flaskapp/                   # Main application module
│   ├── __init__.py             # Flask app factory
│   ├── routes.py               # App routes
│   ├── models.py               # Database models
│   ├── forms.py                # WTForms for registration/login
│   ├── templates/              # HTML templates
│   └── static/                 # CSS, JS, image assets
│
├── instance/                   # Configuration & database instance
│
├── run.py                      # Entry point to start the Flask server
├── requirements.txt            # Dependencies list
├── tips.txt                    # Setup/deployment tips
└── README.md                   # Project documentation
|






## ✅ Features

  🧑‍💼 User Registration & Authentication

  🛠️ Service Offering by Freelancers

  🛒 Service Ordering by Users

  🔐 Admin Approval for New Service Providers

  📋 Service Listings & Dashboard

  💬 Flask-Flash Messaging

  🌐 Responsive UI with Bootstrap

## 🔧 Getting Started
  1. Clone the Repository
     git clone https://github.com/your-username/CSE471_Lab_Project.git
     cd CSE471_Lab_Project

  2. Set Up Virtual Environment
     python -m venv venv
     source venv/bin/activate  # Windows: venv\Scripts\activate

  3. Install Dependencies
     pip install -r requirements.txt

  4. Run the App
     python run.py


  The app will be accessible at http://127.0.0.1:5000

## 🧪 Testing the App

Register as a user and browse available services.
Apply to become a service provider.
Log in as admin to approve or reject provider applications.
Order services or manage your own listings.

## 📌 Future Improvements (Suggestions)

Add user reviews/ratings
Email notifications
Payment gateway integration
Chat system between users and providers
Role-based dashboard views

## 📄 License

This project is part of the CSE471 course and intended for educational purposes.
