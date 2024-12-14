"""
pip3 install --upgrade google-api-python-client
pip3 install --upgrade google-auth-oauthlib google-auth-httplib2


"""
# re.compile("^.*title=\"([^\"]+)\".*/channel/([A-Z0-9\-\_]{24})", re.MULTILINE | re.IGNORECASE)
import sys
import argparse
import os



# the current and root directories
currentDirectory = os.path.dirname(os.path.realpath(__file__))
rootDirectory    = os.path.dirname(os.path.dirname(currentDirectory))

# CHECK: log file can be created
LOG_FILENAME = os.path.join(currentDirectory, "{}.log".format(os.path.basename(__file__)))
logFileDir = os.path.dirname(LOG_FILENAME)
if not os.path.exists(logFileDir):
  raise FileNotFoundError("log directory does not exist: {}".format(logFileDir))

# CHECK: fetcher is in path
pkgLocation = os.path.join(rootDirectory, "managedYoutubeDL")
if pkgLocation not in sys.path:
  sys.path.insert(0, pkgLocation)

# create a file logger that automatically rotates log files
import logging
logging.getLogger("").setLevel(logging.DEBUG)
from logging.handlers import RotatingFileHandler
fileHandler = RotatingFileHandler(filename=LOG_FILENAME, maxBytes=5000000, backupCount=5, encoding="utf-8")
fileHandler.setLevel(logging.DEBUG)
fileHandler.setFormatter(logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s'))
logging.getLogger("").addHandler(fileHandler)



from managedYoutubeDL.manager import Manager
from managedYoutubeDL import YAMLBuilder




def initialise(**kwargs):
  manager = Manager.createNewManager(
    clientSecretsFileLocation = kwargs.get("clientSecretsFile"),
    configFileLocation        = kwargs.get("configFileLocation"),
  )

  # how many API credits did we use
  logger.info("Used {} API credits".format(manager.getAPICreditsUsed()))

def downloadNew(**kwargs):
  
  # location of configuration file to use
  configFileLocation = kwargs.get("configFileLocation")
  
  # create the manager from the configuration file
  manager = YAMLBuilder.loadManager(configFileLocation)
  
  # video quality
  quality = Manager.VideoQuality(kwargs.get("quality"))
  
  # download new videos
  numDownloaded, numFailed = manager.downloadNewVideos(quality=quality)
  logger.info("{} videos downloaded. {} failed.".format(numDownloaded, numFailed))
  
  # safe dump the manager
  YAMLBuilder.safeDumpManager(manager, configFileLocation, overwrite=True)
  
  # how many API credits did we use
  logger.info("Used {} API credits".format(manager.getAPICreditsUsed()))
  

def updateChannels(**kwargs):
  
  # location of configuration file to use
  configFileLocation = kwargs.get("configFileLocation")
  
  # create the manager from the configuration file
  logger.debug("updateChannels: Creating manager")
  manager = YAMLBuilder.loadManager(configFileLocation)
  
  # update channels
  logger.info("Updating channels")
  numAdded, numRemoved = manager.updateChannels()
  
  # create config file only if the channel list has changed
  if numAdded == numRemoved == 0:
    logger.info("No channels added or removed")
  else:
    logger.info("Added {} channels. Removed {} channels".format(numAdded, numRemoved))
    logger.debug("updateChannels: Creating the config file")
    YAMLBuilder.safeDumpManager(manager, configFileLocation, overwrite=True)
  
  # how many API credits did we use
  logger.info("Used {} API credits".format(manager.getAPICreditsUsed()))


def manualDownload(**kwargs):
  
  # location of configuration file to use
  configFileLocation = kwargs.get("configFileLocation")
  
  # create the manager from the configuration file
  manager = YAMLBuilder.loadManager(configFileLocation)
  
  # urlList
  urlList = kwargs.get("urlList")
  
  # video quality
  try:
    quality_str = kwargs.get("quality")
    quality     = Manager.VideoQuality(quality_str)
  except ValueError:
    raise ValueError(f"Unknown video quality {quality_str}. Supported qualitities: {list(Manager.SUPPORTED_QUALITIES.keys())}")
  
  options = {
    'quiet':                True,
    'ignoreerrors':         True,
    'outtmpl':              os.path.join(manager.downloadDirectory, "%(title)s-%(id)s.%(ext)s"),
    'ffmpeg_location':      manager.ffmpegLocation,
    'merge_output_format': 'mkv',
    
    #'format': 'bestvideo[ext=mp4]+bestaudio[ext=webm]',
    'format': Manager.SUPPORTED_QUALITIES.get(quality, None),
  }
  
  import yt_dlp
  with yt_dlp.YoutubeDL(options) as ydl:
    
    for i, videoURL in enumerate(urlList):
      logger.info("Downloading: {}/{}, {}".format(i+1, len(urlList), videoURL))
      returnCode = ydl.download([videoURL])
      logger.info("Success" if returnCode == 0 else "Problem")
    


main = "here"
if __name__ == "__main__":
  
  #############################################################################
  # Setup arguments
  #############################################################################
  
  # parser
  parser = argparse.ArgumentParser()
  subparsers = parser.add_subparsers(metavar="operation", required=True)
  
  # optional arguments
  parser.add_argument("--verbose", action="store_true", help="turn on verbose mode")
  parser.set_defaults(verbose=False)
  
  
  ##############################
  # fetch and download new videos
  ##############################
  sp = subparsers.add_parser("download-new", help="fetch and download newly added videos",
                             description="Fetch newly added videos.")
  sp.add_argument(metavar="config-file", type=str, dest="configFileLocation",
                  help="location of the configuration file to use")
  sp.set_defaults(func=downloadNew)
  
  # optional arguments
  sp.add_argument("--quality", type=str, help="quality level of videos", default="max")
  
  ##############################
  # initialise
  ##############################
  sp = subparsers.add_parser("init", help="register credentials and create the yaml configuration file",
                             description="Register credentials and create the yaml configuration file.")
  sp.add_argument(metavar="client-secrets-file", type=str, dest="clientSecretsFile",
                  help="location of the json file containing the secret client information")
  sp.add_argument(metavar="config-file", type=str, dest="configFileLocation",
                  help="location to store the new configuration file")
  sp.set_defaults(func=initialise)
  
  
  ##############################
  # update channels
  ##############################
  sp = subparsers.add_parser("update-channels", help="update the current list of channel subscriptions",
                             description="Update the known list of channel subscriptions.")
  sp.add_argument(metavar="config-file", type=str, dest="configFileLocation",
                  help="location of the configuration file to use")
  sp.set_defaults(func=updateChannels)
  
  
  ##############################
  # manual download
  ##############################
  sp = subparsers.add_parser("manual-download", help="download a list of videos",
                             description="Download a list of videos.")
  sp.add_argument(metavar="config-file", type=str, dest="configFileLocation",
                  help="location of the configuration file to use")
  sp.add_argument(metavar="download-list", nargs="+", dest="urlList",
                  help="videos to download")
  sp.set_defaults(func=manualDownload)
  
  # optional arguments
  sp.add_argument("--quality", type=str, help="quality level of video", default="max")
  
  #############################################################################
  # Process arguments
  #############################################################################
  
  # parse the arguments
  args = parser.parse_args()
  
  # Setup console logger
  #  -verbose turns on DEBUG messages
  console = logging.StreamHandler()
  console.setLevel(logging.DEBUG if args.verbose else logging.INFO)
  console.setFormatter(logging.Formatter("%(message)s"))
  logging.getLogger("").addHandler(console)
  logger = logging.getLogger(__name__)
  
  
  #############################################################################
  # Perform operation
  #############################################################################
  args.func(**vars(args))
  sys.exit(0)
