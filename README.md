# 🧋 Boba Bliss — Cute & Pink Full-Stack Web App

A beginner-friendly boba pickup order manager built with **Python Flask, SQLAlchemy, SQLite/PostgreSQL, HTML, CSS and JavaScript**. It is a fictional store created for a school assignment.

## Features

- **Public pages:** Home, Menu (also `/preview`), Contact
- **Sample pickup orders:** Choose drink, size, sweetness, quantity and notes; see total before submitting
- **Admin login:** Password-protected dashboard with secure hashed passwords
- **Drink CRUD:** Create, read, update and delete drinks; change price, display order and availability
- **Order management:** View orders and change their statuses (New, Preparing, Ready, Completed, Cancelled)
- **Responsive:** Mobile menu and layout, tablet-friendly grids, desktop dashboard
- **Database:** SQLite locally or PostgreSQL on Render stores admins, drinks and orders
- **Basic protections:** CSRF checks on forms, parameterized SQL queries, password hashing and server-side validation

## 1. Open the project in VS Code

Open the `boba_bliss` folder in VS Code, then open **Terminal → New Terminal**.

## 2. Install Flask

**Windows (PowerShell):**

```powershell
py -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

**macOS / Linux:**

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## 3. Create your admin account

Run this command in the project directory:

```bash
flask --app app create-admin
```

Enter a username (at least 3 characters) and a **password of at least 8 characters**. The password won't be displayed as you type. Do not share your admin password.

## 4. Start the website

```bash
flask --app app run --debug
```

Open **http://127.0.0.1:5000** in your browser.

- Public home: http://127.0.0.1:5000/
- Menu/preview: http://127.0.0.1:5000/preview
- Contact: http://127.0.0.1:5000/contact
- Admin login: http://127.0.0.1:5000/admin/login

The database file `boba_bliss.db` is created automatically in the project folder. Six sample drinks are added on the first launch.

## 5. Try the features

1. Visit **Menu** and choose a drink.
2. Fill in a **sample** pickup order (do not use real personal information).
3. Log in as admin at `/admin/login`.
4. Find your order and change its status.
5. Add a new drink, edit the price, or delete a drink.
6. Click **Public preview** to see your changes.
7. Resize your browser or use a phone to show the responsive design.

## 6. Publish online (live link)

For a public URL, use a hosting service that can run Flask and **persist SQLite data**. PythonAnywhere is one option; check its current plan and deployment instructions. Upload your project, install `requirements.txt` in a virtual environment, configure its web app to load `app` from `app.py`, and run `flask --app app create-admin` in its console. Your actual live URL is assigned by the hosting service — **no live site has been deployed for you by this ZIP**.

Another option is a Flask host with a **persistent disk/volume**. Set `DATABASE_PATH` to a location on that persistent volume. Hosting SQLite on ephemeral storage (including many default cloud deployments) means your drinks and orders may disappear on restart. Configure `SECRET_KEY` as a long random environment secret; use HTTPS. Do not expose a demo admin password publicly.

**Important:** This is a classroom demonstration, not a real payment or order fulfillment system. It does not process payments or send orders to a store. The contact details are fictitious. To handle real customers, add privacy, rate limits, proper order ownership / confirmations, and production infrastructure.

## Pages & backend routes

| Route | Purpose |
|---|---|
| `/` | Homepage |
| `/menu`, `/preview` | Public drink list |
| `/order/<drink_id>` | Submit sample pickup order |
| `/contact` | Sample contact details |
| `/admin/login` | Admin authentication |
| `/admin` | Protected dashboard |
| `/admin/drinks/new` | Add drink |
| `/admin/drinks/<id>/edit` | Edit drink |
| `/admin/drinks/<id>/delete` | Delete drink via POST |
| `/admin/orders/<id>/status` | Update order status via POST |

## Submission summary (copy and edit)

**Project Name:** Boba Bliss — Boba Pickup Order Manager

**Live application link:** [Paste your deployed website link here]

**Summary:** Boba Bliss is a beginner-friendly full-stack website for a fictional bubble tea shop. Visitors can browse drinks and place sample pickup orders by selecting a size, sweetness level and quantity. An administrator can securely log in, add/edit/delete drinks, and update pickup order statuses. The site also includes a public preview page, sample contact information, and responsive design for phones, tablets and computers. It uses Python Flask for the backend, SQLite for the database, and HTML, CSS, and JavaScript for the frontend.


## Render PostgreSQL connection (production)

1. In the Render **Postgres** dashboard, copy the **Internal Database URL** using the Connect menu.
2. In the Render **Web Service** dashboard, open **Environment** and add a private `DATABASE_URL` variable containing that URL. Do not paste it into GitHub or screenshots.
3. Add a long random `SECRET_KEY` to the web service Environment.
4. For the **first admin account**, set `ADMIN_USERNAME` and `ADMIN_PASSWORD` (at least 12 characters) privately on Render, then redeploy. The app creates an account if it doesn't exist; it will not replace existing credentials.
5. Render will automatically create the database tables and initial sample drinks on first connection. A new PostgreSQL database starts with empty orders and fresh menu data; existing SQLite data is **not migrated automatically**.
6. Test the menu, admin login, and a **sample** pickup order, then test again after a redeploy.

The database uses Flask-SQLAlchemy and psycopg; local development continues to use a SQLite file when `DATABASE_URL` is absent. Render's free PostgreSQL databases expire; check your database expiry date in its dashboard.

### Fixing an incorrect admin password on Render

Set `ADMIN_USERNAME` to the existing account name, set `ADMIN_PASSWORD` to a new private password with at least 12 characters, and temporarily add `ADMIN_RESET_PASSWORD=yes` in the web service Environment. Save and deploy. After login succeeds, remove `ADMIN_RESET_PASSWORD` (or set it to `no`) so later starts cannot overwrite the password. Do **not** share any passwords in chat, screenshots, or GitHub. Changing `ADMIN_PASSWORD` alone does not reset an existing account.
