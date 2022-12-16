import gc
import board
import busio
from digitalio import DigitalInOut
import adafruit_requests as requests
import adafruit_esp32spi.adafruit_esp32spi_socket as socket
from adafruit_esp32spi import adafruit_esp32spi
import circuitpython_base64 as base64

try:
    from secrets import secrets
except ImportError:
    print("Settings are kept in secrets.py, please add them there!")
    raise

esp = None

@micropython.native
def initWiFi():
    global esp

    esp32_cs = DigitalInOut(board.ESP_CS)
    esp32_ready = DigitalInOut(board.ESP_BUSY)
    esp32_reset = DigitalInOut(board.ESP_RESET)

    spi = busio.SPI(board.SCK, board.MOSI, board.MISO)
    esp = adafruit_esp32spi.ESP_SPIcontrol(spi, esp32_cs, esp32_ready, esp32_reset)

    requests.set_socket(socket, esp)

    if esp.status == adafruit_esp32spi.WL_IDLE_STATUS:
        print("ESP32 found and in idle mode")
    print("Connecting to AP...")
    while not esp.is_connected:
        try:
            esp.connect_AP(secrets["ssid"], secrets["password"])
        except OSError as e:
            print("Could not connect to AP, retrying: ", e)
            continue
    print("Connected to", str(esp.ssid, "utf-8"), "\tRSSI:", esp.rssi)
    print("My IP address is", esp.pretty_ip(esp.ip_address))

    gc.collect()
    return esp

@micropython.native
def getCurrentTime():
    try:
        gc.collect()
        print("Getting current time...")
        time = int(requests.get("https://currentmillis.com/time/minutes-since-unix-epoch.php").text) % 1440 # Minutes in day
        print("Got time: %i" % time)
        return time 
    except Exception as e:
        if(attempts > 3):
            print("Too many attempts")
            return "MAXATTEMPTS"
        print(gc.mem_free())
        gc.collect()
        print("Retrying %i/3: " % attempts, e)
        return getCurrentTime()

@micropython.native
def getArtwork(h, w, r, g, b, bright, contr, artworkURL, attempts = 0):
    try:
        gc.collect()
        print("Getting artwork...")
        artwork = requests.get("http://fishy-confirmed-saturday.glitch.me/?h=%i&w=%i&r=%i&g=%i&b=%i&bright=%.2f&contr=%.2f&imgurl=%s" %(h,w,r,g,b,bright,contr,artworkURL)).json()
        gc.collect()
        return artwork
    except Exception as e:
        if(attempts > 3):
            print("Too many attempts")
            return "MAXATTEMPTS"
        print(gc.mem_free())
        gc.collect()
        print("Retrying %i/3: " % attempts, e)
        return getArtwork(h, w, r, g, b, bright, contr, artworkURL, attempts+1)
    
@micropython.native
def getArtworkURL(spotifyAccessToken, attempts = 0):
    try:
        gc.collect()
        print("Getting artwork URL...")
        trackRequest = requests.get("https://api.spotify.com/v1/me/player/currently-playing", headers = {"Authorization": "Bearer " + spotifyAccessToken}).json()
        if ("error" in trackRequest):
            print("Error: " + trackRequest["error"]["message"])
            return "ERROR"
        allAlbumArtwork = trackRequest["item"]["album"]["images"]
        artworkURL = allAlbumArtwork[len(allAlbumArtwork)-1]["url"]
        print("Got artwork URL: " + artworkURL)
        gc.collect()
        return artworkURL
    except Exception as e:
        if(str(e) == "syntax error in JSON"):
            return "ERROR"
        if(attempts > 3):
            print("Too many attempts")
            return "MAXATTEMPTS"
        print(gc.mem_free())
        gc.collect()
        print("Retrying %i/3: " % attempts, e)
        return getArtworkURL(spotifyAccessToken, attempts+1)

@micropython.native
def checkAnyDeviceActive(spotifyAccessToken):
    print("Checking if any device is active...")
    deviceRequest = requests.get("https://api.spotify.com/v1/me/player/devices", headers = {"Authorization": "Bearer " + spotifyAccessToken}).json()
    if ("error" in deviceRequest):
        print("Error: " + deviceRequest["error"]["message"])
        gc.collect()
        return -1 # Error
    for device in deviceRequest["devices"]:
        if device["is_active"]:
            print("Device " + device["name"] + " is active")
            gc.collect()
            return 1 # Active
    #gc.collect()
    return 0 # Idle

@micropython.native
def getSpotifyAccessToken():
    tokenRequest = requests.post("https://accounts.spotify.com/api/token",
        data = "grant_type=refresh_token&refresh_token=" + secrets["spotify_refresh_token"],
        headers = {
            "Authorization": "Basic " + str(base64.encodebytes(bytes(secrets["spotify_client_id"] + ":" + secrets["spotify_client_secret"], "ascii"))).replace("\\n","")[2:-1],
            "Content-Type": "application/x-www-form-urlencoded"
        }
    ).json()
    gc.collect()
    return tokenRequest["access_token"]

@micropython.native
def getSpotifyRefreshToken(authorizationCode):
    tokenRequest = requests.post("https://accounts.spotify.com/api/token",
        data = "grant_type=authorization_code&code=" + authorizationCode + "&redirect_uri=" + secrets["spotify_redirect_uri"],
        headers = {
            "Authorization": "Basic " + str(base64.encodebytes(bytes(secrets["spotify_client_id"] + ":" + secrets["spotify_client_secret"], "ascii"))).replace("\\n","")[2:-1],
            "Content-Type": "application/x-www-form-urlencoded"
        }
    ).json()
    gc.collect()
    return tokenRequest["refresh_token"]