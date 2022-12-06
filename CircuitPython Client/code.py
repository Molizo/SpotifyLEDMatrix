import gc
from math import ceil
import time
import board
import displayio
from framebufferio import FramebufferDisplay
from rgbmatrix import RGBMatrix
import network
from adafruit_bitmap_font import bitmap_font
from adafruit_display_text import label
import circuitpython_parse as urlparser
import digitalio

try:
    from secrets import secrets  # type: ignore
except ImportError:
    print("Settings are kept in settings.py, please add them there!")
    raise

upBtn = digitalio.DigitalInOut(board.BUTTON_UP)
upBtn.direction = digitalio.Direction.INPUT
upBtn.pull = digitalio.Pull.UP
downBtn = digitalio.DigitalInOut(board.BUTTON_DOWN)
downBtn.direction = digitalio.Direction.INPUT
downBtn.pull = digitalio.Pull.UP

displayio.release_displays()
matrix = RGBMatrix(
    width=64,
    height=64,
    bit_depth=4,
    rgb_pins=[
        board.MTX_R1,   # type: ignore
        board.MTX_G1,   # type: ignore
        board.MTX_B1,   # type: ignore
        board.MTX_R2,   # type: ignore
        board.MTX_G2,   # type: ignore
        board.MTX_B2,   # type: ignore
    ],
    addr_pins=[
        board.MTX_ADDRA,   # type: ignore
        board.MTX_ADDRB,   # type: ignore
        board.MTX_ADDRC,   # type: ignore
        board.MTX_ADDRD,   # type: ignore
        board.MTX_ADDRE,   # type: ignore
    ],
    clock_pin=board.MTX_CLK,   # type: ignore
    latch_pin=board.MTX_LAT,   # type: ignore
    output_enable_pin=board.MTX_OE,   # type: ignore
)
display = FramebufferDisplay(matrix)

redBits = 6
greenBits = 6
blueBits = 6
brightness = -0.3
contrast = 0.3

rawPalette = []
for red in range(0, 255, ceil(255/redBits)):
    for green in range(0, 255, ceil(255/greenBits)):
        for blue in range(0, 255, ceil(255/blueBits)):
            rawPalette.append(min(255*pow(16,4), int(red*pow(16,4))) + min(255*pow(16,2), int(green*pow(16,2))) + min(255, int(blue)))

palette = displayio.Palette(redBits*greenBits*blueBits)
for i in range(redBits*greenBits*blueBits):
    palette[i] = rawPalette[i]

del rawPalette

gc.collect()

font = bitmap_font.load_font("/resources/TruenoRg-8.bdf")

text_area = label.Label(font, text=" "*60, color=0x0065A9, anchor_point=(0.0,0.0))
text_area.text = "Starting up\n\n\n"

# Set the location
text_area.x = 0
text_area.y = 4

# Show it
display.show(text_area)

gc.collect()

network.initWiFi(text_area)

if ("spotify_refresh_token" not in secrets or secrets["spotify_refresh_token"] == ""):
    text_area.text = "Spotify Account\nGuided Setup\n\nConnect to PC\nand open serial"

    print("[Spotify Setup] Please go to https://accounts.spotify.com/authorize?client_id=%s&response_type=code&redirect_uri=%s&scope=user-read-currently-playing%%20user-read-playback-state" % (secrets["spotify_client_id"], secrets["spotify_redirect_uri"]))
    callbackUrl = input("[Spotify Setup] Enter the URL from your browser's address bar after authorizing: ")
    authorizationCode = urlparser.urlparse(callbackUrl)[4][5:] # Query is the 4th element in the urlparse tuple, and the code starts at the 5th index in the query string
    refreshToken = network.getSpotifyRefreshToken(authorizationCode)
    print("[Spotify Setup] spotify_refresh_token = " + refreshToken)

    while True:
        pass

@micropython.native
def drawArtwork(artwork):
    gc.collect()
    for x in range(0, display.width):
        for y in range(0, display.height):
            try:
                artworkBitmap[x, y] = artwork[x][y]
            except:
                print(x, y, artwork[x][y])
    gc.collect()

artworkBitmap = displayio.Bitmap(display.width, display.height, redBits*greenBits*blueBits)
bitmapTileGrid = displayio.TileGrid(artworkBitmap, pixel_shader=palette)
bitmapDisplayGroup = displayio.Group()
bitmapDisplayGroup.append(bitmapTileGrid)

spotifyAccessToken = ""
oldArtworkURL = ""
print(gc.mem_free())

try:
    while True:
        playbackStatus = network.checkAnyDeviceActive(spotifyAccessToken)
        if(playbackStatus == "ERROR"):
            spotifyAccessToken = network.getSpotifyAccessToken()
            continue
        
        if(playbackStatus == "ACTIVE"):
            gc.collect()
            print(gc.mem_free())
            artworkURL = network.getArtworkURL(spotifyAccessToken)

            if (artworkURL == "ERROR"):
                gc.collect()
                spotifyAccessToken = network.getSpotifyAccessToken()
                continue
            if (artworkURL == "MAXATTEMPTS"):
                gc.collect()
                continue

            if (oldArtworkURL != artworkURL):
                artwork = network.getArtwork(display.height, display.width, redBits, greenBits, blueBits, brightness, contrast, artworkURL)

                oldArtworkURL = artworkURL
                del artworkURL
                gc.collect()
                print(gc.mem_free())

                if (artwork == "MAXATTEMPTS"):
                    oldArtworkURL = ""
                    gc.collect()
                    continue

                print("Drawing...")
                drawArtwork(artwork)

                del artwork
                gc.collect()
                print(gc.mem_free())
                display.show(bitmapDisplayGroup)
            
            
        if(playbackStatus == "IDLE"):
            display.show(text_area)
            text_area.text = "No active device"
            time.sleep(20)

except Exception as e:
    from supervisor import reload
    print("Unrecoverable error: ", e)
    print("Reloading...")
    reload()