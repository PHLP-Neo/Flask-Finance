import requests
import yfinance as yf

from flask import redirect, render_template, session
from functools import wraps


def apology(message, code=400):
    """Render message as an apology to user."""

    def escape(s):
        """
        Escape special characters.

        https://github.com/jacebrowning/memegen#special-characters
        """
        for old, new in [
            ("-", "--"),
            (" ", "-"),
            ("_", "__"),
            ("?", "~q"),
            ("%", "~p"),
            ("#", "~h"),
            ("/", "~s"),
            ('"', "''"),
        ]:
            s = s.replace(old, new)
        return s

    return render_template("apology.html", top=code, bottom=escape(message)), code


def login_required(f):
    """
    Decorate routes to require login.

    https://flask.palletsprojects.com/en/latest/patterns/viewdecorators/
    """

    @wraps(f)
    def decorated_function(*args, **kwargs):
        if session.get("user_id") is None:
            return redirect("/login")
        return f(*args, **kwargs)

    return decorated_function


def lookup(ticker_symbol):
    """Look up quote for symbol."""
    try:
        if not ticker_symbol or not isinstance(ticker_symbol.upper(), str):
            raise ValueError("Ticker symbol must be a non-empty string.")
        
        symbol = ticker_symbol.upper()
        ticker = yf.Ticker(symbol)
        info = ticker.info  # Dictionary with company details

        name = info.get("shortName") or info.get("longName")
        price = info.get("regularMarketPrice")

        # Validate if data exists
        if name is None or price is None:
            return {"error": f"No valid data found for ticker '{ticker_symbol.upper()}'."}
        return {
            "name": info["shortName"],
            "price": float(price),
            "symbol": symbol
        }
    except Exception as e:
        return {"error": str(e)}
    # url = f"https://finance.cs50.io/quote?symbol={symbol.upper()}"
    # try:
    #     response = requests.get(url)
    #     response.raise_for_status()  # Raise an error for HTTP error responses
    #     quote_data = response.json()
    #     return {
    #         "name": quote_data["companyName"],
    #         "price": quote_data["latestPrice"],
    #         "symbol": symbol.upper()
    #     }
    # except requests.RequestException as e:
    #     print(f"Request error: {e}")
    # except (KeyError, ValueError) as e:
    #     print(f"Data parsing error: {e}")
    # return None
        


def usd(value):
    """Format value as USD."""
    return f"${value:,.2f}"
