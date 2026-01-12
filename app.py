import os

from cs50 import SQL
import sqlite3
from flask import Flask, flash, redirect, render_template, request, session
from flask_session import Session
from werkzeug.security import check_password_hash, generate_password_hash

from helpers import apology, login_required, lookup, usd

# Configure application
app = Flask(__name__)

# Custom filter
app.jinja_env.filters["usd"] = usd

# Configure session to use filesystem (instead of signed cookies)
app.config["SESSION_PERMANENT"] = False
app.config["SESSION_TYPE"] = "filesystem"
Session(app)

# Configure CS50 Library to use SQLite database
#db = SQL("sqlite:///finance.db")
DB_PATH = "finance.db"
def get_db_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row  # return rows as dict-like objects
    return conn

@app.after_request
def after_request(response):
    """Ensure responses aren't cached"""
    response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    response.headers["Expires"] = 0
    response.headers["Pragma"] = "no-cache"
    return response


@app.route("/")
@login_required
def index():
    """Show portfolio of stocks"""
    # held_share = db.execute(
    #     """
    #     select purchase_symbol as symbol, sum(purchase_shares) as shares
    #     from transactions
    #     where userid = ?
    #     group by purchase_symbol
    #     """, session["user_id"]
    # )
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute(
        """
        select purchase_symbol as symbol, sum(purchase_shares) as shares
        from transactions
        where userid = ?
        group by purchase_symbol
        """, (session["user_id"],)
    )
    held_share = cur.fetchall()
    
    total = 0
    for entry in held_share:
        entry["unit_price"] = lookup(entry["symbol"])["price"]
        entry["total_price"] = entry["unit_price"] * entry["shares"]
        total += entry["total_price"]
    cur.execute(
        """
        select cash from users
        where id = ?
        """, (session["user_id"],)
    )
    cash = cur.fetchall()
    cur.close()
    liquid_cash = cash[0]["cash"]
    total += liquid_cash
    return render_template("index.html", records=held_share, cash=liquid_cash, total=total)


@app.route("/buy", methods=["GET", "POST"])
@login_required
def buy():
    """Buy shares of stock"""
    if request.method == "POST":
        # pass
        if not request.form.get("symbol"):
            return apology("must provide Symbol", 400)
        if not lookup(request.form.get("symbol")):
            return apology("cannot find Symbol", 400)
        if not request.form.get("shares"):
            return apology("must provide shares", 400)
        result = lookup(request.form.get("symbol"))
        price = result['price']
        try:
            shares = int(request.form.get("shares"))
        except:
            return apology("share need to be int", 400)
        if shares <= 0:
            return apology("share need to be positive", 400)
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute("SELECT * FROM users WHERE id = ?", (session["user_id"],))
        rows = cur.fetchall()
        cash = rows[0]["cash"]
        username = rows[0]["username"]
        if price*shares > cash:
            return apology("does not have enough balance", 400)
        else:
            new_cash = cash - price*shares
            cur.execute(
                """
                CREATE TABLE IF NOT EXISTS transactions(
                    userid TEXT NOT NULL,
                    username TEXT NOT NULL,
                    purchase_symbol TEXT NOT NULL,
                    purchase_shares INTEGER NOT NULL,
                    purchase_price REAL NOT NULL,
                    event_date TEXT NOT NULL,
                    PRIMARY KEY (userid, event_date, purchase_symbol, purchase_shares)
            )""")
            cur.execute(
                """
               INSERT INTO transactions(userid,username,purchase_symbol,purchase_shares,purchase_price,event_date)
               VALUES(?, ?, ?, ?, ?, datetime('now'))
               """, (session["user_id"], username, request.form.get("symbol"), shares, price))
            cur.execute(
                """
                UPDATE users
                SET cash = ?
                where id = ?
                """, (new_cash, session["user_id"])
            )
            conn.commit()
            conn.close()
        return redirect("/")
    else:
        return render_template("buy.html")


@app.route("/history")
@login_required
def history():
    """Show history of transactions"""
    conn = get_db_connection()
    cur = conn.cursor()

    cur.execute(
        """
        select
            purchase_symbol as symbol,
            purchase_shares as shares,
            purchase_price as price,
            event_date as transacted
        from transactions
        where userid = ?
        """, (session["user_id"],)
    )
    records = cur.fetchall()
    conn.close()

    return render_template("history.html", records=records)


@app.route("/login", methods=["GET", "POST"])
def login():
    """Log user in"""

    # Forget any user_id
    session.clear()

    # User reached route via POST (as by submitting a form via POST)
    if request.method == "POST":
        # Ensure username was submitted
        if not request.form.get("username"):
            return apology("must provide username", 403)

        # Ensure password was submitted
        elif not request.form.get("password"):
            return apology("must provide password", 403)

        # Query database for username
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute(
            "SELECT * FROM users WHERE username = ?", (request.form.get("username"),)
        )
        rows = cur.fetchall()
        # Ensure username exists and password is correct
        if len(rows) != 1 or not check_password_hash(
            rows[0]["hash"], request.form.get("password")
        ):
            return apology("invalid username and/or password", 403)

        # Remember which user has logged in
        session["user_id"] = rows[0]["id"]
        cur.execute(
            """
                CREATE TABLE IF NOT EXISTS transactions(
                    userid TEXT NOT NULL,
                    username TEXT NOT NULL,
                    purchase_symbol TEXT NOT NULL,
                    purchase_shares INTEGER NOT NULL,
                    purchase_price REAL NOT NULL,
                    event_date TEXT NOT NULL,
                    PRIMARY KEY (userid, event_date, purchase_symbol, purchase_shares)
        )""")
        conn.commit()
        conn.close()
        # Redirect user to home page
        return redirect("/")

    # User reached route via GET (as by clicking a link or via redirect)
    else:
        return render_template("login.html")


@app.route("/logout")
def logout():
    """Log user out"""

    # Forget any user_id
    session.clear()

    # Redirect user to login form
    return redirect("/")


@app.route("/quote", methods=["GET", "POST"])
@login_required
def quote():
    """Get stock quote."""
    # return apology("TODO-QUOTE")
    if request.method == "POST":
        # pass
        if not request.form.get("symbol"):
            return apology("Must Provide Quote", 400)
        elif not lookup(request.form.get("symbol")):
            return apology("Quote Does Not Exist", 400)
        else:
            result = lookup(request.form.get("symbol"))
            result['price'] = usd(result['price'])
            return render_template("quote.html", quote=result)
    else:
        return render_template("quote.html")


@app.route("/register", methods=["GET", "POST"])
def register():
    """Register user"""
    if request.method == "POST":
        if not request.form.get("username"):
            return apology("you need to provide username", 400)
        elif not request.form.get("password") or not request.form.get("confirmation"):
            return apology("must provide password", 400)
        elif request.form.get("confirmation") != request.form.get("password"):
            return apology("password does not match", 400)
        # lookup user name from database
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute(
            "SELECT * FROM users WHERE username = ?", 
            (request.form.get("username"),)
        )
        rows = cur.fetchall()
        if len(rows) > 0:
            # user name already exist
            return apology("user name already exist", 400)
        else:
            cur.execute(
                "INSERT INTO users (username, hash) VALUES (?, ?)", 
                (
                    request.form.get("username"), 
                    generate_password_hash(
                        request.form.get("password"), 
                        method='scrypt', 
                        salt_length=16
                        ),
                ),
            )
            conn.commit()
        # return render_template("login.html")
        conn.close()
        return render_template("registersuccess.html")
    else:
        return render_template("register.html")

    # return render_template("register.html")
    # return apology("TODO")


@app.route("/sell", methods=["GET", "POST"])
@login_required
def sell():
    """Sell shares of stock"""
    # return apology("TODO-BUY")
    if request.method == "POST":
        # pass
        if not request.form.get("symbol"):
            return apology("must provide Symbol", 400)
        try:
            shares = int(request.form.get("shares"))
        except:
            return apology("share need to be int", 400)
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute(
            """
            select sum(purchase_shares) as purchase_shares
            from transactions
            where userid = ? and purchase_symbol = ?
            """, (session["user_id"], request.form.get("symbol"))
        )
        user_stat = cur.fetchall()
        try:
            user_share = user_stat[0]['purchase_shares']
        except:
            user_share = 0
        if shares > user_share:
            return apology("You dont have these many shares", 400)
        else:
            result = lookup(request.form.get("symbol"))
            price = result["price"]
            symbol = result["symbol"]
            name = result["name"]
            sold_price = shares * price
            cur.execute(
                """
                select username, cash
                from users
                where id = ?
                """, (session["user_id"],)
            )
            user_stat = cur.fetchall()
            user_name = user_stat[0]["username"]
            cash = user_stat[0]["cash"]
            newcash = cash + sold_price
            cur.execute(
                """
                INSERT INTO transactions(userid,username,purchase_symbol,purchase_shares,purchase_price,event_date)
                VALUES(?, ?, ?, ?, ?, datetime('now'))
                """, (session["user_id"], user_name, symbol, shares * -1, price)
            )
            cur.execute(
                """
                update users
                set cash = ?
                where id = ?
                """, (newcash, session["user_id"])
            )
            conn.commit()
            conn.close()
        return redirect("/")
    else:
        conn = get_db_connection()
        cur = conn.cursor()

        cur.execute(
            """
            select purchase_symbol as symbol, sum(purchase_shares) as shares
            from transactions
            where userid = ?
            group by purchase_symbol
            """, (session["user_id"],)
        )
        data = cur.fetchall()
        conn.close()
        print(data)
        return render_template("sell.html", options=data)
