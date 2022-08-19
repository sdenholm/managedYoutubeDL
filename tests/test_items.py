import datetime
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


from managedYoutubeDL.items import Channel, Video

"""
sudo python3 -m unittest tests.test_items.test_Items.
.
"""


class test_Items(unittest.TestCase):
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


  def test_Channel(self):
    """  """
    logger.info("test_Channel")
  
    ###########################################################################
    # TEST: instantiation
    ###########################################################################
    
    # arguments and examples of acceptable values
    arguments = {
      "title":          "string val",
      "id":             "string val",
      "publishedAt":    str(datetime.datetime.utcfromtimestamp(0)),
      "ignore":         False,
      "excludeFilter":  "string val",
      "includeFilter":  "string val",
      "minVideoDate":   str(datetime.datetime.utcfromtimestamp(0)),
      "maxVideoDate":   str(datetime.datetime.utcfromtimestamp(1)),
      "minVideoLength": timedelta(0),
      "maxVideoLength": timedelta(0),
    }
  
    # TEST: acceptable arguments are accepted and assigned correctly
    for argName, argVal in arguments.items():
      channel = Channel(**{argName: argVal})
      self.assertEqual(str(getattr(channel, argName)), str(argVal))
    
    # TEST: our test has assigned all arguments
    channel = Channel(**arguments)
    self.assertListEqual(list(arguments.keys()), list(channel.__dict__.keys()))
    
    # TEST: unacceptable arguments raise errors
    for arg in arguments.keys():
      self.assertRaises(AttributeError, Channel, **{"{}-diff".format(arg): None})
      
      
    ###########################################################################
    # TEST: string representation
    ###########################################################################
    numChannels = 10
  
    for i in range(numChannels):
      
      # create a channel with unique attributes
      localArguments = {
        "title":          str((i + 1) * 10),
        "id":             str((i + 1) * 100),
        "publishedAt":    str(datetime.datetime.utcfromtimestamp(i+1)),
        "ignore":         False,
        "excludeFilter":  str((i + 1) * 1000),
        "includeFilter":  str((i + 1) * 10000),
        "minVideoDate":   str(datetime.datetime.utcfromtimestamp((i+1)*10)),
        "maxVideoDate":   str(datetime.datetime.utcfromtimestamp((i+1)*100)),
        "minVideoLength": timedelta(seconds=(i+1)*10),
        "maxVideoLength": timedelta(seconds=(i+1)*100),
      }
      
      # TEST: none of the arguments have the same values
      keys = [key for key in localArguments.keys()]
      for ind1 in range(len(keys) - 1):
        for ind2 in range(ind1 + 1, len(keys)):
          self.assertNotEqual(localArguments[keys[ind1]], localArguments[keys[ind2]])
          
      channel = Channel(**localArguments)

      # TEST: its string representation is correct
      correctStr = "\n".join(["{}: {}".format(k,v) for k,v in localArguments.items()])
      self.assertEqual(str(channel), correctStr)
    
    
    ###########################################################################
    # TEST: equality
    ###########################################################################
    numChannels = 10
  
    # TEST: channels with DIFFERENT titles and DIFFERENT ids are different
    channelList = [Channel(title="title{}".format(i), id=str(i)) for i in range(numChannels)]
    for ind1 in range(numChannels - 1):
      for ind2 in range(ind1 + 1, numChannels):
        self.assertNotEqual(channelList[ind1], channelList[ind2])
  
    # TEST: channels with DIFFERENT titles and SAME ids are different
    channelList = [Channel(title="title{}".format(i), id=str(0)) for i in range(numChannels)]
    for ind1 in range(numChannels - 1):
      for ind2 in range(ind1 + 1, numChannels):
        self.assertNotEqual(channelList[ind1], channelList[ind2])
  
    # TEST: channels with SAME titles and DIFFERENT ids are different
    channelList = [Channel(title="title", id=str(i)) for i in range(numChannels)]
    for ind1 in range(numChannels - 1):
      for ind2 in range(ind1 + 1, numChannels):
        self.assertNotEqual(channelList[ind1], channelList[ind2])
  
    # TEST: channels with SAME titles and SAME ids are the same
    channelList = [Channel(title="title", id=str(0)) for i in range(numChannels)]
    for ind1 in range(numChannels - 1):
      for ind2 in range(ind1 + 1, numChannels):
        self.assertEqual(channelList[ind1], channelList[ind2])
        self.assertNotEqual(id(channelList[ind1]), id(channelList[ind2]))


    
  def test_Video(self):
    """  """
    logger.info("test_Video")


    ###########################################################################
    # TEST: instantiation
    ###########################################################################
    
    # arguments and examples of acceptable values
    arguments = {
      "title":        "string val",
      "id":           "string val",
      "thumbnailURL": "string val",
      "publishedAt":  str(datetime.datetime.utcfromtimestamp(0))
    }

    # TEST: acceptable arguments are accepted and assigned correctly
    for argName, argVal in arguments.items():
      vid = Video(**{argName:argVal})
      self.assertEqual(str(getattr(vid, argName)), argVal)
    
    # TEST: our test has assigned all arguments
    video = Video(**arguments)
    self.assertListEqual(list(arguments.keys()), list(video.__dict__.keys()))
    
    # TEST: unacceptable arguments raise errors
    for arg in arguments.keys():
      self.assertRaises(AttributeError, Video, **{"{}-diff".format(arg): None})
      
      
    ###########################################################################
    # TEST: string representation
    ###########################################################################
    numVideos = 10
    
    for i in range(numVideos):
      
      # create a video with unique attributes
      title        = str((i+1)*10)
      videoID      = str((i+1)*100)
      thumbnailURL = str((i+1)*1000)
      publishedAt  = str(datetime.datetime.utcfromtimestamp(i+1))
      self.assertNotEqual(title, videoID)
      self.assertNotEqual(videoID, thumbnailURL)
      self.assertNotEqual(thumbnailURL, publishedAt)
      vid = Video(
        title        = title,
        id           = videoID,
        thumbnailURL = thumbnailURL,
        publishedAt  = publishedAt,
      )

      # TEST: its string representation is correct
      correctStr = "title: {}\nid: {}\npublishedAt: {}\nthumbnailURL: {}\n"\
        .format(title, videoID, publishedAt, thumbnailURL)
      self.assertEqual(str(vid), correctStr)
    
    
    ###########################################################################
    # TEST: equality
    ###########################################################################
    numVideos = 10
    
    # TEST: videos with DIFFERENT titles and DIFFERENT ids are different
    videoList = [Video(title="title{}".format(i), id=str(i)) for i in range(numVideos)]
    for ind1 in range(numVideos-1):
      for ind2 in range(ind1+1, numVideos):
        self.assertNotEqual(videoList[ind1], videoList[ind2])

    # TEST: videos with DIFFERENT titles and SAME ids are different
    videoList = [Video(title="title{}".format(i), id=str(0)) for i in range(numVideos)]
    for ind1 in range(numVideos-1):
      for ind2 in range(ind1+1, numVideos):
        self.assertNotEqual(videoList[ind1], videoList[ind2])

    # TEST: videos with SAME titles and DIFFERENT ids are different
    videoList = [Video(title="title", id=str(i)) for i in range(numVideos)]
    for ind1 in range(numVideos-1):
      for ind2 in range(ind1+1, numVideos):
        self.assertNotEqual(videoList[ind1], videoList[ind2])

    # TEST: videos with SAME titles and SAME ids are the same
    videoList = [Video(title="title", id=str(0)) for i in range(numVideos)]
    for ind1 in range(numVideos-1):
      for ind2 in range(ind1+1, numVideos):
        self.assertEqual(videoList[ind1], videoList[ind2])
        self.assertNotEqual(id(videoList[ind1]), id(videoList[ind2]))
    
    
    
    