import base64
import datetime
import os
import pickle
import tempfile
import logging
import yaml
import unittest

from io import StringIO
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


from managedYoutubeDL import YAMLBuilder
from managedYoutubeDL.items import Channel
from managedYoutubeDL.manager import Manager

"""
sudo python3 -m unittest tests.test_yamlBuilder.test_YAMLBuilder.
.
"""


class test_YAMLBuilder(unittest.TestCase):
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
  def createmanager(**kwargs):
    
    arguments = {
      "clientSecretsFile":    None,
      "pickledCredentials":   base64.b64encode(pickle.dumps("pickleStr")).decode("utf-8"),
      "downloadDirectory":    str(os.path.dirname(os.path.realpath(__file__))),
      "ffmpegLocation":       str(os.path.realpath(__file__)),
      "channelList":          [],
      "globalMinVideoDate":   str(datetime.datetime.utcfromtimestamp(0)),
      "globalMaxVideoDate":   str(datetime.datetime.utcfromtimestamp(1)),
      "seenChannelVideos":    {"a": "b"},
      "globalIncludeFilter":  "something",
      "globalExcludeFilter":  "other",
      "globalMinVideoLength": timedelta(0),
      "globalMaxVideoLength": timedelta(1),
    }
  
    arguments.update(kwargs)
    return Manager(**arguments), arguments
  
  
  
  def compareDumpedAndLoadedManager(self, manager, arguments):
    """
    # TEST: original manager and loaded manager contain the same values
    #
    :param manager:
    :param arguments:
    :return:
    """
    with tempfile.TemporaryDirectory() as tmpDir:
      tempFileLoc = os.path.join(tmpDir, "temp_config.yaml")
    
      # dump manager to file
      YAMLBuilder.dumpManager(manager, tempFileLoc)
    
      # load manager
      loadedManager = YAMLBuilder.loadManager(tempFileLoc)
    
      # TEST: original manager and loaded manager contain the same values
      for argName, _ in arguments.items():
        self.assertEqual(getattr(manager, argName), getattr(loadedManager, argName))
        
  
  def test_dumpAndLoad(self):
    """  """
    logger.info("test_dumpAndLoad")
    
    
    ###########################################################################
    # TEST: basic dump and load
    ###########################################################################
    manager, arguments = test_YAMLBuilder.createmanager()
    self.compareDumpedAndLoadedManager(manager, arguments)
    
    
    ###########################################################################
    # TEST: populated channelList
    ###########################################################################
    
    numChannels = 100
    channelList = [Channel(title="title-{}".format(i), id="id-{}".format(i)) for i in range(numChannels)]
    manager, arguments = test_YAMLBuilder.createmanager(channelList=channelList)
    self.compareDumpedAndLoadedManager(manager, arguments)
    
    
    ###########################################################################
    # TEST: populated seenChannelVideos
    ###########################################################################
    
    numChannels         = 100
    numVideosPerChannel =  10
    seenChannelVideos = {
      "channelID-{}".format(iCh): ["videoID-{}-{}".format(iCh, iVid)
         for iVid in range(numVideosPerChannel)] for iCh in range(numChannels)
    }
    manager, arguments = test_YAMLBuilder.createmanager(seenChannelVideos=seenChannelVideos)
    self.compareDumpedAndLoadedManager(manager, arguments)
    
    
    ###########################################################################
    # TEST: overwriting existing files
    ###########################################################################
    
    # basic manager
    manager, arguments = test_YAMLBuilder.createmanager()
    
    with tempfile.TemporaryDirectory() as tmpDir:
      tempFileLoc = os.path.join(tmpDir, "temp_config.yaml")
  
      # TEST: dumping to an existing file fails by default
      with open(tempFileLoc, "w") as _: pass
      self.assertRaises(FileExistsError, YAMLBuilder.dumpManager, manager, tempFileLoc)

      # TEST: overwriting will overwrite the original file
      with open(tempFileLoc, "w") as _: pass
      self.assertEqual(os.stat(tempFileLoc).st_size, 0)
      YAMLBuilder.dumpManager(manager, tempFileLoc, overwrite=True)
      self.assertGreater(os.stat(tempFileLoc).st_size, 0)
  
      # TEST: original manager and loaded manager contain the same values
      loadedManager = YAMLBuilder.loadManager(tempFileLoc)
      for argName, argValue in arguments.items():
        self.assertEqual(getattr(manager, argName), getattr(loadedManager, argName))
    


  def test_safeDump(self):
    """  """
    logger.info("test_safeDump")
    
    # overwrite dump method later, so remember the original now
    originalDumpFn = YAMLBuilder.dumpManager
    
    # basic manager
    manager, arguments = test_YAMLBuilder.createmanager()

    with tempfile.TemporaryDirectory() as tmpDir:
      tempFileLoc = os.path.join(tmpDir, "temp_config.yaml")

      #########################################################################
      # TEST: raise error when newly dumped file doesn't exist
      #########################################################################
      YAMLBuilder.dumpManager = lambda _manager, _fileLoc, _overwrite=False: None
      self.assertRaises(FileNotFoundError, YAMLBuilder.safeDumpManager, manager, tempFileLoc)


      #########################################################################
      # TEST: raise error when newly dumped file has size of 0
      #########################################################################
      open(tempFileLoc, "w").close()
      YAMLBuilder.dumpManager = lambda _manager, _fileLoc, overwrite=False: open(_fileLoc, "w").close()
      self.assertRaises(SystemError, YAMLBuilder.safeDumpManager, manager, tempFileLoc, True)
      os.remove(tempFileLoc)
      
      
      #########################################################################
      # TEST: backup file's size difference is greater than expected
      #########################################################################
      
      # create a small, config file
      testStr = "test file contents"
      with open(tempFileLoc, "w") as f: f.write(testStr)
      
      # reinstate the original dump function
      YAMLBuilder.dumpManager = originalDumpFn
      
      # safe-dump the manager
      YAMLBuilder.safeDumpManager(manager, tempFileLoc, overwrite=True, maxChangeFraction=0.0)
      
      # TEST: the newly created dump file matches the manager
      self.compareDumpedAndLoadedManager(manager, arguments)
      
      # TEST: there should be a newly created backup file
      #  -should be only other file in this temp directory
      #  -should end in ".old"
      self.assertEqual(len(list(os.scandir(tmpDir))), 2)
      newFileLoc = None
      for item in os.scandir(tmpDir):
        if item.is_file() and item.name != os.path.basename(tempFileLoc):
          newFileLoc = os.path.join(tmpDir, item.name)
          #break
      self.assertIsNotNone(newFileLoc)
      self.assertEqual(os.path.splitext(newFileLoc)[-1], ".old")

      # TEST: the backup file matches the original config file
      with open(newFileLoc, "r") as backupFile:
        self.assertListEqual(backupFile.readlines(), [testStr])

    
    # undo our fakery
    YAMLBuilder.dumpManager = originalDumpFn



  def test_Channel(self):
    """  """
    logger.info("test_Channel")
    
    arguments = {
      "title":          "string title",
      "id":             "string id",
      "publishedAt":    str(datetime.datetime.utcfromtimestamp(0)),
      "ignore":         False,
      "excludeFilter":  "string exclude filter",
      "includeFilter":  "string include filter",
      "minVideoDate":   str(datetime.datetime.utcfromtimestamp(1)),
      "maxVideoDate":   str(datetime.datetime.utcfromtimestamp(2)),
      "minVideoLength": timedelta(2),
      "maxVideoLength": timedelta(3),
    }
    
    channel = Channel(**arguments)
    
    # TEST: all channel values are set
    for argName, argValue in arguments.items():
      self.assertEqual(str(getattr(channel, argName)), str(argValue))
    self.assertListEqual(list(arguments.keys()), list(channel.__dict__.keys()))
    
    
    with tempfile.TemporaryDirectory() as tmpDir:
      tempFileLoc = os.path.join(tmpDir, "temp_config.yaml")
      
      # dump the channel
      with open(tempFileLoc, 'w') as f:
        yaml.SafeDumper.add_representer(timedelta, YAMLBuilder.Timedelta.representer)
        yaml.SafeDumper.add_representer(Channel, YAMLBuilder.Channel.representer)
        yaml.safe_dump(channel, f)

      # load the channel
      with open(tempFileLoc, 'r') as f:
        yaml.SafeLoader.add_constructor(YAMLBuilder.Timedelta.YAML_TAG, YAMLBuilder.Timedelta.constructor)
        yaml.SafeLoader.add_constructor(YAMLBuilder.Channel.YAML_TAG, YAMLBuilder.Channel.constructor)
        loadedChannel = yaml.safe_load(f)
      
      
      # TEST: loaded channel is the same as the original
      self.assertEqual(channel, loadedChannel)
      for argName in arguments.keys():
        self.assertEqual(str(getattr(channel, argName)), str(getattr(loadedChannel, argName)))
  
  
  def test_Manager(self):
    """  """
    logger.info("test_Manager")
  
    # arguments and examples of acceptable values
    arguments = {
      "clientSecretsFile":    None,
      "pickledCredentials":   base64.b64encode(pickle.dumps("pickleStr")).decode("utf-8"),
      "downloadDirectory":    str(os.path.dirname(os.path.realpath(__file__))),
      "ffmpegLocation":       str(os.path.realpath(__file__)),
      "channelList":          [],
      "globalMinVideoDate":   str(datetime.datetime.utcfromtimestamp(0)),
      "globalMaxVideoDate":   str(datetime.datetime.utcfromtimestamp(1)),
      "seenChannelVideos":    {"a":"b"},
      "globalIncludeFilter":  "something",
      "globalExcludeFilter":  "other",
      "globalMinVideoLength": timedelta(0),
      "globalMaxVideoLength": timedelta(1),
      "downloadTimeout":      timedelta(0),
      "postTimeoutWait":      timedelta(0),
    }
  
    manager = Manager(**arguments)
    
    # TEST: our test has assigned all arguments
    initAssignedFields = ["ytFetcher"]
    self.assertListEqual(list(arguments.keys())+initAssignedFields, list(manager.__dict__.keys()))
    
    # TEST: all manager values are set
    for argName, argValue in arguments.items():
      self.assertEqual(str(getattr(manager, argName)), str(argValue))
  
    with tempfile.TemporaryDirectory() as tmpDir:
      tempFileLoc = os.path.join(tmpDir, "temp_config.yaml")
    
      # dump the manager
      with open(tempFileLoc, 'w') as f:
        yaml.SafeDumper.add_representer(timedelta, YAMLBuilder.Timedelta.representer)
        yaml.SafeDumper.add_representer(Channel, YAMLBuilder.Channel.representer)
        yaml.SafeDumper.add_representer(Manager, YAMLBuilder.Manager.representer)
        yaml.safe_dump(manager, f)
    
      # load the manager
      with open(tempFileLoc, 'r') as f:
        yaml.SafeLoader.add_constructor(YAMLBuilder.Timedelta.YAML_TAG, YAMLBuilder.Timedelta.constructor)
        yaml.SafeLoader.add_constructor(YAMLBuilder.Channel.YAML_TAG, YAMLBuilder.Channel.constructor)
        yaml.SafeLoader.add_constructor(YAMLBuilder.Manager.YAML_TAG, YAMLBuilder.Manager.constructor)
        loadedManager = yaml.safe_load(f)
    
      # TEST: loaded manager is the same as the original
      for argName in arguments.keys():
        self.assertEqual(str(getattr(manager, argName)), str(getattr(loadedManager, argName)))
  
  
  def test_timedelta(self):
    """  """
    logger.info("test_timedelta")
    
    numIntervals = 3
    argCombinations = [(i,j,k) for i in range(numIntervals) for j in range(numIntervals) for k in range(numIntervals)]
    for timedeltaArgs in argCombinations:
      
      td = timedelta(hours=timedeltaArgs[0], minutes=timedeltaArgs[1], seconds=timedeltaArgs[2])

      with tempfile.TemporaryDirectory() as tmpDir:
        tempFileLoc = os.path.join(tmpDir, "temp_config.yaml")
    
        # dump the timedelta
        with open(tempFileLoc, 'w') as f:
          yaml.SafeDumper.add_representer(timedelta, YAMLBuilder.Timedelta.representer)
          yaml.safe_dump(td, f)
    
        # load the timedelta
        with open(tempFileLoc, 'r') as f:
          yaml.SafeLoader.add_constructor(YAMLBuilder.Timedelta.YAML_TAG, YAMLBuilder.Timedelta.constructor)
          loadedTimedelta = yaml.safe_load(f)
    
        # TEST: loaded timedelta is the same as the original
        self.assertEqual(td, loadedTimedelta)

