import logging
logger = logging.getLogger(__name__)

import os
import re
import math
import pickle
import base64
from datetime import timedelta

import google_auth_oauthlib.flow
import googleapiclient.discovery
import googleapiclient.errors


class Fetcher:
  API_SERVICE_NAME = "youtube"
  API_VERSION      = "v3"
  SCOPES           = ["https://www.googleapis.com/auth/youtube.readonly"]

  VIDEO_URL_PREFIX = "https://www.youtube.com/watch?v="
  
  @staticmethod
  def _parseSubscriptions(data: dict) -> list:
    """
    # Parse the dictionary of information returned from requesting the
    # channels we're subscribed to
    #
    :param data:
    :return:
    """
    from managedYoutubeDL.items import Channel
    
    # channels are given as items in a list
    channelList = []
    for item in data.get("items", []):
    
      # if this is a subscription item
      if item.get("kind", None) == "youtube#subscription":
        
        # create a Channel object, and add it to the channel list
        snippet = item.get("snippet", {})
        channelList.append(
          Channel(
            title       = snippet.get("title", None),
            publishedAt = snippet.get("publishedAt", None),
            id          = snippet.get("resourceId", {}).get("channelId", None),
          ))
  
    return channelList
  
  
  @staticmethod
  def _parsePlaylistVideos(data: dict) -> list:
    """
    # Parse a dictionary returned from requesting the items in a playlist
    #
    :param data:
    :return:
    """
    from managedYoutubeDL.items import Video
    
    # videos are stored as a list of items
    videoList = []
    for item in data.get("items", []):
    
      # if this item is a video
      if item.get("kind", None) == "youtube#playlistItem":
        
        # assemble video information
        snippet = item.get("snippet", {})
        videoList.append(
          Video(
            id           = snippet.get("resourceId", {}).get("videoId", None),
            publishedAt  = snippet.get("publishedAt", None),
            title        = snippet.get("title", None),
            thumbnailURL = snippet.get("thumbnails", {}).get("high", {}).get("url", None),
          ))
  
    return videoList


  @staticmethod
  def _convertVideoDuration(durationStr: str):
    """
    # Convert the YouTube string describing a video's duration into a timedelta
    #
    :param durationStr:
    :return:
    """
    
    # possible formats:
    """
    PT1H12M29S
    PT5M38S
    PT5M
    PT56M1S
    P0D
    """
  
    # video is live
    if durationStr == "P0D":
      return None
    
    # use a regular expression to separate out any hour, minute and second components
    pat = re.compile("^PT(\d{1,2}H)?(\d{1,2}M)?(\d{1,2}S)?", re.MULTILINE | re.IGNORECASE)
    results = pat.findall(durationStr)
    if len(results) == 1 and results[0] != ("", "", ""):
      
      # construct the timedelta from the hour, minute and second results
      return timedelta(
        hours   = int(results[0][0][:-1]) if results[0][0] else 0,
        minutes = int(results[0][1][:-1]) if results[0][1] else 0,
        seconds = int(results[0][2][:-1]) if results[0][2] else 0,
      )
  
    return None
  
  
  @staticmethod
  def fetchCredentials(clientSecretsFile: str):
    """
    # Ask the user to authorise this applpication to access their person data
    #  -requires user interaction on the command line
    #
    :param clientSecretsFile:
    :return:
    """
  
    # CHECK: clientSecretsFile file exists
    if not os.path.exists(clientSecretsFile):
      raise FileNotFoundError("client secrets file not found at {}".format(clientSecretsFile))
  
    # create a flow and use it to get credentials
    #  -requires human interaction
    logger.info("Fetching credentials:")
    flow = google_auth_oauthlib.flow.InstalledAppFlow.from_client_secrets_file(
      clientSecretsFile, Fetcher.SCOPES)
    credentials = flow.run_console()
    
    # pickle the credentials into a string and return them
    return Fetcher._pickleObject(credentials)

  
  @staticmethod
  def _pickleObject(credentialsObj):
    """
    # Pickle an object into a base64 string that can be stored in a YAML file
    #
    :param credentialsObj:
    :return:
    """
    return base64.b64encode(pickle.dumps(credentialsObj)).decode("utf-8")

  @staticmethod
  def _unpickleObject(credentialsStr):
    """
    # Unpickle a string into its original object
    #
    :param credentialsStr:
    :return:
    """
    return pickle.loads(base64.b64decode(credentialsStr.encode("utf-8")))
  
  @staticmethod
  def assembleVideoURL(videoID: str):
    """
    # Return the URL link to a youtube video based on its ID
    #
    :param videoID:
    :return:
    """
    return Fetcher.VIDEO_URL_PREFIX + videoID
  
  
  def __init__(self, clientSecretsFile, pickledCredentials):
    
    # Disable OAuthlib's HTTPS verification when running locally.
    # *DO NOT* leave this option enabled in production.
    # os.environ["OAUTHLIB_INSECURE_TRANSPORT"] = "1"
    
    # CHECK: clientSecretsFile file exists
    if not os.path.exists(clientSecretsFile):
      raise FileNotFoundError("client secrets file not found at {}".format(clientSecretsFile))
    
    # unpickle and store the credentials
    if pickledCredentials is None:
      raise ValueError("pickledCredentials cannot be None")
    self.credentials = Fetcher._unpickleObject(pickledCredentials)
    
    self.clientSecretsFile = clientSecretsFile
    
    # keep track of how many requests we make and their cost
    self.creditsUsed = 0
    self.creditCost  = {
      "channels.list.contentDetails": 3,
      "playlistItems.list.snippet":   3,
      "subscriptions.list.snippet":   3,
      "videos.list.contentDetails":   3,
    }
    
    # create the youtube client
    self.youtubeClient = googleapiclient.discovery.build(
                           Fetcher.API_SERVICE_NAME,
                           Fetcher.API_VERSION,
                           credentials     = self.credentials,
                           cache_discovery = False,
                         )
  
  
  def _countCredits(self, requestType: str):
    """
    # Keep track of the quota cost of each request we make
    #
    :param requestType:
    :return:
    """
    cost = self.creditCost.get(requestType, None)
    if cost is None:
      raise ValueError("unknown request type {}".format(requestType))
    self.creditsUsed += cost
  
  
  def fetchMySubscribedChannels(self, maxResultsPerPage: int=50):
    """
    # Return a list of all the channels I'm subscribed to
    #
    :param maxResultsPerPage:
    :return:
    """
    
    # results per page
    if not (1 <= maxResultsPerPage <= 50):
      raise ValueError("maxResultsPerPage must be [1-50]")
    
    
    # how many times, on average, we try to fetch new results from each page
    maxNextPageAttemptMultiplier = 10
    
    # make a request for my subscriptions
    def _requestMySubscriptions(pageToken=None):
      self._countCredits("subscriptions.list.snippet")
      return self.youtubeClient.subscriptions().list(
        part       = "snippet",
        mine       = True,
        maxResults = maxResultsPerPage,
        pageToken  = pageToken,
        order      = "alphabetical"
      ).execute()
      
    
    
    
    # get the first page of channels I'm subscribed to
    logger.debug("fetchMySubscriptions: Getting first page")
    data      = _requestMySubscriptions()
    channList = Fetcher._parseSubscriptions(data)
    logger.debug("fetchMySubscriptions: Got {} channels".format(len(channList)))
    
    # if there are other pages
    nextPageToken = data.get("nextPageToken", None)
    if nextPageToken is not None:
      totalChannels = data.get("pageInfo", {}).get("totalResults", 1)
      
      # as "next" pages seem to return results from previous pages as well, we
      # will need to fetch the next page more times
      #  -max attempts = expected * <maxNextPageAttemptMultiplier>
      attempt = 0
      maxAttempts = (int(math.ceil(totalChannels / maxResultsPerPage)) - 1) * maxNextPageAttemptMultiplier
      
      # iterate over the remaining pages and get the subscriptions
      logger.debug("fetchMySubscriptions: Max next-page attempts: {}".format(maxAttempts))
      while len(channList) < totalChannels and attempt < maxAttempts:
        attempt += 1
        
        # get the next page of channels
        logger.debug("fetchMySubscriptions: ({}/{} attempts) getting next page".format(attempt, maxAttempts))
        data          = _requestMySubscriptions(pageToken=nextPageToken)
        pageChanns    = Fetcher._parseSubscriptions(data)
        nextPageToken = data.get("nextPageToken", None)
        logger.debug("fetchMySubscriptions: Got {} channels".format(len(pageChanns)))
        
        
        # for each channel on this page, if it hasn't been seen before, add it
        for item in pageChanns:
          if item not in channList:
            channList.append(item)
        logger.debug("fetchMySubscriptions: Channels count now {}/{}".format(len(channList), totalChannels))
    
    
      # CHECK: we got all the channels
      if len(channList) != totalChannels:
        msg  = "Could only fetch {}/{} channels due to youtube's strange paging. "\
          .format(len(channList), totalChannels)
        msg += "Try fetching again and see if that works, or increase this method's"
        msg += " <maxNextPageAttemptMultiplier> value to increase the number of attempts per page."
        msg += "\nCurrently, maxNextPageAttemptMultiplier = {}".format(maxNextPageAttemptMultiplier)
        logger.error(msg)
        raise SystemError(msg)
    
    
    return channList
  
  
  def fetchVideoDetails(self, video):
    """
    # Request details from youtube about a specific video
    #
    :param video:
    :return:
    """
    
    # default response
    details = {
      "duration": None
    }
    
    # get the video info
    logger.debug("fetchVideoDetails: Getting content details for video ID {}".format(video.id))
    self._countCredits("videos.list.contentDetails")
    request = self.youtubeClient.videos().list(
      part = "contentDetails",
      id   = video.id,
    )
    videosResp = request.execute()
    
    # CHECK: have items in the results
    items = videosResp.get("items", [])
    if len(items) != 1:
      logger.error("fetchVideoDetails: Expected 1 result, but got {}".format(len(items)))
      return details
    
    # get the video duration
    duration = items[0].get("contentDetails", {}).get("duration", None)

    # convert the duration into a timedelta
    if duration is not None:
      details["duration"] = self._convertVideoDuration(duration)
      
    return details
  
  

  
  
  def fetchRecentVideos(self, channelID, maxResults=10):
    """
    # Return a list of recent videos belonging to this channel
    #
    :param channelID:
    :param maxResults:
    :return:
    """
    
    # get the channel info
    logger.debug("fetchRecentVideos: getting content details for channel ID {}".format(channelID))
    self._countCredits("channels.list.contentDetails")
    request = self.youtubeClient.channels().list(
      part = "contentDetails",
      id   = channelID,
    )
    channelResp = request.execute()
    
    # CHECK: have items
    items = channelResp.get("items", None)
    if items is None:
      logger.debug("fetchRecentVideos: no recent videos")
      return []
    
    # CHECK: items in valid format
    playlistID = items[0].get("contentDetails", {}).get("relatedPlaylists", {}).get("uploads", None)
    if playlistID is None:
      logger.error("fetchRecentVideos: unknown format for channel {}:\n{}".format(channelID, channelResp))
      return None
    
    # get the recent videos playlist
    logger.debug("fetchRecentVideos: getting recent videos")
    self._countCredits("playlistItems.list.snippet")
    request = self.youtubeClient.playlistItems().list(
      part       = "snippet",
      playlistId = playlistID,
      maxResults = maxResults
    )
    
    # parse and return the data
    parsedResults = Fetcher._parsePlaylistVideos(request.execute())
    logger.debug("fetchRecentVideos: got {} results".format(len(parsedResults)))
    return parsedResults


