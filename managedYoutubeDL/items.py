import logging
logger = logging.getLogger(__name__)

import datetime
import re
from datetime import timedelta

class Item:
  pass


class Channel(Item):
  
  def setTitle(self, title):
    self.title = title
  
  def setID(self, channelID):
    self.id = channelID
  
  def setPublishedAt(self, publishedAt):
    from managedYoutubeDL import convertTime
    self.publishedAt = convertTime(publishedAt)
    
  def setIgnore(self, ignore):
    self.ignore = ignore
    
  def setExcludeFilter(self, excludeFilter):
    self.excludeFilter = excludeFilter
    
  def setIncludeFilter(self, includeFilter):
    self.includeFilter = includeFilter
    
  def setMinVideoDate(self, minVideoDate):
    from managedYoutubeDL import convertTime
    self.minVideoDate = convertTime(minVideoDate)
  
  def setMaxVideoDate(self, maxVideoDate):
    from managedYoutubeDL import convertTime
    self.maxVideoDate = convertTime(maxVideoDate)
  
  def setMinVideoLength(self, minVideoLength):
    if isinstance(minVideoLength, int):
      self.minVideoLength = timedelta(seconds=minVideoLength)
    elif isinstance(minVideoLength, timedelta):
      self.minVideoLength = minVideoLength
    elif minVideoLength is None:
      self.minVideoLength = None
    else:
      raise TypeError("minVideoLength must be an int, None, or timedelta")
    
  def setMaxVideoLength(self, maxVideoLength):
    if isinstance(maxVideoLength, int):
      self.maxVideoLength = timedelta(seconds=maxVideoLength)
    elif isinstance(maxVideoLength, timedelta):
      self.maxVideoLength = maxVideoLength
    elif maxVideoLength is None:
      self.maxVideoLength = None
    else:
      raise TypeError("maxVideoLength must be an int, None, or timedelta")
  
  def __init__(self, **kwargs):
    self.title          = None
    self.id             = None
    self.publishedAt    = None
    self.ignore         = None
    self.excludeFilter  = None
    self.includeFilter  = None
    self.minVideoDate   = None
    self.maxVideoDate   = None
    self.minVideoLength = None
    self.maxVideoLength = None
    
    # channel details
    self.setTitle(kwargs.get("title", None))
    self.setID(kwargs.get("id", None))
    self.setPublishedAt(kwargs.get("publishedAt", None))
    
    # limits on video length
    self.setMinVideoLength(kwargs.get("minVideoLength", timedelta(seconds=0)))
    self.setMaxVideoLength(kwargs.get("maxVideoLength", None))
    
    # should we ignore this channel
    self.setIgnore(kwargs.get("ignore", None))

    # title filters: exclude videos that match
    self.setExcludeFilter(kwargs.get("excludeFilter", None))

    # title filters: include videos that match
    self.setIncludeFilter(kwargs.get("includeFilter", None))
    
    # date filter: published after
    self.setMinVideoDate(kwargs.get("minVideoDate", datetime.datetime.utcfromtimestamp(0)))
    self.setMaxVideoDate(kwargs.get("maxVideoDate", None))
    
    
    # CHECK: no extra attributes were passed
    extraKeys = [x for x in kwargs if x not in self.__dict__.keys()]
    if len(extraKeys) > 0:
      raise AttributeError("unknown attribute(s): {}".format(extraKeys))
  
    
  def __str__(self):
    return "\n".join(["{}: {}".format(k,v) for k,v in self.__dict__.items()])


  def __eq__(self, other):
    if not isinstance(other, Channel):
      return False
    else:
      return self.title == other.title and self.id == other.id
  
  

  
class Video(Item):
  
  def __init__(self, **kwargs):
    from managedYoutubeDL import convertTime
    
    self.title        = kwargs.get("title", None)
    self.id           = kwargs.get("id", None)
    self.thumbnailURL = kwargs.get("thumbnailURL", None)
    
    publishedAt = kwargs.get("publishedAt", None)
    self.publishedAt = convertTime(publishedAt)
    
    # CHECK: no extra attributes were passed
    extraKeys = [x for x in kwargs if x not in self.__dict__.keys()]
    if len(extraKeys) > 0:
      raise AttributeError("unknown attribute(s): {}".format(extraKeys))
    
    
  def __str__(self):
    st  = "title: {}\n".format(self.title)
    st += "id: {}\n".format(self.id)
    st += "publishedAt: {}\n".format(self.publishedAt)
    st += "thumbnailURL: {}\n".format(self.thumbnailURL)
    return st

  def __eq__(self, other):
    if not isinstance(other, Video):
      return False
    else:
      return self.title == other.title and self.id == other.id
    