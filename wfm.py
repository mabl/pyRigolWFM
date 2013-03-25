from __future__ import print_function

import collections
import struct
import array
import sys

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

def __named_struct_parse(field_names, binary_format, data):
  """
  Interprets given binary data according to the binary description. The 
  resulting data is then stored in a OrderedDict.
  """
  Class = collections.namedtuple('Class', field_names)
  return Class._asdict(Class._make(struct.unpack(binary_format, data)))
  

def parseRigolWFM(f):
  """
  Parse a file object which has opened a Rigol WFM file in read-binary 
  mode (rb).
  
  The parser has been developed based on a RIGOL DS1052E and protocol 
  information derived from http://meteleskublesku.cz/wfm_view/file_wfm.zip.
  
  The result of the parsing is a nested dictionary containing all relevant data.
  
  Note, that trigger information might be per-channel specific (i.e. in 
  alternate trigger mode). In such cases, you have to use the trigger 
  information in the channel data.
  """
  
  def named_struct_parse_from_file(field_names, binary_format, file_obj):
    data = file_obj.read(struct.calcsize(binary_format))
    return __named_struct_parse(field_names, binary_format, data)
  
  
  def protocolAssumption(statement, msg):
    if not statement:
      
      introduction = """\nThe WFM file format is not yet 100%% deciphered.
There are several field which usage is not known but which typically always have the defined value.

You are lucky and hit a file, which does not have these standard values in one of its unknown fields.
Most likely you can just ignore this warning. But if you like to help in the development of this program,
please report your file, settings and scope id to matthias(AT)blaicher.com.

The protocol warning message is:
%s


""" % msg
      
      print(introduction, file=sys.stderr)
  
  # # # #
  # First read in all the known fields and data of the waveform file. It is
  # interpreted later on.
  
  # # # #
  # The Rigol file format as implemented here consists of several blocks
  #
  # +----------------------+
  # | waveHdr Part 1       |
  # +----------------------+
  # | chanHdr Channel 1    |
  # +----------------------+
  # | chanHdr Channel 2    |
  # +----------------------+
  # | timeHdr Scale 1      |
  # +----------------------+
  # | Unknown              |
  # +----------------------+
  # | Trigger mode         |
  # +----------------------+
  # | trigHdr 1            |
  # +----------------------+
  # | trigHdr 2            |
  # +----------------------+
  # | waveHdr Part 2       |
  # +----------------------+
  # | timeHdr Scale 2      |
  # +----------------------+
  # | waveHdr Part 3       |
  # +----------------------+
  
  
  waveHdr1Format = ("magic fooA points1 activeCh fooB",
                   "<H26sIB3s")
  waveHdr1 = named_struct_parse_from_file(*waveHdr1Format, file_obj=f)
  #print("waveHdr1\t:", waveHdr1)
  
  assert waveHdr1['magic'] == 0xa5a5, "Not a Rigol waveform file."
  protocolAssumption(waveHdr1['fooA'] == b'\x00'*26, "Unknown field fooA contains not only zeroes")
  protocolAssumption(waveHdr1['fooB'] == b'\x00'*3, "Unknown field fooB contains not only zeroes")
 
 
  chanHdrFormat = ("scaleD shiftD fooA probeAtt invertD written invertM fooB scaleM shiftM fooC",
                   "<ihHfBBBBihH")
  chanHdrCh1 = named_struct_parse_from_file(*chanHdrFormat, file_obj=f)
  chanHdrCh2 = named_struct_parse_from_file(*chanHdrFormat, file_obj=f)
  chanHdr = (chanHdrCh1, chanHdrCh2)
  #print("chanHdrCh1\t:", chanHdrCh1)
  #print("chanHdrCh2\t:", chanHdrCh2)
  
  for i in range(2):
    protocolAssumption(chanHdr[i]["fooA"] == 0, "Unknown field fooA does not contain zero")
    protocolAssumption(chanHdr[i]["fooB"] == 0, "Unknown field fooB does not contain zero")
    protocolAssumption(chanHdr[i]["scaleD"] == chanHdr[i]["scaleM"], "scaleD and scaleM field differ")
    protocolAssumption(chanHdr[i]["shiftD"] == chanHdr[i]["shiftM"], "shiftD and shiftM field differ")
    protocolAssumption(chanHdr[i]["invertD"] == chanHdr[i]["invertM"], "invertD and invertM field differ")
  
  timeHdrFormat = ("scaleD delayD smpRate scaleM delayM",
                   "<qqfqq")
  timeHdrScl1 = named_struct_parse_from_file(*timeHdrFormat, file_obj=f)
  #print("timeHdrScl1\t:", timeHdrScl1)
  
  unkownHdrFormat = ("fooC fooD fooE fooF",
                     "<4s8s8s2s")
  unkownHdr = named_struct_parse_from_file(*unkownHdrFormat, file_obj=f)
  #print("unkownHdr\t:", unkownHdr)
  
  protocolAssumption(unkownHdr["fooC"] == b'\x00\x00\x00\x00', "Unknown field fooC contains not only zeroes")
  protocolAssumption(unkownHdr["fooD"] == b'\x00\x01\x02\x03\x04\x05\x06\x07', "Unknown field fooD contains unknown sequence")
  protocolAssumption(unkownHdr["fooE"] == b'\x00\x01\x02\x03\x04\x05\x06\x07', "Unknown field fooE contains unknown sequence")
  protocolAssumption(unkownHdr["fooF"] == b'\x07\x07', "Unknown field fooE contains unknown sequence")
  
  trigModeHdrFormat = ("mode", "<B")
  trigModeHdr = named_struct_parse_from_file(*trigModeHdrFormat, file_obj=f)
  protocolAssumption(trigModeHdr['mode'] in range(0,5), "Unknown trigger mode")
  #print("trigModeHdr\t:", trigModeHdr)
  
  trigHdrFormat = ("mode source coupling sweep fooA sens holdoff level direct pulseType fooB PulseWidth slopeType fooC lower slopeWid videoPol videoSync videoStd",
                   "<BBBBBfffBBHfB3sffBBB")
  trigHdr1 = named_struct_parse_from_file(*trigHdrFormat, file_obj=f)
  trigHdr2 = named_struct_parse_from_file(*trigHdrFormat, file_obj=f)
  trigHdr = (trigHdr1, trigHdr2)
  
  for i in range(2):
    protocolAssumption(trigHdr[i]["fooA"] == 0, "Unknown field fooA does not contain zero")
    protocolAssumption(trigHdr[i]["fooB"] == 0, "Unknown field fooB does not contain zero")
    protocolAssumption(trigHdr[i]["fooC"] == b'\x00\x00\x00', "Unknown field fooB does not contain zero")
  
  
  #print("trigHdr1\t:", trigHdr1)
  #print("trigHdr2\t:", trigHdr2)
  
  waveHdr2Format = ("fooG points2",
                   "<9si")
  waveHdr2 = named_struct_parse_from_file(*waveHdr2Format, file_obj=f)
  #print("waveHdr2\t:", waveHdr2)
  
  timeHdrScl2 = named_struct_parse_from_file(*timeHdrFormat, file_obj=f)
  timeHdrScl = (timeHdrScl1, timeHdrScl2)
  #print("timeHdrScl2\t:", timeHdrScl2)
  
  waveHdr3Format = ("smpRate", "<f")
  waveHdr3 = named_struct_parse_from_file(*waveHdr3Format, file_obj=f)
  #print("waveHdr3\t:", waveHdr3)
  
  # Join all waveHdr fields to one dict for convenience
  waveHdr = dict()
  waveHdr.update(waveHdr1)
  waveHdr.update(waveHdr2)
  waveHdr.update(waveHdr3)
  #print("waveHdr\t:", waveHdr)
  
  # Read in the sample data from the scope
  dataIdx = 0
  for channel in range(2):
    if chanHdr[channel]['written']:
      #print("Channel %i written, reading it" % channel)
      nBytes = (waveHdr['points1'], waveHdr['points2'])[dataIdx] * struct.calcsize("B")
      
      if nBytes == 0 and dataIdx==1:
        nBytes = waveHdr['points1']
      
      assert nBytes > 0
      
      sampleData = array.array('B')
      sampleData.fromfile(f, nBytes)
      chanHdr[channel]['data'] = sampleData
      dataIdx = dataIdx + 1
  
  
  # # # # # # # # # # # #
  # Interpreter all the results to mean something useful.
  scopeData = dict()
  
  # Other general information
  scopeData["activeChannel"] = ("CH1", "CH2", "REF", "MATH")[waveHdr["activeCh"] - 1]
  scopeData["samplerate"] = waveHdr["smpRate"]
  
  # If we are not using alternate trigger, all channels share the same trigger
  # information.
  scopeData["alternateTrigger"] = (trigModeHdr["mode"] == 4)
  assert scopeData["alternateTrigger"] or trigModeHdr["mode"] == trigHdr1['mode'], "Not in alternate mode, but mode headers don't match"
  
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
      trgDict["slope"] = (trgDict["level"] -  trgDict["slopeLowerLevel"]) / trgDict["slopeWidth"]       # V/s
    
    if trgDict["mode"] in ("Video",):
      trgDict["videoPol"] = ("POS", "NEG")[trigHdr["videoPol"]]
      trgDict["videoSync"] = ("All Lines", "Line Num", "Odd Field", "Even Field")[trigHdr["videoSync"]]
      trgDict["videoStd"] = ("NTSC", "PAL/SECAM")[trigHdr["videoStd"]]
    
    return trgDict
  

  if not scopeData["alternateTrigger"]:
    scopeData["trigger"] = parseTriggerHdr(trigHdr1)
  
  scopeData["channel"] = dict()
  for channel in range(2):
    channelDict = dict()
    channelDict["enabled"] = chanHdr[channel]['written']
    
    channelDict["channelName"] = "CH" + str(channel+1)
    
    if channelDict["enabled"]:
      if scopeData["alternateTrigger"]:
        channelDict["trigger"] = parseTriggerHdr((trigHdr1, trigHdr2)[channel])
        # The source field is not valid in alternate trigger mode
        channelDict["trigger"]["source"] = channelDict["channelName"]
      else:
        channelDict["trigger"] = scopeData["trigger"]
        
      channelDict["probeAttenuation"] = chanHdr[channel]["probeAtt"]
      channelDict["scale"] = chanHdr[channel]["scaleM"] * 1e-6 * channelDict["probeAttenuation"]
      
      # FIXME: Check if division by 255 is correct. Some people do multiply by 0.04 (which is 250). 
      channelDict["shift"] = chanHdr[channel]["shiftM"] / 250. * channelDict["scale"] 
      channelDict["inverted"] = chanHdr[channel]["invertM"]
      
      if channelDict["inverted"]:
        sign = -1
      else:
        sign = 1
      
      # Calculate the sample data
      channelDict["samples"] = {'raw' : chanHdr[channel]['data']}
      channelDict["samples"]["volts"] =  [((125-x)/25.*channelDict["scale"] + channelDict["shift"])*sign for x in channelDict["samples"]["raw"]]
      
      samples = len(channelDict["samples"]["raw"])
      channelDict["nsamples"] = samples
      
      if not scopeData["alternateTrigger"]:
        timebase = timeHdrScl1
      else:
        timebase = timeHdrScl[channel]
      
      channelDict["samplerate"] = timebase["smpRate"]
      channelDict["timeScale"] = 1./timebase["smpRate"]
      channelDict["timeDelay"] = 1e-12 * timebase['delayM']
      
      channelDict["timeDiv"] = timebase['scaleM'] * 1e-12 
      
      channelDict["samples"]["time"] = [
        (t - samples/2) * channelDict["timeScale"] + channelDict["timeDelay"]
                          for t in range(samples)]
      
    # Save channel data to the overall scope data
    scopeData["channel"][channel+1] = channelDict
  
  return scopeData
  
  
  
  
def describeScopeData(scopeData):
  """
  Returns a human-readable string representation of a scope data dictionary.
  """
  def describeDict(d, description, ljust=0):
    tmp = ""
    for item, desc in description.items():
      if item in d:
        tmp = tmp + "%s: %s\n" % (desc[0].ljust(ljust), desc[1] % d[item])
    return tmp

  def header(header_name, sep = '='):
    return "\n%s\n%s\n" % (header_name, sep*len(header_name))
  
  headerDsc = {
    'activeChannel'     : ("Cur. selected channel", "%s"),
    'alternateTrigger'  : ("Alternate trigger", "%s")
    }
  
  channelDsc = {
    'enabled'           : ("Enabled", "%s"),
    'probeAttenuation'  : ("Probe attenuation", "%0.1f"),
    'scale'             : ("Y grid scale", "%0.3e V/div"),
    'shift'             : ("Y shift", "%0.3e V"),
    'inverted'          : ("Y inverted", "%s"),
    'timeDiv'           : ("Time grid scale", "%0.3e s/div"),
    'samplerate'        : ("Samplerate", "%0.3e Samples/s"),
    'timeDelay'         : ("Time delay", "%0.3e s"),
    'nsamples'          : ("No. of recorded samples", "%i")
    }
    
  triggerDsc = {
    'mode'              : ("Mode", "%s"),
    'source'            : ("Source", "%s"),
    'coupling'          : ("Coupling", "%s"),
    'sweep'             : ("Sweep", "%s"),
    'holdoff'           : ("Holdoff", "%0.3e s"),
    'sensitivity'       : ("Sensitivity", "%0.3e V"),
    'level'             : ("Level", "%0.3e V"),
    
    'edgeDirection'     : ("Edge direction", "%s"),
    
    'pulseType'         : ("Pulse type", "%s"),
    'pulseWidth'        : ("Pulse type","%0.3e s"),
    
    'slopeType'         : ("Slope type", "%s"),
    'slopeLowerLevel'   : ("Slope lower level","%0.3e V"),
    'slopeWidth'        : ("Slope width","%0.3e s"),
    'slope'             : ("Slope slope","%0.3e V/s"),
    
    'videoPol'          : ("Video polarity", "%s"),
    'videoSync'         : ("Video sync", "%s"),
    'videoStd'          : ("Video standard", "%s"),
    }
  
  tmp = ""
  
  tmp = tmp + header("General")
  tmp = tmp + describeDict(scopeData, headerDsc, ljust=25)
  
  for i in range(1,3):
    channelDict = scopeData["channel"][i]
    
    tmp = tmp + header("Channel %s" % channelDict["channelName"])
    tmp = tmp + describeDict(channelDict, channelDsc, ljust=25)
    
    if scopeData["alternateTrigger"]:
      tmp = tmp + header("Channel %s Trigger" % channelDict["channelName"], sep='-')
      tmp = tmp + describeDict(channelDict["trigger"], triggerDsc, ljust=25)
    
  return tmp