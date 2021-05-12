# -*- coding: utf-8 -*-
import os
from cs50 import SQL
from flask import Flask, flash, redirect, render_template, request, session
from flask_session import Session
from tempfile import mkdtemp
from werkzeug.exceptions import default_exceptions, HTTPException, InternalServerError
from werkzeug.security import check_password_hash, generate_password_hash
import datetime
from helpers import apology, login_required, lookup, usd
import spotipy
from spotipy.oauth2 import SpotifyOAuth
import requests
import psycopg2
import psycopg2.extras
import pandas as pd
import lyricsgenius 
import csv
from rq import Queue
from worker import conn
from utils import word_count,get_freq,getlyrics
import time
q = Queue(connection=conn)

# Configure application
app = Flask(__name__)
app.secret_key = "56203ed941434ffc8f9444fbb8d3ea0e"
CLI_ID="92c6a3d2dd7d4efb89ad40c7a33f6e87"
API_BASE = 'https://accounts.spotify.com'
SHOW_DIALOG = True
CLI_SEC="56203ed941434ffc8f9444fbb8d3ea0e"

# Make sure you add this to Redirect URIs in the setting of the application dashboard
REDIRECT_URI = "https://hearthere.herokuapp.com/callback"

SCOPE = 'playlist-modify-private,playlist-modify-public,user-top-read'
genius=lyricsgenius.Genius("gFaD-lKo5gGKfo0W5pz-LYopBmkcLdurWAdaIcukMmB-fCh0ewfD6binGo6dXVe9")



# Ensure templates are auto-reloaded
app.config["TEMPLATES_AUTO_RELOAD"] = True

reader = csv.reader(open('CS50wordcount.csv', 'r',encoding="ISO-8859-1"))
worddata=dict(reader)

# Ensure responses aren't cached
@app.after_request
def after_request(response):
    response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    response.headers["Expires"] = 0
    response.headers["Pragma"] = "no-cache"
    return response


# Custom filter
app.jinja_env.filters["usd"] = usd

# Configure session to use filesystem (instead of signed cookies)
#app.config["SESSION_FILE_DIR"] = mkdtemp()
app.config["SESSION_PERMANENT"] = False
app.config["SESSION_TYPE"] = "filesystem"
Session(app)

#dbs=os.environ['dbu']
#db = SQL(dbs)
datab=psycopg2.connect(os.environ["DATABASE_URL"], sslmode='require')
db=datab.cursor(cursor_factory=psycopg2.extras.DictCursor)


# Configure CS50 Library to use SQLite database
#db=psycopg2.connect(dbs, sslmode='require')

# Make sure API key is set
if not os.environ.get("API_KEY"):
    raise RuntimeError("API_KEY not set")


@app.route("/")
@login_required
def index():
    user = session.get("user_id")
    try:
        return(render_template("index.html",portfolio=session["toke"]))
    except:
        return(apology("Login first!"))


@app.route("/buy", methods=["GET", "POST"])
@login_required
def buy():
    if request.method == "GET":
        print("here")
        sp = spotipy.Spotify(auth=session['toke'])
        response = sp.current_user_top_tracks(limit="10")
        wordbundle=[]
        ratios={}
        for item in response['items']:
            name=item['name']
            artist=item['artists'][0]['name']
            lyrics=getlyrics(name,artist,genius)

            lyrics=lyrics.split("\n")
            for i in lyrics:
                if i:
                    if i[0]=="[" and i[-1]=="]":
                        lyrics.remove(i)
            lyrics=' '.join(lyrics)
            wordbundle.append(lyrics.upper())
        collapsebundle=' '.join(wordbundle)
        collapsebundle=collapsebundle.replace("'","").replace("]","").replace("[","").replace("!","").replace(".","").replace(",","").replace("(","").replace(")","").replace("{","").replace("}","").replace("?","").replace(":","").replace(";","").replace(r"VERSE |[1|2|3]|CHORUS|BRIDGE|OUTRO","").replace("[","").replace("]","").replace(r"INSTRUMENTAL|INTRO|GUITAR|SOLO","")
        big=word_count(collapsebundle)
        total=0
        for key in big:
            total+=int(big[key])
        for key in big:
            if key in worddata:
                ratios[key]=float(big[key])/float(worddata[key])/total
        lyrics=ratios["THE"]
        ratiot = [(k, v) for k, v in ratios.items()]
        ratiot.sort(key = lambda x: x[1])   
        ratiot=ratiot[1:10]
        return render_template("quoted.html",lyrics=ratiot)
    else:
        return apology("sowwy")



@app.route("/history")
@login_required
def history():
   
    user = session.get("user_id")
    sp = spotipy.Spotify(auth=session['toke'])
    response = sp.current_user_top_tracks(limit="30")
    job=q.enqueue(get_freq,args=(response,genius,worddata,datab,user))
    while not job.result:
        pass
    
    return render_template("quoted.html",lyrics=job.result)


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
        db.execute("SELECT * FROM users WHERE username = (%s)", (request.form.get("username"),))
        rows = db.fetchall()
        # Ensure username exists and password is correct
        if len(rows) != 1 or not check_password_hash(rows[0]["hash"], request.form.get("password")):
            return apology("invalid username and/or password", 403)

        # Remember which user has logged in
        session["user_id"] = rows[0]["id"]

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


@app.route("/connect", methods=["GET", "POST"])
@login_required
def connect():
    if request.method == "GET":
        return(render_template("connect.html"))
    if request.method == "POST":

        auth_url = f'{API_BASE}/authorize?client_id={CLI_ID}&response_type=code&redirect_uri={REDIRECT_URI}&scope={SCOPE}&show_dialog={SHOW_DIALOG}'
    
        return redirect(auth_url)


@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "GET":
        return(render_template("register.html"))

    else:
        if request.form.get("username") and request.form.get("password"):
            username = request.form.get("username")
            password = request.form.get("password")
            confirmation = request.form.get("confirmation")
            if confirmation == password:
                phash = generate_password_hash(password)
                check = db.execute("SELECT username FROM users WHERE username = ?", username)
                # A repeated username raises an exception
                try:
                    db.execute("INSERT INTO users (username, hash) VALUES(?, ?)", username, phash)
                    return redirect("/login")
                except:
                    return apology("Username taken!")
            else:
                return apology("Passwords must match!")
        else:
            return apology("Fill everything out!")


@app.route("/sell", methods=["GET", "POST"])
@login_required
def sell():
    if request.method == "GET":
        user = session.get("user_id")
        stockhist = db.execute("SELECT symbol,quantity,buysell FROM transactions WHERE id=?", user)
        transacted = {}
        stocks = []

        for i in stockhist:
            # Goes through and counts how many stocks we have at our disposal
            if i["symbol"] not in transacted:
                if i["buysell"] == "buy":
                    transacted[i["symbol"]] = i["quantity"]
                else:
                    transacted[i["symbol"]] = -i["quantity"]
            else:
                if i["buysell"] == "buy":
                    transacted[i["symbol"]] += i["quantity"]
                else:
                    transacted[i["symbol"]] -= i["quantity"]
        for i in transacted:

            if transacted[i] > 0:
                # Add stock to list of owned stocks
                stocks.append(i.upper())

        return(render_template("sell.html", stocks=stocks))
    else:
        shares = request.form.get("shares")
        symbol = request.form.get("symbol").lower()
        if not shares.isnumeric():
            return apology("Not a valid sell request")
        if float(shares).is_integer():
            shares = int(shares)
            user = session.get("user_id")
            try:
                # This catches people altering the HTML to try and sell a stock that isn't listed
                price = lookup(symbol)['price']
            except:
                return(apology("Editing the HTML sure is fun!"))
            cash = db.execute("SELECT cash FROM users WHERE id=?", user)[0]['cash']

            stockhist = db.execute("SELECT quantity,buysell FROM transactions WHERE symbol=? AND id=?", symbol, user)

            q = 0
            # Count how many stocks we have left
            if stockhist:
                for i in stockhist:
                    if i['buysell'] == "buy":
                        q += i['quantity']

                    else:
                        q -= i['quantity']
            # Check if we have enough to sell
            if q >= shares:
                db.execute("UPDATE users SET cash = ? WHERE id = ?", int(cash + shares * price), user)
                db.execute("INSERT INTO transactions (id, price, time, symbol, quantity, buysell) VALUES(?, ?, ?, ?, ?, ?)",
                           user, price, datetime.datetime.now(), symbol, shares, "sell")
                return redirect("/")
            else:
                return apology("You don't own enough shares!")
        else:
            return apology("Not a valid sell request")

    return apology("TODO")
@app.route("/callback")
def callback():
    code = request.args.get('code')

    auth_token_url = f"{API_BASE}/api/token"
    res = requests.post(auth_token_url, data={
        "grant_type":"authorization_code",
        "code":code,
        "redirect_uri":REDIRECT_URI,
        "client_id":CLI_ID,
        "client_secret":CLI_SEC
        })

    res_body = res.json()
 
    session["toke"] = res_body.get("access_token")

    return redirect("/")

@app.route("/deposit", methods=["GET", "POST"])
@login_required
def deposit():

    return render_template("quoted.html",lyrics=ratiot)


def errorhandler(e):
    """Handle error"""
    if not isinstance(e, HTTPException):
        e = InternalServerError()
    return apology(e.name, e.code)


# Listen for errors
for code in default_exceptions:
    app.errorhandler(code)(errorhandler)
