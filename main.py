import os
import io
import requests
from PIL import Image, ImageDraw, ImageFont

# --- Configuration & Credentials ---
CLIENT_ID = os.getenv("OSU_CLIENT_ID")
CLIENT_SECRET = os.getenv("OSU_CLIENT_SECRET")
MUTUALS_RAW = os.getenv("MUTUALS", "") 
MUTUALS = [m.strip() for m in MUTUALS_RAW.split(",") if m.strip()]

# Layout & Dimensions
CARD_WIDTH = 210
CARD_HEIGHT = 38
PADDING = 10
HEADER_HEIGHT = 65

# osu! Official Dark Theme Colors
BG_COLOR = (24, 20, 28, 255)            # Main background
BOX_BG = (46, 41, 56, 255)             # Container box (#2e2938)
CARD_BG = (56, 46, 67, 255)            # Card background (#382e43)
TEXT_MAIN = (255, 255, 255, 255)       
TEXT_MUTED = (175, 165, 190, 255)      

MODE_CONFIG = {
    "osu": {"title": "osu!", "color": (232, 91, 131, 255)},
    "mania": {"title": "osu!mania", "color": (43, 141, 237, 255)},
    "taiko": {"title": "osu!taiko", "color": (235, 71, 71, 255)},
    "fruits": {"title": "osu!catch", "color": (46, 189, 89, 255)}
}

def get_osu_token():
    url = "https://osu.ppy.sh/oauth/token"
    data = {
        "client_id": CLIENT_ID,
        "client_secret": CLIENT_SECRET,
        "grant_type": "client_credentials",
        "scope": "public"
    }
    try:
        response = requests.post(url, data=data, timeout=10)
        return response.json().get("access_token")
    except Exception as e:
        print(f"Auth error: {e}")
        return None

def fetch_user_data(identifier, token):
    headers = {"Authorization": f"Bearer {token}", "Accept": "application/json"}
    lookup_id = identifier if identifier.isdigit() else f"@{identifier}"
    url = f"https://osu.ppy.sh/api/v2/users/{lookup_id}"
    
    try:
        res = requests.get(url, headers=headers, timeout=10)
        if res.status_code == 200:
            data = res.json()
            stats = data.get("statistics", {})
            return {
                "username": data.get("username"),
                "avatar_url": data.get("avatar_url"),
                "country_code": data.get("country_code", "XX"),
                "global_rank": stats.get("global_rank"),
                "pp": stats.get("pp", 0),
                "mode": data.get("playmode", "osu")
            }
    except Exception as e:
        print(f"Error fetching {identifier}: {e}")
    return None

def fetch_image(url):
    if not url:
        return None
    try:
        res = requests.get(url, headers={"User-Agent": "Mozilla/5.0"}, timeout=5)
        if res.status_code == 200:
            return Image.open(io.BytesIO(res.content)).convert("RGBA")
    except Exception:
        pass
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
        print("Failed to authenticate.")
        return

    # Categorize users by mode
    grouped_users = {"osu": [], "mania": [], "taiko": [], "fruits": []}
    
    for username in MUTUALS:
        print(f"Fetching {username}...")
        user = fetch_user_data(username, token)
        if user and user["mode"] in grouped_users:
            grouped_users[user["mode"]].append(user)

    # Filter out empty mode columns automatically
    active_modes = [m for m in ["osu", "mania", "taiko", "fruits"] if len(grouped_users[m]) > 0]

    if not active_modes:
        print("No players found in any mode.")
        return

    # Determine canvas height based on the column with the most players
    max_players_in_col = max(len(grouped_users[m]) for m in active_modes)
    
    cols_count = len(active_modes)
    img_width = cols_count * CARD_WIDTH + (cols_count + 1) * PADDING
    img_height = HEADER_HEIGHT + (max_players_in_col * (CARD_HEIGHT + PADDING)) + PADDING + 40

    canvas = Image.new("RGBA", (img_width, img_height), BG_COLOR)
    draw = ImageDraw.Draw(canvas)

    font_header = load_font(18, bold=True)
    font_mode_title = load_font(13, bold=True)
    font_name = load_font(11, bold=True)
    font_sub = load_font(9, bold=False)

    # Header Bar (#2e2938)
    draw.rounded_rectangle([PADDING, PADDING, img_width - PADDING, HEADER_HEIGHT - 10], radius=8, fill=BOX_BG)
    total_mutuals = sum(len(grouped_users[m]) for m in active_modes)
    draw.text((PADDING + 16, PADDING + 12), "★ OSU! MUTUALS", fill=TEXT_MAIN, font=font_header)
    draw.text((PADDING + 16, PADDING + 34), f"Active Friends: {total_mutuals}", fill=TEXT_MUTED, font=font_sub)

    # Render Active Mode Columns
    for col_idx, mode_key in enumerate(active_modes):
        col_x = PADDING + col_idx * (CARD_WIDTH + PADDING)
        mode_info = MODE_CONFIG[mode_key]
        players = grouped_users[mode_key]

        # Column Box Header Tag
        col_header_y = HEADER_HEIGHT + 5
        draw.rounded_rectangle([col_x, col_header_y, col_x + CARD_WIDTH, col_header_y + 24], radius=4, fill=BOX_BG)
        draw.rectangle([col_x, col_header_y + 2, col_x + 4, col_header_y + 22], fill=mode_info["color"])
        draw.text((col_x + 10, col_header_y + 5), f"{mode_info['title']} ({len(players)})", fill=mode_info["color"], font=font_mode_title)

        # Render Tiny Player Cards
        for row_idx, user in enumerate(players):
            x = col_x
            y = col_header_y + 32 + row_idx * (CARD_HEIGHT + PADDING)

            # Tiny Card Surface (#382e43)
            draw.rounded_rectangle([x, y, x + CARD_WIDTH, y + CARD_HEIGHT], radius=6, fill=CARD_BG)

            # Avatar
            avatar_img = fetch_image(user["avatar_url"])
            if avatar_img:
                avatar_img = avatar_img.resize((28, 28), Image.Resampling.LANCZOS)
                mask = Image.new("L", (28, 28), 0)
                ImageDraw.Draw(mask).ellipse((0, 0, 28, 28), fill=255)
                canvas.paste(avatar_img, (x + 5, y + 5), mask)

            # Username
            text_x = x + 38
            draw.text((text_x, y + 4), user["username"], fill=TEXT_MAIN, font=font_name)

            # Flag
            flag_img = fetch_image(f"https://flagcdn.com/w40/{user['country_code'].lower()}.png")
            info_x = text_x
            if flag_img:
                flag_img = flag_img.resize((12, 8), Image.Resampling.LANCZOS)
                canvas.paste(flag_img, (info_x, y + 21), flag_img)
                info_x += 16

            # Rank & PP
            rank_str = f"#{user['global_rank']:,}" if user["global_rank"] else "Unranked"
            pp_str = f"{int(user['pp']):,}pp" if user["pp"] else "0pp"
            draw.text((info_x, y + 20), f"{rank_str} • {pp_str}", fill=TEXT_MUTED, font=font_sub)

    canvas.convert("RGB").save("mutuals.png", "PNG")
    print("mutuals.png generated successfully!")

if __name__ == "__main__":
    create_banner()
    
