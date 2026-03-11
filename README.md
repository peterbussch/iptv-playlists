# tv — IPTV Playlists

Free IPTV playlists for post-Soviet channels and US TV, built for Apple TV (iPlayTV) and IINA.

## Quick start

```bash
# Watch post-Soviet TV in IINA
./tv

# Watch US TV
./tv us

# Update channels from upstream + rebuild
./tv rebuild

# Start local server for Apple TV
./tv serve

# List available playlists
./tv list
```

## Playlists

| Playlist | Channels | What's in it |
|---|---|---|
| `post-soviet-tv.m3u` | ~1,000 | Russia, Ukraine, + 13 former Soviet states |
| `us-tv.m3u` | ~2,400 | US free-to-air and streaming channels |
| `news-channels.m3u8` | 14 | Working US & international news (ABC, CBS, Fox, BBC, Al Jazeera, etc.) |

## Apple TV setup (iPlayTV)

1. Install **iPlayTV** from the App Store (~$6)
2. On your Mac, run: `./tv serve`
3. On Apple TV → iPlayTV → **Add Playlist** → enter:
   - `http://<your-mac-ip>:8642/post-soviet-tv.m3u`
   - `http://<your-mac-ip>:8642/us-tv.m3u`
   - `http://<your-mac-ip>:8642/news-channels.m3u8`
4. Done — folders show up automatically from group-title tags

The server prints your Mac's local IP when it starts.

## Folder structure (after migration)

```
~/Documents/tv/
├── build.py              # playlist builder
├── tv                    # quick launcher (alias this)
├── serve.py              # HTTP server for iPlayTV
├── README.md
├── output/
│   ├── post-soviet-tv.m3u
│   ├── us-tv.m3u
│   └── news-channels.m3u8
└── upstream/
    ├── iptv-org/         # github.com/iptv-org/iptv (streams)
    ├── free-tv/          # github.com/Free-TV/IPTV (curated)
    └── channels.csv      # genre database from iptv-org
```

## How grouping works

**Post-Soviet playlist** — big countries (RU, UA) get genre subfolders with Russian labels; smaller countries get one folder each:

| Folder | Example |
|---|---|
| 🇷🇺 Новости | RT, Первый канал, Россия 24 |
| 🇷🇺 Кино | Мосфильм, TV1000, Кинокомедия |
| 🇷🇺 Регионы | Башкортостан 24, Кубань 24 |
| 🇺🇦 Новости | 1+1, Рада, Espreso |
| 🇬🇪 Georgia | All Georgian channels in one folder |
| 🇰🇿 Kazakhstan | All Kazakh channels in one folder |

**US playlist** — simple English genre folders: News, Movies, Sports, Kids, Docs, etc.

## Updating

```bash
./tv rebuild
```

This pulls the latest from `iptv-org/iptv` and `Free-TV/IPTV`, downloads a fresh `channels.csv` for genre data, and rebuilds both playlists.

## Migration

If you still have the old flat layout (files scattered in `~/Documents/`), run:

```bash
bash ~/Documents/migrate-tv.sh
```
