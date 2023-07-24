import logging
logger = logging.getLogger(__name__)

import datetime
import os
import re
import sys
import time
import multiprocessing
from datetime import timedelta

from managedYoutubeDL import Fetcher, YAMLBuilder
from managedYoutubeDL.items import Channel, Video

#import youtube_dl
import yt_dlp

class Manager:
  
  # max time (seconds) to allow for video to download
  DOWNLOAD_TIMEOUT = 60*3
  
  # if download times out, time (seconds) to wait until we try again
  POST_TIMEOUT_WAIT = 60
  
  # time (seconds) to wait between consecutive downloads
  WAIT_BETWEEN_DOWNLOADS = 10
  
  def setClientSecretsFile(self, value):
    self.clientSecretsFile = value
    
  def setPickledCredentials(self, value):
    self.pickledCredentials = value

  def setDownloadDirectory(self, value):
    
    # CHECK: downloadDirectory is valid
    if value not in [None, ""]:
      if not os.path.exists(value):
        raise NotADirectoryError("downloadDirectory does not exist: {}".format(value))
      if not os.path.isdir(value):
        raise NotADirectoryError("downloadDirectory is not a directory: {}".format(value))
      
    self.downloadDirectory = value
  
  def setFFmpegLocation(self, value):
    
    # CHECK: ffmpegLocation is valid
    if value is not None:
      if not os.path.exists(value):
        raise FileNotFoundError("ffmpegLocation does not exist at: {}".format(value))
    self.ffmpegLocation = value
  
  
  def setChannelList(self, value):
    
    # alphabetically sort the channel list
    if value is not None and len(value) > 0:
      value = sorted(value, key=lambda x: x.title.lower())
    self.channelList = value
    
  def setDownloadTimeout(self, value):
    if value is not None:
      if isinstance(value, timedelta):
        self.downloadTimeout = value
      elif isinstance(value, int):
        self.downloadTimeout = timedelta(seconds=value)
      else:
        raise TypeError("downloadTimeout must be either a timedelta or an int")
  
    else:
      self.downloadTimeout = value
    
  
  def setPostTimeoutWait(self, value):
    if value is not None:
      if isinstance(value, timedelta):
        self.postTimeoutWait = value
      elif isinstance(value, int):
        self.postTimeoutWait = timedelta(seconds=value)
      else:
        raise TypeError("postTimeoutWait must be either a timedelta or an int")
  
    else:
      self.postTimeoutWait = value
    
    
  def setGlobalMinVideoDate(self, value):
    from managedYoutubeDL import convertTime
    self.globalMinVideoDate = convertTime(value)
    
  def setGlobalMaxVideoDate(self, value):
    from managedYoutubeDL import convertTime
    self.globalMaxVideoDate = convertTime(value)

  def setSeenChannelVideos(self, value):
    self.seenChannelVideos = value

  def setGlobalIncludeFilter(self, value):
    self.globalIncludeFilter = value

  def setGlobalExcludeFilter(self, value):
    self.globalExcludeFilter = value

  def setGlobalMinVideoLength(self, value):
    
    if value is not None:
      if isinstance(value, timedelta):
        self.globalMinVideoLength = value
      elif isinstance(value, int):
        self.globalMinVideoLength = timedelta(seconds=value)
      else:
        raise TypeError("globalMinVideoLength must be either a timedelta or an int")
  
    else:
      self.globalMaxVideoLength = value
    
  def setGlobalMaxVideoLength(self, value):
    
    if value is not None:
      if isinstance(value, timedelta):
        self.globalMaxVideoLength = value
      elif isinstance(value, int):
        self.globalMaxVideoLength = timedelta(seconds=value)
      else:
        raise TypeError("globalMaxVideoLength must be either a timedelta or an int")
    
    else:
      self.globalMaxVideoLength = value


  @staticmethod
  def _getFFmpegInPath():
    """
    # Return the location of FFmpeg by searching the PATH
    :return:
    """
    for pathDir in sys.path:
      if os.path.isdir(pathDir) and os.path.exists(pathDir):
        for possibleName in ["ffmpeg", "ffmpeg.exe"]:
          possiblePath = os.path.join(pathDir, possibleName)
          if os.path.exists(possiblePath):
            return possiblePath
    return None
  
  
  @staticmethod
  def createNewManager(clientSecretsFileLocation: str, configFileLocation: str):
    """
    # Given a client-secrets file, create a new Manager and store it in
    # a YAML config file at <configFileLocation>
    #
    :param clientSecretsFileLocation:
    :param configFileLocation:
    :return:
    """
  
    # CHECK: client secrets file exists
    if not os.path.exists(clientSecretsFileLocation):
      raise FileNotFoundError("client secrets file not found at {}".format(clientSecretsFileLocation))
    
    # CHECK: configFileLocation doesn't exist
    if os.path.exists(configFileLocation):
      raise FileExistsError("config file already exists at {}".format(configFileLocation))
    
    # get credentials
    logger.debug("createNewManager: Fetching credentials")
    pickledCredentials = Fetcher.fetchCredentials(clientSecretsFileLocation)

    # create blank Manager
    logger.debug("createNewManager: Creating a blank Manager")
    manager = Manager(
      clientSecretsFile  = clientSecretsFileLocation,
      pickledCredentials = pickledCredentials,
    )
    
    # fetch channels
    logger.debug("createNewManager: Updating channels")
    manager.updateChannels()
    
    # create config file
    logger.debug("createNewManager: Creating the config file")
    YAMLBuilder.dumpManager(manager, configFileLocation)
    if not os.path.exists(configFileLocation):
      logger.error("ERROR: Config file was NOT created")
    
    # return the newly created manager
    return manager
  
  
  def __init__(self, **kwargs):
    self.clientSecretsFile    = None
    self.pickledCredentials   = None
    self.downloadDirectory    = None
    self.ffmpegLocation       = None
    self.channelList          = None
    self.globalMinVideoDate   = None
    self.globalMaxVideoDate   = None
    self.seenChannelVideos    = None
    self.globalIncludeFilter  = None
    self.globalExcludeFilter  = None
    self.globalMinVideoLength = None
    self.globalMaxVideoLength = None
    
    self.downloadTimeout = None
    self.postTimeoutWait = None
    

    
    # youtube setup
    self.setClientSecretsFile(kwargs.get("clientSecretsFile", None))
    self.setPickledCredentials(kwargs.get("pickledCredentials", None))
    
    # download directory for videos
    self.setDownloadDirectory(kwargs.get("downloadDirectory", ""))
    
    # location of ffmpeg
    self.setFFmpegLocation(kwargs.get("ffmpegLocation", Manager._getFFmpegInPath()))
    
    # subscribed channel list
    self.setChannelList(kwargs.get("channelList", []))
    
    # seen videos
    self.setSeenChannelVideos(kwargs.get("seenChannelVideos", {}))
    
    # video date filters
    self.setGlobalMinVideoDate(kwargs.get("globalMinVideoDate", datetime.datetime.utcfromtimestamp(0)))
    self.setGlobalMaxVideoDate(kwargs.get("globalMaxVideoDate", datetime.datetime.utcfromtimestamp(2**32)))
  
    # video title filters
    self.setGlobalIncludeFilter(kwargs.get("globalIncludeFilter", None))
    self.setGlobalExcludeFilter(kwargs.get("globalExcludeFilter", None))

    # video length filters
    self.setGlobalMinVideoLength(kwargs.get("globalMinVideoLength", timedelta(seconds=0)))
    self.setGlobalMaxVideoLength(kwargs.get("globalMaxVideoLength", None))
    
    # download options
    self.setDownloadTimeout(kwargs.get("downloadTimeout", Manager.DOWNLOAD_TIMEOUT))
    self.setPostTimeoutWait(kwargs.get("postTimeoutWait", Manager.POST_TIMEOUT_WAIT))
    
    
    # CHECK: no extra attributes were passed
    extraKeys = [x for x in kwargs if x not in self.__dict__.keys()]
    if len(extraKeys) > 0:
      raise AttributeError("unknown attribute(s): {}".format(extraKeys))

    # load the YouTube fetcher
    if self.clientSecretsFile is not None:
      self.ytFetcher = Fetcher(
        clientSecretsFile  = self.clientSecretsFile,
        pickledCredentials = self.pickledCredentials
      )
    else:
      self.ytFetcher = None
    
    
  def getAPICreditsUsed(self):
    return 0 if self.ytFetcher is None else self.ytFetcher.creditsUsed

  def _isolateIgnoreChannels(self):
    """
    # Return a separate list of channels to ignore, and not
    :return:
    """
    
    channelList = []
    ignoreChannelList = []
    for channel in self.channelList:
      if channel.ignore:
        ignoreChannelList.append(channel)
      else:
        channelList.append(channel)
        
    return ignoreChannelList, channelList
  
    
  
  def _downloadVideo(self, channel: Channel, video: Video, timeout: timedelta=None) -> bool:
    """
    # Download the <channel>'s <video> and report on whether it was a success
    #
    :param channel:
    :param video:
    :return:
    """
    
    """
    from subprocess import Popen, PIPE
    from threading import Timer
    
    def run(cmd, timeout_sec):
        proc = Popen(cmd.split(), stdout=PIPE, stderr=PIPE)
        timer = Timer(timeout_sec, proc.kill)
        try:
            timer.start()
            stdout, stderr = proc.communicate()
        finally:
            timer.cancel()
    
    run("sleep 1", 5)
    run("sleep 5", 1)
    """
    
    # throw timeout error
    #  -have timeout argument=None
    
    # OS-friendly channel name
    channelName = "".join([s for s in channel.title if s.isalpha() or s.isdigit()])
  
    # assemble the video's name and download location
    videoName = "{}--%(title)s-%(id)s.%(ext)s".format(channelName)
    videoLoc = os.path.join(self.downloadDirectory, videoName)
  
    # set the basic options
    options = {
      "quiet":        True,
      "ignoreerrors": True,
      "outtmpl":      videoLoc
    }
  
    # if ffmpeg is defined we can download the highest quality video and audio
    # and combine them together
    # --format bestvideo[ext=mp4]+bestaudio[ext=webm] --merge_output_format mkv
    if self.ffmpegLocation is not None:
      options["ffmpeg_location"] = self.ffmpegLocation
      options["format"] = "bestvideo[ext=mp4]+bestaudio[ext=webm]"
      options["merge_output_format"] = "mkv"
  
    # otherwise, use highest quality, mixed audio/video file
    else:
      logger.warning("_download: FFmpeg not in path. Download may not be the highest possible quality")
      options["format"] = "bestaudio/best"

    
    
    returnQueue = multiprocessing.Queue()
    proc = multiprocessing.Process(
      target = Manager._callYoutubeDL,
      args   = (returnQueue, options, [self.ytFetcher.assembleVideoURL(video.id)])
    )
    proc.start()
    proc.join(timeout=timeout.total_seconds())
    
    if proc.is_alive():
      proc.terminate()
      proc.kill()
      raise TimeoutError()
    return returnQueue.get()
    
    # download the video and return whether we were successful
    #return Manager._callYoutubeDL(options, [self.ytFetcher.assembleVideoURL(video.id)])
    
    #with youtube_dl.YoutubeDL(options) as ydl:
    #  returnCode = ydl.download([self.ytFetcher.assembleVideoURL(video.id)])
    #return returnCode == 0
  
  
  @staticmethod
  def _getVideoInfo(options: dict, urlList: list) -> list:
    """
    # For each video in <urlList> return a dictionary of video info
    #
    :param options:
    :param urlList:
    :return:
    """
    
    # list of dictionaries to return
    infoList = []
    
    # get a yt-dlp object
    with yt_dlp.YoutubeDL(options) as ydl:
    
      # for each video url
      for url in urlList:
        
        # create a blank info to return
        info = {
          "videoSize":   -1,
          "audioSize":   -1,
          "height":      -1,
          "width":       -1,
          "duration":    -1,
          "viewCount":   -1,
          "description": None,
          "tags":        []
        }
        
        # get the info and extract the details we want
        try:
          urlInfo = ydl.extract_info(url, download=False)
          
          # extract the info we are interested in
          info["videoSize"]   = urlInfo["requested_formats"][0]["filesize"]
          info["audioSize"]   = urlInfo["requested_formats"][1]["filesize"]
          info["height"]      = urlInfo["requested_formats"][0]["height"]
          info["width"]       = urlInfo["requested_formats"][0]["width"]
          info["duration"]    = urlInfo["duration"]
          info["viewCount"]   = urlInfo["view_count"]
          info["description"] = urlInfo["description"]
          info["tags"]        = urlInfo["tags"]

        except Exception as err:
          logger.error("_getVideoInfo: Couldn't get info for {}: {}\n{}".format(url, err, info))

        infoList.append(info)
    
    
    return infoList
  
  @staticmethod
  def _callYoutubeDL(returnQueue: multiprocessing.Queue, options: dict, urlList: list):
    
    # download the video and return whether we were successful
    #with youtube_dl.YoutubeDL(options) as ydl:
    with yt_dlp.YoutubeDL(options) as ydl:
      
      try:
        #logger.info(urlList)
        info = ydl.extract_info(urlList[0], download=False)
        logger.info("File size test result: {}".format(list(info["requested_formats"][0].keys())))
        
        # requested_formats
        #   -filesize, height, width
        # duration, view_count, description, tags,
        videoInfo = info["requested_formats"][0]
        audioInfo = info["requested_formats"][1]
        
        #
        logger.info(info["filesize_approx"] / (1024 * 1024))
        ##logger.info(videoInfo["filesize"]/(1024*1024))
      except Exception as err:
        logger.info("File size test failed: {}".format(err))

      returnCode = ydl.download(urlList)
    
    
    returnQueue.put(returnCode == 0)
    

  def addSeenVideo(self, channel: Channel, video: Video):
    """
    # Add the <video>'s ID to the list of seen videos for <channel>
    #
    :param channel:
    :param video:
    :return:
    """
    
    currentSeenVideos = self.seenChannelVideos.get(channel.id, [])
    if video.id not in currentSeenVideos:
      currentSeenVideos.append(video.id)
      self.seenChannelVideos[channel.id] = currentSeenVideos
      
      
  def haveSeenVideo(self, channel: Channel, video: Video) -> bool:
    """
    # Have we seen this <channel>'s <video> before
    #
    :param channel:
    :param video:
    :return:
    """
    return video.id in self.seenChannelVideos.get(channel.id, [])
  
  
  def downloadNewVideos(self):
    """
    # Iterate over our list of subscribed channels, fetching new
    # videos, filtering them by channel-specific and global filters, then
    # downloading them
    #
    :return:
    """
    
    downloadResults = {
      "Downloaded": 0,
      "Failed":     0
    }
    
    # separate to-ignore and to-download channels
    ignoreChannelList, channelList = self._isolateIgnoreChannels()
    logger.debug("downloadNewVideos: Ignoring {} channel(s)".format(len(ignoreChannelList)))
    logger.debug("downloadNewVideos: Ignoring: " + ", ".join([x.title for x in ignoreChannelList]))
    
    
    # for each subscribed channel, get the recent channel videos
    channelVideos  = []
    lenChannelList = len(channelList)
    if lenChannelList == 1: logger.info("Checking 1 channel")
    else:                   logger.info("Checking {} channels".format(len(channelList)))
    
    for channel in channelList:
      logger.debug("downloadNewVideos: Checking channel {}".format(channel.title))
      
      # get the recent channel videos
      videoList = self.ytFetcher.fetchRecentVideos(channel.id)
      logger.debug("downloadNewVideos: Found {} recent videos".format(len(videoList)))
      
      # apply global and per-channel filters
      videoList = self.filterChannelVideos(channel, videoList)
      logger.debug("downloadNewVideos: {} videos remain after channel filtering".format(len(videoList)))
    
      # add the videos to the master list
      if len(videoList) > 0:
        channelVideos.append((channel, videoList))
    
    
    # log total number of videos found
    if len(channelVideos) == 0:
      numVideos = 0
    else:
      numVideos = sum([len(videoList) for _, videoList in channelVideos])
    if numVideos == 1: logger.info("Found 1 new video")
    else:              logger.info("Found {} new videos".format(numVideos))
    
    # print a list of the video titles
    #  -NOTE: this is general copy of the youtube-dl format in _downloadVideo()
    #         so may not 100% match the download file name
    for channel, videoList in channelVideos:
      logger.info("{}".format(channel.title))
      for video in videoList:
        logger.info("--{}-{}".format(video.title, video.id))
    
    
    # for each channel's videos:
    for channel, videoList in channelVideos:
      logger.info("Downloading from channel: {}".format(channel.title))
      
      for video in videoList:
        logger.info("Downloading video: {}".format(video.title))

        while True:
          try:
            
            # if it downloaded successfully
            if self._downloadVideo(channel, video, timeout=self.downloadTimeout):
              downloadResults["Downloaded"] += 1
              logger.debug("downloadNewVideos: Downloaded successfully")
            
              # add to "seen" list
              self.addSeenVideo(channel=channel, video=video)
              
              # update this channel's min video date to our latest video
              if channel.minVideoDate is None or video.publishedAt > channel.minVideoDate:
                channel.setMinVideoDate(video.publishedAt)
                logger.debug("downloadNewVideos: Min video date for channel {} is now {}"
                             .format(channel.title, video.publishedAt))
            
            # else, download unsuccessful
            else:
              downloadResults["Failed"] += 1
              logger.error("downloadNewVideos: Could not download video: title: {}, id: {}"
                              .format(video.title, video.id))

            # wait between consecutive downloads
            time.sleep(Manager.WAIT_BETWEEN_DOWNLOADS)
            
            # no timeout
            break
          
          except TimeoutError:
            waitingTime = 0 if self.postTimeoutWait is None else self.postTimeoutWait.total_seconds()
            wakeTime = datetime.datetime.now() + datetime.timedelta(seconds=waitingTime)
            logger.error("Download timed out. Waiting {}s (until {})"
                         .format(waitingTime, wakeTime))
            time.sleep(waitingTime)
          
    
    
    
    # return how we did overall
    return downloadResults["Downloaded"], downloadResults["Failed"]
  
  
  def filterChannelVideos(self, channel: Channel, videoList: list):
    """
    # Apply global and channel-specific filters to all of thet videos in
    # <channel>'s <videoList>
    #
    :param channel:
    :param videoList:
    :return:
    """
    
    # compare two values of the same type, where one or more may be None
    def _compare(comparison, value1, value2):
      if   value1 is None: return value2
      elif value2 is None: return value1
      else:
        return {
          "max": max,
          "min": min,
        }.get(comparison)(value1, value2)
    
    logger.debug("filterChannelVideos: Filtering channel: {}".format(channel.title))
  
    # filter each channel video
    approvedVideos = []
    for video in videoList:
      logger.debug("filterChannelVideos: Filtering video: {}".format(video.title))

      #########################################################################
      # CHECK: item is a video
      #########################################################################
      if not isinstance(video, Video):
        raise TypeError("{} is not a Video".format(video))
      
      
      #########################################################################
      # FILTER: not seen this video before
      #########################################################################
      if self.haveSeenVideo(channel, video):
        logger.debug("filterChannelVideos: FILTERED OUT: seen before")
        continue
        
        
      #########################################################################
      # FILTER: video min/max date
      #########################################################################
      
      minVideoDate = _compare("max", channel.minVideoDate, self.globalMinVideoDate)
      if not (minVideoDate is None or video.publishedAt >= minVideoDate):
        logger.debug("filterChannelVideos: FILTERED OUT: published before min date")
        continue
      maxVideoDate = _compare("min", channel.maxVideoDate, self.globalMaxVideoDate)
      if not (maxVideoDate is None or video.publishedAt <= maxVideoDate):
        logger.debug("filterChannelVideos: FILTERED OUT: published after max date")
        continue
      
        
      #########################################################################
      # FILTER: regex video title inclusion
      #########################################################################
      
      # channel filter
      if channel.includeFilter:
        includePattern = re.compile(channel.includeFilter, re.MULTILINE | re.IGNORECASE)
        if len(includePattern.findall(video.title)) == 0:
          logger.debug("filterChannelVideos: FILTERED OUT: didn't match include filter")
          continue
          
      # global filter
      if self.globalIncludeFilter:
        includePattern = re.compile(self.globalIncludeFilter, re.MULTILINE | re.IGNORECASE)
        if len(includePattern.findall(video.title)) == 0:
          logger.debug("filterChannelVideos: FILTERED OUT: didn't match include filter")
          continue
          
          
      #########################################################################
      # FILTER: regex video title exclusion
      #########################################################################

      # channel filter
      if channel.excludeFilter:
        excludePattern = re.compile(channel.excludeFilter, re.MULTILINE | re.IGNORECASE)
        if len(excludePattern.findall(video.title)) > 0:
          logger.debug("filterChannelVideos: FILTERED OUT: matched exclude filter")
          continue

      # global filter
      if self.globalExcludeFilter:
        excludePattern = re.compile(self.globalExcludeFilter, re.MULTILINE | re.IGNORECASE)
        if len(excludePattern.findall(video.title)) > 0:
          logger.debug("filterChannelVideos: FILTERED OUT: matched exclude filter")
          continue
          
          
      #########################################################################
      # FILTER: video duration
      #  -involves an API call, so is done last
      #########################################################################
      minVideoLength = _compare("max", channel.minVideoLength, self.globalMinVideoLength)
      maxVideoLength = _compare("min", channel.maxVideoLength, self.globalMaxVideoLength)
      
      if minVideoLength or maxVideoLength:
      
        # get this video's duration
        videoDetails = self.ytFetcher.fetchVideoDetails(video)
        if videoDetails is None or videoDetails["duration"] is None:
          logger.error("filterChannelVideos: unable to determine duration of video: {}"
                       .format(video.title))
          continue
      
        # reject this video if it's too short or too long
        if minVideoLength and videoDetails["duration"] < minVideoLength:
          logger.debug("filterChannelVideos: FILTERED OUT: video length too short ({} < {})"
                       .format(videoDetails["duration"], minVideoLength))
          continue
        if maxVideoLength and videoDetails["duration"] > maxVideoLength:
          logger.debug("filterChannelVideos: FILTERED OUT: video length too long ({} > {})"
                       .format(videoDetails["duration"], maxVideoLength))
          continue
    
    
      # this video is approved
      approvedVideos.append(video)
    
    
    # return this channel's approved videos
    return approvedVideos
  
  
  def updateChannels(self):
    """
    # Fetch the currently subscribed channels for the user, adding new
    # channels to our list of known channels, and removing old ones
    #
    :return:
    """
  
    # load the existing channel list
    channelList = [] + self.channelList
    
    # how many channels do we know about
    numKnownChannels = len(channelList)
    logger.debug("updateChannels: Found {} channels in the current channel list".format(numKnownChannels))
  
    # fetch currently subscribed channels
    currentChannels = self.ytFetcher.fetchMySubscribedChannels()
    
    # for each of the CURRENTLY SUBSCRIBED channels
    #  -add it to the channel list if it's not already there
    numAdded = 0
    for channel in currentChannels:
      if channel not in channelList:
        logger.debug("updateChannels: Adding channel: {}".format(channel.title))
        numAdded += 1
        channelList.append(channel)
    logger.debug("updateChannels: Found {} new channels".format(numAdded))
    
    # for each EXISTING channel
    #  -remove it from the list if it's not a current channel
    numKnownChannels = len(channelList)
    channelList      = list(filter(lambda _ch: _ch in currentChannels, channelList))
    numRemoved       = numKnownChannels - len(channelList)
    logger.debug("updateChannels: Removed {} old channels".format(numRemoved))

    # store the channel list
    self.setChannelList(channelList)
    
    return numAdded, numRemoved
  