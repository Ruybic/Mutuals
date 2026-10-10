import os
import io
import requests
from PIL import Image, ImageDraw, ImageFont

# --- Configuration & Credentials ---
CLIENT_ID = os.getenv("OSU_CLIENT_ID")
CLIENT_SECRET = os.getenv("OSU_CLIENT_SECRET")
# Comma-separated list of your mutual usernames or IDs
MUTUALS_RAW = os.getenv("MUTUALS", "peppy,FlyTuna") 
MUTUALS = [m.strip() for m in MUTUALS_RAW.split(",") if m.strip()]

# Layout Configuration
COLS = 3
CARD_WIDTH = 380
CARD_HEIGHT = 90
PADDING = 12
HEADER_HEIGHT = 60
BG_COLOR = (24, 20, 28, 255)         # Dark sleek osu! background
CARD_BG = (35, 30, 42, 255)           # Card background
TEXT_MAIN = (255, 255, 255, 255)      # White
TEXT_MUTED = (160, 150, 175, 255)     # Muted grey-purple

MODE_COLORS = {
    "osu": (232, 91, 131, 255),       # Standard - Pink/Red
    "taiko": (235, 71, 71, 255),      # Taiko - Red/Orange
    "fruits": (46, 189, 89, 255),     # Catch - Green
    "mania": (43, 141, 237, 255)      # Mania - Blue
}

def get_osu_token():
    url = "https://osu.ppy.sh/oauth/token"
    data = {
        "client_id": CLIENT_ID,
        "client_secret": CLIENT_SECRET,
        "grant_type": "client_credentials",
        "scope": "public"
    }
    response = requests.post(url, data=data)
    return response.json().get("access_token")

def fetch_user_data(username, token):
    headers = {"Authorization": f"Bearer {token}", "Accept": "application/json", "Content-Type": "application/json"}
    url = f"https://osu.ppy.sh/api/v2/users/{username}"
    res = requests.get(url, headers=headers)
    if res.status_code == 200:
        data = res.json()
        stats = data.get("statistics", {})
        return {
            "username": data.get("username"),
            "avatar_url": data.get("avatar_url"),
            "country": data.get("country", {}).get("code", "XX"),
            "global_rank": stats.get("global_rank"),
            "pp": stats.get("pp", 0),
            "mode": data.get("playmode", "osu")
        }
    return None

def load_font(size, bold=False):
    try:
        font_name = "DejaVuSans-Bold.ttf" if bold else "DejaVuSans.ttf"
        return ImageFont.truetype(font_name, size)
    except IOError:
        return ImageFont.load_default()

def create_banner():
    if not CLIENT_ID or not CLIENT_SECRET:
        print("Missing OSU_CLIENT_ID or OSU_CLIENT_SECRET environment variables.")
        return

    token = get_osu_token()
    if not token:
        print("Failed to authenticate with osu! API.")
        return

    users_data = []
    for username in MUTUALS:
        print(f"Fetching {username}...")
        user = fetch_user_data(username, token)
        if user:
            users_data.append(user)

    if not users_data:
        print("No user data retrieved.")
        return

    # Calculate canvas dimensions
    rows = (len(users_data) + COLS - 1) // COLS
    img_width = COLS * CARD_WIDTH + (COLS + 1) * PADDING
    img_height = HEADER_HEIGHT + rows * CARD_HEIGHT + (rows + 1) * PADDING

    canvas = Image.new("RGBA", (img_width, img_height), BG_COLOR)
    draw = ImageDraw.Draw(canvas)

    font_title = load_font(18, bold=True)
    font_name = load_font(14, bold=True)
    font_sub = load_font(11, bold=False)

    # Draw Header Title
    draw.text((PADDING, 18), "★ My OSU! Mutuals & Friends", fill=TEXT_MAIN, font=font_title)

    for index, user in enumerate(users_data):
        col = index % COLS
        row = index // COLS

        x = PADDING + col * (CARD_WIDTH + PADDING)
        y = HEADER_HEIGHT + PADDING + row * (CARD_HEIGHT + PADDING)

        # Draw Card Background
        draw.rounded_rectangle([x, y, x + CARD_WIDTH, y + CARD_HEIGHT], radius=8, fill=CARD_BG)

        # Download & Paste Avatar
        avatar_img = None
        if user["avatar_url"]:
            try:
                avatar_res = requests.get(user["avatar_url"], timeout=5)
                if avatar_res.status_code == 200:
                    avatar_img = Image.open(io.BytesIO(avatar_res.content)).convert("RGBA")
                    avatar_img = avatar_img.resize((60, 60), Image.Resampling.LANCZOS)
            except Exception:
                pass

        if avatar_img:
            canvas.paste(avatar_img, (x + 15, y + 15), avatar_img)

        # Mode Indicator Stripe
        mode = user["mode"]
        mode_color = MODE_COLORS.get(mode, (255, 255, 255, 255))
        draw.rectangle([x, y + 15, x + 4, y + 75], fill=mode_color)

        # Text Details
        text_x = x + 85
        draw.text((text_x, y + 16), user["username"], fill=TEXT_MAIN, font=font_name)

        rank_str = f"#{user['global_rank']:,}" if user["global_rank"] else "Unranked"
        pp_str = f"{int(user['pp']):,} pp" if user["pp"] else "0 pp"
        details_str = f"{rank_str} • {pp_str} • [{user['country']}]"
        
        draw.text((text_x, y + 42), details_str, fill=TEXT_MUTED, font=font_sub)
        draw.text((text_x, y + 60), f"Mode: {mode.capitalize()}", fill=mode_color, font=font_sub)

    canvas.convert("RGB").save("mutuals.png", "PNG")
    print("mutuals.png generated successfully!")

if __name__ == "__main__":
    create_banner()
