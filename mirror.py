import sys
from PyQt6.QtCore import *
from PyQt6.QtGui import *
from PyQt6.QtWidgets import *
from PyQt6.QtMultimedia import *
from PyQt6.QtMultimediaWidgets import *
from multiprocessing import Process, Queue
from threading import Thread
from datetime import datetime
import time
import requests
import json
import feedparser
import speech_recognition as sr
import vlc
import pafy
import http.server
import cgi
from os import curdir, sep
import socket

#Add widget: https://www.biblegateway.com/votd/get/?format=json&version=kjv

# Web Server Values
HOST_NAME = ''
PORT_NUMBER = 8000

# OpenWeatherMap API Values
latitude = 32.500706
longitude = -94.740486
location = "Longview"
weatherAPIKey = "e8daae205d7d385ea3588d79781c9327"

#Coin Market Cap API
cryptoAPI = '9883a0ee-d826-4d44-8728-e2e117927dc5'

# Queue that will contain the commands recieved by the web server and the voice recognition service
# Queue is used for data sharing between processes
q = Queue()

# Preset fonts
font12 = QFont("Montserrat", 12)
font15 = QFont("Montserrat", 15)
font18 = QFont("Montserrat", 18)
font25 = QFont("Montserrat", 25)
numFont15 = QFont("Roboto Light", 15)
numFont18 = QFont("Roboto Light", 18)
numFont35 = QFont("Roboto Light", 50)


class MyHandler(http.server.BaseHTTPRequestHandler):
    # handler for GET requests
    def do_GET(self):
        if self.path == "/" or self.path == "/send":
            self.path = "/index.html"

        try:
            sendReply = False
            if self.path.endswith(".html"):
                mimetype = "text/html"
                sendReply = True

            if sendReply:
                f = open(curdir + sep + self.path)
                self.send_response(200)
                self.send_header("Content-type", mimetype)
                self.end_headers()
                self.wfile.write(f.read().encode())
                f.close()
            return

        except IOError:
            self.send_error(404, "File not found: %s" % self.path)

    # handler for POST requests
    def do_POST(self):
        global q
        if self.path == "/send":
            self.path = "/"
            form = cgi.FieldStorage(
                fp=self.rfile,
                headers=self.headers,
                environ={"REQUEST_METHOD": "POST",
                         "CONTENT_TYPE": self.headers["Content-Type"],
                         })

            if form["command"].value == "EXIT":
                q.put("EXIT")
            elif form["command"].value == "SEARCH":
                query = form.getvalue('ytsearch')
                q.put("SEARCH-YOUTUBE")
                q.put("%20".join(query.split()))
            elif form["command"].value.isnumeric():
                q.put("SELECT-FROM-YOUTUBE-MENU")
                q.put(int(form["command"].value) - 1)
            elif form["command"].value == "EXIT YOUTUBE MENU":
                q.put("CLOSE-YOUTUBE-MENU")
            elif form["command"].value == "EXIT YOUTUBE":
                q.put("CLOSE-YOUTUBE")
            elif form["command"].value == "PLAY":
                q.put("UNPAUSE-YOUTUBE")
            elif form["command"].value == "PAUSE":
                q.put("PAUSE-YOUTUBE")

            self.do_GET()
            return


# Weather Widget
class Weather(QWidget):
    def __init__(self):
        super(Weather, self).__init__()
        locationLabel = QLabel(location)
        locationLabel.setFont(font15)
        locationLabel.setAlignment(Qt.AlignmentFlag.AlignRight)
        self.icons = [QLabel(), QLabel(), QLabel(), QLabel(), QLabel()]
        self.temps = [QLabel(), QLabel(), QLabel(), QLabel()]

        for i in self.temps:
            i.setFont(numFont18)
            i.setAlignment(Qt.AlignmentFlag.AlignCenter)

        for i in self.icons:
            i.setAlignment(Qt.AlignmentFlag.AlignRight)

        self.icons[0].setAlignment(Qt.AlignmentFlag.AlignCenter)

        self.current = QHBoxLayout()
        self.currText = QLabel()
        self.currText.setFont(numFont35)
        self.current.addWidget(self.icons[0])
        self.current.addWidget(self.currText)

        self.future1 = QHBoxLayout()
        self.future1.addWidget(self.icons[1])
        self.future1.addWidget(self.temps[0])

        self.future2 = QHBoxLayout()
        self.future2.addWidget(self.icons[2])
        self.future2.addWidget(self.temps[1])

        self.future3 = QHBoxLayout()
        self.future3.addWidget(self.icons[3])
        self.future3.addWidget(self.temps[2])

        self.future4 = QHBoxLayout()
        self.future4.addWidget(self.icons[4])
        self.future4.addWidget(self.temps[3])

        # Container
        self.firstContainer = QVBoxLayout()
        self.firstContainer.addWidget(locationLabel)
        self.firstContainer.addLayout(self.current)
        hourlytxt = QLabel("Hourly Forecast")
        hourlytxt.setFont(numFont15)
        hourlytxt.setAlignment(Qt.AlignmentFlag.AlignRight)
        self.container = QVBoxLayout()
        self.firstContainer.addWidget(hourlytxt)
        self.secondContainer = QVBoxLayout()
        self.secondContainer.addLayout(self.future1)
        self.secondContainer.addLayout(self.future2)
        self.secondContainer.addLayout(self.future3)
        self.secondContainer.addLayout(self.future4)
        self.secondContainer.setAlignment(Qt.AlignmentFlag.AlignRight)
        self.container.addLayout(self.firstContainer)
        self.container.addLayout(self.secondContainer)
        self.container.setContentsMargins(0, 0, 0, 0)

        self.setLayout(self.container)

        # Timer to update weather every hour
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.getWeather)
        self.timer.start(3600000)
        self.getWeather()

    # Gets and sets the current weather data
    def getWeather(self):
        print("API: getting weather")

        # Get data from API URL
        OWMAPIURL = "https://api.openweathermap.org/data/2.5/forecast?lat=" + str(latitude) + \
            "&lon=" + \
            str(longitude) + "&exclude=alerts&units=imperial&cnt=5&appid=" + \
            str(weatherAPIKey)
        weatherJSON = json.loads(requests.get(OWMAPIURL).text)

        # Set Temperatures
        self.currText.setText(
            str(round(float(weatherJSON["list"][0]["main"]["temp"]), 1)) + "°")
        for i in range(len(weatherJSON["list"]) - 1):
            self.temps[i].setText(
                "   " + str(round(float(weatherJSON["list"][i + 1]["main"]["temp"]), 1)) + "°")

        # Get and set icons
        icon = weatherJSON["list"][0]["weather"][0]["icon"]
        image = QImage()
        image.loadFromData(requests.get(
            "https://openweathermap.org/img/wn/" + str(icon) + "@2x.png").content)
        pix = QPixmap(image)
        self.icons[0].setPixmap(pix)
        for i in range(len(weatherJSON["list"]) - 1):
            icon = weatherJSON["list"][i + 1]["weather"][0]["icon"]

            image = QImage()
            image.loadFromData(requests.get(
                "https://openweathermap.org/img/wn/" + str(icon) + "@2x.png").content)
            pix = QPixmap(image)
            pix = pix.scaled(64, 64, Qt.AspectRatioMode.KeepAspectRatio)
            self.icons[i + 1].setPixmap(pix)

        print("API: weather received")


# News Widget
class News(QWidget):
    def __init__(self):
        super(News, self).__init__()

        self.heading = QLabel()
        self.heading.setFont(font25)
        self.heading.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.heading.setWordWrap(True)

        self.vbox = QVBoxLayout()
        self.vbox.addWidget(self.heading)

        self.setLayout(self.vbox)

        self.parsedNews = []
        self.currPlace = 0
        self.getNews()

        # Timer that updates news feed every hour
        timer = QTimer(self)
        timer.timeout.connect(self.getNews)
        timer.start(3600000)

    # Gets and sets current news by Babylon Bee
    def getNews(self):
        print("API: getting news")
        try:
            # Parse XML
            rawNews = feedparser.parse("https://babylonbee.com/feed")
            self.parsedNews = [i.title for i in rawNews.entries]
            self.heading.setText(self.parsedNews[self.currPlace])

            # Timer that calls nextArticle() every 10 seconds
            timer = QTimer(self)
            timer.timeout.connect(self.nextArticle)
            timer.start(10000)
            print("API: news received")
        except Exception as e:
            print("ERROR " + str(e) + ". Issue with fetching news")

    # Sets displayed headline to next headline in cycle
    def nextArticle(self):
        self.currPlace += 1
        if self.currPlace >= len(self.parsedNews):
            self.currPlace = 0

        self.heading.setText(self.parsedNews[self.currPlace])


# Clock Widget
class Clock(QWidget):
    def __init__(self):
        super(Clock, self).__init__()
        self.wholeContainer = QVBoxLayout()

        self.dateLabel = QLabel()
        self.dateLabel.setFont(font18)
        self.timeLabel = QLabel()
        self.timeLabel.setFont(numFont35)

        self.wholeContainer.addWidget(self.dateLabel)
        self.wholeContainer.addWidget(self.timeLabel)

        self.setLayout(self.wholeContainer)

        # Timer that calls getTime() every 0.9 seconds
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.getTime)
        self.timer.start(900)

    # Updates time with python time module
    def getTime(self):
        tm = time.strftime('%I:%M %p')
        if tm[0] == "0":
            self.timeLabel.setText(time.strftime('%I:%M %p')[1:])
        else:
            self.timeLabel.setText(time.strftime('%I:%M %p'))
        if self.dateLabel.text != time.strftime('%A, %b %d %Y'):
            self.dateLabel.setText(time.strftime("%A, %b %d %Y"))


# Cryptocurrency Widget
class Crypto(QWidget):
    def __init__(self):
        super().__init__()
        self.container = QHBoxLayout()
        self.icons = [QLabel(), QLabel(), QLabel()]

        # Coin 1
        image = QImage()
        image.loadFromData(requests.get(
            "https://s2.coinmarketcap.com/static/img/coins/64x64/1.png").content)
        pix = QPixmap(image)
        pix = pix.scaled(37, 37, Qt.AspectRatioMode.KeepAspectRatio)
        self.icons[0].setPixmap(pix)
        self.icons[0].setAlignment(Qt.AlignmentFlag.AlignCenter)

        # Coin 2
        image2 = QImage()
        image2.loadFromData(requests.get(
            "https://s2.coinmarketcap.com/static/img/coins/64x64/1027.png").content)
        pix = QPixmap(image2)
        pix = pix.scaled(37, 37, Qt.AspectRatioMode.KeepAspectRatio)
        self.icons[1].setPixmap(pix)
        self.icons[1].setAlignment(Qt.AlignmentFlag.AlignCenter)

        # Coin 3
        image3 = QImage()
        image3.loadFromData(requests.get(
            "https://s2.coinmarketcap.com/static/img/coins/64x64/5994.png").content)
        pix = QPixmap(image3)
        pix = pix.scaled(48, 48, Qt.AspectRatioMode.KeepAspectRatio)
        self.icons[2].setPixmap(pix)
        self.icons[2].setAlignment(Qt.AlignmentFlag.AlignCenter)

        # Coins Layout
        self.iconVBox = QVBoxLayout()
        txt0 = QLabel("Coin Gecko")
        txt0.setFont(font15)
        txt0.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.iconVBox.addWidget(txt0)
        self.iconVBox.addWidget(self.icons[0])
        self.iconVBox.addWidget(self.icons[1])
        self.iconVBox.addWidget(self.icons[2])
        self.container.addLayout(self.iconVBox)

        # Prices Layout
        self.prices = [QLabel(), QLabel(), QLabel()]
        for i in self.prices:
            i.setFont(numFont18)
            i.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.priceVBox = QVBoxLayout()
        txt1 = QLabel("Price")
        txt1.setFont(font15)
        txt1.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.priceVBox.addWidget(txt1)
        self.priceVBox.addWidget(self.prices[0])
        self.priceVBox.addWidget(self.prices[1])
        self.priceVBox.addWidget(self.prices[2])
        self.container.addLayout(self.priceVBox)

        # Hourly changes Layout
        self.hourlyChange = [QLabel(), QLabel(), QLabel()]
        for i in self.hourlyChange:
            i.setFont(numFont18)
            i.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.hourlyVBox = QVBoxLayout()
        txt2 = QLabel("1h %")
        txt2.setFont(font15)
        txt2.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.hourlyVBox.addWidget(txt2)
        self.hourlyVBox.addWidget(self.hourlyChange[0])
        self.hourlyVBox.addWidget(self.hourlyChange[1])
        self.hourlyVBox.addWidget(self.hourlyChange[2])
        self.container.addLayout(self.hourlyVBox)

        # Daily changes Layout
        self.dailyChange = [QLabel(), QLabel(), QLabel()]
        for i in self.dailyChange:
            i.setFont(numFont18)
            i.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.dailyVBox = QVBoxLayout()
        txt3 = QLabel("24h %")
        txt3.setFont(font15)
        txt3.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.dailyVBox.addWidget(txt3)
        self.dailyVBox.addWidget(self.dailyChange[0])
        self.dailyVBox.addWidget(self.dailyChange[1])
        self.dailyVBox.addWidget(self.dailyChange[2])
        self.container.addLayout(self.dailyVBox)

        # Weekly changes layout
        self.weeklyChange = [QLabel(), QLabel(), QLabel()]
        for i in self.weeklyChange:
            i.setFont(numFont18)
            i.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.weeklyVBox = QVBoxLayout()
        txt4 = QLabel("7d %")
        txt4.setFont(font15)
        txt4.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.weeklyVBox.addWidget(txt4)
        self.weeklyVBox.addWidget(self.weeklyChange[0])
        self.weeklyVBox.addWidget(self.weeklyChange[1])
        self.weeklyVBox.addWidget(self.weeklyChange[2])

        self.container.addLayout(self.weeklyVBox)

        self.setLayout(self.container)

        # Update Crypto Data every 5 minutes
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.getCryptoStuff)
        self.timer.start(300000)

    def getCryptoStuff(self):
        print("API: getting crypto data")
        # url = 'https://pro-api.coinmarketcap.com/v1/cryptocurrency/quotes/latest'

        # parameters = { 'slug': 'bitcoin,ethereum,shiba-inu', 'convert': 'USD' }
        # headers = {
        # 'Accepts': 'application/json',
        # 'X-CMC_PRO_API_KEY': cryptoAPI,
        # }
        
        # session = requests.Session()
        # session.headers.update(headers)

        # cryptoData = json.loads(session.get(url, params=parameters).text)

        #Dummy Data for Testing
        cryptoData = {'status': {'timestamp': '2024-05-08T02:24:59.921Z', 'error_code': 0, 'error_message': None, 'elapsed': 46, 'credit_count': 1, 'notice': None}, 'data': {'1': {'id': 1, 'name': 'Bitcoin', 'symbol': 'BTC', 'slug': 'bitcoin', 'num_market_pairs': 11025, 'date_added': '2010-07-13T00:00:00.000Z', 'tags': ['mineable', 'pow', 'sha-256', 'store-of-value', 'state-channel', 'coinbase-ventures-portfolio', 'three-arrows-capital-portfolio', 'polychain-capital-portfolio', 'binance-labs-portfolio', 'blockchain-capital-portfolio', 'boostvc-portfolio', 'cms-holdings-portfolio', 'dcg-portfolio', 'dragonfly-capital-portfolio', 'electric-capital-portfolio', 'fabric-ventures-portfolio', 'framework-ventures-portfolio', 'galaxy-digital-portfolio', 'huobi-capital-portfolio', 'alameda-research-portfolio', 'a16z-portfolio', '1confirmation-portfolio', 'winklevoss-capital-portfolio', 'usv-portfolio', 'placeholder-ventures-portfolio', 'pantera-capital-portfolio', 'multicoin-capital-portfolio', 'paradigm-portfolio', 'bitcoin-ecosystem', 'ftx-bankruptcy-estate'], 'max_supply': 21000000, 'circulating_supply': 19695325, 'total_supply': 19695325, 'is_active': 1, 'infinite_supply': False, 'platform': None, 'cmc_rank': 1, 'is_fiat': 0, 'self_reported_circulating_supply': None, 'self_reported_market_cap': None, 'tvl_ratio': None, 'last_updated': '2024-05-08T02:24:00.000Z', 'quote': {'USD': {'price': 62742.46267781855, 'volume_24h': 25910254672.231747, 'volume_change_24h': -12.2546, 'percent_change_1h': 0.29687516, 'percent_change_24h': -1.61850602, 'percent_change_7d': 5.36664474, 'percent_change_30d': -9.45216392, 'percent_change_60d': -7.9191499, 'percent_change_90d': 40.58676603, 'market_cap': 1235733193740.0066, 'market_cap_dominance': 53.5561, 'fully_diluted_market_cap': 1317591716234.19, 'tvl': None, 'last_updated': '2024-05-08T02:24:00.000Z'}}}, '1027': {'id': 1027, 'name': 'Ethereum', 'symbol': 'ETH', 'slug': 'ethereum', 'num_market_pairs': 8900, 'date_added': '2015-08-07T00:00:00.000Z', 'tags': ['pos', 'smart-contracts', 'ethereum-ecosystem', 'coinbase-ventures-portfolio', 'three-arrows-capital-portfolio', 'polychain-capital-portfolio', 'binance-labs-portfolio', 'blockchain-capital-portfolio', 'boostvc-portfolio', 'cms-holdings-portfolio', 'dcg-portfolio', 'dragonfly-capital-portfolio', 'electric-capital-portfolio', 'fabric-ventures-portfolio', 'framework-ventures-portfolio', 'hashkey-capital-portfolio', 'kenetic-capital-portfolio', 'huobi-capital-portfolio', 'alameda-research-portfolio', 'a16z-portfolio', '1confirmation-portfolio', 'winklevoss-capital-portfolio', 'usv-portfolio', 'placeholder-ventures-portfolio', 'pantera-capital-portfolio', 'multicoin-capital-portfolio', 'paradigm-portfolio', 'injective-ecosystem', 'layer-1', 'ftx-bankruptcy-estate'], 'max_supply': None, 'circulating_supply': 120103321.12759581, 'total_supply': 120103321.12759581, 'is_active': 1, 'infinite_supply': True, 'platform': None, 'cmc_rank': 2, 'is_fiat': 0, 'self_reported_circulating_supply': None, 'self_reported_market_cap': None, 'tvl_ratio': None, 'last_updated': '2024-05-08T02:23:00.000Z', 'quote': {'USD': {'price': 3029.5986263570344, 'volume_24h': 11914695438.332094, 'volume_change_24h': -10.1295, 'percent_change_1h': 0.25721041, 'percent_change_24h': -1.997289, 'percent_change_7d': 1.83943281, 'percent_change_30d': -11.65717152, 'percent_change_60d': -22.57770018, 'percent_change_90d': 24.51184675, 'market_cap': 363864856709.08203, 'market_cap_dominance': 15.7779, 'fully_diluted_market_cap': 363864856709.08, 'tvl': None, 'last_updated': '2024-05-08T02:23:00.000Z'}}}, '5994': {'id': 5994, 'name': 'Shiba Inu', 'symbol': 'SHIB', 'slug': 'shiba-inu', 'num_market_pairs': 805, 'date_added': '2020-08-01T00:00:00.000Z', 'tags': ['memes', 'ethereum-ecosystem', 'doggone-doggerel'], 'max_supply': None, 'circulating_supply': 589289410812691, 'total_supply': 589534086491242.2, 'platform': {'id': 1027, 'name': 'Ethereum', 'symbol': 'ETH', 'slug': 'ethereum', 'token_address': '0x95ad61b0a150d79219dcf64e1e6cc01f0b64c4ce'}, 'is_active': 1, 'infinite_supply': False, 'cmc_rank': 11, 'is_fiat': 0, 'self_reported_circulating_supply': None, 'self_reported_market_cap': None, 'tvl_ratio': None, 'last_updated': '2024-05-08T02:23:00.000Z', 'quote': {'USD': {'price': 2.3064574049514156e-05, 'volume_24h': 413871655.89457685, 'volume_change_24h': -28.7664, 'percent_change_1h': -0.22770932, 'percent_change_24h': -4.3326218, 'percent_change_7d': 6.24862726, 'percent_change_30d': -17.7332248, 'percent_change_60d': -34.92189397, 'percent_change_90d': 154.16718823, 'market_cap': 13591709252.28388, 'market_cap_dominance': 0.5893, 'fully_diluted_market_cap': 13597352592.59, 'tvl': None, 'last_updated': '2024-05-08T02:23:00.000Z'}}}}}
        num = 0
        for i in cryptoData["data"]:
            self.prices[num].setText(
                ("{:.2f}".format(cryptoData["data"][i]["quote"]["USD"]["price"])).rstrip('.'))

            hrChnge = ("{:.2f}".format(
                cryptoData["data"][i]["quote"]["USD"]["percent_change_1h"])).rstrip('.')
            if self.hourlyChange[num] != hrChnge + "%":
                self.hourlyChange[num].setText(hrChnge + "%")
                if float(hrChnge) < 0:
                    self.hourlyChange[num].setStyleSheet(
                        "color: rgb(234, 57, 67);")
                elif float(hrChnge) > 0:
                    self.hourlyChange[num].setStyleSheet(
                        "color: rgb(22, 199, 132);")
                else:
                    self.hourlyChange[num].setText("0%")
                    self.hourlyChange[num].setStyleSheet("color: white;")

            dayChnge = ("{:.2f}".format(
                cryptoData["data"][i]["quote"]["USD"]["percent_change_24h"])).rstrip('.')
            if self.dailyChange[num] != dayChnge + "%":
                self.dailyChange[num].setText(dayChnge + "%")
                if float(dayChnge) < 0:
                    self.dailyChange[num].setStyleSheet(
                        "color: rgb(234, 57, 67);")
                elif float(dayChnge) > 0:
                    self.dailyChange[num].setStyleSheet(
                        "color: rgb(22, 199, 132);")
                else:
                    self.dailyChange[num].setStyleSheet("color: white;")

            weekChnge = ("{:.2f}".format(
                cryptoData["data"][i]["quote"]["USD"]["percent_change_7d"])).rstrip('.')
            if self.weeklyChange[num] != weekChnge + "%":
                self.weeklyChange[num].setText(weekChnge + "%")
                if float(weekChnge) < 0:
                    self.weeklyChange[num].setStyleSheet(
                        "color: rgb(234, 57, 67);")
                elif float(weekChnge) > 0:
                    self.weeklyChange[num].setStyleSheet(
                        "color: rgb(22, 199, 132);")
                else:
                    self.weeklyChange[num].setStyleSheet("color: white;")
            num += 1
        print("API: crypto data recieved")

# YouTube Widget
class YouTube(QWidget):
    def __init__(self):
        super(YouTube, self).__init__()
        # Create VLC media player
        self.mediaplayer = vlc.MediaPlayer()

        # Create QFrame
        self.videoframe = QFrame()
        self.videoframe.setFixedSize(300, 300)

        # Embed media player in QFrame
        if sys.platform.startswith("linux"):
            self.mediaplayer.set_xwindow(self.videoframe.winId())
        elif sys.platform == "win32":
            self.mediaplayer.set_hwnd(self.videoframe.winId())

        self.vboxlayout = QVBoxLayout()
        self.vboxlayout.insertWidget(0, self.videoframe)

        self.setLayout(self.vboxlayout)

        self.mediaplayer.stop()

    # Creates new VLC mediaplayer with new youtube ID
    def newVid(self, videoId):
        self.mediaplayer = vlc.MediaPlayer(pafy.new(videoId).getbest().url)
        self.videoframe = QFrame()

        if sys.platform.startswith("linux"):
            self.mediaplayer.set_xwindow(self.videoframe.winId())
        elif sys.platform == "win32":
            self.mediaplayer.set_hwnd(self.videoframe.winId())

        self.vboxlayout.insertWidget(0, self.videoframe)

        self.mediaplayer.play()
        self.videoframe.setFixedSize(300, 300)
        self.setFixedSize(300, 300)

    # Not to be used to play a video
    # Just for adding an appropriately sized space in the middle of the screen
    # Video ID entered is a DUMMY ID to get the mediaplayer to work properly and take up the space
    def createVid(self):
        self.mediaplayer = vlc.MediaPlayer(
            pafy.new("dQw4w9WgXcQ").getbest().url)
        self.videoframe = QFrame()

        if sys.platform.startswith("linux"):
            self.mediaplayer.set_xwindow(self.videoframe.winId())
        elif sys.platform == "win32":
            self.mediaplayer.set_hwnd(self.videoframe.winId())

        self.vboxlayout.insertWidget(0, self.videoframe)
        self.mediaplayer.stop()

        self.videoframe.setFixedSize(300, 300)
        self.setFixedSize(300, 300)


# Youtube Menu Widget
class YTMenu(QWidget):
    def __init__(self):
        super(YTMenu, self).__init__()
        self.container = QGridLayout()
        self.setLayout(self.container)

    # Adds videos to the menu
    def addVideos(self, vidList):
        n = 0
        for i in range(3):
            for k in range(3):
                if n >= len(vidList):
                    break
                vbox = QVBoxLayout()
                image = QImage()
                image.loadFromData(requests.get(vidList[n][0]).content)
                pixmap = QPixmap(image)
                imgLbl = QLabel()
                imgLbl.setPixmap(pixmap)
                vbox.addWidget(imgLbl)
                if len(vidList[n][1]) > 25:
                    l = QLabel(vidList[n][1][:20] + "...")
                else:
                    l = QLabel(vidList[n][1])
                l.setFont(font12)
                vbox.addWidget(l)
                self.container.addLayout(vbox, i, k)
                n += 1
        print("LOG: all layouts added to YouTube menu")

    # Removes all videos and deletes the menu
    def removeVideos(self):
        for i in reversed(range(self.container.count())):
            for k in reversed(range(self.container.itemAt(i).layout().count())):
                self.container.itemAt(i).layout().itemAt(
                    k).widget().deleteLater()

# MainWindow Widget
# Contains all widgets with proper placement
class MainWindow(QWidget):
    def __init__(self):
        super().__init__()
        self.setAutoFillBackground(True)

        pal = QPalette()
        pal.setColor(QPalette.ColorRole.Window, QColor(0, 0, 0))
        pal.setColor(QPalette.ColorRole.WindowText, QColor(255, 255, 255))
        self.setPalette(pal)

        self.container = QGridLayout()

        self.clock = Clock()
        self.clock.setFixedHeight(150)

        self.weather = Weather()
        self.weather.setFixedHeight(400)
        self.weather.setFixedWidth(300)

        self.youtubeMenu = YTMenu()
        self.output = []
        self.youtube = YouTube()
        self.youtube.setFixedSize(854, 480)

        self.news = News()
        self.news.setFixedHeight(100)

        self.todo = Crypto()
        self.todo.setFixedHeight(275)
        self.todo.setFixedWidth(350)

        self.crypto = Crypto()
        self.crypto.setFixedHeight(275)
        self.crypto.setFixedWidth(625)

        # Border adds a spacing to above and below all the widgets
        border = QLabel()
        border.setFixedHeight(5)

        self.container.addWidget(border, 0, 0, 1, 3)
        self.container.addWidget(
            self.clock, 1, 0, 1, 2, Qt.AlignmentFlag.AlignTop)
        self.container.addWidget(
            self.weather, 1, 2, Qt.AlignmentFlag.AlignRight)
        self.container.addWidget(
            self.youtube, 2, 0, 1, 3, Qt.AlignmentFlag.AlignCenter)
        self.container.addWidget(self.news, 3, 0, 1, 3)
        self.container.addWidget(self.todo, 4, 0)
        self.container.addWidget(
            self.crypto, 4, 2, Qt.AlignmentFlag.AlignRight)
        self.container.addWidget(border, 5, 0, 1, 3)

        self.youtube.createVid()
        self.youtube.videoframe.setFixedSize(854, 480)

        # Create timer that calls commandCheck() ever 0.5 seconds
        self.checkTimer = QTimer(self)
        self.checkTimer.timeout.connect(self.commandCheck)
        self.checkTimer.start(500)

        # Create process that runs the voice assistant
        voiceAssistantProcess = Process(target=getSpeech, args=(q, ))
        voiceAssistantProcess.daemon = True
        voiceAssistantProcess.start()

        # Create thread that runs the web server
        webServerThread = Thread(target=runServer)
        webServerThread.daemon = True
        webServerThread.start()

        self.setLayout(self.container)
        self.setFixedSize(1080, 1920)

    # Checks the queue for new commands that come from the web server and voice assistant
    def commandCheck(self):
        if not q.empty():
            cmd = q.get()
            if cmd == "EXIT":
                sys.exit(0)
            elif cmd == "CLOSE-YOUTUBE":
                if self.youtube:
                    self.youtube.mediaplayer.stop()
                    self.youtube.deleteLater()
                    self.youtube = None
                    self.youtube = YouTube()
                    self.youtube.createVid()
                    self.container.addWidget(
                        self.youtube, 2, 0, 1, 3, Qt.AlignmentFlag.AlignCenter)
            elif cmd == "PAUSE-YOUTUBE":
                if self.youtube and self.youtube.mediaplayer.is_playing():
                    print("LOG: pausing youtube")
                    self.youtube.mediaplayer.pause()
            elif cmd == "UNPAUSE-YOUTUBE":
                if self.youtube:
                    print("LOG: unpausing youtube")
                    self.youtube.mediaplayer.play()
            elif cmd == "SEARCH-YOUTUBE":
                if self.youtube:
                    self.youtube.mediaplayer.stop()
                    self.youtube.deleteLater()
                    self.youtube = None
                if self.youtubeMenu:
                    self.youtubeMenu.removeVideos()
                    self.youtubeMenu.deleteLater()
                    self.youtubeMenu = None

                self.youtube = YouTube()
                self.youtube.setFixedSize(854, 480)
                query = q.get()

                videoData = json.loads(requests.get(
                    "https://youtube.googleapis.com/youtube/v3/search?part=snippet&maxResults=9&q=" + query + "&type=video&key=AIzaSyDQzpnQ3n0CGBxvlV0CWw35sk5Ok73Nfdk").text)
                self.output = []
                for i in range(9):
                    self.output.append(
                        [videoData["items"][i]["snippet"]["thumbnails"]["default"]["url"], videoData["items"][i]["snippet"]["title"], videoData["items"][i]["id"]["videoId"]])
                print("LOG: add videos function called")
                if not self.youtubeMenu:
                    self.youtubeMenu = YTMenu()
                self.youtubeMenu.setFixedWidth(1030)
                self.youtubeMenu.addVideos(self.output)
                self.youtubeMenu.setFixedHeight(400)
                self.container.addWidget(self.youtubeMenu, 2, 0, 1, 3)
            elif cmd == "SELECT-FROM-YOUTUBE-MENU":
                try:
                    query = int(q.get())
                except:
                    print("ERROR: Something went wrong with inputting selection")
                if self.output:
                    self.youtubeMenu.removeVideos()
                    self.youtubeMenu.deleteLater()
                    self.youtubeMenu = None
                    if self.youtube:
                        self.youtube.mediaplayer.stop()
                        self.youtube.deleteLater()
                        self.youtube = None
                    self.youtube = YouTube()
                    self.youtube.newVid(self.output[query][2])
                    self.youtube.setFixedSize(854, 480)
                    self.youtube.videoframe.setFixedSize(854, 480)
                    self.container.addWidget(
                        self.youtube, 2, 0, 1, 3, Qt.AlignmentFlag.AlignCenter)
                    self.output = []
            elif cmd == "CLOSE-YOUTUBE-MENU":
                if self.youtubeMenu:
                    self.youtubeMenu.removeVideos()
                    self.youtubeMenu.deleteLater()
                    self.youtubeMenu = None
                    self.youtube = None
                    self.youtube = YouTube()
                    self.youtube.createVid()
                    self.container.addWidget(
                        self.youtube, 2, 0, 1, 3, Qt.AlignmentFlag.AlignCenter)
            elif cmd == "IP":
                s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
                s.connect(("8.8.8.8", 80))
                self.news.heading.setText(s.getsockname()[0])
                s.close()


# Returns a string with the recognized phrase the user speaks
def listen():
    r = sr.Recognizer()
    with sr.Microphone() as source:
        r.adjust_for_ambient_noise(source, duration=1)
        audio = r.listen(source, )
        try:
            recognised_speech = r.recognize_google(audio).lower()
            print("LOG: Received audio: \"" + recognised_speech + "\"")
            return recognised_speech
        except Exception:
            print("LOG: Voice was unclear or undetected")
        return ""


# Calls listen() and adds any appropriate commands to the queue
def getSpeech(q):
    while True:
        print("get query")
        query = listen()
        while not query:
            query = listen()

        # User says "exit"
        if query == "exit":
            print("LOG: exiting mirror")
            q.put("EXIT")
        # User says "what is your address"
        elif query == "what is your address":
            print("LOG: user requested IP address")
            q.put("IP")
        # User says "search for _______ on youtube"
        elif "search for" in query and "on youtube" in query:
            # Search for video
            print("LOG: search on youtube")
            q.put("SEARCH-YOUTUBE")
            query = query.split()
            q.put(
                "%20".join(query[query.index("for") + 1:query.index("on")]))
        # User says "select _____"
        elif "select " in query:
            # select from youtube menu
            print("LOG: select from youtube menu")
            query = query.split()[1]
            numConversions = {
                "one": 1,
                "won": 1,
                "two": 2,
                "too": 2,
                "to": 2,
                "three": 3,
                "four": 4,
                "for": 4,
                "fore": 4,
                "five": 5,
                "six": 6,
                "seven": 7,
                "eight": 8,
                "ate": 8,
                "nine": 9
            }
            try:
                if query in numConversions.keys():
                    q.put("SELECT-FROM-YOUTUBE-MENU")
                    q.put(numConversions[query] - 1)
                elif query.isnumeric():
                    q.put("SELECT-FROM-YOUTUBE-MENU")
                    q.put(int(query) - 1)
                else:
                    raise Exception
            except:
                print("ERROR: Something went wrong with inputting selection")
        # User says "pause youtube"
        elif query == "pause youtube":
            # Pause video
            print("LOG: pause youtube")
            q.put("PAUSE-YOUTUBE")
        # User says "unpause youtube"
        elif query == "unpause youtube":
            # Unpause video
            print("LOG: unpause youtube")
            q.put("UNPAUSE-YOUTUBE")
        # User says "close youtube"
        elif query == "close youtube":
            # Close video
            print("LOG: close youtube")
            q.put("CLOSE-YOUTUBE")
        # User says "close youtube youtube"
        elif query == "close youtube menu":
            q.put("CLOSE-YOUTUBE-MENU")


# Creates and runs the web server
def runServer():
    try:
        server = http.server.HTTPServer((HOST_NAME, PORT_NUMBER), MyHandler)
        print("LOG: started HTTP server on port", str(PORT_NUMBER))

        server.serve_forever()

    except Exception as e:
        print(e)
        print("LOG: shutting down web server")
    finally:
        server.socket.close()


if __name__ == '__main__':
    a = QApplication([])
    window = MainWindow()
    window.showFullScreen()

    QFontDatabase.addApplicationFont("Montserrat-Regular.ttf")
    QFontDatabase.addApplicationFont("Roboto-Light.ttf")

    sys.exit(a.exec())
