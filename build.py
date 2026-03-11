#!/usr/bin/env python3
"""Build IPTV playlists from iptv-org and Free-TV repos.

Channels are grouped for easy Apple TV / iPlayTV navigation:
  - Big countries (RU, UA) get per-genre folders with Russian labels
  - Small countries get one folder each with flag + name
  - US playlist gets simple English genre folders
  - Channel names are clean (no redundant genre prefix)

Genre data comes from iptv-org/database's channels.csv.

Usage:
    python3 build.py              # build all playlists
    python3 build.py post-soviet  # build just one
"""

import csv
import re
import sys
from pathlib import Path

# ---------------------------------------------------------------------------
# Paths — auto-detect environment
# ---------------------------------------------------------------------------

# Try consolidated ~/Documents/tv/ layout first, fall back to legacy flat
_tv_dir = Path(__file__).resolve().parent
_cowork = Path("/sessions/trusting-gallant-archimedes/mnt/Documents")

if (_tv_dir / "upstream").exists():
    # New consolidated layout: ~/Documents/tv/
    TV_HOME = _tv_dir
    IPTV_ORG = TV_HOME / "upstream" / "iptv-org" / "streams"
    FREE_TV = TV_HOME / "upstream" / "free-tv" / "playlists"
    CHANNELS_DB = TV_HOME / "upstream" / "channels.csv"
    OUTPUT = TV_HOME / "output"
elif _cowork.exists():
    # Running inside Cowork VM
    TV_HOME = _cowork
    IPTV_ORG = TV_HOME / "iptv-org" / "streams"
    FREE_TV = TV_HOME / "IPTV" / "playlists"
    CHANNELS_DB = TV_HOME / "iptv-org-database" / "data" / "channels.csv"
    OUTPUT = TV_HOME
else:
    # Legacy flat layout in ~/Documents/
    TV_HOME = Path.home() / "Documents"
    IPTV_ORG = TV_HOME / "iptv-org" / "streams"
    FREE_TV = TV_HOME / "IPTV" / "playlists"
    CHANNELS_DB = TV_HOME / "iptv-org-database" / "data" / "channels.csv"
    OUTPUT = TV_HOME

OUTPUT.mkdir(parents=True, exist_ok=True)

# ---------------------------------------------------------------------------
# Playlist definitions
# ---------------------------------------------------------------------------

PLAYLISTS = {
    "post-soviet-tv": {
        "countries": {
            "ru": "Russia",
            "kz": "Kazakhstan",
            "ua": "Ukraine",
            "by": "Belarus",
            "uz": "Uzbekistan",
            "tj": "Tajikistan",
            "kg": "Kyrgyzstan",
            "tm": "Turkmenistan",
            "az": "Azerbaijan",
            "ge": "Georgia",
            "am": "Armenia",
            "md": "Moldova",
            "lv": "Latvia",
            "lt": "Lithuania",
            "ee": "Estonia",
        },
        "free_tv_map": {
            "playlist_russia.m3u8": "ru",
            "playlist_kazakhstan.m3u8": "kz",
            "playlist_ukraine.m3u8": "ua",
            "playlist_belarus.m3u8": "by",
            "playlist_uzbekistan.m3u8": "uz",
            "playlist_azerbaijan.m3u8": "az",
            "playlist_georgia.m3u8": "ge",
            "playlist_armenia.m3u8": "am",
            "playlist_moldova.m3u8": "md",
            "playlist_latvia.m3u8": "lv",
            "playlist_lithuania.m3u8": "lt",
            "playlist_estonia.m3u8": "ee",
        },
        "big_countries": {"ru", "ua"},
        "big_threshold": 100,
    },
    "us-tv": {
        "countries": {
            "us": "United States",
        },
        "free_tv_map": {
            "playlist_usa.m3u8": "us",
        },
        "big_countries": {"us"},
        "big_threshold": 0,
    },
}

# ---------------------------------------------------------------------------
# Genre mapping
# ---------------------------------------------------------------------------

GENRE_ORDER = {
    "news":          (1,  "News"),
    "entertainment": (2,  "Entertainment"),
    "movies":        (3,  "Movies"),
    "series":        (3,  "Movies"),
    "comedy":        (3,  "Movies"),
    "classic":       (3,  "Movies"),
    "sports":        (4,  "Sports"),
    "music":         (5,  "Music"),
    "kids":          (6,  "Kids"),
    "animation":     (6,  "Kids"),
    "family":        (6,  "Kids"),
    "documentary":   (7,  "Docs"),
    "science":       (7,  "Docs"),
    "education":     (7,  "Docs"),
    "culture":       (8,  "Lifestyle"),
    "lifestyle":     (8,  "Lifestyle"),
    "travel":        (8,  "Lifestyle"),
    "cooking":       (8,  "Lifestyle"),
    "outdoor":       (8,  "Lifestyle"),
    "business":      (9,  "Business"),
    "legislative":   (9,  "Business"),
    "religious":     (10, "Religious"),
    "general":       (11, "Regional"),
    "shop":          (12, "Shopping"),
    "auto":          (13, "Misc"),
    "relax":         (13, "Misc"),
    "weather":       (13, "Misc"),
}
OTHER_PRIORITY = 14
OTHER_LABEL = "Misc"

# Name-based rescue: pull channels out of Misc by keywords
NAME_RESCUE = [
    (re.compile(r"\b(news|новост|вести|известия|информ)", re.I), 1, "News"),
    (re.compile(r"\b(sport|спорт|матч|футбол|nba|nfl|nhl|espn|fox sports)", re.I), 4, "Sports"),
    (re.compile(r"\b(music|музык|mtv|vh1|hits|rock|jazz|concert)", re.I), 5, "Music"),
    (re.compile(r"\b(kids|kid|детск|мульт|cartoon|disney|nick|toon|baby)", re.I), 6, "Kids"),
    (re.compile(r"\b(movie|film|кино|фильм|cinema|hbo|showtime|drama|thriller|action|comedy ch)", re.I), 3, "Movies"),
    (re.compile(r"\b(document|discovery|national geo|nat geo|history|наук|познават|animal)", re.I), 7, "Docs"),
    (re.compile(r"\b(food|cook|travel|кулинар|путешеств|garden|home|hgtv|tlc|lifestyle)", re.I), 8, "Lifestyle"),
    (re.compile(r"\b(entertainment|развлеч|bravo|reality|e!)", re.I), 2, "Entertainment"),
    (re.compile(r"\b(church|храм|christian|gospel|bible|god|faith|tbn|daystar|спас)", re.I), 10, "Religious"),
    (re.compile(r"\b(shop|qvc|hsn|магазин)", re.I), 12, "Shopping"),
    (re.compile(r"\b(business|бизнес|cnbc|bloomberg|finance|экономик)", re.I), 9, "Business"),
    (re.compile(r"\b(\d{1,2}\s*(канал|channel)|область|край|ТВ$|телевидение|регион)", re.I), 11, "Regional"),
]

COUNTRY_FLAGS = {
    "ru": "🇷🇺", "kz": "🇰🇿", "ua": "🇺🇦", "by": "🇧🇾",
    "uz": "🇺🇿", "tj": "🇹🇯", "kg": "🇰🇬", "tm": "🇹🇲",
    "az": "🇦🇿", "ge": "🇬🇪", "am": "🇦🇲", "md": "🇲🇩",
    "lv": "🇱🇻", "lt": "🇱🇹", "ee": "🇪🇪",
    "us": "🇺🇸",
}

GENRE_LABELS_RU = {
    "News":          "Новости",
    "Entertainment": "Развлечения",
    "Movies":        "Кино",
    "Sports":        "Спорт",
    "Music":         "Музыка",
    "Kids":          "Детям",
    "Docs":          "Документальные",
    "Lifestyle":     "Культура",
    "Business":      "Бизнес",
    "Religious":     "Религия",
    "Regional":      "Регионы",
    "Shopping":      "Магазины",
    "Misc":          "Разное",
}

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def load_channel_db():
    db = {}
    try:
        with open(CHANNELS_DB, "r", encoding="utf-8") as f:
            for row in csv.DictReader(f):
                cid = row["id"].strip()
                cats = [c.strip().lower() for c in row["categories"].split(";") if c.strip()]
                if "xxx" in cats:
                    continue
                best_pri, best_label = OTHER_PRIORITY, OTHER_LABEL
                for cat in cats:
                    if cat in GENRE_ORDER:
                        pri, label = GENRE_ORDER[cat]
                        if pri < best_pri:
                            best_pri, best_label = pri, label
                db[cid.lower()] = (best_pri, best_label)
    except FileNotFoundError:
        print(f"⚠️  {CHANNELS_DB} not found — all channels will be '{OTHER_LABEL}'")
    return db


def extract_tvg_id(extinf):
    m = re.search(r'tvg-id="([^"]*)"', extinf)
    return re.sub(r"@\w+$", "", m.group(1).strip()) if m else ""


def extract_channel_name(extinf):
    m = re.search(r",([^,]*)$", extinf)
    return m.group(1).strip() if m else ""


def clean_channel_name(name):
    name = re.sub(r"^[\U0001F1E0-\U0001F1FF]{2}\s+\w[\w &/]*\s*│\s*", "", name)
    name = re.sub(r"^[\w &/]+\s*│\s*", "", name)
    return name.strip()


def parse_m3u(filepath):
    entries = []
    try:
        with open(filepath, "r", encoding="utf-8", errors="replace") as f:
            lines = f.readlines()
    except FileNotFoundError:
        return entries
    extinf = None
    for line in lines:
        line = line.strip()
        if line.startswith("#EXTINF"):
            extinf = line
        elif extinf and line and not line.startswith("#"):
            entries.append((extinf, line))
            extinf = None
    return entries


def get_genre(extinf, db):
    tid = extract_tvg_id(extinf).lower()
    pri, label = db.get(tid, (OTHER_PRIORITY, OTHER_LABEL))
    if pri != OTHER_PRIORITY:
        return (pri, label)
    name = clean_channel_name(extract_channel_name(extinf))
    for pattern, rescue_pri, rescue_label in NAME_RESCUE:
        if pattern.search(name):
            return (rescue_pri, rescue_label)
    return (OTHER_PRIORITY, OTHER_LABEL)


# ---------------------------------------------------------------------------
# Builder
# ---------------------------------------------------------------------------


def build_playlist(name, config, db):
    countries = config["countries"]
    free_tv_map = config["free_tv_map"]
    big_countries = config.get("big_countries", set())
    big_threshold = config.get("big_threshold", 100)

    all_channels = {}
    seen_urls = set()

    for cc in countries:
        all_channels[cc] = []
        files = [IPTV_ORG / f"{cc}.m3u"]
        for extra in IPTV_ORG.glob(f"{cc}_*.m3u"):
            files.append(extra)
        for filepath in files:
            for extinf, url in parse_m3u(filepath):
                if url not in seen_urls:
                    seen_urls.add(url)
                    all_channels[cc].append((extinf, url))

    for filename, cc in free_tv_map.items():
        for extinf, url in parse_m3u(FREE_TV / filename):
            if url not in seen_urls:
                seen_urls.add(url)
                all_channels[cc].append((extinf, url))

    big_set = set()
    for cc in countries:
        if cc in big_countries or len(all_channels.get(cc, [])) >= big_threshold:
            big_set.add(cc)

    multi_country = len(countries) > 1

    def sort_key(entry):
        pri, _ = get_genre(entry[0], db)
        return (pri, clean_channel_name(extract_channel_name(entry[0])).lower())

    output = OUTPUT / f"{name}.m3u"
    total = 0
    genre_stats = {}

    with open(output, "w", encoding="utf-8") as f:
        f.write("#EXTM3U\n")
        for cc, country_name in countries.items():
            channels = all_channels.get(cc, [])
            if not channels:
                continue
            channels.sort(key=sort_key)
            flag = COUNTRY_FLAGS.get(cc, "")

            for extinf, url in channels:
                pri, genre_label = get_genre(extinf, db)
                genre_stats[genre_label] = genre_stats.get(genre_label, 0) + 1

                if cc in big_set and multi_country:
                    ru_label = GENRE_LABELS_RU.get(genre_label, genre_label)
                    group = f"{flag} {ru_label}"
                elif cc in big_set:
                    group = genre_label
                else:
                    group = f"{flag} {country_name}"

                if "group-title=" not in extinf:
                    extinf = extinf.replace(",", f' group-title="{group}",', 1)
                else:
                    extinf = re.sub(r'group-title="[^"]*"', f'group-title="{group}"', extinf)

                raw_name = extract_channel_name(extinf)
                ch_name = clean_channel_name(raw_name)
                if cc in big_set and multi_country and not ch_name.startswith(flag):
                    ch_name = f"{flag} {ch_name}"
                extinf = re.sub(r",([^,]*)$", f",{ch_name}", extinf)

                f.write(f"{extinf}\n{url}\n")
                total += 1

    pct_misc = 100 * genre_stats.get("Misc", 0) // total if total else 0
    print(f"\n📺 {name}.m3u → {output}")
    print(f"   {total} channels ({pct_misc}% uncategorized)")
    for cc, cname in countries.items():
        count = len(all_channels.get(cc, []))
        if count:
            print(f"   {cname:15s} {count:4d}")
    print(f"   Genres:")
    for label, count in sorted(genre_stats.items(), key=lambda x: -x[1]):
        print(f"     {label:15s} {count:4d}")
    return total


def main():
    print(f"TV Home: {TV_HOME}")
    print(f"Output:  {OUTPUT}\n")
    print("Loading channel database...")
    db = load_channel_db()
    print(f"  {len(db)} channels with genre data\n")

    targets = sys.argv[1:] if len(sys.argv) > 1 else list(PLAYLISTS.keys())
    grand_total = 0
    for name in targets:
        if name not in PLAYLISTS:
            print(f"Unknown playlist: {name}")
            print(f"Available: {', '.join(PLAYLISTS.keys())}")
            sys.exit(1)
        grand_total += build_playlist(name, PLAYLISTS[name], db)

    print(f"\n✅ Done — {grand_total} total channels across {len(targets)} playlist(s)")


if __name__ == "__main__":
    main()
