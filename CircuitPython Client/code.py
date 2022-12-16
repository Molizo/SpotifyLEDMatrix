import gc
from math import ceil
import time
import board
import displayio
from framebufferio import FramebufferDisplay
from rgbmatrix import RGBMatrix
import network
import random

try:
    from secrets import secrets  # type: ignore
except ImportError:
    print("Settings are kept in settings.py, please add them there!")
    raise

displayio.release_displays()
matrix = RGBMatrix(
    width=64,
    height=64,
    bit_depth=5,
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

startNightTime = 1200 # In minutes, also factoring in timezones (use UTC time)
endNightTime = 360 # In minutes, also factoring in timezones (use UTC time)
dayBrightness = 0.0 # Use -0.3 w/o diffuser, 0.0 with diffuser
nightBrightness = -0.7 # Number between -1.0 and +1.0 (negative numbers lower brightness, positive numbers increase brightness)

redBits = 8
greenBits = 8
blueBits = 8
brightness = nightBrightness
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

network.initWiFi()

if ("spotify_refresh_token" not in secrets or secrets["spotify_refresh_token"] == ""):
    import setupWizard
    setupWizard.startSpotifySetup(display)

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

GOLPalette = None

GOL1Bitmap = None
GOL1TileGrid = None
GOL1Group = None

GOL2Bitmap = None
GOL2TileGrid = None
GOL2Group = None

@micropython.native
def initGameOfLife():
    print("Initing Game of Life")
    print(gc.mem_free())

    global GOlPalette, GOL1Bitmap, GOL1TileGrid, GOL1Group, GOL2Bitmap, GOL2TileGrid, GOL2Group

    GOLPalette = displayio.Palette(2)
    GOLPalette[0] = 0x000000
    GOLPalette[1] = (
        (0x0000ff if random.random() > .33 else 0) |
        (0x00ff00 if random.random() > .33 else 0) |
        (0xff0000 if random.random() > .33 else 0)) or 0xffffff

    GOL1Bitmap = displayio.Bitmap(display.width, display.height, 2)
    GOL1TileGrid = displayio.TileGrid(GOL1Bitmap, pixel_shader=GOLPalette)
    GOL1Group = displayio.Group()
    GOL1Group.append(GOL1TileGrid)

    GOL2Bitmap = displayio.Bitmap(display.width, display.height, 2)
    GOL2TileGrid = displayio.TileGrid(GOL2Bitmap, pixel_shader=GOLPalette)
    GOL2Group = displayio.Group()
    GOL2Group.append(GOL2TileGrid)

    for x in range(0, GOL1Bitmap.width):
        for y in range(0, GOL1Bitmap.height):
            GOL1Bitmap[x, y] = 1 if random.randint(0, 6) == 0 else 0
    
    gc.collect()
    print(gc.mem_free())

@micropython.native
def unInitGameOfLife():
    print("Uniniting Game of Life")
    print(gc.mem_free())
    
    global GOlPalette, GOL1Bitmap, GOL1TileGrid, GOL1Group, GOL2Bitmap, GOL2TileGrid, GOL2Group

    GOLPalette = None

    GOL1Bitmap = None
    GOL1TileGrid = None
    GOL1Group = None

    GOL2Bitmap = None
    GOL2TileGrid = None
    GOL2Group = None
    
    gc.collect()
    print(gc.mem_free())

@micropython.native
def runGameOfLife(old, new):
    print("Running Game of Life")
    print(gc.mem_free())
    width = old.width
    height = old.height
    for y in range(height):
        yyy = y * width
        ym1 = ((y + height - 1) % height) * width
        yp1 = ((y + 1) % height) * width
        xm1 = width - 1
        for x in range(width):
            xp1 = (x + 1) % width
            neighbors = (
                old[xm1 + ym1] + old[xm1 + yyy] + old[xm1 + yp1] +
                old[x   + ym1] +                  old[x   + yp1] +
                old[xp1 + ym1] + old[xp1 + yyy] + old[xp1 + yp1])
            new[x+yyy] = neighbors == 3 or (neighbors == 2 and old[x+yyy])
            xm1 = x
    gc.collect()
    print(gc.mem_free())

spotifyAccessToken = ""
oldArtworkURL = ""
print(gc.mem_free())

try:
    while True:

        playbackStatus = network.checkAnyDeviceActive(spotifyAccessToken)

        if(playbackStatus == -1): # Error
            spotifyAccessToken = network.getSpotifyAccessToken()
            continue
        
        if(playbackStatus == 1): # Active
            if(GOL1Bitmap is not None): # Uninitialize the game of life if we are about to display artwork
                unInitGameOfLife()

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
                gc.collect()
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

                currentTime = network.getCurrentTime()
                if (currentTime > startNightTime or currentTime < endNightTime):
                    print("Using night brightness")
                    brightness = nightBrightness
                else:
                    print("Using day brightness")
                    brightness = dayBrightness
                gc.collect()
            
            
        if(playbackStatus == 0): # Idle
            if (GOL1Bitmap is None):
                oldArtworkURL = ""
                initGameOfLife()
            for _ in range (0, 5):
                display.show(GOL1Group)
                runGameOfLife(GOL1Bitmap, GOL2Bitmap)
                time.sleep(1)
                display.show(GOL2Group)
                runGameOfLife(GOL2Bitmap, GOL1Bitmap)
                time.sleep(1)
            
            #display.show(text_area)
            #text_area.text = "No active device"
            #time.sleep(20)

except Exception as e:
    from supervisor import reload
    print("Unrecoverable error: ", e)
    print("Reloading...")
    reload()