from adafruit_bitmap_font import bitmap_font
from adafruit_display_text import label
import circuitpython_parse as urlparser
import network

try:
    from secrets import secrets  # type: ignore
except ImportError:
    print("Settings are kept in settings.py, please add them there!")
    raise

def startSpotifySetup(display):
    font = bitmap_font.load_font("/resources/TruenoRg-8.bdf")

    text_area = label.Label(font, text=" "*60, color=0x0065A9, anchor_point=(0.0,0.0))

    # Set the location
    text_area.x = 0
    text_area.y = 4

    # Show it
    display.show(text_area)

    text_area.text = "Spotify Account\nGuided Setup\n\nConnect to PC\nand open serial"

    print("[Spotify Setup] Please go to https://accounts.spotify.com/authorize?client_id=%s&response_type=code&redirect_uri=%s&scope=user-read-currently-playing%%20user-read-playback-state" % (secrets["spotify_client_id"], secrets["spotify_redirect_uri"]))
    callbackUrl = input("[Spotify Setup] Enter the URL from your browser's address bar after authorizing: ")
    authorizationCode = urlparser.urlparse(callbackUrl)[4][5:] # Query is the 4th element in the urlparse tuple, and the code starts at the 5th index in the query string
    refreshToken = network.getSpotifyRefreshToken(authorizationCode)
    print("[Spotify Setup] spotify_refresh_token = " + refreshToken)

    while True:
        pass