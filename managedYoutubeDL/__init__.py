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
  
  # if it's None we're done
  if timeValue is None:
    return timeValue

  # if it's already a datetime, ensure it's UTC-aware
  if isinstance(timeValue, datetime.datetime):
    if timeValue.tzinfo is None:
      return timeValue.replace(tzinfo=datetime.timezone.utc)
    return timeValue

  # if it's a string, try and convert it (YouTube API uses ISO 8601 with Z suffix)
  elif isinstance(timeValue, str):
    strTime = timeValue.replace("T", " ").replace("Z", "")
    try:
      dt = datetime.datetime.strptime(strTime, "%Y-%m-%d %H:%M:%S.%f")
    except ValueError:
      dt = datetime.datetime.strptime(strTime, "%Y-%m-%d %H:%M:%S")
    return dt.replace(tzinfo=datetime.timezone.utc)
  
  # no idea what this is
  else:
    raise TypeError("timeValue must be None, a datetime, or a string: {}".format(timeValue))
  
