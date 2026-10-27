import os
import sys
import time
import json
import math

APP_DIR = "/system/apps/universe_schedule"
os.chdir(APP_DIR)
sys.path.insert(0, APP_DIR)

from badgeware import State
import missing_details
import fortmason
try:
    # Optional private office map for indoor testing; never published.
    import sfoffice
except ImportError:
    sfoffice = None
fm = fortmason

badge.mode(HIRES | VSYNC)
screen.antialias = image.X2
screen.fill_rule = image.EVEN_ODD

W, H = screen.width, screen.height
FONT = font.load("/system/assets/fonts/MonaSans-Medium.af")
screen.font = FONT
MONA = image.load("assets/mona_walk.png").spritesheet(7, 1)

# GitHub Universe 2026 palette
BLACK = color.rgb(0, 0, 0)
WHITE = color.rgb(255, 255, 255)
OFFWHITE = color.rgb(242, 245, 243)
GREEN = color.rgb(95, 237, 131)
DKGREEN = color.rgb(8, 135, 43)
LIME = color.rgb(220, 255, 150)
PURPLE = color.rgb(88, 58, 247)
LTPURPLE = color.rgb(174, 133, 255)
GOLD = color.rgb(187, 160, 10)
ORANGE = color.rgb(192, 82, 0)
YELLOW = color.rgb(250, 191, 33)
MUTED = color.rgb(165, 173, 167)
DIM = color.rgb(105, 114, 108)
CARD = color.rgb(13, 17, 14)
CARD_HI = color.rgb(22, 30, 24)
BORDER = color.rgb(50, 56, 52)
SUBTLE = color.rgb(35, 41, 37)
WATER = color.rgb(8, 34, 44)
WAVE = color.rgb(20, 62, 76)
LAND = color.rgb(14, 18, 15)
ROAD = color.rgb(38, 46, 40)
BLDG = color.rgb(30, 37, 32)
BLDG_EDGE = color.rgb(72, 82, 75)

TYPE_COLOR = {
    "Keynote": GREEN, "Main Stage": GREEN,
    "Breakout Session": LIME, "Panel Discussion": LIME,
    "Product Demo": LTPURPLE, "Workshop": YELLOW,
    "Sandbox Session": YELLOW, "Ship & Tell": GOLD,
    "Social": ORANGE, "Session After Party": ORANGE,
    "Special Event": OFFWHITE,
}
TYPE_SHORT = {
    "Breakout Session": "BREAKOUT", "Panel Discussion": "PANEL",
    "Product Demo": "DEMO", "Sandbox Session": "SANDBOX",
    "Session After Party": "AFTER PARTY", "Special Event": "SPECIAL EVENT",
    "Ship & Tell": "SHIP & TELL", "Main Stage": "MAIN STAGE",
}
DAYS = ("MON", "TUE", "WED", "THU", "FRI", "SAT", "SUN")
DAY_NAMES = ("Monday", "Tuesday", "Wednesday", "Thursday", "Friday",
             "Saturday", "Sunday")

STATE_KEY = "universe_schedule"
UTC_OFFSET_H = -7  # Pacific Daylight Time during Universe 2026
BASE = time.mktime((2026, 10, 26, 0, 0, 0, 0, 0))

# Session rows: key, start, end, title, type, track, room, where, speakers, popular
K, S, E, TITLE, TYPE, TRACK, ROOM, WHERE, SPEAKERS, POP = range(10)
with open("assets/sessions.json") as f:
    UNIVERSE = json.load(f)["sessions"]
SESSIONS = UNIVERSE

state = {"stars": [], "offset": 0, "mode": "all", "test": False}
State.load(STATE_KEY, state)
if state.get("demo"):
    # Older versions had a demo clock; go back to the real one.
    state["offset"] = state.get("real_offset", 0)
# Older versions listened for Wi-Fi and Bluetooth to follow you around.
for _old in ("demo", "real_offset", "real_guess", "gk", "here", "here_alt",
             "fp", "fpv", "bk", "bkr"):
    state.pop(_old, None)
if not isinstance(state.get("stars"), list):
    state["stars"] = []
if not isinstance(state.get("offset"), int):
    state["offset"] = 0
if state.get("mode") not in ("all", "mine"):
    state["mode"] = "all"
state["test"] = state.get("test") is True
state.pop("t0", None)
try:
    os.remove("/state/universe_follow_log.txt")
except OSError:
    pass
stars = set(state["stars"])
KEY_INDEX = {}


def save():
    state["stars"] = sorted(stars)
    State.save(STATE_KEY, state)


# ---------------------------------------------------------------- clock
# The clock sets itself over Wi-Fi when the app opens. With no clock at
# all, the app shows a preview that starts on Wednesday morning.

offset = state["offset"]
preview = False


def clock_valid(extra=0):
    return time.localtime(time.time() + extra)[0] >= 2026


if not clock_valid(offset):
    offset = 0
    if not clock_valid():
        offset = int(time.mktime((2026, 10, 28, 8, 30, 0, 0, 0)) - time.time() + 1)
        preview = True

# "Test day" (hold MENU) pretends it's Wednesday morning, so you can try
# the app anywhere. It starts at 10:20 AM each time the app opens.
TEST_DAY = (2026, 10, 28, 10, 20, 0, 0, 0)


def test_offset():
    return int(time.mktime(TEST_DAY) - time.time() + 1)


def office_test():
    """Office test: a private floor map with practice sessions on the
    real clock. Without that file, Test day pretends it's Wednesday."""
    return state["test"] and sfoffice is not None


def load_venue():
    global fm, SESSIONS, KEY_INDEX, BLOCKS
    if office_test():
        m = now_min()
        fm = sfoffice
        SESSIONS = sfoffice.sessions(m - m % 1440)
    else:
        fm = fortmason
        SESSIONS = UNIVERSE
    KEY_INDEX = dict((r[K], i) for i, r in enumerate(SESSIONS))
    BLOCKS = sorted(set(r[S] // 30 for r in SESSIONS))


if state["test"] and sfoffice is None:
    offset, preview = test_offset(), False


def toast(msg):
    sync["state"], sync["since"], sync["msg"] = "done", badge.ticks, msg


def toggle_test():
    global offset, preview, detail
    detail = None
    state["test"] = not state["test"]
    if sfoffice is not None:
        if state["test"]:
            load_venue()
            stars.update(sfoffice.STARRED)
            toast("Office test: " + sfoffice.FLOOR)
        else:
            for key in [k for k in stars if k not in UNIVERSE_KEYS]:
                stars.discard(key)
            load_venue()
            toast("Back to Universe")
    elif state["test"]:
        offset, preview = test_offset(), False
        toast("Test day: Wed Oct 28, 10:20 AM")
    else:
        offset, preview = state["offset"], False
        if not clock_valid(offset):
            offset = 0
            if not clock_valid():
                offset, preview = int(time.mktime((2026, 10, 28, 8, 30, 0, 0, 0)) - time.time() + 1), True
        start_sync()
    hushed.clear()
    save()
    rebuild(False)


def now_min():
    return int((time.time() + offset - BASE) // 60)


UNIVERSE_KEYS = set(r[K] for r in UNIVERSE)
load_venue()

def set_now(y, mo, d, h, mi):
    """Move the app clock (used by the simulator tests)."""
    global offset, preview
    offset = int(time.mktime((y, mo, d, h, mi, 0, 0, 0)) - time.time() + 1)
    preview = False
    state["offset"] = offset
    save()
    rebuild()


def hm(m):
    h, mi = (m // 60) % 24, m % 60
    suffix = "AM" if h < 12 else "PM"
    h = h % 12 or 12
    return "%d:%02d %s" % (h, mi, suffix)


def hm_short(m):
    h, mi = (m // 60) % 24, m % 60
    return "%d:%02d" % (h % 12 or 12, mi)


def day_label(m):
    return "%s OCT %d" % (DAYS[(m // 1440) % 7], 26 + m // 1440)


def time_range(r):
    a, b = r[S], r[E]
    if (a // 60 % 24 < 12) == (b // 60 % 24 < 12):
        return hm_short(a) + "-" + hm(b)
    return hm(a) + "-" + hm(b)


# ------------------------------------------------------------ Wi-Fi time

SSID_MISSING = missing_details.missing("WIFI_SSID")
sync = {"state": "", "since": 0, "msg": ""}


def sync_fail():
    # Only speak up when the clock really is unknown.
    sync["state"], sync["since"] = "done", badge.ticks
    sync["msg"] = "No Wi-Fi: showing a preview" if preview else ""


def start_sync():
    if SSID_MISSING:
        sync_fail()
        return
    sync["state"], sync["msg"], sync["since"] = "connecting", "Setting the clock...", badge.ticks


def step_sync():
    global offset, preview
    st = sync["state"]
    if st == "connecting":
        try:
            import wifi
            if wifi.connect(timeout=15, retries=1):
                sync["state"] = "ntp"
            elif badge.ticks - sync["since"] > 20000:
                sync_fail()
        except Exception:
            sync_fail()
    elif st == "ntp":
        try:
            import ntptime
            utc = ntptime.time()
            real = int(utc + UTC_OFFSET_H * 3600 - time.time())
            state["offset"] = real
            save()
            sync["msg"] = ""
            if not state["test"] or sfoffice is not None:
                offset, preview = real, False
                if office_test():
                    load_venue()
                rebuild()
                sync["msg"] = "Clock set: " + day_label(now_min()) + " " + hm(now_min())
            sync["state"], sync["since"] = "done", badge.ticks
        except Exception:
            sync_fail()
    elif st == "done" and badge.ticks - sync["since"] > 3000:
        sync["state"] = ""


# -------------------------------------------- time-to-go case lights
# Ten minutes before a starred session, the four case lights breathe and
# a banner says where to go. Any button press quiets the lights.

ALERT_MIN = 10
hushed = set()
_glow = [-1.0]


def next_alert():
    m = now_min()
    best = None
    for key in stars:
        i = KEY_INDEX.get(key)
        if i is None:
            continue
        r = SESSIONS[i]
        if 0 < r[S] - m <= getattr(fm, "ALERT_MIN", ALERT_MIN) and (best is None or r[S] < SESSIONS[best][S]):
            best = i
    return best


def lights(level):
    if abs(level - _glow[0]) < 0.02:
        return
    _glow[0] = level
    try:
        badge.caselights(level)
    except Exception:
        pass


def step_alert(i):
    level = 0.0
    if i is not None:
        key = SESSIONS[i][K]
        if badge.pressed():
            hushed.add(key)
        if key not in hushed:
            level = 0.1 + 0.9 * abs(math.sin(badge.ticks / 450.0))
    lights(level)


def on_exit():
    lights(0.0)


# ------------------------------------------------------------ text tools

_cache = {}


def _remember(key, value):
    if len(_cache) > 220:
        _cache.clear()
    _cache[key] = value
    return value


def text_w(text, size):
    return screen.measure_text(text, font_size=size)[0]


def fit(text, size, width):
    key = ("f", text, size, width)
    if key in _cache:
        return _cache[key]
    if text_w(text, size) <= width:
        return _remember(key, text)
    cut = len(text)
    while cut > 1 and text_w(text[:cut].rstrip() + "...", size) > width:
        cut -= 1
    return _remember(key, text[:cut].rstrip() + "...")


def wrap(text, size, width, lines=99):
    key = ("w", text, size, width, lines)
    if key in _cache:
        return _cache[key]
    out, line = [], ""
    for word in text.split(" "):
        trial = (line + " " + word) if line else word
        if text_w(trial, size) <= width:
            line = trial
            continue
        if line:
            out.append(line)
        line = word
    if line:
        out.append(line)
    if len(out) > lines:
        rest = " ".join(out[lines - 1:])
        out = out[:lines - 1] + [fit(rest, size, width)]
    return _remember(key, out)


def put(text, x, y, size, pen):
    screen.pen = pen
    screen.text(text, x, y, size)


def put_right(text, x, y, size, pen):
    put(text, x - text_w(text, size), y, size, pen)


def put_center(text, x, y, size, pen):
    put(text, x - text_w(text, size) // 2, y, size, pen)


def fill(pen, sh):
    screen.pen = pen
    screen.shape(sh)


def poly(pen, *pts):
    fill(pen, shape.custom([vec2(x, y) for x, y in pts]))


def star_icon(x, y, r, on):
    s = shape.star(x, y, 5, r * 0.45, r)
    fill(YELLOW if on else DIM, s if on else s.stroke(1.2))


def chip(text, x, y, pen, size=9):
    w = text_w(text, size) + 8
    fill(pen, shape.rounded_rectangle(x, y, w, size + 5, 3))
    put(text, x + 4, y + 2, size, BLACK)
    return w


def card(x, y, w, h, hi=False):
    fill(BORDER, shape.rectangle(x + 2, y + 2, w, h))
    fill(CARD_HI if hi else CARD, shape.rectangle(x, y, w, h))
    fill(GREEN if hi else BORDER, shape.rectangle(x, y, w, h).stroke(1))


# --------------------------------------------------------------- chrome

def screen_like_image():
    pixel_bytes = len(screen.raw) // (W * H)
    if pixel_bytes == 2:
        return image(W, H, bytearray(W * H * 2), image.RGB565)
    return image(W, H)


def build_background():
    try:
        bg = screen_like_image()
    except Exception:
        return None
    bg.antialias = image.OFF
    bg.pen = BLACK
    bg.rectangle(0, 0, W, H)
    bg.pen = color.rgb(28, 34, 30)
    for y in range(32, H - 14, 12):
        for x in range(6, W, 12):
            bg.rectangle(x, y, 1, 1)
    return bg


BACKGROUND = build_background()


def draw_background():
    if BACKGROUND is not None:
        screen.blit(BACKGROUND, vec2(0, 0))
    else:
        screen.pen = BLACK
        screen.clear()


def header(subtitle=None):
    fill(BLACK, shape.rectangle(0, 0, W, 24))
    put("UNIVERSE", 8, 4, 15, WHITE)
    x = 8 + text_w("UNIVERSE", 15) + 3
    put("26", x, 4, 15, GREEN)
    if subtitle:
        put(subtitle, x + text_w("26", 15) + 8, 7, 10, MUTED)
    # brand stripe
    stripe = ((DKGREEN, 120), (GREEN, 70), (LIME, 50), (PURPLE, 50), (YELLOW, 30))
    x = 0
    for pen, w in stripe:
        fill(pen, shape.rectangle(x, 22, w, 2))
        x += w
    m = now_min()
    clock = hm(m)
    put_right(clock, W - 8, 4, 13, GREEN)
    day = DAYS[(m // 1440) % 7] if 0 <= m < 7 * 1440 else ""
    put_right(day, W - 12 - text_w(clock, 13), 7, 10, MUTED)
    tag = ("OFFICE TEST" if office_test() else "TEST DAY") if state["test"] else "PREVIEW" if preview else None
    if tag:
        dw = text_w(tag, 8) + 8
        chip(tag, W - 20 - text_w(clock, 13) - text_w(day, 10) - dw, 6, YELLOW, 8)


def draw_alert(i):
    """Banner for a starred session that starts within ten minutes."""
    r = SESSIONS[i]
    mins = r[S] - now_min()
    place = fm.building_for(r[ROOM], r[WHERE])
    where = fm.LABEL[place] if place else (r[WHERE] or r[ROOM])
    y = H - 37
    glow = abs(math.sin(badge.ticks / 450.0))
    fill(YELLOW, shape.rounded_rectangle(4, y, W - 8, 20, 5))
    fill(WHITE if glow > 0.6 else ORANGE, shape.rounded_rectangle(4, y, W - 8, 20, 5).stroke(1.5))
    lead = "GO NOW  %d min  " % mins
    put(lead, 12, y + 4, 11, BLACK)
    x = 12 + text_w(lead, 11)
    hint = "SELECT: map"
    put_right(hint, W - 12, y + 5, 9, DKGREEN)
    put(fit(where + "  -  " + r[TITLE], 11, W - x - text_w(hint, 9) - 22), x, y + 4, 11, BLACK)


def footer(*hints):
    fill(BLACK, shape.rectangle(0, H - 15, W, 15))
    fill(SUBTLE, shape.rectangle(0, H - 15, W, 1))
    x = 8
    for key, label in hints:
        put(key, x, H - 12, 9, GREEN)
        x += text_w(key, 9) + 3
        put(label, x, H - 12, 9, MUTED)
        x += text_w(label, 9) + 10


def arrow_left(x, y, pen):
    poly(pen, (x, y), (x + 6, y - 5), (x + 6, y + 5))


def arrow_right(x, y, pen):
    poly(pen, (x, y), (x - 6, y - 5), (x - 6, y + 5))


# -------------------------------------------------------------- lists

view = "home"          # home | list | detail | map
home_sel = 0
map_back = "home"      # where BACK goes from the map
page = 0
pages = []             # list of (title, rows); rows: ("h", text) or ("s", index)
home_page = 0
sel = 0
scroll = 0
detail = None          # session index


def is_starred(i):
    return SESSIONS[i][K] in stars


def build_all():
    global home_page
    m = now_min()
    out = []
    home_at = None
    for b in BLOCKS:
        if home_at is None and b * 30 > m:
            home_at = len(out)
        rows = [("s", i) for i, r in enumerate(SESSIONS) if r[S] // 30 == b]
        out.append((day_label(b * 30) + "  " + hm(b * 30), rows))

    now_rows = [i for i, r in enumerate(SESSIONS) if r[S] <= m < r[E]]
    upcoming = [r[S] for r in SESSIONS if r[S] > m]
    rows = []
    if now_rows:
        rows.append(("h", "HAPPENING NOW"))
        rows += [("s", i) for i in now_rows]
    if upcoming:
        b = min(upcoming) // 30
        when = hm(min(upcoming))
        if min(upcoming) // 1440 != m // 1440:
            when = day_label(min(upcoming)) + " " + when
        rows.append(("h", "UP NEXT  " + when))
        rows += [("s", i) for i, r in enumerate(SESSIONS) if r[S] > m and r[S] // 30 == b]
    if not rows:
        rows.append(("h", "THAT'S A WRAP"))
    if home_at is None:
        home_at = len(out)
    out.insert(home_at, ("NOW & NEXT", rows))
    home_page = home_at
    return out


def build_mine():
    global home_page
    m = now_min()
    mine = [i for i, r in enumerate(SESSIONS) if r[K] in stars]
    rows = []
    day = -1
    first = None
    for i in mine:
        d = SESSIONS[i][S] // 1440
        if d != day:
            rows.append(("h", day_label(SESSIONS[i][S])))
            day = d
        if first is None and SESSIONS[i][E] > m:
            first = len(rows)
        rows.append(("s", i))
    home_page = 0
    return [("MY SESSIONS", rows)], first


def rebuild(keep=True):
    global pages, page, sel, scroll
    old = current_session() if keep and pages else None
    if state["mode"] == "mine":
        pages, first = build_mine()
        page = 0
        rows = pages[0][1]
        sel = first if first is not None else 0
    else:
        was_home = page == home_page
        pages = build_all()
        if was_home or not keep or page >= len(pages):
            page = home_page
        sel = 0
    rows = pages[page][1]
    if old is not None:
        for n, row in enumerate(rows):
            if row[0] == "s" and row[1] == old:
                sel = n
                break
    sel = fix_sel(rows, sel, 1)
    scroll = 0


def fix_sel(rows, n, direction):
    if not rows:
        return 0
    n = max(0, min(len(rows) - 1, n))
    while 0 <= n < len(rows) and rows[n][0] != "s":
        n += direction
    if not 0 <= n < len(rows):
        n = max(0, min(len(rows) - 1, n))
        while 0 <= n < len(rows) and rows[n][0] != "s":
            n -= direction
    return max(0, min(len(rows) - 1, n))


def current_session():
    if not pages:
        return None
    rows = pages[page][1]
    if 0 <= sel < len(rows) and rows[sel][0] == "s":
        return rows[sel][1]
    return None


ROW_H = 40
HEAD_H = 18
LIST_TOP = 48
LIST_BOTTOM = H - 18


def row_height(row):
    return HEAD_H if row[0] == "h" else ROW_H


def draw_list():
    global scroll
    draw_background()
    header("MY SESSIONS" if state["mode"] == "mine" else None)
    title, rows = pages[page]

    # page title bar
    if state["mode"] == "all":
        pen = GREEN if page == home_page else OFFWHITE
        put_center(title, W // 2, 30, 12, pen)
        if page > 0:
            arrow_left(10, 37, GREEN)
        if page < len(pages) - 1:
            arrow_right(W - 10, 37, GREEN)
    else:
        n = len([r for r in rows if r[0] == "s"])
        put_center("%d starred" % n if n else "No stars yet", W // 2, 30, 12, GREEN)

    if not [r for r in rows if r[0] == "s"]:
        if state["mode"] == "mine":
            lines = ("Open any session in the Full catalog", "and press SELECT to star it.",
                     "Your picks show up here.")
        else:
            lines = ("Nothing on the schedule here.",)
        y = 96
        for line in lines:
            put_center(line, W // 2, y, 12, MUTED)
            y += 18
        star_icon(W // 2, 78, 10, False)
        return

    # keep the selection visible
    ys, y = [], 0
    for row in rows:
        ys.append(y)
        y += row_height(row) + 3
    view_h = LIST_BOTTOM - LIST_TOP
    top = ys[sel]
    if sel > 0 and rows[sel - 1][0] == "h":
        top = ys[sel - 1]
    if top < scroll:
        scroll = top
    if ys[sel] + ROW_H > scroll + view_h:
        scroll = ys[sel] + ROW_H - view_h
    m = now_min()

    screen.clip = rect(0, LIST_TOP, W, view_h + 2)
    for n, row in enumerate(rows):
        y = LIST_TOP + ys[n] - scroll
        if y > LIST_BOTTOM or y + row_height(row) < LIST_TOP:
            continue
        if row[0] == "h":
            put(row[1], 12, y + 4, 10, LIME)
            fill(SUBTLE, shape.rectangle(12 + text_w(row[1], 10) + 6, y + 9, W - 30 - text_w(row[1], 10), 1))
            continue
        draw_row(SESSIONS[row[1]], 8, y, W - 18, n == sel, m)
    screen.clip = rect(0, 0, W, H)

    # scrollbar
    total = ys[-1] + row_height(rows[-1])
    if total > view_h:
        bar = max(14, view_h * view_h // total)
        pos = LIST_TOP + (view_h - bar) * scroll // max(1, total - view_h)
        fill(SUBTLE, shape.rectangle(W - 5, LIST_TOP, 2, view_h))
        fill(GREEN, shape.rectangle(W - 5, pos, 2, bar))


def draw_row(r, x, y, w, hi, m):
    card(x, y, w, ROW_H, hi)
    fill(TYPE_COLOR.get(r[TYPE], MUTED), shape.rectangle(x + 1, y + 1, 3, ROW_H - 2))
    starred = r[K] in stars
    right = x + w - 8
    if starred:
        star_icon(right - 5, y + 11, 6, True)
        right -= 15
    if r[POP]:
        tag = "POPULAR"
        tw = text_w(tag, 8) + 6
        fill(ORANGE, shape.rounded_rectangle(right - tw, y + 5, tw, 12, 2))
        put(tag, right - tw + 3, y + 7, 8, BLACK)
        right -= tw + 4
    if r[S] <= m < r[E]:
        put_right("NOW", right, y + 6, 9, GREEN)
        right -= text_w("NOW", 9) + 6
    meta = time_range(r) + "   " + r[ROOM]
    put(fit(meta, 10, right - x - 12), x + 10, y + 6, 10, MUTED)
    put(fit(r[TITLE], 13, w - 18), x + 10, y + 20, 13, WHITE if hi else OFFWHITE)


# ---------------------------------------------------------------- detail

def draw_detail():
    r = SESSIONS[detail]
    m = now_min()
    draw_background()
    header()
    x0 = 12
    w = chip(TYPE_SHORT.get(r[TYPE], r[TYPE].upper()), x0, 32, TYPE_COLOR.get(r[TYPE], MUTED))
    if r[TRACK]:
        put(fit(r[TRACK], 10, W - x0 - w - 50), x0 + w + 6, 34, 10, MUTED)
    star_icon(W - 22, 40, 11, r[K] in stars)

    y = 52
    for line in wrap(r[TITLE], 18, W - 40, 3):
        put(line, x0, y, 18, WHITE)
        y += 21
    y += 4

    put(day_label(r[S]) + "   " + hm(r[S]) + " - " + hm(r[E]), x0, y, 12, GREEN)
    y += 17
    if m < r[S]:
        mins = r[S] - m
        if mins < 60:
            status, pen = "Starts in %d min" % mins, LIME
        elif r[S] // 1440 == m // 1440:
            status, pen = "Starts in %dh %02dm" % (mins // 60, mins % 60), MUTED
        else:
            days = r[S] // 1440 - m // 1440
            status = "Tomorrow" if days == 1 else "In %d days" % days
            status, pen = status + ", " + DAY_NAMES[(r[S] // 1440) % 7], MUTED
    elif m < r[E]:
        status, pen = "On now  -  %d min left" % (r[E] - m), GREEN
    else:
        status, pen = "Ended", DIM
    put(status, x0, y, 11, pen)
    if r[POP]:
        chip("POPULAR - ARRIVE EARLY", W - 12 - text_w("POPULAR - ARRIVE EARLY", 9) - 8, y - 1, ORANGE)
    y += 18

    fill(SUBTLE, shape.rectangle(x0, y, W - 24, 1))
    y += 6
    building = fm.building_for(r[ROOM], r[WHERE])
    floor = fm.floor_for(r[ROOM], r[WHERE])
    put(r[ROOM], x0, y, 13, OFFWHITE)
    y += 16
    where = r[WHERE] or ""
    if floor and floor not in where:
        where = (where + ", " if where else "") + floor
    if where:
        put(fit(where, 11, W - 24), x0, y, 11, MUTED)
        y += 15
    if r[SPEAKERS]:
        for line in wrap(r[SPEAKERS], 11, W - 24, 2):
            put(line, x0, y, 11, LTPURPLE)
            y += 14

    starred = r[K] in stars
    footer(("SELECT", "unstar" if starred else "star"),
           ("RIGHT", "map" if building else "where"), ("BACK", "list"))


# ------------------------------------------------------------------ map

MAP_X0, MAP_Y0 = 2, 27
MAP_W = 211                      # drawn map size in base units (1x zoom)
MAP_TOP, MAP_BOT = 25, H - 15
BAR_Y = H - 62                   # top of the direction bar
VIEW_CY = (MAP_TOP + BAR_Y) / 2  # middle of the visible map
ZOOM_IN, ZOOM_OUT = 2.0, 0.72
route_pts = []                   # base units
route_steps = []
route_mins = 0
mona = {"d": 0.0, "pause": 0}
cam = {"x": 105.0, "y": 120.0, "z": ZOOM_IN, "zoom": True, "set": False}
_lbl = {}


def bx(x):
    return MAP_X0 + (x - fm.VIEW[0]) * fm.VIEW[2]


def by(y):
    return MAP_Y0 + (y - fm.VIEW[1]) * fm.VIEW[3]


def sx(b):
    return W / 2 + (b - cam["x"]) * cam["z"]


def sy(b):
    return VIEW_CY + (b - cam["y"]) * cam["z"]


def tx(x):
    return sx(bx(x))


def ty(y):
    return sy(by(y))


def start_place():
    """Every route starts at the venue's front door."""
    return fm.PLACES[0]


def target_building():
    if detail is None:
        return None
    r = SESSIONS[detail]
    return fm.building_for(r[ROOM], r[WHERE])


def set_route():
    global route_pts, route_steps, route_mins
    mona["d"], mona["pause"] = 0.0, 0
    if detail is None:
        route_pts, route_steps, route_mins = [], [], 0
        return
    r = SESSIONS[detail]
    target = target_building()
    if not target:
        route_pts, route_steps, route_mins = [], [], 0
        return
    floor = fm.floor_for(r[ROOM], r[WHERE])
    start = start_place()
    path = fm.route(start, target)
    route_pts = [(bx(x), by(y)) for x, y in fm.points(path)]
    route_mins = fm.walk_minutes(path)
    route_steps = ["Start at " + fm.LABEL[start] + "."] + fm.directions(start, target, floor)
    room = r[ROOM]
    if room and room != fm.LABEL[target] and room != target and room not in route_steps[-1]:
        route_steps.append("Find " + room + (", " + floor if floor and floor not in room else "") + ".")


def path_len():
    total = 0
    for i in range(1, len(route_pts)):
        (ax, ay), (bx_, by_) = route_pts[i - 1], route_pts[i]
        total += math.sqrt((bx_ - ax) ** 2 + (by_ - ay) ** 2)
    return total


def point_at(d):
    for i in range(1, len(route_pts)):
        (ax, ay), (bx_, by_) = route_pts[i - 1], route_pts[i]
        seg = math.sqrt((bx_ - ax) ** 2 + (by_ - ay) ** 2)
        if d <= seg and seg > 0:
            t = d / seg
            return ax + (bx_ - ax) * t, ay + (by_ - ay) * t, bx_ - ax
        d -= seg
    x, y = route_pts[-1]
    return x, y, 0


def step_mona(dt):
    """Move Mona along the route; returns base x, y, flip, frame, hop."""
    total = path_len()
    if total < 1:
        x, y = route_pts[0]
        return x, y, False, 4 + (badge.ticks // 200) % 2, abs(math.sin(badge.ticks / 160.0)) * 4
    if mona["pause"] > 0:
        mona["pause"] -= dt
        x, y, _ = point_at(total)
        if mona["pause"] <= 0:
            mona["d"] = 0.0
        return x, y, False, 4 + (badge.ticks // 180) % 2, abs(math.sin(badge.ticks / 120.0)) * 5
    mona["d"] += 36 * dt / 1000.0
    if mona["d"] >= total:
        mona["d"] = total
        mona["pause"] = 1600
    x, y, dx = point_at(mona["d"])
    return x, y, dx < -0.01, (badge.ticks // 110) % 4, 0


def update_cam(dt, fx, fy):
    want = ZOOM_IN if cam["zoom"] else ZOOM_OUT
    k = 1 if not cam["set"] else min(1.0, dt / 160.0)
    cam["z"] += (want - cam["z"]) * k
    z = cam["z"]
    if not cam["zoom"]:
        fx, fy = MAP_W / 2, (MAP_TOP + MAP_BOT) / 2
    hw, hh = W / 2 / z, (BAR_Y - MAP_TOP) / 2 / z
    fx = min(max(fx, hw), MAP_W - hw) if MAP_W > 2 * hw else MAP_W / 2
    top, bot = MAP_TOP, MAP_BOT - 2
    fy = min(max(fy, top + hh), bot - hh) if bot - top > 2 * hh else (top + bot) / 2
    k = 1 if not cam["set"] else min(1.0, dt / 300.0)
    cam["x"] += (fx - cam["x"]) * k
    cam["y"] += (fy - cam["y"]) * k
    cam["set"] = True


def lsize(big):
    return int(min(big + 5, max(8, big * cam["z"] * 0.8)))


def map_label(key, lines, cx, cy, bw, bh, big, pen):
    """Biggest text size up to `big` that fits the box; skip it if nothing fits."""
    ck = (fm.NAME, key, int(cam["z"] * 20))
    size = _lbl.get(ck)
    if size is None:
        size = big
        while size > 7 and (max(text_w(l, size) for l in lines) > bw - 4 or len(lines) * (size + 1) > bh + 2):
            size -= 1
        if max(text_w(l, size) for l in lines) > bw + 4:
            size = 0
        _lbl[ck] = size
    if not size:
        return
    lh = size + 1
    ly = cy - len(lines) * lh / 2 - 1
    for line in lines:
        put_center(line, cx, ly, size, pen)
        ly += lh


def draw_campus():
    shore = ty(104)
    top = sy(MAP_TOP)
    fill(WATER, shape.rectangle(sx(0), top, MAP_W * cam["z"], shore - top))
    screen.pen = WAVE
    for row, wy in enumerate(range(32, int(by(104)) - 4, 9)):
        y = sy(wy)
        if MAP_TOP - 2 < y < BAR_Y:
            for wx in range(6 + (row % 2) * 9, MAP_W - 8, 18):
                screen.shape(shape.line(sx(wx), y, sx(wx + 6), y, 1))
    put("SF BAY", sx(170), sy(62), lsize(8), color.rgb(60, 120, 140))


def draw_floor():
    z = cam["z"]
    sw, sh = fm.VIEW[2] * z, fm.VIEW[3] * z
    x, y, w, h = fm.OUTLINE
    fill(color.rgb(20, 25, 21), shape.rounded_rectangle(tx(x), ty(y), w * sw, h * sh, 3))
    fill(BORDER, shape.rounded_rectangle(tx(x), ty(y), w * sw, h * sh, 3).stroke(1.5))
    for (dx, dy, dw, dh), label in fm.DECOR:
        fill(SUBTLE, shape.rounded_rectangle(tx(dx), ty(dy), dw * sw, dh * sh, 2))
        if label:
            map_label(label, (label,), tx(dx + dw / 2), ty(dy + dh / 2), dw * sw, dh * sh, lsize(7), MUTED)
    poly(SUBTLE, *[(tx(px), ty(py)) for px, py in fm.OCTAGON])
    put_right(fm.TITLE, tx(x + w - 4), ty(y + 3), lsize(8), MUTED)


def draw_base_map(target, here, pulse):
    z = cam["z"]
    fill(LAND, shape.rectangle(0, MAP_TOP, W, MAP_BOT - MAP_TOP))
    if fm.KIND == "floor":
        draw_floor()
    else:
        draw_campus()

    # walkways
    screen.pen = ROAD
    width = max(3, (5 if fm.KIND == "campus" else 4) * z * 0.75)
    for a, b in fm.EDGES:
        ax, ay = fm.NODES[a]
        bx_, by_ = fm.NODES[b]
        screen.shape(shape.line(tx(ax), ty(ay), tx(bx_), ty(by_), width))
    if fm.KIND == "campus":
        fill(ROAD, shape.rectangle(sx(0), ty(232), MAP_W * z, 5 * z * 0.8))
        put("MARINA BLVD", sx(8), ty(232) - lsize(8) - 3, lsize(8), MUTED)

    sw, sh = fm.VIEW[2] * z, fm.VIEW[3] * z
    for name in fm.PLACES:
        if name == "Entrance":
            continue
        x, y, w, h = fm.BUILDINGS[name]
        bx_, by_, bw, bh = tx(x), ty(y), w * sw, h * sh
        if bx_ > W or bx_ + bw < 0 or by_ > BAR_Y or by_ + bh < MAP_TOP:
            continue
        if name == target:
            fill(DKGREEN, shape.rounded_rectangle(bx_, by_, bw, bh, 3))
            glow = 1 + (pulse % 1000) / 500.0
            fill(GREEN, shape.rounded_rectangle(bx_ - glow, by_ - glow, bw + 2 * glow, bh + 2 * glow, 4).stroke(2))
            pen = WHITE
        else:
            fill(BLDG, shape.rounded_rectangle(bx_, by_, bw, bh, 3))
            fill(LTPURPLE if name == here else BLDG_EDGE,
                 shape.rounded_rectangle(bx_, by_, bw, bh, 3).stroke(2 if name == here else 1))
            pen = OFFWHITE
        map_label(name, fm.MAP_LABEL[name], bx_ + bw / 2, by_ + bh / 2, bw, bh, lsize(9), pen)

    # entrance gate
    if "Entrance" not in fm.BUILDINGS:
        return
    x, y, w, h = fm.BUILDINGS["Entrance"]
    fill(PURPLE if here == "Entrance" else BLDG_EDGE,
         shape.rounded_rectangle(tx(x + 10), ty(y) + 1, (w - 20) * sw, 4 * z * 0.8, 2))
    put_center("Entrance", tx(x + w / 2), ty(y) + 4 * z + 2, lsize(8), LTPURPLE if here == "Entrance" else MUTED)


def draw_route(t):
    if len(route_pts) < 2:
        return
    z = cam["z"]
    pts = [(sx(x), sy(y)) for x, y in route_pts]
    screen.pen = LIME
    for i in range(1, len(pts)):
        (ax, ay), (bx_, by_) = pts[i - 1], pts[i]
        screen.shape(shape.line(ax, ay, bx_, by_, max(2, 1.6 * z)))
    # marching dots
    total = path_len()
    d = (t / 40.0) % 12
    while d < total:
        x, y, _ = point_at(d)
        fill(WHITE, shape.circle(sx(x), sy(y), max(1.3, 0.9 * z)))
        d += 12
    # arrowhead at the destination
    (ax, ay), (bx_, by_) = pts[-2], pts[-1]
    ang = math.atan2(by_ - ay, bx_ - ax)
    s = 5 + 2 * z
    p1 = (bx_ + math.cos(ang) * 2, by_ + math.sin(ang) * 2)
    p2 = (bx_ - math.cos(ang - 0.5) * s, by_ - math.sin(ang - 0.5) * s)
    p3 = (bx_ - math.cos(ang + 0.5) * s, by_ - math.sin(ang + 0.5) * s)
    poly(LIME, p1, p2, p3)


def draw_start():
    if len(route_pts) < 2:
        return
    x, y = sx(route_pts[0][0]), sy(route_pts[0][1])
    r = 3 + cam["z"]
    fill(PURPLE, shape.circle(x, y, r))
    fill(WHITE, shape.circle(x, y, r * 0.4))
    size = lsize(8)
    tw = text_w("START", size)
    fill(BLACK, shape.rounded_rectangle(x - tw / 2 - 3, y + r + 2, tw + 6, size + 4, 3))
    put_center("START", x, y + r + 3, size, LTPURPLE)


def draw_mona(m):
    x, y, flip, frame, hop = m
    s = int(14 + 5 * cam["z"])
    x, y = sx(x), sy(y)
    if flip:
        screen.blit(MONA.sprite(frame, 0), rect(x - s / 2, y - s - hop, -s, s))
    else:
        screen.blit(MONA.sprite(frame, 0), rect(x - s / 2, y - s - hop, s, s))


def draw_bar(target, r):
    y = BAR_Y
    fill(BLACK, shape.rectangle(0, y, W, MAP_BOT - y))
    fill(GREEN if target else ORANGE if r else PURPLE, shape.rectangle(0, y, W, 2))
    x = 8
    if r is None:
        put(fit(fm.NAME, 15, W - 16), x, y + 6, 15, LTPURPLE)
        for n, line in enumerate(wrap("Star a session to see its path from " + fm.LABEL[start_place()] + ".", 11, W - 16, 2)):
            put(line, x, y + 26 + n * 13, 11, MUTED)
        return
    if not target:
        put(fit(r[ROOM], 15, W - 16), x, y + 6, 15, ORANGE)
        for n, line in enumerate(wrap((r[WHERE] or "Off-site") + "  -  not on this map", 11, W - 16, 2)):
            put(line, x, y + 26 + n * 13, 11, OFFWHITE)
        return
    right = ("~%d min walk" % route_mins) if route_mins else ""
    put_right(right, W - 8, y + 8, 12, WHITE)
    put(fit(r[ROOM] or fm.LABEL[target], 15, W - 26 - text_w(right, 12)), x, y + 6, 15, GREEN)
    if route_steps:
        n = route_step()
        fill(DKGREEN, shape.circle(x + 6, y + 32, 6))
        put_center(str(n + 1), x + 6, y + 27, 9, WHITE)
        for k, line in enumerate(wrap(route_steps[n], 11, W - 30, 2)):
            put(line, x + 18, y + 25 + k * 13, 11, OFFWHITE)


step_pick = {"n": None, "t": 0}


def route_step():
    """Steps take turns on their own; LEFT/RIGHT flips through them."""
    if step_pick["n"] is not None and badge.ticks - step_pick["t"] < 8000:
        return step_pick["n"] % len(route_steps)
    step_pick["n"] = None
    return (badge.ticks // 3500) % len(route_steps)


def draw_map(dt):
    r = SESSIONS[detail] if detail is not None else None
    target = target_building()
    here = start_place() if target else None
    m = step_mona(dt) if route_pts else None
    if m:
        update_cam(dt, m[0], m[1])
    else:
        update_cam(dt, MAP_W / 2, (MAP_TOP + MAP_BOT) / 2)
    draw_background()
    draw_base_map(target, here, badge.ticks)
    draw_route(badge.ticks)
    draw_start()
    if m:
        draw_mona(m)
    if r and not target:
        fill(color.rgb(0, 0, 0, 150), shape.rectangle(0, MAP_TOP, W, BAR_Y - MAP_TOP))
        card(W // 2 - 80, 70, 160, 46)
        fill(ORANGE, shape.rectangle(W // 2 - 80, 70, 160, 3))
        put_center("OFF-SITE", W // 2, 79, 14, ORANGE)
        put_center("Not at " + fm.NAME, W // 2, 97, 11, MUTED)
    header("MAP")
    draw_bar(target, r)
    if route_steps:
        footer(("L/R", "steps"), ("SELECT", "zoom"), ("BACK", "back"))
    else:
        footer(("SELECT", "zoom"), ("BACK", "back"))


# ---------------------------------------------------------------- home

HOME_ITEMS = ("Full catalog", "My schedule", "Map")


def next_mine():
    """Starred session that's on now or coming up next."""
    m = now_min()
    best = None
    for key in stars:
        i = KEY_INDEX.get(key)
        if i is not None and SESSIONS[i][E] > m and (best is None or SESSIONS[i][S] < SESSIONS[best][S]):
            best = i
    return best


def home_icon(n, x, y, hi):
    fill(DKGREEN if hi else BORDER, shape.rounded_rectangle(x, y, 34, 34, 6))
    cx, cy = x + 17, y + 17
    if n == 0:
        for k in range(3):
            fill(LIME if k == 0 else WHITE, shape.rounded_rectangle(x + 8, y + 9 + k * 6, 18 - k * 4, 3, 1))
    elif n == 1:
        star_icon(cx, cy, 11, True)
    else:
        fill(PURPLE, shape.circle(cx, cy - 3, 8))
        poly(PURPLE, (cx - 7, cy), (cx + 7, cy), (cx, cy + 12))
        fill(WHITE, shape.circle(cx, cy - 3, 3))


def home_subtitle(n):
    m = now_min()
    if n == 0:
        on = len([1 for r in SESSIONS if r[S] <= m < r[E]])
        if on:
            return "%d on now  -  every session, by time" % on
        return "All %d sessions, by time" % len(SESSIONS)
    if n == 1:
        i = next_mine()
        if i is None:
            return "Star sessions to build your day" if not stars else "All done for now"
        r = SESSIONS[i]
        when = "NOW" if r[S] <= m else hm_short(r[S])
        return when + "  " + r[TITLE]
    i = next_mine()
    place = fm.building_for(SESSIONS[i][ROOM], SESSIONS[i][WHERE]) if i is not None else None
    if place:
        return "From " + fm.LABEL[start_place()] + " to " + fm.LABEL[place]
    return fm.NAME


def draw_home():
    draw_background()
    header()
    for n, label in enumerate(HOME_ITEMS):
        x, y, w, h = 12, 32 + n * 58, W - 24, 50
        hi = n == home_sel
        card(x, y, w, h, hi)
        if hi:
            fill(LIME, shape.rectangle(x + 1, y + 1, 3, h - 2))
        home_icon(n, x + 10, y + 8, hi)
        put(label, x + 54, y + 8, 15, WHITE if hi else OFFWHITE)
        put(fit(home_subtitle(n), 10, w - 80), x + 54, y + 29, 10, LIME if hi else MUTED)
        if hi:
            arrow_right(x + w - 10, y + h // 2, GREEN)
    footer(("UP/DN", "pick"), ("SELECT", "open"), ("HOME", "exit"))


def home_input():
    global view, home_sel, detail, map_back
    if repeat(BUTTON_DOWN):
        home_sel = (home_sel + 1) % len(HOME_ITEMS)
    if repeat(BUTTON_UP):
        home_sel = (home_sel - 1) % len(HOME_ITEMS)
    if badge.pressed(BUTTON_SELECT) or badge.pressed(BUTTON_RIGHT):
        if home_sel < 2:
            state["mode"] = "all" if home_sel == 0 else "mine"
            save()
            rebuild(False)
            view = "list"
        else:
            detail = next_mine()
            map_back = "home"
            set_route()
            view = "map"
    elif badge.pressed(BUTTON_BACK):
        go_menu()


# --------------------------------------------------------------- input

_hold = {}


def repeat(button):
    if badge.pressed(button):
        _hold[button] = 0
        return True
    if badge.held(button):
        t = _hold.get(button, 0) + badge.ticks_delta
        _hold[button] = t
        if t > 420:
            _hold[button] = 420 - 110
            return True
        return False
    _hold[button] = 0
    return False


def list_input():
    global page, sel, scroll, view, detail
    rows = pages[page][1]
    if repeat(BUTTON_DOWN):
        sel = fix_sel(rows, sel + 1, 1)
    if repeat(BUTTON_UP):
        n = fix_sel(rows, sel - 1, -1)
        if rows and rows[n][0] == "s":
            sel = n
        if sel <= 1:
            scroll = 0
    if state["mode"] == "all":
        if repeat(BUTTON_RIGHT) and page < len(pages) - 1:
            page += 1
            sel, scroll = fix_sel(pages[page][1], 0, 1), 0
        if repeat(BUTTON_LEFT) and page > 0:
            page -= 1
            sel, scroll = fix_sel(pages[page][1], 0, 1), 0
    else:
        # jump a day at a time in My sessions
        step = 0
        if repeat(BUTTON_RIGHT):
            step = 1
        if repeat(BUTTON_LEFT):
            step = -1
        if step:
            heads = [n for n, r in enumerate(rows) if r[0] == "h"]
            here = max([h for h in heads if h < sel] or [0])
            pick = [h for h in heads if (h > here if step > 0 else h < here)]
            if pick:
                target = pick[0] if step > 0 else pick[-1]
                sel = fix_sel(rows, target + 1, 1)
    if badge.pressed(BUTTON_SELECT):
        i = current_session()
        if i is not None:
            detail = i
            view = "detail"
    if badge.pressed(BUTTON_BACK):
        view = "home"


def detail_input():
    global view, sel, detail, map_back
    r = SESSIONS[detail]
    if badge.pressed(BUTTON_SELECT):
        if r[K] in stars:
            stars.discard(r[K])
        else:
            stars.add(r[K])
        save()
    if badge.pressed(BUTTON_RIGHT):
        map_back = "detail"
        set_route()
        view = "map"
    if badge.pressed(BUTTON_BACK) or badge.pressed(BUTTON_LEFT):
        if state["mode"] == "mine":
            rebuild()
        view = "list"
    if badge.pressed(BUTTON_DOWN) or badge.pressed(BUTTON_UP):
        # step to the neighbouring session in the current list
        rows = pages[page][1]
        step = 1 if badge.pressed(BUTTON_DOWN) else -1
        n = fix_sel(rows, sel + step, step)
        if rows and rows[n][0] == "s":
            sel = n
            detail = rows[n][1]


def map_input():
    global view
    step = 0
    if badge.pressed(BUTTON_RIGHT):
        step = 1
    if badge.pressed(BUTTON_LEFT):
        step = -1
    if step and route_steps:
        step_pick["n"] = route_step() + step
        step_pick["t"] = badge.ticks
    if badge.pressed(BUTTON_SELECT):
        cam["zoom"] = not cam["zoom"]
    if badge.pressed(BUTTON_BACK):
        view = map_back


# ---------------------------------------------------------------- loop

last_minute = now_min()
rebuild(False)
start_sync()


menu_hold = [0, True]


def go_map(i, back):
    global view, detail, map_back
    detail, map_back = i, back
    cam["set"] = False
    set_route()
    view = "map"


def go_menu():
    on_exit()
    reset()


def update():
    global last_minute, view
    # HOME is also the USB boot button: restarting while it's held down
    # boots into USB disk mode, so wait until it's let go.
    if badge.released(BUTTON_HOME):
        go_menu()
    dt = badge.ticks_delta
    if sync["state"]:
        step_sync()

    m = now_min()
    if m != last_minute:
        if office_test() and m // 1440 != last_minute // 1440:
            load_venue()  # a new day of office test meetings
        last_minute = m
        if view == "list":
            rebuild()
    alert = next_alert()
    step_alert(alert)

    if badge.pressed(BUTTON_MENU):
        menu_hold[0], menu_hold[1] = badge.ticks, False
    if badge.held(BUTTON_MENU) and not menu_hold[1] and badge.ticks - menu_hold[0] > 1500:
        menu_hold[1] = True
        toggle_test()
        view = "home"
        alert = next_alert()

    if alert is not None and view in ("home", "list") and badge.pressed(BUTTON_SELECT):
        go_map(alert, view)
    elif badge.pressed(BUTTON_MENU) and view != "home":
        view = "home"
    elif view == "home":
        home_input()
    elif view == "list":
        list_input()
    elif view == "detail":
        detail_input()
    else:
        map_input()

    if view == "home":
        draw_home()
    elif view == "list":
        draw_list()
        if state["mode"] == "all":
            footer(("L/R", "time"), ("SELECT", "open"), ("BACK", "menu"), ("HOME", "exit"))
        else:
            footer(("L/R", "day"), ("SELECT", "open"), ("BACK", "menu"), ("HOME", "exit"))
    elif view == "detail":
        draw_detail()
    else:
        draw_map(dt)

    if alert is not None and view != "map":
        draw_alert(alert)
    if sync["state"] and sync["msg"]:
        msg = sync["msg"]
        mw = text_w(msg, 11) + 16
        fill(BLACK, shape.rounded_rectangle((W - mw) // 2, H - 60, mw, 20, 4))
        fill(GREEN, shape.rounded_rectangle((W - mw) // 2, H - 60, mw, 20, 4).stroke(1))
        put_center(msg, W // 2, H - 56, 11, WHITE)


run(update)
