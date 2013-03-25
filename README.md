# Python RIGOL oscilloscopes waveform libary & tools

While RIGOL oscilloscopes offer great value for money there seems to be a great lack of tools to read RIGOL oscilloscopes waveform (WFM) files.

Based on the [protocol](http://meteleskublesku.cz/wfm_view/file_wfm.zip) extracted by the [wfm_view](http://meteleskublesku.cz/wfm_view/) project this project implements a feature complete WFM reader library.

The library has been tested with RIGOL DS1052E but should also work with other oscilloscopes.

Additionally a small example application wfmutil.py is included which provides

 - Header extraction 
 - Export to CSV, identical to the internal CSV export of the scope. Just faster.
 - Interactive plotting of the waveform, including a FFT.


## Features

 - Extract all trigger information
 - Support for alternate trigger and different time bases
 - Correct treatment of time and voltage shifts

## Problems
If you run into problems while parsing your waveform, please open an issue.

## Examples

### Information extraction
    % python wfmutil.py info foo.wfm

    General
    =======
    Alternate trigger        : True
    Cur. selected channel    : CH1

    Channel CH1
    ===========
    Enabled                  : 1
    Samplerate               : 2.500e+08 Samples/s
    No. of recorded samples  : 524288
    Y inverted               : 0
    Time delay               : 0.000e+00 s
    Y shift                  : -8.320e-02 V
    Y grid scale             : 2.000e-01 V/div
    Probe attenuation        : 1.0
    Time grid scale          : 2.000e-08 s/div

    Channel CH1 Trigger
    -------------------
    Edge direction           : RISE
    Coupling                 : DC
    Holdoff                  : 5.000e-07 s
    Source                   : CH1
    Mode                     : Edge
    Level                    : 9.600e-01 V
    Sweep                    : Auto
    Sensitivity              : 3.800e-01 V

    Channel CH2
    ===========
    Enabled                  : 1
    Samplerate               : 2.000e+07 Samples/s
    No. of recorded samples  : 524288
    Y inverted               : 0
    Time delay               : 0.000e+00 s
    Y shift                  : -2.000e-01 V
    Y grid scale             : 1.000e+00 V/div
    Probe attenuation        : 10.0
    Time grid scale          : 1.000e-03 s/div

    Channel CH2 Trigger
    -------------------
    Coupling                 : DC
    Slope lower level        : 0.000e+00 V
    Slope type               : RISE >
    Holdoff                  : 5.000e-07 s
    Source                   : CH2
    Slope slope              : 1.040e+06 V/s
    Mode                     : Slope
    Level                    : 1.040e+00 V
    Slope width              : 1.000e-06 s
    Sweep                    : Auto
    Sensitivity              : 3.800e-01 V


