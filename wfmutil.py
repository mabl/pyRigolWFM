#! /usr/bin/env python

from __future__ import print_function
import argparse
import collections

import wfm

if __name__ == "__main__":
  import argparse
  import pprint
  
  parser = argparse.ArgumentParser(description='Rigol DS1052E WFM file reader')
  parser.add_argument('action', choices=['info', 'csv', 'plot'], help="Action")
  parser.add_argument('infile', type=argparse.FileType('rb'))
  
  
  args = parser.parse_args()
  
  scopeData = wfm.parseRigolWFM(args.infile)
  scopeDataDsc = wfm.describeScopeData(scopeData)
  
  if args.action == "info":
    print(scopeDataDsc)
    
  if args.action == "csv":
    if scopeData["alternateTrigger"]:
      # In alternateTrigger mode, there are two time scales
      assert scopeData["channel"][1]["nsamples"] == scopeData["channel"][2]["nsamples"]
      
      print("X(CH1),CH1,X(CH2),CH2,")
      print("Second,Volt,Second,Volt,")
      for i in range(scopeData["channel"][1]["nsamples"]):
        for channel in range(1,3):
          sampleDict = scopeData["channel"][channel]["samples"]
          print("%0.5e,%0.2e," % (sampleDict["time"][i], sampleDict["volts"][i]), end='')
        print()
        
    else:
      nsamples = 0
      channels = []
      for channel in range(1,3):
        if scopeData["channel"][channel]["enabled"]:
          nsamples = max(nsamples, scopeData["channel"][channel]["nsamples"])
          channels.append(channel)
          
      # Print first line with column source description
      print("X,", end="")
      for channel in channels:
        print("%s," % scopeData["channel"][channel]["channelName"],end="")
      print()
      
      # Print second line with column unit description
      print("Second,", end="")
      for channel in channels:
        print("Volt,",end="")
      print()
      
      for i in range(nsamples):
        print("%0.5e," % scopeData["channel"][channels[0]]["samples"]["time"][i], end='')
        for channel in channels:
          sampleDict = scopeData["channel"][channel]["samples"]
          print("%0.2e," % sampleDict["volts"][i], end='')
        print()
      
  if args.action == "plot":
    import numpy as np
    import matplotlib.pyplot as plt
    import scipy
    import scipy.fftpack
    
    plt.subplot(211)
    
    for i in range(2):
      if scopeData["channel"][i+1]["enabled"]:
        plt.plot(scopeData["channel"][i+1]["samples"]["time"], scopeData["channel"][i+1]["samples"]["volts"])
    plt.grid()
    plt.title("Waveform")
    plt.ylabel("Voltage [V]")
    plt.xlabel("Time [s]")
    
    
    plt.subplot(212)
    for i in range(2):
      channelDict = scopeData["channel"][i+1]
      if channelDict["enabled"]:
        
        signal = np.array(channelDict["samples"]["volts"])
        fft = np.abs(np.fft.fftshift(scipy.fft(signal)))
        freqs = np.fft.fftshift(scipy.fftpack.fftfreq(signal.size, channelDict["timeScale"] / 250))
        plt.plot(freqs, 20 * np.log10(fft))
    
    plt.grid()
    plt.title("FFT")
    plt.ylabel("Magnitude [dB]")
    plt.xlabel("Frequency [Hz]")
    plt.show()