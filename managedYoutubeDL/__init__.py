import datetime

from managedYoutubeDL.fetcher import Fetcher
from managedYoutubeDL.yamlBuilder import YAMLBuilder



def convertTime(timeValue):
  """
  # Convert a value to datetime.datetime
  #
  :param timeValue:
  :return:
  """
  
  # if it's None, or already a datetime, we're done
  if timeValue is None or isinstance(timeValue, datetime.datetime):
    return timeValue
  
  # if it's a string, try and convert it
  elif isinstance(timeValue, str):
    strTime = timeValue.replace("T", " ").replace("Z", "")
    try:
      return datetime.datetime.strptime(strTime, "%Y-%m-%d %H:%M:%S.%f")
    except ValueError:
      return datetime.datetime.strptime(strTime, "%Y-%m-%d %H:%M:%S")
  
  # no idea what this is
  else:
    raise TypeError("timeValue must be None, a datetime, or a string: {}".format(timeValue))
  
