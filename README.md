### Managed YouTube Downloader

<br>

[yt-dlp](https://github.com/yt-dlp/yt-dlp) (previously [youtube-dl](https://github.com/ytdl-org/youtube-dl)) is very good for downloading YouTube videos, but deciding which videos to download is tricky to automate. This download manager checks your YouTube channel subscriptions and downloads videos based on the criteria you set.

All configuration is done using YAML, and can be set for individual channels or globally.

Reasons it's interesting:

1. Uses the YouTube Data API (with OAuth 2.0 credentials)
2. Represents and constructs (dumps and loads) custom classes in YAML
3. Uses YAML as a way to get and set properties of a program
4. Contains a quick how-to guide for setting up your own app's OAuth 2.0 credentials with Google. If you think this shouldn't be too difficult or strange, boy do I have a few wasted hours of my life to share with you...

<br>

---
### Installation

Install the pyhon project requirements like normal

```bash
pip3 install -r requirements.txt
```

#### Credentials

Obtaining the YouTube API credentials is an awkward process (described by Google [here](https://developers.google.com/identity/protocols/oauth2/)), but I've tried to simplify it below. This app just needs read-only access to the channels you're subscribed to (which can be seen in the _fetcher.py_ file), but the process is awkward all the same.

__Enable the YouTube Data API for your account__

Log in to to your [Google API console](https://console.developers.google.com/) and enable the [YouTube Data API](https://console.developers.google.com/apis/api/youtube.googleapis.com).


__Obtain OAuth 2.0 credentials__

You need to set up your [OAuth consent screen](https://console.developers.google.com/apis/credentials/consent). That's right, you have to create a consent screen for yourself... I just called my version "App", and clicked save, but you can go nuts if you'd like.

Go to the [credentials](https://console.developers.google.com/apis/credentials) section of the API console, click the _Create Credentials_ button and choose _OAuth Client ID_. Make it a _Desktop app_ and give it a name.
 
Back on the credentials screen, you can download the json file containing the client secrets. Keep this somewhere safe.

<br>

---
### Operations

#### Initialisation

Create the YAML config file using the command:
```bash
python3 managedYoutubeDL init /path/to/secrets.json config.yaml
```

where _/path/to/secrets.json_ is the client-secrets file obtained in the previous step, and _config.yaml_ is the name you want to call your YAML config file.

Google will display a link to go to in order to authorise the application. Paste the code into the console, and you're done forever with authorisation. The manager will get a list of your channel subscriptions and create your YAML configuration file.


#### Download new videos

To process the _config.yaml_ file and download the new videos in your subscribed channels, run:
```bash
python3 managedYoutubeDL download-new config.yaml
```

#### Update channel list

If your subscription list has changed, you can add new channels and remove old ones from _config.yaml_ using:
```bash
python3 managedYoutubeDL update-channels config.yaml
```

#### Manual video download

To download one or more YouTube videos directly:

```bash
python3 managedYoutubeDL manual-download config.yaml "videoURL1 videoURL2 videoURL3"
```

where the *videoURL*s are the direct links to the YouTube videos. Note, this command does **not** use the YouTube API, and therefore does not cost API credits.

<br>

---
### Configuring your download preferences

An example YAML configuration file is shown here:
```
!Manager
clientSecretsFile: /path/to/secrets.json
downloadDirectory: /path/to/download/directory
ffmpegLocation: /path/to/ffmpeg
pickledCredentials: <LONG ASCII STRING>
globalMinVideoDate: 2020-06-01 12:00:00
globalMaxVideoDate: null
globalIncludeFilter: null
globalExcludeFilter: null
globalMaxVideoLength: !timedelta '7200s'
globalMinVideoLength: !timedelta '60s'
channelList:
- !Channel
  title: Fermilab
  id: UCD5B6VoXv41fJ-IW8Wrhz9A
  ignore: false
  publishedAt: 2019-06-17 02:36:07.310000
  excludeFilter: null
  includeFilter: null
  minVideoDate: null
  maxVideoDate: null
  minVideoLength: !timedelta '0s'
  maxVideoLength: null
seenChannelVideos: {}
```

General properties, such as _downloadDirectory_, are listed at the top. The _clientSecretsFile_ and _pickledCredentials_ entries are set at initialisation, so you don't need to worry about them.

#### Filters

There are global filters, applied to all videos, and local filters that are applied to each channel individually. The _minVideoDate_ of each channel is automatically updated to reflect the past videos that have been downloaded.

__regex include__:

- only download videos whose title contain at least one match to the regular expression __X__

__regex exclude__:

- only download videos whose title contain no matches to the regular expression __X__


__minimum date__: 

- only download videos published on or after __date__

__minimum video length__: 

- only download videos that are at least __S__ seconds long

__maximum video length__: 

- only download videos with a length no longer than __S__ seconds

Note: All regular expressions have the _MULTILINE_ and _IGNORECASE_ flags set.


#### Video conversion

YouTube's highest quality video and audio are often stored separately, and so yt-dlp requires [FFmpeg](https://ffmpeg.org/download.html) to combine them together. If you don't already have it, you can download FFmpeg via the link.

Setting your configuration file's _ffmpegLocation_ property to the location of FFmpeg on your system, or if the location FFmpeg is already in your PATH, will allow yt-dlp to download videos at the highest possible quality.
