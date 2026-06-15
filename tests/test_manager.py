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
      "globalMinVideoDate":    datetime.datetime.fromtimestamp(0, datetime.timezone.utc),
      "globalMaxVideoDate":    datetime.datetime.fromtimestamp(1, datetime.timezone.utc),
      "seenChannelVideos":     {"a":"b"},
      "globalIncludeFilter":   "something",
      "globalExcludeFilter":   "other",
      "globalMinVideoLength":  timedelta(0),
      "globalMaxVideoLength":  timedelta(1),
      "downloadTimeout":       timedelta(seconds=10),
      "postTimeoutWait":       timedelta(seconds=5),
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
  
  
  @staticmethod
  def createManager(**kwargs):
    args = {
      "clientSecretsFile":  None,
      "pickledCredentials": base64.b64encode(pickle.dumps("pickleStr")).decode("utf-8"),
      "downloadDirectory":  str(os.path.dirname(os.path.realpath(__file__))),
      "ffmpegLocation":     str(os.path.realpath(__file__)),
      "channelList":        [],
      "seenChannelVideos":  {},
    }
    args.update(kwargs)
    return Manager(**args)


  def test_seenVideos(self):
    """  """
    logger.info("test_seenVideos")

    manager  = test_Manager.createManager()
    channel1 = Channel(title="ch1", id="ch-id-1")
    channel2 = Channel(title="ch2", id="ch-id-2")
    video1   = Video(title="vid1", id="vid-id-1")
    video2   = Video(title="vid2", id="vid-id-2")

    # TEST: unseen video is not recognised
    self.assertFalse(manager.haveSeenVideo(channel1, video1))

    # TEST: after adding, video is recognised as seen
    manager.addSeenVideo(channel1, video1)
    self.assertTrue(manager.haveSeenVideo(channel1, video1))

    # TEST: different video in same channel is not seen
    self.assertFalse(manager.haveSeenVideo(channel1, video2))

    # TEST: same video ID in different channel is not seen
    self.assertFalse(manager.haveSeenVideo(channel2, video1))

    # TEST: adding same video twice does not duplicate
    manager.addSeenVideo(channel1, video1)
    self.assertEqual(manager.seenChannelVideos[channel1.id].count(video1.id), 1)

    # TEST: cap at 25; oldest entries dropped, most recent retained
    CAP        = 25
    capChannel = Channel(title="cap", id="cap-ch")
    videoIds   = ["cap-vid-{}".format(i) for i in range(CAP + 5)]
    for vid_id in videoIds:
      manager.addSeenVideo(capChannel, Video(title=vid_id, id=vid_id))
    stored = manager.seenChannelVideos[capChannel.id]
    self.assertEqual(len(stored), CAP)
    self.assertListEqual(stored, videoIds[5:])

    # TEST: cap is per-channel (other channel's list unaffected)
    manager.addSeenVideo(channel2, video2)
    self.assertEqual(len(manager.seenChannelVideos[channel2.id]), 1)


    
  def test_downloadNewVideos(self):
    """  """
    logger.info("test_downloadNewVideos")
    import unittest.mock

    UTC     = datetime.timezone.utc
    QUALITY = Manager.VideoQuality.QUALITY_MAX

    def makeVideo(n):
      return Video(
        title="video-{}".format(n),
        id="vid-id-{}".format(n),
        publishedAt=datetime.datetime(2020, 1, n + 1, tzinfo=UTC),
      )

    def makeChannel(n, ignore=False):
      return Channel(title="ch-{}".format(n), id="ch-id-{}".format(n), ignore=ignore)

    ###########################################################################
    # TEST: no channels → (0, 0)
    ###########################################################################
    manager = test_Manager.createManager(channelList=[])
    manager.ytFetcher = type("F", (), {"fetchRecentVideos": lambda self, cid: []})()
    with unittest.mock.patch("managedYoutubeDL.manager.time.sleep"):
      downloaded, failed = manager.downloadNewVideos(quality=QUALITY)
    self.assertEqual((downloaded, failed), (0, 0))

    ###########################################################################
    # TEST: ignored channels are not fetched or downloaded
    ###########################################################################
    fetchCalls = []
    manager = test_Manager.createManager(channelList=[makeChannel(0, ignore=True)])
    manager.ytFetcher = type("F", (), {
      "fetchRecentVideos": lambda self, cid: fetchCalls.append(cid) or [makeVideo(0)]
    })()
    manager._downloadVideo = lambda ch, v, quality, timeout: True
    with unittest.mock.patch("managedYoutubeDL.manager.time.sleep"):
      downloaded, failed = manager.downloadNewVideos(quality=QUALITY)
    self.assertEqual(fetchCalls, [])
    self.assertEqual((downloaded, failed), (0, 0))

    ###########################################################################
    # TEST: successful download → seenChannelVideos updated, minVideoDate advanced
    ###########################################################################
    ch   = makeChannel(0)
    vid0 = makeVideo(0)
    vid1 = makeVideo(1)
    manager = test_Manager.createManager(channelList=[ch])
    manager.ytFetcher = type("F", (), {
      "fetchRecentVideos": lambda self, cid: [vid0, vid1]
    })()
    manager._downloadVideo = lambda channel, video, quality, timeout: True
    with unittest.mock.patch("managedYoutubeDL.manager.time.sleep"):
      downloaded, failed = manager.downloadNewVideos(quality=QUALITY)
    self.assertEqual((downloaded, failed), (2, 0))
    self.assertTrue(manager.haveSeenVideo(ch, vid0))
    self.assertTrue(manager.haveSeenVideo(ch, vid1))
    self.assertEqual(ch.minVideoDate, vid1.publishedAt)

    ###########################################################################
    # TEST: failed download → counted as failed, not added to seen
    ###########################################################################
    ch  = makeChannel(0)
    vid = makeVideo(0)
    manager = test_Manager.createManager(channelList=[ch])
    manager.ytFetcher = type("F", (), {
      "fetchRecentVideos": lambda self, cid: [vid]
    })()
    manager._downloadVideo = lambda channel, video, quality, timeout: False
    with unittest.mock.patch("managedYoutubeDL.manager.time.sleep"):
      downloaded, failed = manager.downloadNewVideos(quality=QUALITY)
    self.assertEqual((downloaded, failed), (0, 1))
    self.assertFalse(manager.haveSeenVideo(ch, vid))

    ###########################################################################
    # TEST: mix of success and failure → correct counts
    ###########################################################################
    ch      = makeChannel(0)
    vid0    = makeVideo(0)
    vid1    = makeVideo(1)
    results = [True, False]
    idx     = [0]
    def alternating(channel, video, quality, timeout):
      r = results[idx[0] % 2]; idx[0] += 1; return r
    manager = test_Manager.createManager(channelList=[ch])
    manager.ytFetcher = type("F", (), {
      "fetchRecentVideos": lambda self, cid: [vid0, vid1]
    })()
    manager._downloadVideo = alternating
    with unittest.mock.patch("managedYoutubeDL.manager.time.sleep"):
      downloaded, failed = manager.downloadNewVideos(quality=QUALITY)
    self.assertEqual((downloaded, failed), (1, 1))

    ###########################################################################
    # TEST: minVideoDate not rolled back when video is older than current
    ###########################################################################
    ch   = makeChannel(0)
    vid0 = makeVideo(0)   # Jan 1
    vid1 = makeVideo(1)   # Jan 2
    ch.setMinVideoDate(vid1.publishedAt)   # already at Jan 2
    manager = test_Manager.createManager(channelList=[ch])
    manager.ytFetcher = type("F", (), {
      "fetchRecentVideos": lambda self, cid: [vid0]  # only Jan 1 video returned
    })()
    manager._downloadVideo = lambda channel, video, quality, timeout: True
    with unittest.mock.patch("managedYoutubeDL.manager.time.sleep"):
      manager.downloadNewVideos(quality=QUALITY)
    self.assertEqual(ch.minVideoDate, vid1.publishedAt)


  def test_downloadNewVideos_idempotentAcrossRuns(self):
    """
    # The core promise of the tool: a video downloaded on one run is NOT
    # downloaded again on the next run, even if the API still returns it.
    """
    logger.info("test_downloadNewVideos_idempotentAcrossRuns")
    import unittest.mock

    UTC     = datetime.timezone.utc
    QUALITY = Manager.VideoQuality.QUALITY_MAX

    def makeVideo(n):
      return Video(
        title="video-{}".format(n),
        id="vid-id-{}".format(n),
        publishedAt=datetime.datetime(2020, 1, n + 1, tzinfo=UTC),
      )

    ch   = Channel(title="ch-0", id="ch-id-0", ignore=False)
    vid0 = makeVideo(0)
    vid1 = makeVideo(1)
    vid2 = makeVideo(2)

    # record which videos _downloadVideo was actually asked to download
    downloadCalls = []
    manager = test_Manager.createManager(channelList=[ch])
    manager._downloadVideo = lambda channel, video, quality, timeout: (
      downloadCalls.append(video.id) or True)

    # RUN 1: vid0 and vid1 are available, both should download
    manager.ytFetcher = type("F", (), {
      "fetchRecentVideos": lambda self, cid: [vid0, vid1]
    })()
    with unittest.mock.patch("managedYoutubeDL.manager.time.sleep"):
      downloaded, failed = manager.downloadNewVideos(quality=QUALITY)
    self.assertEqual((downloaded, failed), (2, 0))
    self.assertEqual(downloadCalls, [vid0.id, vid1.id])

    # RUN 2: the same two videos are still returned, plus a new vid2
    downloadCalls.clear()
    manager.ytFetcher = type("F", (), {
      "fetchRecentVideos": lambda self, cid: [vid0, vid1, vid2]
    })()
    with unittest.mock.patch("managedYoutubeDL.manager.time.sleep"):
      downloaded, failed = manager.downloadNewVideos(quality=QUALITY)

    # TEST: only the new video is downloaded; already-seen videos are skipped
    self.assertEqual((downloaded, failed), (1, 0))
    self.assertEqual(downloadCalls, [vid2.id])


  def test_downloadNewVideos_retriesAfterTimeout(self):
    """
    # A download that times out once is retried (after postTimeoutWait) and
    # then succeeds; the video is ultimately counted and marked seen.
    """
    logger.info("test_downloadNewVideos_retriesAfterTimeout")
    import unittest.mock

    UTC     = datetime.timezone.utc
    QUALITY = Manager.VideoQuality.QUALITY_MAX

    ch  = Channel(title="ch-0", id="ch-id-0", ignore=False)
    vid = Video(title="video-0", id="vid-id-0",
                publishedAt=datetime.datetime(2020, 1, 1, tzinfo=UTC))

    manager = test_Manager.createManager(channelList=[ch])
    manager.ytFetcher = type("F", (), {
      "fetchRecentVideos": lambda self, cid: [vid]
    })()

    # first attempt times out, second attempt succeeds
    attempts = [0]
    def flakyDownload(channel, video, quality, timeout):
      attempts[0] += 1
      if attempts[0] == 1:
        raise TimeoutError()
      return True
    manager._downloadVideo = flakyDownload

    with unittest.mock.patch("managedYoutubeDL.manager.time.sleep"):
      downloaded, failed = manager.downloadNewVideos(quality=QUALITY)

    # TEST: retried exactly once, then succeeded and was recorded as seen
    self.assertEqual(attempts[0], 2)
    self.assertEqual((downloaded, failed), (1, 0))
    self.assertTrue(manager.haveSeenVideo(ch, vid))


  def test_updateChannels(self):
    """  """
    logger.info("test_updateChannels")

    def ch(n):
      return Channel(title="title-{}".format(n), id="id-{}".format(n))

    def makeFetcher(subscribed):
      return type("F", (), {
        "fetchMySubscribedChannels": lambda self: list(subscribed)
      })()

    # TEST: starting from empty list, all subscribed channels are added
    manager = test_Manager.createManager(channelList=[])
    manager.ytFetcher = makeFetcher([ch(0), ch(1), ch(2)])
    added, removed = manager.updateChannels()
    self.assertEqual(added,   3)
    self.assertEqual(removed, 0)
    for i in range(3):
      self.assertIn(ch(i), manager.channelList)

    # TEST: new channel added when not in current list
    manager = test_Manager.createManager(channelList=[ch(0), ch(1)])
    manager.ytFetcher = makeFetcher([ch(0), ch(1), ch(2)])
    added, removed = manager.updateChannels()
    self.assertEqual(added,   1)
    self.assertEqual(removed, 0)
    self.assertIn(ch(2), manager.channelList)

    # TEST: removed channel is no longer in list
    manager = test_Manager.createManager(channelList=[ch(0), ch(1), ch(2)])
    manager.ytFetcher = makeFetcher([ch(0), ch(2)])
    added, removed = manager.updateChannels()
    self.assertEqual(added,   0)
    self.assertEqual(removed, 1)
    self.assertNotIn(ch(1), manager.channelList)
    self.assertIn(ch(0), manager.channelList)
    self.assertIn(ch(2), manager.channelList)

    # TEST: no changes returns (0, 0)
    manager = test_Manager.createManager(channelList=[ch(0), ch(1)])
    manager.ytFetcher = makeFetcher([ch(0), ch(1)])
    added, removed = manager.updateChannels()
    self.assertEqual(added,   0)
    self.assertEqual(removed, 0)
    self.assertEqual(len(manager.channelList), 2)

    # TEST: mix — some added, some removed, some unchanged
    manager = test_Manager.createManager(channelList=[ch(0), ch(1), ch(2)])
    manager.ytFetcher = makeFetcher([ch(1), ch(2), ch(3)])
    added, removed = manager.updateChannels()
    self.assertEqual(added,   1)
    self.assertEqual(removed, 1)
    self.assertNotIn(ch(0), manager.channelList)
    self.assertIn(ch(1), manager.channelList)
    self.assertIn(ch(2), manager.channelList)
    self.assertIn(ch(3), manager.channelList)


    
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
    
    
  def test_filterChannelVideos(self):
    """  """
    logger.info("test_filterChannelVideos")

    UTC       = datetime.timezone.utc
    EPOCH     = datetime.datetime.fromtimestamp(0, UTC)
    BASE_DATE = datetime.datetime(2020, 1, 10, tzinfo=UTC)

    def createChannel(**kwargs):
      kwargs.setdefault("title", "channel title")
      kwargs.setdefault("id",    "channel-id")
      return Channel(**kwargs)

    def createVideo(**kwargs):
      kwargs.setdefault("title",       "video title")
      kwargs.setdefault("id",          "video-id")
      kwargs.setdefault("publishedAt", BASE_DATE)
      return Video(**kwargs)

    ###########################################################################
    # TEST: non-Video in list raises TypeError
    # (objects must have a .title attribute; the type check follows a debug log)
    ###########################################################################
    manager = test_Manager.createManager()
    channel = createChannel()
    for bad in ["string", Channel(), Channel(title="has a title")]:
      self.assertRaises(TypeError, manager.filterChannelVideos, channel, [bad])

    ###########################################################################
    # TEST: seen filter
    ###########################################################################
    manager = test_Manager.createManager()
    channel = createChannel()
    video   = createVideo()
    self.assertIn(video, manager.filterChannelVideos(channel, [video]))
    manager.addSeenVideo(channel, video)
    self.assertNotIn(video, manager.filterChannelVideos(channel, [video]))

    ###########################################################################
    # TEST: date filter — channel minVideoDate
    ###########################################################################
    manager = test_Manager.createManager(globalMinVideoDate=EPOCH)
    channel = createChannel(minVideoDate=BASE_DATE)

    video = createVideo(publishedAt=BASE_DATE)
    self.assertIn(video, manager.filterChannelVideos(channel, [video]))

    video = createVideo(publishedAt=BASE_DATE + timedelta(seconds=1))
    self.assertIn(video, manager.filterChannelVideos(channel, [video]))

    video = createVideo(publishedAt=BASE_DATE - timedelta(seconds=1))
    self.assertNotIn(video, manager.filterChannelVideos(channel, [video]))

    ###########################################################################
    # TEST: date filter — globalMinVideoDate
    ###########################################################################
    manager = test_Manager.createManager(globalMinVideoDate=BASE_DATE)
    channel = createChannel()

    video = createVideo(publishedAt=BASE_DATE)
    self.assertIn(video, manager.filterChannelVideos(channel, [video]))

    video = createVideo(publishedAt=BASE_DATE - timedelta(seconds=1))
    self.assertNotIn(video, manager.filterChannelVideos(channel, [video]))

    ###########################################################################
    # TEST: effective minVideoDate = stricter of channel vs global
    ###########################################################################
    DAY5  = datetime.datetime(2020, 1,  5, tzinfo=UTC)
    DAY7  = datetime.datetime(2020, 1,  7, tzinfo=UTC)
    DAY10 = datetime.datetime(2020, 1, 10, tzinfo=UTC)

    # global stricter
    manager = test_Manager.createManager(globalMinVideoDate=DAY10)
    channel = createChannel(minVideoDate=DAY5)
    video   = createVideo(publishedAt=DAY7)
    self.assertNotIn(video, manager.filterChannelVideos(channel, [video]))

    # channel stricter
    manager = test_Manager.createManager(globalMinVideoDate=DAY5)
    channel = createChannel(minVideoDate=DAY10)
    video   = createVideo(publishedAt=DAY7)
    self.assertNotIn(video, manager.filterChannelVideos(channel, [video]))

    ###########################################################################
    # TEST: maxVideoDate filter
    ###########################################################################
    manager = test_Manager.createManager(globalMinVideoDate=EPOCH, globalMaxVideoDate=BASE_DATE)
    channel = createChannel()

    video = createVideo(publishedAt=BASE_DATE)
    self.assertIn(video, manager.filterChannelVideos(channel, [video]))

    video = createVideo(publishedAt=BASE_DATE + timedelta(seconds=1))
    self.assertNotIn(video, manager.filterChannelVideos(channel, [video]))

    ###########################################################################
    # TEST: include filter — channel
    ###########################################################################
    manager = test_Manager.createManager(globalMinVideoDate=EPOCH)
    channel = createChannel(includeFilter=".*match.*")

    video = createVideo(title="this matches")
    self.assertIn(video, manager.filterChannelVideos(channel, [video]))

    video = createVideo(title="no hit")
    self.assertNotIn(video, manager.filterChannelVideos(channel, [video]))

    ###########################################################################
    # TEST: include filter — global
    ###########################################################################
    manager = test_Manager.createManager(globalMinVideoDate=EPOCH, globalIncludeFilter=".*match.*")
    channel = createChannel()

    video = createVideo(title="this matches")
    self.assertIn(video, manager.filterChannelVideos(channel, [video]))

    video = createVideo(title="no hit")
    self.assertNotIn(video, manager.filterChannelVideos(channel, [video]))

    ###########################################################################
    # TEST: both include filters must match
    ###########################################################################
    manager = test_Manager.createManager(globalMinVideoDate=EPOCH, globalIncludeFilter=".*global.*")
    channel = createChannel(includeFilter=".*channel.*")

    video = createVideo(title="both channel and global")
    self.assertIn(video, manager.filterChannelVideos(channel, [video]))

    video = createVideo(title="only global here")
    self.assertNotIn(video, manager.filterChannelVideos(channel, [video]))

    ###########################################################################
    # TEST: exclude filter — channel
    ###########################################################################
    manager = test_Manager.createManager(globalMinVideoDate=EPOCH)
    channel = createChannel(excludeFilter=".*exclude.*")

    video = createVideo(title="exclude this")
    self.assertNotIn(video, manager.filterChannelVideos(channel, [video]))

    video = createVideo(title="allow this")
    self.assertIn(video, manager.filterChannelVideos(channel, [video]))

    ###########################################################################
    # TEST: exclude filter — global
    ###########################################################################
    manager = test_Manager.createManager(globalMinVideoDate=EPOCH, globalExcludeFilter=".*exclude.*")
    channel = createChannel()

    video = createVideo(title="exclude this")
    self.assertNotIn(video, manager.filterChannelVideos(channel, [video]))

    video = createVideo(title="allow this")
    self.assertIn(video, manager.filterChannelVideos(channel, [video]))

    ###########################################################################
    # TEST: duration filter
    ###########################################################################
    ONE_MIN  = timedelta(minutes=1)
    TEN_MIN  = timedelta(minutes=10)

    def makeManagerWithLength(minLen=None, maxLen=None):
      m = test_Manager.createManager(
        globalMinVideoDate=EPOCH,
        globalMinVideoLength=minLen,
        globalMaxVideoLength=maxLen,
      )
      return m

    def setFakeDuration(manager, duration):
      manager.ytFetcher = type("F", (), {
        "fetchVideoDetails": lambda self, v: {"duration": duration}
      })()

    channel = createChannel()
    video   = createVideo()

    # exactly at min passes
    manager = makeManagerWithLength(minLen=ONE_MIN)
    setFakeDuration(manager, ONE_MIN)
    self.assertIn(video, manager.filterChannelVideos(channel, [video]))

    # below min excluded
    manager = makeManagerWithLength(minLen=ONE_MIN)
    setFakeDuration(manager, ONE_MIN - timedelta(seconds=1))
    self.assertNotIn(video, manager.filterChannelVideos(channel, [video]))

    # exactly at max passes
    manager = makeManagerWithLength(maxLen=TEN_MIN)
    setFakeDuration(manager, TEN_MIN)
    self.assertIn(video, manager.filterChannelVideos(channel, [video]))

    # above max excluded
    manager = makeManagerWithLength(maxLen=TEN_MIN)
    setFakeDuration(manager, TEN_MIN + timedelta(seconds=1))
    self.assertNotIn(video, manager.filterChannelVideos(channel, [video]))

    # unknown duration (None) excluded when filter is set
    manager = makeManagerWithLength(minLen=ONE_MIN)
    setFakeDuration(manager, None)
    self.assertNotIn(video, manager.filterChannelVideos(channel, [video]))

    # duration fetch not called when no length filters set
    fetchCount = [0]
    manager = test_Manager.createManager(globalMinVideoDate=EPOCH)
    manager.ytFetcher = type("F", (), {
      "fetchVideoDetails": lambda self, v: fetchCount.__setitem__(0, fetchCount[0]+1) or {"duration": ONE_MIN}
    })()
    manager.filterChannelVideos(createChannel(), [createVideo()])
    self.assertEqual(fetchCount[0], 0)

    # effective minLength = stricter of channel vs global
    manager = test_Manager.createManager(globalMinVideoDate=EPOCH, globalMinVideoLength=ONE_MIN)
    setFakeDuration(manager, timedelta(seconds=30))
    channel = createChannel(minVideoLength=timedelta(minutes=2))
    self.assertNotIn(video, manager.filterChannelVideos(channel, [video]))

    ###########################################################################
    # TEST: short-circuit — seen video does not trigger duration fetch
    ###########################################################################
    fetchCount = [0]
    manager = test_Manager.createManager(globalMinVideoDate=EPOCH, globalMinVideoLength=ONE_MIN)
    manager.ytFetcher = type("F", (), {
      "fetchVideoDetails": lambda self, v: fetchCount.__setitem__(0, fetchCount[0]+1) or {"duration": ONE_MIN}
    })()
    channel = createChannel()
    video   = createVideo()
    manager.addSeenVideo(channel, video)
    manager.filterChannelVideos(channel, [video])
    self.assertEqual(fetchCount[0], 0)

