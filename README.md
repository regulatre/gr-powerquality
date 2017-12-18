
# Power Quality on a Pi

acpq.py (found in the examples directory) is the main AC Power Quality application. It uses the custom gnuradio block called getfreqcpp to calculate precise frequency, and also tracks min/max/average voltage as well. It can also be configured to treat the voltage readings as current readings, for example if a CT coil (eg. CTYRZCH SCT-013-000) is clampped to a power wire for. In this case you typically need a shunt across the CT coil to get the voltage within acceptable limits of the sound card input.

### Feature Backlog
+ (done) Basic application that runs from commandline, reads config file
+ (done) Display meaured power every 1 second using tuning parameters defined in the config file
+ (done) Add a block to apply averaging to the output of RMS reading. Config file variable calibration.voltage_calculation_averaging
+ (done) Add Hz measurement - print precise frequency to the screen every N seconds. Requres a NEW wavelength calculator block written in C++
+ (done) Add the ability to specify wav or soundcard input
+ (done) Rewrite the wavelength calculator block in C++ --> getfreqcpp
	- Reason 1: it takes up so much CPU as-is that interpolation of 10 (lowest) is not even possible.
	- Reason 2: we need this to be able to run on a Raspberry Pi nano.
+ (done) Add config file support for logging
+ (done) Define log schema, which is required for template. --> Done - checked into scripts/ directory of project.
+ (done) Create Elasticsearch index template in support of logging
+ (done) Add support for remote logging. Elasticsearch via HTTPs request to Elasticsearch server
	+ (done) Log whatever we have right now at this moment - voltage, frequency.
	+ (done) Log frequency... every 1 minute, with min/max attributes as well?
+ (done) Add support for reporting spikes/sags each metric print interval (min/max freq and volts)
+ (done) Added an always-on TCP/IP listener (port 5555) that taps the input source and makes it available as raw samples on this port.
+ (done) Add support for specifying the config file name/path - because on pq I need to run 4 instances and this feature would be nifty.
+ (done) Eliminate all fields named "type" - they seem to be colliding with reserved words. + (done) Add support for distinction between RMSVOLTS and RMSCURRENT probe types.
+ (done) Add baseband audio streaming support (wav file to VLC). Internally from same app if possible so stdout not used up. 
	+ (done) Make it controllable via config file so those blocks can be disabled if not needed. 
	* try making a block that offers INT not float on the server port - initial try of streaming float fails.
+ (done) Do so by adding a simple TCP service where other flow graphs can tap into raw baseband feed.
		- As a new python module if at all possible. One module per large feature.
		- Maybe a fifo pipe that VLC can connect to for the wav stream.
		- Also need the add accumulate logic, and to use the precise frequency calculation 
to eliminate the fundamental. Which we're already doing, so re-use that logic.
+ Audio Streamer - connect to the probe application and transform the wave into something audible, feed that to VLC for streaming
+ (done) PNG generator  - generate a PNG image of one or two cycles of the waveform. Do this periodically, eventually stitch them into an AVI
- As a means of calibrating PQ sensors, use TCXO RTL-SDR tuned to a frequency with known powerline noise, and make a flow graph that isolates the noise and runs frequency analysis against it. Compare the result to the result of PQ sensors.
- Periodically log Harmonic amplitude using one big RMS or an FFT with 16 bins or so (to reduce log volume). Run it against the pre-AGC stage
- Goertzel samples - /home/pi/gr/gnuradio/gr-fft/python/fft/qa_goertzel.py
- Log the number of times the signal hit the rails per interval. Can use a binary slicer? 
	- So that we can try and track arcing
- The "add/multiply/delay" technique filter may be shifting/doubling frequencies other than 60Hz
	- Run a series of tests by introducing a known signal input, and looking for it in the FFT. Shift the signal around to see if/how it gets distorted to better understand the filter.
	- If it is indeed distorting the signal in a destructive manner then explore techniques for mitigating that destruction.
- Log the rate of frequency change (how many milliarcseconds per second is the phase angle changing?)
- Devise some sort of algorithm that calculates a periodic marker that links a discrete event with the absolutely most precise time stamp possible. 
	- With multiple collectors reporting in, these markers can be compared with time stamp to determins phase differences between two collectors. 
	- 0.017 seconds per cycle means clocks should be accurate to within 0.001 seconds using NTP.
- Monitor the "BIAS" of the input signal using a simple moving average block. 
	- 5v power sources are often noisy and introduce bias into the Pi and it shows right through into the readings. 
	- Monitor instantaneous bias, bias slope, min, max. 
	- Measure the slope of the bias as well - This bias might skew current readings depending on the slope of the bias.
	- These readings might also be useful for mitigating any interference the bias introduces.
- Add min/max parameters to the getfreqcpp block, so that it only updates the average if the calculated wavelength falls within that range. 
	- This would let us more effectively use the block for EMI use cases
	- This should eliminate the large skew that happens sometimes when a voltage surge or sag occurs
- is there a way to catch overrun/underrun events? How about using a rate probe? When the flow graph goes wonky we need to detect and bail out of the app to let it restart.
- Create a systemd service file to run acpq
- Create a service to run the VLC streamer service on sdr.vmnet
	- tried, it failed.
- Create a service to run the VLC recorder script on sdr.vmnet
- Create a service to run each individual pq process
- GPS / GPSd integration with acpq such that each reading is geotagged. If no geotag/gpsd available leave those fields absent.
	- Use case: Roaming RFI noise measurement - find quietest environment for HF operation.
- use the precise Hz calculation logic to balance delayed-inverse and undelayed signals to perfectly match them and produce clean baseband. 
	--> Did so, built a new python script but it would be better if it connects to the new tcp baseband port. Also requires build environment and acsound custom block.
- Create a separate interface for other python apps to connect and get a feed
	- This is a shitshow. TCP client block is "deprecated"!? Nano Wi-Fi not strong enough - gets knocked offline when trying to stream 48khz data.
- Use the TCP interface to create a Rotating wav file logging support
- Use the TCP interface to create a PNG wave output module for streaming
- Use the TCP interface to create an audible stream that has 60hz cancelled using interpolation and getfreqcpp block.
- Calculate FFT event N seconds and log the peaks and amplitudes periodically. 
- Calculate change in FFT results from one sampling to the next, to spot what's background noise and what is new/changing. 
- Enable a TCP server service on the collector in support of having separate modules performing additional tasks. 
- Install Gnuradio from source on a Raspberry pi (already did it on Nano! use this as a starting point).
- Periodically log solar conditions - K index, Geomagnetic storm level, stuff like that.
	http://services.swpc.noaa.gov/products/noaa-scales.json **** Best one right here I think. 
	http://services.swpc.noaa.gov/products/noaa-estimated-planetary-k-index-1-minute.json ** This has the last 400 minutes of K-index data. Pull this a couple times a day and index all of it..?
	http://services.swpc.noaa.gov/products/summary/solar-wind-mag-field.json
	http://services.swpc.noaa.gov/products/summary/solar-wind-speed.json
	http://services.swpc.noaa.gov/products/summary/10cm-flux.json
- Periodically log the weather conditions for the area
	- wind speed, temperature, lightning_present?
- If any errors happen in the flowgraph, count those errors, and report on them during the periodic report to ELK
- Take into account load average on the probe. Either log load average with each request, or add logic to take it offline if load is above N (specified in config file)
- Flatline detection - keep track of number of times the values of frequency and rmsvolts have remained constant, and if remains constant for N seconds consider the app flatlined and force exit. 
- Enable some sort of simple queueing within the app, to buffer up records locally if ES is offline for a period of time. 
	- new messages always go to queue, each add triggers an attempt to run the queue? 
-  Raw datalogger - connect to the probe application and save the unaltered waveform to wav file, circular buffer of wav files. buffer size specified as cmdline option
- Waveform streamer - coordinates FFMPEG to stitch png's into AVI, and VLC to read from a playlist - playlist contains FFMPEG AVI, a static video, on permanent loop.


## acpq (python script) - The Voltage/Frequency/Current logger

### Installation

Install yaml library dependency, not present in stripped down raspbian image
```
apt-get install libyaml-dev
```

Install required Python Modules
```
sudo easy_install pip
sudo pip install elasticsearch certifi PyYAML
```
Install the gr-powerquality gnuradio module
```
<git clone it>
<mkdir build; cd build; make; sudo make install>
ldconfig # This is key. 
```

### Remote Logging

Remote logging to Elastic Search is supported. Fill out the required fields in the configuration file to make the connection and describe the logger and probe.



### Accuracy: AC Frequency Measurement

The accuracy of the AC frequency measurement depends on several factors: 
1. sample rate - typically 48khz
1. the accuracy of the custom block used to measure the period of the fundamental
1. interpolation or no interpolation during the calculation
1. if interpolating, by what factor? Higher interpolation factor means more accuracy

At 48k S/s sample rate, a 60Hz signal has a period of 800 samples. A single sample (most accurate) represents 1/(48000/60) = 60/48000 = 0.00125Hz. 

	48K S/s		1.25E-3
	480K S/s	1.25E-4
	4.8M S/s	1.25E-5
	48M S/s		1.25E-6
	480M S/s	1.25E-7 (approaches the 2.5ppm (2.5E-8) accuracy of the clock in the USB soundcard used for measurements)	

Several approaches were considered for AC frequency measurement. 

1. Simply calculate the period of the frequency from the raw source - accuracy: 1.25E-3
1. Add delay lines to both inputs of the add block and adjust either delay until signals are in phase
1. Use an interpolating block 

### The best approach
A number of factors must be carefully balanced to determine the "Best" approach"; namely, accuracy vs computational demand.

* TODO: use testFrequency.py to gather CPU vs accuracy numbers and plot them here. 

#### Device-specific Calibration

Operating system: Linux. Command line (terminal)

First time calibration:

Start alsamizer utility, press F4 to switch to the capture context, then ensure that AGC is MM (muted) and the mic gain is number 6. Escape out to exit.
```
alsamixer -d hw:1
```

Now store hw:1 device's configuration so it is loaded on boot.
```
sudo alsactl store 1
```

Calibrating interpolation
```
Interpolation is used to upsample the input in order to take a more precise getfreqcpp (period of the fundamental frequency in terms of samples) measurement. The more precise, the better the flowgraph is at tracking and consistently eliminating the fundamental frequency as it varies over time. 

0.1 = default, 1.45 load average on a Raspberry Pi Nano. 
1.0 = no interpolation, 0.33 load average on Raspberry PI Nano. 

```

## Examples Directory
The examples in this directory use the getfreqcpp block in various ways. 

### stream_acSoundOnly-stereo (bash script)
starts the gnuradio flow graph, pipes the audio to VLC for streaming, VLC waits on HTTP://localhost:2020 for inbound connections such as VLC for android. 

### acSoundOnlyStreamSource-adaptiveFrequency-stereo (python)
used by the stream_acSoundOnly-stereo.sh script to read samples from the sound card, remove the fundamental frequency, and output a two-channel stream of wav audio suitable for piping into the VLC streamer process. 

### acSoundOnlyStreamSource-adaptiveFrequency (python)

This script is older, but probably still works fine. may need minor adjustment. Wrapped by the script named stream_acSoundOnly.sh in the examples directory. 

Use this script to stream 48Khz 16-bit audio from the USB device to VLC (See examples section below). 

This script very carefully tracks the precise fundamental frequency and suppresses it. In other words, if the input frequency is 60.02Hz, this module suppresses that precise frequency, leaving only the higher and lower harmonics that are riding the same carrier wave. This is extremely useful for unmasking subtle variations to the power quality audio stream. Various power events can be "heard" in real time as they occur. 

More specifically, the script takes the 48Khz USB sound input, interpolates the sample rate up to 480,000 samples per second and then calculates the precise frequency of the fundamental using the getfreqcpp block. This block calculates the period of the wave and outputs the period in terms of samples per period. For example at 48,000 samples per second, the period of a 60.00Hz signal would be 800 samples. And at 480,000 samples per second, that same 60Hz wave has a period of 8000 samples. As the input frequency fluctuates slightly, the getfreqcpp block tracks this variation and outputs the precise period as it changes. For example at 59.9925Hz the period becomes 8001 (480000/8001=59.9925). Similarly, at 60.007501Hz the period becomes 7999 (480000/60.007501=7999). The getfreqcpp block actually does in fact return a floating point value, which is calculated as an average. The averaging formula is weighted with an alpha parameter that is supplied to the getfreqcpp block. This is a tunable parameter and is proportional to the frequency of change to the fundamental frequency.

The script relies on the interpolator block for higher resolution, and the getfreqcpp block to calcualte the precise period. 


### Running the streamer as a service

$ cat /etc/systemd/system/pq-streamer.service
```
[Unit]
Description=Power Quality 2-channel Audio Streamer
After=network.target

[Service]
Type=simple
User=brad
WorkingDirectory=/home/brad/git/gr-powerquality/examples
ExecStart=/bin/bash -c ./stream_acSoundOnly-stereo.sh
Restart=always

[Install]
WantedBy=multi-user.target
```

### acpqheadphones (python)

This is an experiment to run a flowgraph completely headless and output the harmonic audio to headphones... suitable for a Raspberry Pi nano on battery power.

```
acpqheadphones.grc - gnuradio flow graph
acpqheadphones.py - connect to sensor, eliminate the fundamental, stream the output on the audio output
acpqheadphones-runner.sh - runs the script repeatedly, capturing raw .wav 
```


###  circularBufferOfVlcRecordings (Bash script)

This script connects to the streamer and transcodes the stream to file in 5-minute clips. It records extra so that each file overlaps with the next, thus there are no gaps in the recorded audio due to rotating from one recording to the next.

This script would be ideal to run headless, but I've had challenges with doing so. Something about not having a TTY allocated. 


## Hardware Upgrades

### Syba 0d8c:0008 USB Sound Crystal Upgrade

Easy to upgrade the crystal to a TCXO - 3.3v source is available. See datasheet: http://www.repeater-builder.com/voip/pdf/cm119-datasheet.pdf 





