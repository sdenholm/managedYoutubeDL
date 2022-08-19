
import math
import os
import random
from io import StringIO
import logging

import unittest

from datetime import timedelta

# create a streamed log, so we can check its output at runtime
logStream = StringIO()
logging.basicConfig(stream=logStream, level=logging.DEBUG)

# console
console = logging.StreamHandler()
console.setLevel(logging.INFO)
#console.setLevel(logging.DEBUG)
console.setFormatter(logging.Formatter("%(levelname)s: %(message)s"))
logging.getLogger("").addHandler(console)
logger = logging.getLogger(__name__)

import googleapiclient.discovery

from managedYoutubeDL import Fetcher
from managedYoutubeDL.items import Channel, Video

"""
sudo python3 -m unittest tests.test_fetcher.test_Fetcher.
.
"""


class test_Fetcher(unittest.TestCase):
  TEST_ALL = True
  
  
  @classmethod
  def setUpClass(cls):
    pass
  
  @classmethod
  def tearDownClass(cls):
    pass
  
  def setUp(self):
    
    # reset log stream
    logStream.truncate(0)
  
  def tearDown(self):
    pass
  
  
  @staticmethod
  def getRandomStringList(stringLength, numStrings):
    return ["".join([chr(random.randint(33, 133)) for _ in range(stringLength)]) for __ in range(numStrings)]
  
  
  def test_pickleAndUnpickle(self):
    """  """
    logger.info("test_pickleAndUnpickle")
    
    # random list of ints, floats and strings to test
    numInts       = 100
    numFloats     = 100
    numStrings    = 100
    stringLength  = 10
    randomInts    = [random.randint(0, 10000) for _ in range(numInts)]
    randomFloats  = [random.randint(0, 10000) + 0.5 for _ in range(numFloats)]
    randomStrings = test_Fetcher.getRandomStringList(stringLength, numStrings)
    
    for testObj in randomInts + randomFloats + randomStrings + [Channel(title="title", id="id")]:
      
      # pickle the object
      pickleStr = Fetcher._pickleObject(testObj)

      # TEST: readable string is returned
      def isAllowedValue(char):
        return char.isdigit() or char.isalpha() or char in ["=", "/", "+", "-"]
      self.assertIsInstance(pickleStr, str)
      self.assertGreater(len(pickleStr), 0)
      self.assertFalse(any(filter(lambda s: not isAllowedValue(s), pickleStr)))
      
      # unpickle the string
      unpickledObj = Fetcher._unpickleObject(pickleStr)
      
      # TEST: unpickled object has the same value as the original
      self.assertEqual(testObj, unpickledObj)
    
    
  
  def test_fetchVideoDetails(self):
    """  """
    logger.info("test_fetchVideoDetails")
    
    # remember original build function, as we will replace it
    originalBuild = googleapiclient.discovery.build
    
    # fake class to replace API call
    class FakeAPI:
      response = {}
      def __init__(self, *args, **kwargs):
        pass
      def videos(self, *args, **kwargs):
        return self
      def list(self, *args, **kwargs):
        return self
      def execute(self, *args, **kwargs):
        return FakeAPI.response
      
    # replace the API call class
    googleapiclient.discovery.build = FakeAPI
    
    # create a fetcher with nonsense details
    fetcher = Fetcher(
      clientSecretsFile  = os.path.abspath(__file__),
      pickledCredentials = Fetcher._pickleObject("pickle string")
    )
    
    # default, blank response if there is a problem
    blankDetails = {"duration": None}
    
    ###########################################################################
    # TEST: when all is correct, returns video duration details
    ###########################################################################
    correctDetails = {"duration": timedelta(hours=1, minutes=2, seconds=3)}
    video = Video(title="video title", id="video id")
    
    FakeAPI.response = {"items": [{"contentDetails": {"duration": "PT1H2M3S"}}]}
    self.assertDictEqual(fetcher.fetchVideoDetails(video), correctDetails)
    

    ###########################################################################
    # TEST: when response has no items, returns blank details
    ###########################################################################
    FakeAPI.response = {}
    self.assertDictEqual(fetcher.fetchVideoDetails(video), blankDetails)


    ###########################################################################
    # TEST: when response items.contentDetails doesn't exist, returns blank details
    ###########################################################################
    FakeAPI.response = {"items":[{}]}
    self.assertDictEqual(fetcher.fetchVideoDetails(video), blankDetails)
    
    
    ###########################################################################
    # TEST: when items.contentDetails.duration doesn't exist, returns blank details
    ###########################################################################
    FakeAPI.response = {"items": [{"contentDetails": {}}]}
    self.assertDictEqual(fetcher.fetchVideoDetails(video), blankDetails)
    
    
    # undo our fakery
    googleapiclient.discovery.build = originalBuild
    
    
  def test_fetchRecentVideos(self):
    """  """
    logger.info("test_fetchRecentVideos")

    # remember original build function, as we will replace it
    originalBuild = googleapiclient.discovery.build

    # fake class to replace API call
    class FakeAPI:
      playlistItemsResponse = {}
      channelsResponse      = {}
      def __init__(self, *args, **kwargs):
        pass
      def channels(self, *args, **kwargs):
        return self.channelsClass
      def playlistItems(self, *args, **kwargs):
        return self.playlistItemsClass
      class playlistItemsClass:
        def list(*args, **kwargs):
          return FakeAPI.playlistItemsClass
        def execute(*args, **kwargs):
          return FakeAPI.playlistItemsResponse
      class channelsClass:
        def list(*args, **kwargs):
          return FakeAPI.channelsClass
        def execute(*args, **kwargs):
          return FakeAPI.channelsResponse
      
      
    
    # replace the API call class
    googleapiclient.discovery.build = FakeAPI
    
    # create a fetcher with nonsense details
    fetcher = Fetcher(
      clientSecretsFile  = os.path.abspath(__file__),
      pickledCredentials = Fetcher._pickleObject("pickle string")
    )

    # fake channel ID for testing
    channelID = "channel ID string"

    ###########################################################################
    # TEST: when all is correct, returns list of videos
    ###########################################################################
    numVideos = 10
    correctVideoList = [Video(
      title        = "title-{}".format(i),
      id           = "id-{}".format(i),
      publishedAt  = "2020-01-01 00:00:00." + "{}".format(i).rjust(6, "0"),
      thumbnailURL = "thumbnailURL-{}".format(i),
    ) for i in range(numVideos)]
    
    FakeAPI.channelsResponse =\
      {"items": [{"contentDetails": {"relatedPlaylists": {"uploads": "ID string"}}}]}
    FakeAPI.playlistItemsResponse = {"items": [
      {"kind": "youtube#playlistItem",
       "snippet": {
         "resourceId": {"videoId": "id-{}".format(i)},
         "title": "title-{}".format(i),
         "publishedAt": "2020-01-01 00:00:00." + "{}".format(i).rjust(6, "0"),
         "thumbnails": {"high": {"url": "thumbnailURL-{}".format(i)}}
       }} for i in range(numVideos)]}
    self.assertListEqual(fetcher.fetchRecentVideos(channelID), correctVideoList)
    

    ###########################################################################
    # TEST: when response has no items, function returns blank video list
    ###########################################################################
    FakeAPI.channelsResponse = {}
    self.assertListEqual(fetcher.fetchRecentVideos(channelID), [])
    
    
    ###########################################################################
    # TEST: when response has no contentDetails, relatedPlaylists, or
    #       uploads, function returns blank video list
    ###########################################################################
    invalidResponses = [
      {"items": [{}]},
      {"items": [{"contentDetails": {}}]},
      {"items": [{"contentDetails": {"relatedPlaylists": {}}}]},
    ]
    for response in invalidResponses:
      FakeAPI.channelsResponse = response
      self.assertIsNone(fetcher.fetchRecentVideos(channelID))
      
      
    # undo our fakery
    googleapiclient.discovery.build = originalBuild
    
    

  def test_fetchMySubscribedChannels_zeroAndOnePages(self):
    """  """
    logger.info("test_fetchMySubscribedChannels_zeroAndOnePages")

    # remember original build function, as we will replace it
    originalBuild = googleapiclient.discovery.build

    # fake class to replace API call
    class FakeAPI:
      callCount = 0
      subscriptionsResponse = {}
      def __init__(self, *args, **kwargs):
        pass
      def subscriptions(self, *args, **kwargs):
        return self.subscriptionsClass
      class subscriptionsClass:
        def list(*args, **kwargs):
          return FakeAPI.subscriptionsClass
        def execute(*args, **kwargs):
          # increment call counter
          FakeAPI.callCount += 1
          # return the stored response
          return FakeAPI.subscriptionsResponse

    # replace the API call class
    googleapiclient.discovery.build = FakeAPI

    # create a fetcher with nonsense details
    fetcher = Fetcher(
      clientSecretsFile=os.path.abspath(__file__),
      pickledCredentials=Fetcher._pickleObject("pickle string")
    )
    
    ###########################################################################
    # TEST: no subscriptions
    ###########################################################################
    numChannels = 0
    FakeAPI.subscriptionsResponse = {
      "nextPageToken": "token string",
      "pageInfo":      {"totalResults": numChannels},
      "items": [
        {"kind": "youtube#subscription",
         "snippet": {
           "resourceId":  {"channelId": "id-{}".format(i)},
           "title":       "title-{}".format(i),
           "publishedAt": "2020-01-01 00:00:00." + "{}".format(i).rjust(6, "0")
         }} for i in range(numChannels)]}
    
    
    # TEST: no channels returned (blank items list)
    #  -only one API call
    FakeAPI.callCount = 0
    self.assertListEqual(fetcher.fetchMySubscribedChannels(), [])
    self.assertEqual(FakeAPI.callCount, 1)

    # TEST: no channels returned (no items list)
    #  -only one API call
    del FakeAPI.subscriptionsResponse["items"]
    FakeAPI.callCount = 0
    self.assertListEqual(fetcher.fetchMySubscribedChannels(), [])
    self.assertEqual(FakeAPI.callCount, 1)
    
    
    ###########################################################################
    # TEST: 1 page of channels
    ###########################################################################
    numChannels = 20
    FakeAPI.subscriptionsResponse = {
      "nextPageToken": "token string",
      "pageInfo":      {"totalResults": numChannels},
      "items": [
        {"kind": "youtube#subscription",
         "snippet": {
           "resourceId":  {"channelId": "id-{}".format(i)},
           "title":       "title-{}".format(i),
           "publishedAt": "2020-01-01 00:00:00." + "{}".format(i).rjust(6, "0")
         }} for i in range(numChannels)]}
    
    
    # the channel list that the method should return
    correctChannelList = [
      Channel(
        title       = "title-{}".format(i),
        id          = "id-{}".format(i),
        publishedAt = "2020-01-01 00:00:00." + "{}".format(i).rjust(6, "0"))
      for i in range(numChannels)
    ]
    
    
    # TEST: 1 page of correct results
    #  -only one API call
    FakeAPI.callCount = 0
    self.assertListEqual(fetcher.fetchMySubscribedChannels(maxResultsPerPage=numChannels), correctChannelList)
    self.assertEqual(FakeAPI.callCount, 1)
    
    
    
    # undo our fakery
    googleapiclient.discovery.build = originalBuild
    
    
  def test_fetchMySubscribedChannels_multiplePages(self):
    """  """
    logger.info("test_fetchMySubscribedChannels_multiplePages")

    # remember original build function, as we will replace it
    originalBuild = googleapiclient.discovery.build

    # youtube API's limit
    MAX_RESULTS_PER_PAGE = 50
    
    # fake class to replace API call
    class FakeAPI:
      callCount = 0
      callbackFunction = None
      subscriptionsResponse = {}
      def __init__(self, *args, **kwargs):
        pass
      def subscriptions(self, *args, **kwargs):
        return self.subscriptionsClass
      class subscriptionsClass:
        def list(*args, **kwargs):
          return FakeAPI.subscriptionsClass
        def execute(*args, **kwargs):
          # increment call counter
          FakeAPI.callCount += 1
          # call testing function
          if FakeAPI.callbackFunction is not None: FakeAPI.callbackFunction()
          # return the stored response
          return FakeAPI.subscriptionsResponse

    
    # create API response of X pages, numbered startIndex to endIndex-1
    def createResponse(startIndex, endIndex):
      return {
        "nextPageToken": "token string",
        "pageInfo":      {"totalResults": numChannels},
        "items": [
          {"kind": "youtube#subscription",
           "snippet": {
             "resourceId":  {"channelId": "id-{}".format(i)},
             "title":       "title-{}".format(i),
             "publishedAt": "2020-01-01 00:00:00." + "{}".format(i).rjust(6, "0")
           }
          } for i in range(startIndex, endIndex)]
      }

    # the channel list that the method should return
    def createChannelList(startIndex, endIndex):
      return [
        Channel(
          title       = "title-{}".format(i),
          id          = "id-{}".format(i),
          publishedAt = "2020-01-01 00:00:00." + "{}".format(i).rjust(6, "0"))
        for i in range(startIndex, endIndex)
      ]
    
    # replace the API call class
    googleapiclient.discovery.build = FakeAPI
    
    # create a fetcher with nonsense details
    fetcher = Fetcher(
      clientSecretsFile  = os.path.abspath(__file__),
      pickledCredentials = Fetcher._pickleObject("pickle string")
    )

    global resultCounter
    
    ###########################################################################
    # TEST: N pages of channels: all pages have unique results
    ###########################################################################

    # when the API gets called, update the returned response to simulate
    # a new page of results
    def callbackFunction():
      global resultCounter
      startInd      = resultCounter
      resultCounter = min(numChannels, resultCounter + maxResultsPerPage)
      FakeAPI.subscriptionsResponse = createResponse(startInd, resultCounter)

    # register the callback function
    FakeAPI.callbackFunction = callbackFunction

    # TEST: 0-100 possible channels, in steps of 10
    for numChannels in range(0, 100, 10):
      
      # max 50 results per page
      minPages = max(1, math.ceil(numChannels/MAX_RESULTS_PER_PAGE))
      
      # results spread over X pages
      for numPages in range(minPages, numChannels+1):

        # number of results per page
        #  -must have at least one result per page
        maxResultsPerPage = int(math.ceil(numChannels / numPages))
        self.assertTrue(1 <= maxResultsPerPage <= MAX_RESULTS_PER_PAGE, msg=maxResultsPerPage)
        
        # reset channel and API counters
        resultCounter     = 0
        FakeAPI.callCount = 0
        
        # TEST: N pages of correct results
        #  -N API calls
        returnedChannelList = fetcher.fetchMySubscribedChannels(maxResultsPerPage=maxResultsPerPage)
        correctChannelList  = createChannelList(0, numChannels)
        self.assertListEqual(returnedChannelList, correctChannelList)
        self.assertEqual(FakeAPI.callCount, math.ceil(numChannels/maxResultsPerPage))
        
        
    ###########################################################################
    # TEST: N pages of channels: some pages have channels we've seen before
    ###########################################################################
    
    # when the API gets called, update the returned response to simulate
    # a new page of results
    #  -randomly include some results from the end of the previous page
    def callbackFunctionWithOverlap():
      global resultCounter
      startInd      = max(0, resultCounter - random.randint(0, max(0, maxResultsPerPage-1)))
      resultCounter = min(numChannels, startInd + maxResultsPerPage)
      FakeAPI.subscriptionsResponse = createResponse(startInd, resultCounter)
      
    # register the new overlapping callback function
    FakeAPI.callbackFunction = callbackFunctionWithOverlap

    # TEST: 10-100 possible channels, in steps of 10
    for numChannels in range(10, 100, 10):
  
      # max 50 results per page
      minPages = max(1, math.ceil(numChannels / MAX_RESULTS_PER_PAGE))
  
      # results spread over X pages
      for numPages in range(minPages, numChannels + 1):
        # number of results per page
        #  -must have at least one result per page
        maxResultsPerPage = int(math.ceil(numChannels / numPages))
        self.assertTrue(1 <= maxResultsPerPage <= MAX_RESULTS_PER_PAGE, msg=maxResultsPerPage)
    
        # reset channel and API counters
        resultCounter     = 0
        FakeAPI.callCount = 0
    
        # TEST: N pages of correct results
        #  -N API calls
        returnedChannelList = fetcher.fetchMySubscribedChannels(maxResultsPerPage=maxResultsPerPage)
        correctChannelList  = createChannelList(0, numChannels)
        self.assertListEqual(returnedChannelList, correctChannelList)
        

    
    # undo our fakery
    googleapiclient.discovery.build = originalBuild
    
    
  def test_fetchMySubscribedChannels_missingChannels(self):
    """  """
    logger.info("test_fetchMySubscribedChannels_missingChannels")
  
    # remember original build function, as we will replace it
    originalBuild = googleapiclient.discovery.build
  
    # youtube API's limit
    MAX_RESULTS_PER_PAGE = 50
  
    # fake class to replace API call
    class FakeAPI:
      callCount = 0
      subscriptionsResponse = {}
      def __init__(self, *args, **kwargs):
        pass
      def subscriptions(self, *args, **kwargs):
        return self.subscriptionsClass
      class subscriptionsClass:
        def list(*args, **kwargs):
          return FakeAPI.subscriptionsClass
        def execute(*args, **kwargs):
          # increment call counter
          FakeAPI.callCount += 1
          # return the stored response
          return FakeAPI.subscriptionsResponse
  
    # create API response of X pages, numbered startIndex to endIndex-1
    def createResponse(startIndex, endIndex):
      return {
        "nextPageToken": "token string",
        "pageInfo":      {"totalResults": numChannels},
        "items": [
          {"kind": "youtube#subscription",
           "snippet": {
             "resourceId":  {"channelId": "id-{}".format(i)},
             "title":       "title-{}".format(i),
             "publishedAt": "2020-01-01 00:00:00." + "{}".format(i).rjust(6, "0")
           }
           } for i in range(startIndex, endIndex)]
      }
  
    # replace the API call class
    googleapiclient.discovery.build = FakeAPI
  
    # create a fetcher with nonsense details
    fetcher = Fetcher(
      clientSecretsFile  = os.path.abspath(__file__),
      pickledCredentials = Fetcher._pickleObject("pickle string")
    )
    
  
    ###########################################################################
    # TEST: N pages of channels: don't get all results from multi-page search
    ###########################################################################
  
    # TEST: <MAX_RESULTS_PER_PAGE>+1 to 150 possible channels
    #  -should be at least 2 pages worth of results
    for numChannels in range(MAX_RESULTS_PER_PAGE+1, 150):
    
      # API counter-call counter
      FakeAPI.callCount = 0
      
      # API response will never have all the channels
      FakeAPI.subscriptionsResponse = createResponse(0, MAX_RESULTS_PER_PAGE-1)
    
      # TEST: raises error when can't get all the channels that are available
      #  -multiple API calls
      self.assertRaises(SystemError, fetcher.fetchMySubscribedChannels, maxResultsPerPage=MAX_RESULTS_PER_PAGE)
      self.assertGreater(FakeAPI.callCount, 1)


    # undo our fakery
    googleapiclient.discovery.build = originalBuild


  def test_convertVideoDuration(self):
    """  """
    logger.info("test_convertVideoDuration")
    
    ###########################################################################
    # TEST: live duration return None
    ###########################################################################
    liveDurationStr = "P0D"
    self.assertIsNone(Fetcher._convertVideoDuration(liveDurationStr))
    
    
    ###########################################################################
    # TEST: nonsense returns None
    ###########################################################################
    numStrings    = 50
    stringLength  = 10
    randomStrings = test_Fetcher.getRandomStringList(stringLength, numStrings)
    for nonsenseStr in [""] + randomStrings:
      self.assertIsNone(Fetcher._convertVideoDuration(nonsenseStr), msg="{} was converted".format(nonsenseStr))
    
    
    ###########################################################################
    # TEST: random values are calculated correctly
    ###########################################################################
    numTests = 100
    for _ in range(numTests):
      
      randomHours   = "{}H".format(random.randint(0,50))
      randomMinutes = "{}M".format(random.randint(0,59))
      randomSeconds = "{}S".format(random.randint(0,59))
      durationStr = "PT{}{}{}".format(
        "" if randomHours   == "0H" else randomHours,
        "" if randomMinutes == "0M" else randomMinutes,
        "" if randomSeconds == "0S" else randomSeconds,
      )
    
      actualDuration = timedelta(
        hours   = int(randomHours[:-1]),
        minutes = int(randomMinutes[:-1]),
        seconds = int(randomSeconds[:-1])
      )
      
      convertedDuration = Fetcher._convertVideoDuration(durationStr)
      self.assertEqual(actualDuration.total_seconds(), convertedDuration.total_seconds())
      
      
    ###########################################################################
    # TEST: zero values are calculated correctly
    ###########################################################################
    
    for hours in [0,1]:
      for minutes in [0,2]:
        for seconds in [0,3]:
          durationStr = "PT{}{}{}".format(
            "" if hours   == 0 else str(hours)   + "H",
            "" if minutes == 0 else str(minutes) + "M",
            "" if seconds == 0 else str(seconds) + "S",
          )
          
          # skip the all-is-nothing case
          if durationStr == "PT":
            continue

          actualDuration    = timedelta(hours=hours, minutes=minutes, seconds=seconds)
          convertedDuration = Fetcher._convertVideoDuration(durationStr)
          self.assertEqual(actualDuration.total_seconds(), convertedDuration.total_seconds())

  