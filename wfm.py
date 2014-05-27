from __future__ import print_function

import collections
import struct
import array
import sys
import os

# Copyright (c) 2013, Matthias Blaicher
# All rights reserved.
# 
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions are met: 
# 
# 1. Redistributions of source code must retain the above copyright notice, this
#   list of conditions and the following disclaimer. 
# 2. Redistributions in binary form must reproduce the above copyright notice,
#   this list of conditions and the following disclaimer in the documentation
#   and/or other materials provided with the distribution. 
# 
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS" AND
# ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED
# WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE
# DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT OWNER OR CONTRIBUTORS BE LIABLE FOR
# ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES
# (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES;
# LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND
# ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
# (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF THIS
# SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.


class FormatError(Exception):
  pass


def _parseFile(f, description, leading="<", strict = True):
  """
  Parse a binary file according to the provided description.
  
  The description is a list of triples, which contain the fieldname, datatype
  and a test condition.
  """
  
  data = collections.OrderedDict()
  
  for field, t, test in description:
    if t == "nested":
      data[field] = _parseFile(f, test, leading)
    else:
      binary_format = leading+t
      tmp = f.read(struct.calcsize(binary_format))
      value = struct.unpack(binary_format, tmp)[0]
      data[field] = value
      
      if test:
        scope, condition, match = test
        
        assert scope in ("expect", "require")
        assert condition  in ("==", ">=", "<=", "<", ">", "in")
        matches = eval("value %s match" % condition)
        
        if not matches and scope == "require":
          raise FormatError("Field %s %s %s not met, got %s" % (field, condition, match, value))
        
        if strict and not matches and scope == "expect":
          raise FormatError("Field %s %s %s not met, got %s" % (field, condition, match, value))
        
  return data

def parseRigolWFM(f, strict=True):
  """
  Parse a file object which has opened a Rigol WFM file in read-binary 
  mode (rb).
  
  The parser has been developed based on a RIGOL DS1052E and protocol 
  information derived from http://meteleskublesku.cz/wfm_view/file_wfm.zip
  and own experimentation.
  
  The result of the parsing is a nested dictionary containing all relevant data.
  
  Note, that trigger information might be per-channel specific (i.e. in 
  alternate trigger mode). In such cases, you have to use the trigger 
  information in the channel data.
  """
  
  # # # #
  # First read in all the known fields and data of the waveform file. It is
  # interpreted later on.
  

  chan_header  = (
    ("scaleD",     "i", None),
    
    ("shiftD",     "h", None),
    ("padding1",   "2s",  ("require", "==", b'\x00'*2)),
    
    ("probeAtt",   "f", ("require", ">", 0)),
    ("invertD",    "B", ("require", "in", (0,1))),
    ("written",    "B", ("require", "in", (0,1))),
    ("invertM",    "B", ("require", "in", (0,1))),
    ("padding2",   "1s",  ("require", "==", b'\x00'*1)),
    ("scaleM",     "i", None),
    ("shiftM",     "h", None)
  )
  
  time_header  = (
    ("scaleD",     "q", None),
    ("delayD",     "q", None),
    ("smpRate",    "f", ("require", ">=", 0)),
    ("scaleM",     "q", None),
    ("delayM",     "q", None)
  )
  
  trigger_header  = (
    ("mode",       "B", None),
    ("source",     "B", None),
    ("coupling",   "B", None),
    ("sweep",      "B", None),
    ("padding1",   "1s",  ("require", "==", b'\x00'*1)),
    ("sens",       "f", None),
    ("holdoff",    "f", None),
    ("level",      "f", None),
    ("direct",     "B", None),
    ("pulseType",  "B", None),
    ("padding2",   "2s",  ("require", "==", b'\x00'*2)),
    ("PulseWidth", "f", None),
    ("slopeType",  "B", None),
    ("padding3",   "3s",  ("require", "==", b'\x00'*3)),
    ("lower",      "f", None),
    ("slopeWid",   "f", None),
    ("videoPol",   "B", None),
    ("videoSync",  "B", None),
    ("videoStd",   "B", None)
  )
  
  logic_analizer_channel = (
    # Todo: Try to add logic analyzer
    ("written",  "B", ("require", "in", (0,1))),
    ("activeCh", "B", ("require", "in", range(16))),
    ("enabledChannels", "H", None), # Each bit corresponds to one enabled channel
    ("position", "16s", None),
    ("group8to15size", "B", ("require", "in", [7,15])),
    ("group0to7size", "B", ("require", "in", [7,15]))
  )
  
  wfm_header = (
    ("magic",    "H",   ("require", "==", 0xa5a5)),
    ("padding1", "2s",  ("require", "==", b'\x00'*2)),
    
    ("unused1",  "4s",   ("expect", "==", b'\x00'*4)),
    ("unused2",  "4s",   ("expect", "==", b'\x00'*4)),
    ("unused3",  "4s",   ("expect", "==", b'\x00'*4)),
    
    ("adcMode",   "B",   ("expect", "in", (0, 1))),
    ("padding2",  "3s",  ("require", "==", b'\x00'*3)),
    
    ("rollStop",  "I",  ("expect", "==", 0)),
    ("unused4",  "4s",   ("expect", "==", b'\x00'*4)),
    
    ("points1",  "I",   None),
    
    ("activeCh", "B",   ("require", "in", range(1,6))),
    ("padding3", "3s",  ("require", "==", b'\x00'*3)),
    
    ("channel1", "nested", chan_header),
    ("padding4", "2s",  ("require", "==", b'\x00'*2)),
    
    ("channel2", "nested", chan_header),
    
    ("timeDelayed", "B",  None),
    ("padding5",    "1s",  ("require", "==", b'\x00'*1)),
    
    ("time1",    "nested", time_header),
    
    ("channelLA", "nested", logic_analizer_channel),
    
    ("trigMode", "B",  None),      #FIXME: Add test
    ("trigHdr1", "nested", trigger_header),
    ("trigHdr2", "nested", trigger_header),
    
    ("fooG",     "9s", ("expect", "==", b'\x00'*9)),
    ("points2",  "i", None),
    
    ("time2",    "nested", time_header)
  )
  
  # There are two known versions of the WFM file format:
  # 1. The presumably older version does not include the laSmpRate 
  #    field.
  # 2. The laSmpRate field is added between the time2 header and
  #    the channel data.
  
  wfm_header_append_v2 = (
    ("laSmpRate",  "f",  ("require", ">=", 0)),
  )
  
  fileHdr = _parseFile(f, wfm_header, strict=strict)
  
  # Add some simple access helpers for the repeating fields
  fileHdr["channels"] = (fileHdr["channel1"], fileHdr["channel2"])
  fileHdr["triggers"] = (fileHdr["trigHdr1"], fileHdr["trigHdr2"])
  fileHdr["times"] = (fileHdr["time1"], fileHdr["time2"])
  
  # Sometimes, the channel length of the second channel is not written
  # so the first channel has to be used.
  fileHdr["points"] = [fileHdr["points1"], fileHdr["points2"]]
  if fileHdr["channels"][1]["written"] and fileHdr["points"][1] == 0:
    fileHdr["points"][1] = fileHdr["points"][0]
  
  totalPointBytes = 0
  for channel in range(2):
    if fileHdr["channels"][channel]['written']:
      totalPointBytes += fileHdr["points"][channel] * struct.calcsize("B")
  if fileHdr['channelLA']['written']:
    #NOTE: It is not exactly sure where the LA sample length is stored.
    #NOTE: we assume it to be the same as points1 for now.
    totalPointBytes += fileHdr["points"][0] * struct.calcsize("H")
  
  # #
  # Detect file version based on file length
  
  # Extract the remaining bytes in the file
  filePosition = f.tell()
  f.seek(0, os.SEEK_END)
  fileSize = f.tell()
  f.seek(filePosition)
  
  # Calculate the bytes difference if the data section was to 
  # start here
  bytesMissing = (fileSize - filePosition) - totalPointBytes
  
  if bytesMissing == 0:
    pass
  elif bytesMissing == struct.calcsize("f"):
    fileHdr_append_v2 = _parseFile(f, wfm_header_append_v2, strict=strict)
    fileHdr.update(fileHdr_append_v2)
  else:
    raise FormatError("File length is not as expected: %i bytes remaining." % (bytesMissing,))
  
  #import pprint
  #pprint.pprint(fileHdr)
  
  # Read in the sample data from the scope
  dataIdx = 0
  for channel in range(2):
    if fileHdr["channels"][channel]['written']:
      #print("Channel %i written, reading it" % channel)
      nBytes = fileHdr["points"][dataIdx] * struct.calcsize("B")
    
      sampleData = array.array('B')
      sampleData.fromfile(f, nBytes)
      fileHdr["channels"][channel]['data'] = sampleData
      dataIdx = dataIdx + 1
  
  if fileHdr['channelLA']['written']:
    nBytes = fileHdr["points"][0] * struct.calcsize("B")
    sampleData = array.array('H')
    sampleData.fromfile(f, nBytes)
    if sys.byteorder == 'big':
      sampleData.byteswap()
      
    fileHdr["channelLA"]['data'] = sampleData
    
  
  # # # # # # # # # # # #
  # Interpreter all the results to mean something useful.
  scopeData = dict()
  
  # Other general information
  scopeData["activeChannel"] = ("CH1", "CH2", "REF", "MATH", "LA")[fileHdr["activeCh"] - 1]
  
  # If we are not using alternate trigger, all channels share the same trigger
  # information.
  scopeData["alternateTrigger"] = (fileHdr["trigMode"] == 4)
  assert scopeData["alternateTrigger"] or fileHdr["trigMode"] == fileHdr["trigHdr1"]['mode'], "Not in alternate mode, but mode headers don't match"
  
  def parseTriggerHdr(trigHdr):
    trgDict = dict()
    trgDict["mode"] = ("Edge", "Pulse", "Slope", "Video", "Alternate")[trigHdr["mode"]]
    trgDict["source"] = ("CH1", "CH2", "EXT", "AC Line")[trigHdr["source"]]
    trgDict["coupling"] = ("DC", "LF Reject", "HF Reject", "AC")[trigHdr["coupling"]]
    trgDict["sweep"] = ("Auto", "Normal", "Single")[trigHdr["sweep"]]
    trgDict["holdoff"] = trigHdr["holdoff"]     # Seconds
    trgDict["sensitivity"] = trigHdr["sens"]    # Volts
    trgDict["level"] = trigHdr["level"]         # Volts
    
    
    if trgDict["mode"] in ("Edge",):
      trgDict["edgeDirection"] = ("RISE", "FALL", "BOTH")[trigHdr["direct"]]
    
    if trgDict["mode"] in ("Pulse",):
      trgDict["pulseType"] = ("POS >", "POS <", "POS =", "NEG >", "NEG <", "NEG =")[trigHdr["pulseType"]]
      trgDict["pulseWidth"] = trigHdr["PulseWidth"]
      
    if trgDict["mode"] in ("Slope",):
      trgDict["slopeType"] = ("RISE >", "RISE <", "RISE =", "FALL >", "FALL <", "FALL =")[trigHdr["slopeType"]]
      trgDict["slopeLowerLevel"] = trigHdr["lower"]  # Volts
      trgDict["slopeWidth"] = trigHdr["slopeWid"]  # Seconds FIXME: What about slopeWid?
      trgDict["slope"] = (trgDict["level"] -  trgDict["slopeLowerLevel"]) / trgDict["slopeWidth"] if trgDict["slopeWidth"] else float('inf')      # V/s
    
    if trgDict["mode"] in ("Video",):
      trgDict["videoPol"] = ("POS", "NEG")[trigHdr["videoPol"]]
      trgDict["videoSync"] = ("All Lines", "Line Num", "Odd Field", "Even Field")[trigHdr["videoSync"]]
      trgDict["videoStd"] = ("NTSC", "PAL/SECAM")[trigHdr["videoStd"]]
    
    return trgDict
  

  if not scopeData["alternateTrigger"]:
    scopeData["triggers"] = parseTriggerHdr(fileHdr["trigHdr1"])
  
  scopeData["channel"] = dict()
  for channel in range(2):
    channelDict = dict()
    channelDict["enabled"] = fileHdr["channels"][channel]['written']
    
    channelDict["channelName"] = "CH" + str(channel+1)
    
    if channelDict["enabled"]:
      if scopeData["alternateTrigger"]:
        channelDict["triggers"] = parseTriggerHdr(fileHdr["triggers"][channel])
        # The source field is not valid in alternate trigger mode
        channelDict["triggers"]["source"] = channelDict["channelName"]
      else:
        channelDict["triggers"] = scopeData["triggers"]
        
      channelDict["probeAttenuation"] = fileHdr["channels"][channel]["probeAtt"]
      channelDict["scale"] = fileHdr["channels"][channel]["scaleM"] * 1e-6 * channelDict["probeAttenuation"]
      
      channelDict["shift"] = fileHdr["channels"][channel]["shiftM"] / 25. * channelDict["scale"] 
      channelDict["inverted"] = fileHdr["channels"][channel]["invertM"]
      
      if channelDict["inverted"]:
        sign = -1
      else:
        sign = 1
      
      # Calculate the sample data
      
      # In rolling mode, not all samples are valid otherwise use all samples
      if fileHdr["rollStop"] == 0:
        channelDict["samples"] = {'raw' : fileHdr["channels"][channel]['data']}
      else:
        channelDict["samples"] = {'raw' : fileHdr["channels"][channel]['data'][:fileHdr["rollStop"]]}
        
      channelDict["samples"]["volts"] =  [((125-x)/25.*channelDict["scale"] - channelDict["shift"])*sign for x in channelDict["samples"]["raw"]]
      
      samples = len(channelDict["samples"]["raw"])
      channelDict["nsamples"] = samples
      
      if not scopeData["alternateTrigger"]:
        timebase = fileHdr["time1"]
      else:
        timebase = fileHdr["times"][channel]
      
      channelDict["samplerate"] = timebase["smpRate"]
      channelDict["timeScale"] = 1./timebase["smpRate"]
      channelDict["timeDelay"] = 1e-12 * timebase['delayM']
      channelDict["timeDiv"] = timebase['scaleM'] * 1e-12 
      
      channelDict["samples"]["time"] = [
        (t - samples/2) * channelDict["timeScale"] + channelDict["timeDelay"]
                          for t in range(samples)]
      
    # Save channel data to the overall scope data
    scopeData["channel"][channel+1] = channelDict
  
  # Add LA channel
  channelDict = dict()
  channelDict["enabled"] = fileHdr["channelLA"]['written']
  channelDict["channelName"] = "CHLA"
  
  if channelDict["enabled"]:
    # NOTE: It is not yet sure what happens if one analog channel and LA is used in alternate trigger
    # NOTE: mode. I have no scope to test if it is even possible.
    # NOTE: For now, we assume that LA is always like time scale 1.
    timebase = fileHdr["time1"]
    if "laSmpRate" in fileHdr:
      channelDict["samplerate"] = fileHdr["laSmpRate"]
    else:
      channelDict["samplerate"] = timebase["smpRate"]
    
    # In rolling mode, not all samples are valid otherwise use all samples
    if fileHdr["rollStop"] == 0:
      channelDict["samples"] = {'raw' : fileHdr["channelLA"]['data']}
    else:
      channelDict["samples"] = {'raw' : fileHdr["channelLA"]['data'][:fileHdr["rollStop"]]}
    
    samples = len(channelDict["samples"]["raw"])
    channelDict["nsamples"] = samples
        
    channelDict["timeScale"] = 1./channelDict["samplerate"]
    channelDict["timeDelay"] = 1e-12 * timebase['delayM']
    channelDict["timeDiv"] = timebase['scaleM'] * 1e-12 
    
    channelDict["samples"]["time"] = [
      (t - samples/2) * channelDict["timeScale"] + channelDict["timeDelay"]
                        for t in range(samples)]
    
    channelDict["activeChannel"] = fileHdr["channelLA"]['activeCh']
    channelDict["enabledChannelsMask"] = [bool(fileHdr["channelLA"]['enabledChannels'] & (1<<p)) for p in range(16)]
    channelDict["enabledChannelsMaskRaw"] = fileHdr["channelLA"]['enabledChannels']
    assert channelDict["enabledChannelsMask"][channelDict["activeChannel"]], "Active channel is not enabled!"
    
    channelDict["enabledChannels"] = list()
    for i in range(16):
      if channelDict["enabledChannelsMask"][i]:
        channelDict["enabledChannels"].append(i)
    
    # Separate data into channels
    channelDict["samples"]['byChannel'] = {
      c : [(sample & 1<<c)>0 for sample in channelDict["samples"]['raw']] for c in channelDict["enabledChannels"]
      }
    
    channelDict["waveSizeGroup1"] = {7:'big', 15:'small'}[fileHdr["channelLA"]['group0to7size']]
    channelDict["waveSizeGroup2"] = {7:'big', 15:'small'}[fileHdr["channelLA"]['group8to15size']]
    
    channelDict["position"] = [p for p in fileHdr["channelLA"]['position']]
    
  # Save channel data to the overall scope data
  scopeData["channel"]['LA'] = channelDict
  
  #pprint.pprint(scopeData)
  return scopeData
  
  
  
  
def describeScopeData(scopeData):
  """
  Returns a human-readable string representation of a scope data dictionary.
  """
  def describeDict(d, description, ljust=0):
    tmp = ""
    for item, desc in description:
      if item in d:
        tmp = tmp + "%s: %s\n" % (desc[0].ljust(ljust), desc[1] % d[item])
    return tmp

  def header(header_name, sep = '='):
    return "\n%s\n%s\n" % (header_name, sep*len(header_name))
  
  headerDsc = (
    ('activeChannel'     , ("Cur. selected channel", "%s")),
    ('alternateTrigger'  , ("Alternate trigger", "%s")),
    )
  
  channelDsc = (
    ('enabled'           , ("Enabled", "%s")),
    ('probeAttenuation'  , ("Probe attenuation", "%0.1f")),
    ('scale'             , ("Y grid scale", "%0.3e V/div")),
    ('shift'             , ("Y shift", "%0.3e V")),
    ('inverted'          , ("Y inverted", "%s")),
    ('timeDiv'           , ("Time grid scale", "%0.3e s/div")),
    ('samplerate'        , ("Samplerate", "%0.3e Samples/s")),
    ('timeDelay'         , ("Time delay", "%0.3e s")),
    ('nsamples'          , ("No. of recorded samples", "%i")),
    
    ('activeChannel'     , ("Active channel", "%i")),
    ('enabledChannels'   , ("Enabled channels", "%s")),
    
    ('waveSizeGroup1'    , ("Size group 1 (D0-D7)", "%s")),
    ('waveSizeGroup1'    , ("Size group 2 (D0-D7)", "%s")),
    )
  
  triggerDsc = (
    ('mode'              , ("Mode", "%s")),
    ('source'            , ("Source", "%s")),
    ('coupling'          , ("Coupling", "%s")),
    ('sweep'             , ("Sweep", "%s")),
    ('holdoff'           , ("Holdoff", "%0.3e s")),
    ('sensitivity'       , ("Sensitivity", "%0.3e div")),
    ('level'             , ("Level", "%0.3e V")),
    
    ('edgeDirection'     , ("Edge direction", "%s")),
    
    ('pulseType'         , ("Pulse type", "%s")),
    ('pulseWidth'        , ("Pulse type","%0.3e s")),
    
    ('slopeType'         , ("Slope type", "%s")),
    ('slopeLowerLevel'   , ("Slope lower level","%0.3e V")),
    ('slopeWidth'        , ("Slope width","%0.3e s")),
    ('slope'             , ("Slope slope","%0.3e V/s")),
    
    ('videoPol'          , ("Video polarity", "%s")),
    ('videoSync'         , ("Video sync", "%s")),
    ('videoStd'          , ("Video standard", "%s")),
    )
  
  tmp = ""
  
  tmp = tmp + header("General")
  tmp = tmp + describeDict(scopeData, headerDsc, ljust=25)
  
  for i in [1, 2, 'LA']:
    channelDict = scopeData["channel"][i]
    
    tmp = tmp + header("Channel %s" % channelDict["channelName"])
    tmp = tmp + describeDict(channelDict, channelDsc, ljust=25)
    
    if scopeData["alternateTrigger"]:
      if "triggers" in channelDict:
        tmp = tmp + header("Channel %s Trigger" % channelDict["channelName"], sep='-')
        tmp = tmp + describeDict(channelDict["triggers"], triggerDsc, ljust=25)
    else:
      tmp = tmp + header("Trigger")
      tmp = tmp + describeDict(scopeData["triggers"], triggerDsc, ljust=25)
  
  return tmp