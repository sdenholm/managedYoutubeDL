# Project Layout — managedYoutubeDL

**Audience:** AI agent seeking to understand the codebase in order to navigate, modify, or extend it.

---

## What it does

`managedYoutubeDL` is a command-line tool that automatically discovers and downloads new videos from a user's YouTube subscriptions. It uses the **YouTube Data API v3** to enumerate subscribed channels and their recent uploads, applies a configurable set of per-channel and global filters (date range, regex title matching, video duration), then downloads matching videos via **yt-dlp**. All state is persisted in a single **YAML config file**.

The tool is designed to be run on a schedule (e.g. cron). Between runs it tracks which videos it has already downloaded to avoid re-processing them.

---

## Repository layout

```
managedYoutubeDL/           # top-level package
  __init__.py               # exports: Fetcher, YAMLBuilder, convertTime()
  __main__.py               # CLI entry point (argparse, logging setup)
  items.py                  # domain objects: Channel, Video
  fetcher.py                # YouTube Data API v3 wrapper
  manager.py                # core business logic orchestrator
  yamlBuilder.py            # YAML serialisation / deserialisation

tests/
  test_init.py              # tests for convertTime()
  test_items.py
  test_fetcher.py
  test_manager.py
  test_yamlBuilder.py

requirements.txt            # 5 dependencies (see below)
venv/                       # local virtualenv — use venv/bin/python to run
```

Run tests: `venv/bin/python -m pytest tests/ -v`
Run the tool: `venv/bin/python -m managedYoutubeDL <subcommand>`

---

## Source files in detail

### `__init__.py`
Thin package init. Exports `Fetcher`, `YAMLBuilder`, and the `convertTime()` helper.

**`convertTime(value)`** — converts `None`, an ISO 8601 string, or an existing `datetime` to a `datetime.datetime`. All returned datetimes are **UTC-aware** (`tzinfo=datetime.timezone.utc`):
- `None` → `None`
- UTC-aware `datetime` → returned unchanged
- Naive `datetime` (no tzinfo) → UTC tzinfo attached, same date/time value
- String in YouTube API format (`"2024-01-15T10:30:00Z"`) → parsed as UTC-aware
- String in legacy YAML format (`"2024-01-15 10:30:00"`, with optional microseconds) → parsed as UTC-aware

Used everywhere dates are read from YAML or from the YouTube API. Existing YAML files that contain naive datetime strings are handled transparently by the naive-datetime path.

---

### `items.py` — domain objects

**`Channel`** — represents one YouTube channel. Fields:
- `title`, `id`, `publishedAt` — identity
- `ignore` (bool) — if True, skip this channel entirely during download
- `includeFilter`, `excludeFilter` — regex strings for video title matching
- `minVideoDate`, `maxVideoDate` — UTC-aware `datetime` range; only download videos published within this window. Default `minVideoDate` is the UTC epoch (`1970-01-01 00:00:00+00:00`).
- `minVideoLength`, `maxVideoLength` — `timedelta` range for video duration

Each field has a dedicated `setX()` method that validates and converts types (e.g. `int` → `timedelta`). `__init__` delegates to these setters so YAML loading and direct construction both go through the same validation path.

`__eq__` compares `title + id`. Unrecognised kwargs raise `AttributeError`.

**`Video`** — lightweight; only `title`, `id`, `publishedAt`, `thumbnailURL`. Same `__eq__` pattern.

---

### `fetcher.py` — YouTube API wrapper

Wraps the YouTube Data API v3. One instance is created per `Manager` and reused across all API calls within a session.

Key methods:
- **`fetchCredentials(clientSecretsFile)`** — static; runs interactive OAuth 2.0 console flow, returns pickled credentials string
- **`fetchMySubscribedChannels()`** — paginates through subscriptions API (alphabetical order, up to 50/page); handles YouTube's non-deterministic pagination by retrying up to `10× expected pages`; raises `SystemError` if it cannot fetch all channels after max attempts
- **`fetchRecentVideos(channelID, maxResults=10)`** — resolves a channel's `uploads` playlist ID then fetches the most recent `maxResults` videos
- **`fetchVideoDetails(video)`** — fetches `contentDetails` (duration only); costs 3 API quota units; called last in the filter pipeline to minimise unnecessary quota spend
- **`_convertVideoDuration(str)`** — parses YouTube's ISO 8601 duration format (e.g. `"PT1H30M45S"`) into a `timedelta`; returns `None` for live streams (`"P0D"`)

**Credential storage:** OAuth credentials are `pickle`-serialised then `base64`-encoded into a string stored in the YAML config. See `_pickleObject` / `_unpickleObject`.

**Quota tracking:** `creditsUsed` accumulates the cost of every request. All known request types cost 3 units. Accessed via `Manager.getAPICreditsUsed()`.

---

### `manager.py` — orchestrator

The central class. Holds all configuration and runs the main workflows.

#### Configuration fields (all with `setX()` validators)

| Field | Type | Purpose |
|---|---|---|
| `clientSecretsFile` | str path | Google OAuth client secrets JSON |
| `pickledCredentials` | str (base64) | Serialised OAuth token |
| `downloadDirectory` | str path | Where to save videos |
| `ffmpegLocation` | str path or None | Path to ffmpeg binary; discovered via `shutil.which("ffmpeg")` if not set |
| `channelList` | list[Channel] | Alphabetically sorted; maintained by `updateChannels()` |
| `seenChannelVideos` | dict[channelID → list[videoID]] | Tracks downloaded videos to avoid re-downloads; capped at 25 entries per channel |
| `globalMinVideoDate` | datetime or None | Global floor for video publish date |
| `globalMaxVideoDate` | datetime or None | Global ceiling for video publish date |
| `globalIncludeFilter` | str (regex) or None | Must match video title to pass |
| `globalExcludeFilter` | str (regex) or None | Must NOT match video title to pass |
| `globalMinVideoLength` | timedelta or None | Minimum video duration |
| `globalMaxVideoLength` | timedelta or None | Maximum video duration |
| `downloadTimeout` | timedelta | Default 3 min; per-video download time limit |
| `postTimeoutWait` | timedelta | Default 1 min; pause after a timeout before retrying |

#### `VideoQuality` enum
Values: `max`, `480p`, `720p`, `1080p`, `1440p`, `2160p`. Maps to yt-dlp format strings in `SUPPORTED_QUALITIES`. Requires ffmpeg to be available for anything other than `max`.

#### Key methods

**`createNewManager(clientSecretsFileLocation, configFileLocation)`** — static factory. Runs OAuth flow, creates a blank Manager, fetches subscriptions, writes the initial YAML config file. Only called once (the `init` CLI command).

**`downloadNewVideos(quality)`** — main download loop:
1. Separate `ignore=True` channels from active ones
2. For each active channel, call `fetchRecentVideos()` then `filterChannelVideos()`
3. Print a summary of all approved videos grouped by channel: channel name in bold, then `[N] title` per video (number right-padded to the total video count width so columns align)
4. For each approved video, log `[N/total] **Channel**: Title` (channel name bold) then call `_downloadVideo()` in a retry loop:
   - On success: add to `seenChannelVideos`, update `channel.minVideoDate`, sleep `WAIT_BETWEEN_DOWNLOADS` (10 s)
   - On `TimeoutError`: sleep `postTimeoutWait` then retry indefinitely

**`filterChannelVideos(channel, videoList)`** — applies all filters in cost order (cheapest API calls first):
1. Already seen (free)
2. Date range — effective date = stricter of channel vs global setting (free)
3. Title regex include/exclude — patterns compiled once before the loop, not per video (free)
4. Duration — calls `fetchVideoDetails()` which costs 3 quota units; skipped if no length filters set. If duration cannot be determined (e.g. live streams), the video is skipped and logged as `Skipped (duration unknown): [Channel] title`

The `_compare("max"/"min", v1, v2)` helper resolves conflicts between channel-level and global-level date/duration filters: it returns whichever is more restrictive, treating `None` as "no constraint".

**`addSeenVideo(channel, video)`** — appends the video's ID to `seenChannelVideos[channel.id]`, then trims the list to the most recent **25 entries**. Older IDs are dropped; they will not be re-fetched from the API anyway because `minVideoDate` advances with each successful download.

**`haveSeenVideo(channel, video)`** — returns `True` if the video's ID is in `seenChannelVideos[channel.id]`.

**`_downloadVideo(channel, video, quality, timeout)`** — spawns a `multiprocessing.Process` running `_callYoutubeDL()`. Joins with `timeout.total_seconds()`. If still alive → `terminate()` + `kill()` + raise `TimeoutError`. Result is retrieved from a `multiprocessing.Queue` with a 5-second safety timeout (returns `False` if the queue is empty, e.g. process was killed mid-write). yt-dlp options include `updatetime: False` to prevent yt-dlp from attempting to set file modification times (which fails silently on WSL2/NTFS and would otherwise produce a warning per download).

**`_callYoutubeDL(returnQueue, options, urlList)`** — static; runs inside the child process. Calls `ydl.extract_info()` to inspect the selected format, then `ydl.download()`. Puts `returnCode == 0` into the queue. Exceptions during `extract_info` are logged at WARNING with traceback.

**`updateChannels()`** — fetches current subscriptions, diffs against `channelList`, appends new channels, removes channels no longer subscribed, and logs both. Only writes the config if the list actually changed. Returns `(numAdded, numRemoved)`.

#### Constants
```python
DOWNLOAD_TIMEOUT     = 60 * 3   # seconds
POST_TIMEOUT_WAIT    = 60       # seconds
WAIT_BETWEEN_DOWNLOADS = 10     # seconds
```

---

### `yamlBuilder.py` — serialisation

Handles reading and writing the YAML config file that is the sole persistence mechanism.

Three custom YAML types:
- `!Manager` — the top-level object; all Manager fields except `ytFetcher` (which is always reconstructed on load)
- `!Channel` — Channel objects, with keys in a specific display order (title, id, ignore first; then reverse-alphabetically grouped)
- `!timedelta` — serialised as an integer seconds string, e.g. `"180s"`

**Important implementation detail:** custom constructors and representers are registered on **local subclasses** of `yaml.SafeLoader` / `yaml.SafeDumper`, not on the global singletons. This means `yaml.safe_load()` called elsewhere in the process is unaffected.

**`loadManager(fileLoc)`** — deserialises YAML to a `Manager` instance. The `!Manager` constructor calls `Manager(**kwargs)`, which runs all `setX()` validators. `ytFetcher` is reconstructed in `Manager.__init__` if `clientSecretsFile` is not None.

**`dumpManager(manager, fileLoc, overwrite=False)`** — serialises a Manager to YAML. Raises `FileExistsError` if file exists and `overwrite=False`.

**`safeDumpManager(manager, fileLoc, overwrite=False, maxChangeFraction=0.1)`** — safe wrapper around `dumpManager`:
1. Writes to a temp file in a temp directory
2. If the target file already exists, checks the new file is non-empty and that its size hasn't changed by more than 10% relative to the old file
3. If size change exceeds 10%, backs up the old file to `<fileLoc>.<UTC timestamp>.old` before overwriting
4. Uses `shutil.copy2` (atomic on same filesystem) to move the temp file into place

---

### `__main__.py` — CLI

Entry point when running `python -m managedYoutubeDL`.

**Logging:** Sets up a `RotatingFileHandler` at `DEBUG` level, writing to `__main__.py.log` in the package directory (max 5 MB, 5 backups). A console `StreamHandler` at `INFO` (or `DEBUG` with `--verbose`) is added after arg parsing.

**Subcommands:**

| Subcommand | Function | What it does |
|---|---|---|
| `init <secrets> <config>` | `initialise()` | OAuth flow + write initial config |
| `download-new <config> [--quality]` | `downloadNew()` | Load config → download → safe-dump updated config → prints blank-line-separated sections: channel count, found-video summary, downloading progress, final `N downloaded. N failed. (N API credits)` |
| `update-channels <config>` | `updateChannels()` | Load config → sync subscriptions → safe-dump if changed |
| `manual-download <config> <url...> [--quality]` | `manualDownload()` | Download arbitrary URLs using the config's ffmpeg/directory settings; no API calls, no seen-video tracking |

**`download-new` terminal output format:**
```
Checking N channels

Found N new videos
  **Channel Name**
    [1] Video title
  **Channel Name**
    [2] Video title

Downloading:
  [1/N] **Channel Name**: Video title
  [2/N] **Channel Name**: Video title

N downloaded. N failed. (N API credits)
```
Channel names are printed in bold (ANSI escape codes) when stderr is a TTY; plain text otherwise.

---

## Data flow

```
YouTube Data API
      │
      ▼
  Fetcher
  ├── fetchMySubscribedChannels() ──► list[Channel]
  ├── fetchRecentVideos(channelID)  ──► list[Video]
  └── fetchVideoDetails(video)      ──► {duration: timedelta}
      │
      ▼
  Manager.filterChannelVideos()
  ├── seen check    (seenChannelVideos dict)
  ├── date filter   (channel + global min/max)
  ├── regex filter  (channel + global include/exclude)
  └── duration filter (API call, last)
      │
      ▼
  Manager._downloadVideo()
  └── multiprocessing.Process → _callYoutubeDL() → yt-dlp
      │
      ▼
  YAMLBuilder.safeDumpManager()
  └── config.yaml  (updated seenChannelVideos + minVideoDate per channel)
```

---

## Design decisions and conventions

**Single YAML file as database.** There is no database. All state — credentials, channel list, per-channel filters, seen video IDs, and per-channel min dates — lives in one YAML file. This keeps the tool self-contained and inspectable.

**`seenChannelVideos` vs `minVideoDate`.** Both are used. `seenChannelVideos` is the definitive "don't re-download" guard; `minVideoDate` is updated per channel after each successful download and acts as the API-level date filter, so the tool fetches progressively fewer old videos over time. They complement each other: `minVideoDate` reduces API calls, `seenChannelVideos` handles edge cases (failed downloads, out-of-order publishing). Each channel's `seenChannelVideos` list is capped at **25 entries** (most recent kept). Because `minVideoDate` advances forward, videos old enough to be evicted from the cap will not be fetched from the API anyway, so the cap does not risk re-downloads in normal operation.

**Filter ordering is intentional.** Filters are applied cheapest-first: seen-check and date/regex are free; duration costs 3 API quota units per video. The duration filter is always last.

**Per-channel settings override or narrow globals.** When a channel setting and a global setting conflict, the more restrictive value wins — implemented by `_compare("max", ...)` for min-bounds and `_compare("min", ...)` for max-bounds.

**Multiprocessing for download timeout.** yt-dlp has no native timeout API. The tool spawns a child process and joins it with a timeout, then kills it. The child returns its result via `multiprocessing.Queue`. The queue `get()` has a 5-second safety timeout in case the process was killed before it could write its result.

**No threading.** Downloads are sequential. One video at a time, with a 10-second sleep between each.

**Channel list is always alphabetically sorted** (by `title.lower()`) in `setChannelList()`. This is cosmetic — it makes the YAML config human-readable.

**YAML key ordering** in `Channel` representer: `title`, `id`, `ignore` first, then remaining keys reverse-alphabetically sorted. This groups related fields visually (e.g. `minVideoDate`/`maxVideoDate` end up adjacent).

**`ignore` flag.** Setting `ignore: true` on a channel in the config file causes it to be skipped during `download-new` without removing it from the channel list. Useful for temporarily pausing a channel.

**`manual-download` bypasses all tracking.** It uses the config only for `downloadDirectory` and `ffmpegLocation`. It does not update `seenChannelVideos` or touch the config file at all.

**All datetimes are UTC-aware.** `convertTime()` ensures every `datetime` in the system carries `tzinfo=datetime.timezone.utc`. Naive datetimes (e.g. loaded from older YAML files that predate this convention) are silently promoted to UTC-aware. This means comparisons between datetimes from different sources (API, YAML, defaults) are always unambiguous.

---

## Test suite

Run: `venv/bin/python -m pytest tests/ -v`. Current state: **30 passing, 1 skipped**.

| File | Covers |
|---|---|
| `tests/test_init.py` | `convertTime()` — all input forms, UTC-awareness asserted |
| `tests/test_items.py` | `Channel` and `Video` — instantiation, string repr, equality |
| `tests/test_fetcher.py` | `Fetcher` — pickle round-trip, all API wrapper methods |
| `tests/test_manager.py` | `Manager` — instantiation, seen-video tracking (incl. 25-entry cap), `filterChannelVideos` (all filter types + short-circuit), `updateChannels`, `downloadNewVideos` (incl. cross-run idempotency and timeout-retry) |
| `tests/test_yamlBuilder.py` | `YAMLBuilder` — Channel/Manager/timedelta round-trips, safe-dump error **and** happy paths |

`test_manager.py` contains a `createManager()` static helper that constructs a `Manager` with `clientSecretsFile=None` (no OAuth flow) and a minimal set of defaults. Tests that need a fake `ytFetcher` assign a simple anonymous class directly to `manager.ytFetcher` after construction.

**Behavioural tests of note:**
- `test_downloadNewVideos_idempotentAcrossRuns` — runs `downloadNewVideos` twice and asserts that previously-seen videos are not re-downloaded on the second run while a newly-published video is. This guards the tool's core promise (don't re-download) end-to-end through the real `filterChannelVideos` + seen-guard + `minVideoDate` logic.
- `test_downloadNewVideos_retriesAfterTimeout` — asserts a download that raises `TimeoutError` once is retried and then succeeds, counted, and marked seen.
- `test_safeDump_happyPathNoBackup` — asserts the common in-place overwrite (no significant size change) creates **no** `.old` backup and reloads to an equivalent `Manager`.

**YAML test isolation:** `test_yamlBuilder.py` uses module-level `dumpWithLocalYAML()` / `loadWithLocalYAML()` helpers that build **local** `SafeLoader` / `SafeDumper` subclasses, and routes the full-`Manager` round-trip through the production `YAMLBuilder.dumpManager` / `loadManager`. This mirrors production and avoids mutating the global `yaml` singletons (earlier versions of these tests registered on the global classes, which leaked state across tests and bypassed the real code path).

`test_createNewManager` remains skipped — it requires mocking the Google OAuth flow, which needs dedicated infrastructure not yet in place.

---

## Dependencies

| Package | Purpose |
|---|---|
| `google-api-python-client` | YouTube Data API v3 client |
| `google-auth-oauthlib` | OAuth 2.0 flow for user authentication |
| `google-auth-httplib2` | HTTP transport for Google auth |
| `PyYAML` | YAML serialisation of config file |
| `yt-dlp` | Video downloading |

FFmpeg is an external binary dependency (not a Python package). Its location is auto-discovered via `shutil.which("ffmpeg")` or can be set explicitly in the config.

---

## Known issues and future work

- **`\d` in regex in `fetcher.py:106`** produces a `SyntaxWarning` in Python 3.12 — the string should be a raw string (`r"^PT(\d..."`) to suppress it. Functionally harmless.
- **`test_createNewManager` is skipped** — testing the `init` subcommand requires mocking the Google OAuth 2.0 flow. No mock infrastructure exists yet.
- **Downloads are always sequential** — one video at a time with a 10-second sleep between each. There is no concurrency. This is simple and safe but slow when many new videos are found.
- **`manual-download` calls `manager.getAPICreditsUsed()` in its log output** but makes no API calls; it will always report 0 credits. (Cosmetic; not currently logged by `manualDownload()` anyway.)
- **`safeDumpManager` writes via a temp file in a separate `tempfile.TemporaryDirectory()`, then `shutil.copy2`s it into place.** When `/tmp` and the config directory are on different filesystems (common), this copy is **not** atomic — a crash mid-copy could leave a truncated config. The size-change and 0-byte guards mitigate but do not eliminate this. Consider writing the temp file in the same directory as the target and using `os.replace()` for a true atomic swap.

### Test coverage gaps

A testing audit measured ~74% line coverage. The well-tested core is filtering, seen/date bookkeeping, the API wrapper, and YAML round-trips. The notable untested areas, in rough priority order:

- **The CLI (`__main__.py`) has 0% coverage.** None of `initialise` / `downloadNew` / `updateChannels` / `manualDownload`, argparse wiring, or the (duplicated) `--quality` string → `VideoQuality` parse-and-raise logic is tested.
- **The real download path is untested.** `_downloadVideo` (multiprocessing spawn, `join(timeout=…)`, `terminate()`/`kill()`, `Queue.get(timeout=5)`), `_callYoutubeDL`, and `_getVideoInfo` have no tests — the `downloadNewVideos` tests stub `_downloadVideo` out. This is the most failure-prone code in the project. Testing it is awkward (fake multiprocessing targets, platform/WSL2 sensitivity), so it is deferred rather than skipped silently.
- **Setter validation branches** on `Manager` and `Channel` (int → `timedelta` conversion, `TypeError` / `NotADirectoryError` / `FileNotFoundError` raises) are largely uncovered. Low real-world risk (these guard against programmer error), so intentionally left as low priority.
- **API quota tracking** (`creditsUsed` / `_countCredits`) has no assertions. Informational only.
