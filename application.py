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
# Configure variables we will be using throughout
app.secret_key = "56203ed941434ffc8f9444fbb8d3ea0e"
CLI_ID="92c6a3d2dd7d4efb89ad40c7a33f6e87"
API_BASE = 'https://accounts.spotify.com'
SHOW_DIALOG = True
CLI_SEC="56203ed941434ffc8f9444fbb8d3ea0e"

# Redirect URI for the Spotify API
REDIRECT_URI = "https://hearthere.herokuapp.com/callback"

SCOPE = 'playlist-modify-private,playlist-modify-public,user-top-read'
# Configure Genius API
genius=lyricsgenius.Genius("gFaD-lKo5gGKfo0W5pz-LYopBmkcLdurWAdaIcukMmB-fCh0ewfD6binGo6dXVe9")



# Ensure templates are auto-reloaded
app.config["TEMPLATES_AUTO_RELOAD"] = True
# Load reference dataset
reader = csv.reader(open('CS50wordcount.csv', 'r',encoding="ISO-8859-1"))
worddata=dict(reader)

# Ensure responses aren't cached
@app.after_request
def after_request(response):
    response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    response.headers["Expires"] = 0
    response.headers["Pragma"] = "no-cache"
    return response




# Configure session to use filesystem (instead of signed cookies)
app.config["SESSION_PERMANENT"] = False
app.config["SESSION_TYPE"] = "filesystem"
Session(app)

#Initialize database connection
datab=psycopg2.connect(os.environ["DATABASE_URL"], sslmode='require')
db=datab.cursor(cursor_factory=psycopg2.extras.DictCursor)






@app.route("/")
@login_required
def index():
    # Check if we've logged into Spotify yet
    user = session.get("user_id")
    try:
        session['toke']
        return(render_template("loggedin.html"))
    except:
        return(render_template("index.html"))


@app.route("/scrape",methods=["GET", "POST"])
@login_required
def scrape():
    # Load scraping page
    if request.method=="GET":
        return render_template("connect.html")
    if request.method=="POST":
        try:
            # Get stuff from the webpage
            lim=int(request.form.get("songno"))
            if lim>50:
                return render_template("warning.html",warning="Max 50!")
            timespan = request.form.get("timespan")
            user = session.get("user_id")
            # Connect to Spotify and get our access token
            sp = spotipy.Spotify(auth=session['toke'])
            response = sp.current_user_top_tracks(limit=lim,time_range=timespan)
            # So that the request doesn't timeout, send it to another worker
            job=q.enqueue(get_freq,args=(response,genius,worddata,user))
            # Show user the songs whose lyrics we just scraped
            songlist=[]
            for item in response['items']:
                name=item['name']
                artist=item['artists'][0]['name']
                songlist.append((name,artist))
            return render_template("songlist.html",songlist=songlist)
        except:
            return render_template("warning.html",warning="You need to log in to Spotify!")
@app.route("/whatis",methods=["GET"])
@login_required
def whatis():
    # Load explainer page
    if request.method=="GET":
        return render_template("whatisthis.html")
    

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
    # Authenticate with Spotify API
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
        # Probably unnecessary connection 
        datab=psycopg2.connect(os.environ["DATABASE_URL"], sslmode='require')
        db=datab.cursor()
        if request.form.get("username") and request.form.get("password"):
            username = request.form.get("username")
            password = request.form.get("password")
            confirmation = request.form.get("confirmation")
            if confirmation == password:
                phash = generate_password_hash(password)
                #check = db.execute("SELECT username FROM users WHERE username = %s", (username,))
                # A repeated username raises an exception
                db.execute("SELECT MAX(id) FROM users ", (username, phash))
                rows=db.fetchall()
               
                newid=rows[0][0]+1
                db.execute("INSERT INTO users (id,username, hash) VALUES (%s,%s, %s)", (newid,username, phash))
                datab.commit()
                return redirect("/login")
                
                
            else:
                return apology("Passwords must match!")
        else:
            return apology("Fill everything out!")

@app.route("/callback")
def callback():
    # Method needed to finish authentication
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

@app.route("/viewdatal", methods=["GET", "POST"])
@login_required
def viewdatal():
    user=session.get("user_id")
    datab=psycopg2.connect(os.environ["DATABASE_URL"], sslmode='require')
    db=datab.cursor(cursor_factory=psycopg2.extras.DictCursor)
    # Ratio tuples - word/fequency pairs
    ratiot=[]
    int(session.get("user_id"))
    db.execute("SELECT * FROM userfreqs WHERE id=%s",(int(user),))
    rows = db.fetchall()
    datab.commit()
    
    if rows:
        # Rows are presorted so let's see what the first 10 elements are
        rows=rows[:10]
        for i in rows:
            ratiot.append((i["word"],round(i["freq"],3)))
        return render_template("freqs.html",freqs=ratiot,whatare="Underrepresented words")
    else:
        render_template("warning.html",warning="Scrape some data from Spotify first!")

@app.route("/viewdatam", methods=["GET", "POST"])
@login_required
def viewdatam():
    user=session.get("user_id")
    datab=psycopg2.connect(os.environ["DATABASE_URL"], sslmode='require')
    db=datab.cursor(cursor_factory=psycopg2.extras.DictCursor)
    ratiot=[]
    int(session.get("user_id"))
    db.execute("SELECT * FROM userfreqs WHERE id=%s",(int(user),))
    rows = db.fetchall()
    # Better safe than sorry. The sheer number of SQL errors I got...
    datab.commit()
    if rows:
        # Rows are presorted so let's see what the last 10 elements are (overrepresented ones)
        rows=rows[-10:]
        for i in rows:
            ratiot.append((i["word"],round(i["freq"],3)))
        return render_template("freqs.html",freqs=ratiot,whatare="Overrepresented words")
    else:
        render_template("warning.html",warning="Scrape some data from Spotify first!")


def errorhandler(e):
    """Handle error"""
    if not isinstance(e, HTTPException):
        e = InternalServerError()
    return apology(e.name, e.code)


# Listen for errors
for code in default_exceptions:
    app.errorhandler(code)(errorhandler)
