import logging
logger = logging.getLogger(__name__)

import os
import datetime
import shutil
import tempfile
import yaml
from yaml import MappingNode

class YAMLBuilder:
  
  @staticmethod
  def loadManager(fileLoc: str):
    """
    # Load the data from the <fileLoc> YAML file and use it to create
    # a Manager object
    #
    :param fileLoc:
    :return:
    """
    
    # CHECK: file exists
    if not os.path.exists(fileLoc):
      raise FileNotFoundError("file not found at {}".format(fileLoc))
    
    # load the data
    with open(fileLoc, 'r') as f:
      
      # add constructors for: Channel, Manager, Timedelta
      for builderClass in [YAMLBuilder.Channel, YAMLBuilder.Manager, YAMLBuilder.Timedelta]:
        yaml.SafeLoader.add_constructor(builderClass.YAML_TAG, builderClass.constructor)
      
      # load the yaml data into the manager
      return yaml.safe_load(f)
    
  
  @staticmethod
  def dumpManager(manager, fileLoc: str, overwrite: bool = False):
    """
    # Dump a given a <manager> to the output config file location <fileLoc>
    #
    :param manager:
    :param fileLoc:
    :param overwrite:
    :return:
    """
    from managedYoutubeDL.items   import Channel
    from managedYoutubeDL.manager import Manager
    from datetime import timedelta
    
    # CHECK: file doesn't already exist, or we can overwrite it
    if not overwrite and os.path.exists(fileLoc):
      raise FileExistsError("file already exists at {}".format(fileLoc))
    
    # dump the data
    with open(fileLoc, 'w') as f:
  
      # add representers for: Channel, Manager, Timedelta
      yaml.SafeDumper.add_representer(Channel, YAMLBuilder.Channel.representer)
      yaml.SafeDumper.add_representer(Manager, YAMLBuilder.Manager.representer)
      yaml.SafeDumper.add_representer(timedelta, YAMLBuilder.Timedelta.representer)
      
      # dump the manager
      yaml.safe_dump(manager, f)
  
  
  @staticmethod
  def safeDumpManager(manager, fileLoc: str,
                      overwrite: bool = False, maxChangeFraction=0.1):
    """
    # A safe version of dumpManager that, in addition to dumping <manager>
    # to <fileLoc>, will:
    #  -make sure the resultant config file exists and has data
    #  -make sure any changes to the config file's size are reasonable, i.e.,
    #   within (<maxChangeFraction> * 100) % of the original
    #
    :param manager:
    :param fileLoc:
    :param overwrite:
    :param maxChangeFraction:
    :return:
    """
    
    # CHECK: make sure that if the output file already exists we can overwrite it
    if os.path.exists(fileLoc) and not overwrite:
      raise FileExistsError("output file {} already exists".format(fileLoc))
    
    
    # use a temporary directory for the file
    with tempfile.TemporaryDirectory() as tmpDir:
    
      # create a temp file in the temp directory
      tmpFileLoc = os.path.join(tmpDir, "tmp.config")
      if os.path.exists(tmpFileLoc):
        raise FileExistsError("temp file already exists at {}".format(tmpFileLoc))
    
      # dump the manager to a temporary config file
      YAMLBuilder.dumpManager(manager, tmpFileLoc)
    
      # CHECK: new config file exists
      if not os.path.exists(tmpFileLoc):
        msg = "Could not yaml-ise the manager into the config file"
        logger.error("safeDumpManager: " + msg)
        raise FileNotFoundError(msg)
      
      # if there is an old config file to overwrite
      #  -check everything is okay before overwriting it
      if os.path.exists(fileLoc):
        
        oldConfigFileStats = os.stat(fileLoc)
        newConfigFileStats = os.stat(tmpFileLoc)
      
        # CHECK: new config file has data
        if newConfigFileStats.st_size == 0:
          msg = "New config file size is 0; Original config file is unchanged"
          logger.error("safeDumpManager: " + msg)
          raise SystemError(msg)
      
        # CHECK: new config file hasn't drastically changed
        sizeChange = newConfigFileStats.st_size / max(oldConfigFileStats.st_size, 1)
        logger.debug("safeDumpManager: Config file size change: {} => {} = {}"
                     .format(oldConfigFileStats.st_size, newConfigFileStats.st_size, sizeChange))
        if abs(sizeChange - 1) > maxChangeFraction:
          msg  = "safeDumpManager: New config file changed by more than {}%; "\
                    .format(maxChangeFraction*100)
          msg +=  "Original config file will be backed up"
          logger.warning(msg)
        
          # backup the original config file file
          now = str(datetime.datetime.utcnow().replace(microsecond=0)).replace(":", "-").replace(" ", "--")
          backupFileLoc = "{}.{}.old".format(fileLoc, now)
          shutil.move(fileLoc, backupFileLoc)
        
          # CHECK: old config file doesn't exist anymore and backup does
          if os.path.exists(fileLoc) or not os.path.exists(backupFileLoc):
            msg = "safeDumpManager: Cannot store new config file at {} as old file was not correctly backed up to {}" \
              .format(fileLoc, backupFileLoc)
            logger.error(msg)
            raise FileExistsError(msg)
    
    
      # store the new config file
      shutil.copy2(tmpFileLoc, fileLoc)
      if not os.path.exists(fileLoc):
        msg = "safeDumpManager: Failed to write config file data to {}".format(fileLoc)
        logger.error(msg)
        raise FileExistsError(msg)
  
  
  class Channel:
    YAML_TAG = u"!Channel"
  
    @staticmethod
    def representer(dumper, channel):
      """
      # Called by YAML when dumping a channel
      #
      :param dumper:
      :param channel:
      :return:
      """
    
      # organise the object so title, id, then ignore are first
      #  -remaining keys are ordered backwards-alphabetically since it
      #   groups similar items together
      orderedKeys    = ["title", "id", "ignore"]
      remainingKeys  = list(filter(lambda x: x not in orderedKeys, channel.__dict__.keys()))
      orderedKeys   += sorted(remainingKeys, key=lambda x: "".join(reversed(x)))
    
      # yaml-ise the key:value pairs
      valueList = []
      for key in orderedKeys:
        yamlKey   = dumper.represent_data(key)
        yamlValue = dumper.represent_data(channel.__dict__[key])
        valueList.append((yamlKey, yamlValue))
    
      return MappingNode(YAMLBuilder.Channel.YAML_TAG, valueList)
  
    @staticmethod
    def constructor(loader, node):
      """
      # Called by YAML when loading a channel
      #
      :param loader:
      :param node:
      :return:
      """
      from managedYoutubeDL.items import Channel
      kwargs = loader.construct_mapping(node, deep=True)
      return Channel(**kwargs)
  
  
  class Manager:
    YAML_TAG = u"!Manager"
    
    @staticmethod
    def representer(dumper, manager):
      """
      # Called by YAML when dumping a Manager
      #
      :param dumper:
      :param manager:
      :return:
      """
      
      # final list of ordered keys
      orderedKeys = []
      
      # all keys in Manager to yaml-ise
      excludeKeys = ["ytFetcher"]
      allKeys = [key for key in manager.__dict__.keys() if key not in excludeKeys]
      
      # order all keys by type
      byTypeDict = {}
      for key in allKeys:
        value = manager.__dict__[key]
        byTypeDict[type(value)] = byTypeDict.get(type(value), []) + [key]
      
      # alphabetically sort the keys of each type
      for keyType in byTypeDict.keys():
        if keyType != type(None):
          byTypeDict[keyType] = sorted(byTypeDict[keyType])
      
      # put all dictionaries then lists at the end
      endTypeList = [list, dict]
      for keyType, keyList in byTypeDict.items():
        if keyType not in endTypeList:
          orderedKeys += keyList
      for endType in endTypeList:
        orderedKeys += byTypeDict.get(endType, [])
      
      # yaml-ise the key:value pairs
      valueList = []
      for key in orderedKeys:
        yamlKey   = dumper.represent_data(key)
        yamlValue = dumper.represent_data(manager.__dict__[key])
        valueList.append((yamlKey, yamlValue))
      
      return MappingNode(YAMLBuilder.Manager.YAML_TAG, valueList)
    
    
    @staticmethod
    def constructor(loader, node):
      """
      # Called by YAML when loading a Manager
      #
      :param loader:
      :param node:
      :return:
      """
      from managedYoutubeDL.manager import Manager
      kwargs = loader.construct_mapping(node, deep=True)
      return Manager(**kwargs)
  
  
  class Timedelta:
    YAML_TAG = u"!timedelta"
    
    @staticmethod
    def representer(dumper, td):
      """
      # Called by YAML when dumping a timedelta
      #
      :param dumper:
      :param td:
      :return:
      """
      serialisedData = str(int(td.total_seconds())) + "s"
      return dumper.represent_scalar(YAMLBuilder.Timedelta.YAML_TAG, serialisedData)
    
    
    @staticmethod
    def constructor(loader, node):
      """
      # Called by YAML when loading a timedelta
      #
      :param loader:
      :param node:
      :return:
      """
      from datetime import timedelta
      value = loader.construct_scalar(node)
      return timedelta(seconds=int(value[:-1]))
  
  