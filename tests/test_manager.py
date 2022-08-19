import base64
import datetime
import os
import pickle
import random
import shutil
import tempfile
from io import StringIO
import logging

import unittest

from datetime import timedelta

# create a streamed log so we can check its output at runtime
logStream = StringIO()
logging.basicConfig(stream=logStream, level=logging.DEBUG)

# console
console = logging.StreamHandler()
console.setLevel(logging.INFO)
console.setFormatter(logging.Formatter("%(levelname)s: %(message)s"))
logging.getLogger("").addHandler(console)
logger = logging.getLogger(__name__)

from managedYoutubeDL.manager import Manager
from managedYoutubeDL.items import Channel, Video


"""
sudo python3 -m unittest tests.test_manager.test_Manager.
.
"""


class test_Manager(unittest.TestCase):
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

  def test_instantiation(self):
    """  """
    logger.info("test_instantiation")
  
    ###########################################################################
    # TEST: instantiation
    ###########################################################################
  
    # arguments and examples of acceptable values
    arguments = {
      "clientSecretsFile":     None,
      "pickledCredentials":    base64.b64encode(pickle.dumps("pickleStr")).decode("utf-8"),
      "downloadDirectory":     str(os.path.dirname(os.path.realpath(__file__))),
      "ffmpegLocation":        str(os.path.realpath(__file__)),
      "channelList":           [],
      "globalMinVideoDate":    str(datetime.datetime.utcfromtimestamp(0)),
      "globalMaxVideoDate":    str(datetime.datetime.utcfromtimestamp(1)),
      "seenChannelVideos":     {"a":"b"},
      "globalIncludeFilter":   "something",
      "globalExcludeFilter":   "other",
      "globalMinVideoLength":  timedelta(0),
      "globalMaxVideoLength":  timedelta(1),
    }
  
    # TEST: acceptable arguments are accepted and assigned correctly
    manager = Manager(**arguments)
    for argName, argVal in arguments.items():
      self.assertEqual(str(getattr(manager, argName)), str(argVal))
    
    # TEST: our test has assigned all arguments
    initAssignedFields = ["ytFetcher"]
    self.assertListEqual(list(arguments.keys())+initAssignedFields, list(manager.__dict__.keys()))
    
    # TEST: unacceptable arguments raise errors
    for arg in arguments.keys():
      self.assertRaises(AttributeError, Manager, **{"{}-diff".format(arg): None})
  
  
  def test_getFFmpegInPath(self):
    """  """
    logger.info("test_getFFmpegInPath")
    #print(Manager._getFFmpegInPath())
    
    print(os.path.exists("ffmpeg"))
  
  
  @unittest.skipIf(True, "ToDo")
  def test_seenVideos(self):
    """  """
    logger.info("test_seenVideos")
    
    # create manager
    
    # add seen videos
    
    # are they added
    
    # have we seen them
    
    
  @unittest.skipIf(True, "ToDo")
  def test_downloadNewVideos(self):
    """  """
    logger.info("test_downloadNewVideos")
    
    # get fake videos for a fake channel
    
    # do we filter them
    
    # do we add to seen
    
    # do we download them
    #  -what if error?
    #  -what if they already exist
    
    # do we correctly return downloaded and failed
    
    # overwrite: self.ytFetcher.fetchRecentVideos(channel.id)
    
    # overwrite: self._downloadVideo(channel, video)
    
    
  @unittest.skipIf(True, "ToDo")
  def test_updateChannels(self):
    """  """
    logger.info("test_updateChannels")
    
    
    # NOTHING TO TEST? MORE A TEST OF MANAGER LOAD AND DUMP?
    
    
    
    
    
    # overwrite: self.ytFetcher.fetchMySubscribedChannels()
    
    # if initial list is blank, do we add all
    
    # if initial list has channels
    #  -do we add new
    #  -do we remove old
    #  -do we leave others untouched
    
    
  @unittest.skipIf(True, "ToDo")
  def test_createNewManager(self):
    """  """
    logger.info("test_createNewManager")
    
    
    # overwrite: Manager
    #  -so we don't need client secrets or pickled data
    
    # overwrite: manager.updateChannels()
    #  -give back list of normally created channels
    
    # do we successfully create a config file
    
    # overwrite: self.ytFetcher.fetchMySubscribedChannels()
  
    # if initial list is blank, do we add all
  
    # if initial list has channels
    #  -do we add new
    #  -do we remove old
    #  -do we leave others untouched
    
    
  @unittest.skipIf(True, "ToDo")
  def test_filterChannelVideos(self):
    """  """
    logger.info("test_filterChannelVideos")
  
    def createChannel(**kwargs):
      localArgs = {}
      localArgs.update(kwargs)
      localArgs["title"] = kwargs.get("title", "channel title")
      localArgs["id"] = kwargs.get("id", "channel id")
      return Channel(**localArgs)
  
    def createVideo(**kwargs):
      localArgs = {}
      localArgs.update(kwargs)
      localArgs["title"] = kwargs.get("title", "video title")
      localArgs["id"] = kwargs.get("id", "video id")
      return Video(**localArgs)
  
    # filter-less channel
    unfilteredChannel = Channel()
  
    ###########################################################################
    # TEST: item is not a video raises an error
    ###########################################################################
    channel = createChannel()
    for invalidEntry in [None, "string", 777, Channel()]:
      self.assertRaises(TypeError, channel.filterVideoList, [invalidEntry])
  
    ###########################################################################
    # TEST: filtered out: min video date
    ###########################################################################
  
    # channel with a minVideoDate filter
    channel = createChannel(minVideoDate="1970-01-01 00:00:00")
  
    # TEST: allowed when no minVideoDate filter is set
    video = createVideo(minVideoDate="1970-01-01 00:00:00")
    self.assertIn(video, unfilteredChannel.filterVideoList([video]))
  
    # TEST: allowed when video date is after minimum
    video = createVideo(minVideoDate=channel.minVideoDate + timedelta(seconds=1))
    self.assertIn(video, channel.filterVideoList([video]))
  
    # TEST: allowed when video date is equal to minimum
    video = createVideo(minVideoDate=channel.minVideoDate)
    self.assertIn(video, channel.filterVideoList([video]))
  
    # TEST: denied when video date is before minimum
    video = createVideo(minVideoDate=channel.minVideoDate - timedelta(seconds=1))
    self.assertNotIn(video, channel.filterVideoList([video]))
  
    ###########################################################################
    # TEST: filtered out: regex video title inclusion
    ###########################################################################
  
    # channel with an inclusion filter
    channel = createChannel(includeFilter=".*thing")
  
    # TEST: allowed when no inclusion filter is set
    video = createVideo(title="something")
    self.assertIn(video, unfilteredChannel.filterVideoList([video]))
  
    # TEST: allowed when matching inclusion filter
    video = createVideo(title="something")
    self.assertIn(video, channel.filterVideoList([video]))
  
    # TEST: denied when not matching inclusion filter
    video = createVideo(title="other")
    self.assertNotIn(video, channel.filterVideoList([video]))
  
    ###########################################################################
    # TEST: filtered out: regex video title exclusion
    ###########################################################################
  
    # channel with an exclusion filter
    channel = createChannel(excludeFilter=".*thing")
  
    # TEST: allowed when no exclusion filter is set
    video = createVideo(title="something")
    self.assertIn(video, unfilteredChannel.filterVideoList([video]))
  
    # TEST: allowed when not matching exclusion filter
    video = createVideo(title="other")
    self.assertIn(video, channel.filterVideoList([video]))
  
    # TEST: denied when matching exclusion filter
    video = createVideo(title="something")
    self.assertNotIn(video, channel.filterVideoList([video]))

