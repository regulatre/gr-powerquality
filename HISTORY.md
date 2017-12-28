### **Synopsis**

In order to better understand the power grid and distribution system in general, I built a small, low cost device that allows me to measure electricity, frequency, and current fluctuations with very high precision. The sensitivity of the device is so great that it can also be used to "listen" to events on the power grid. 

 

The term power quality is an industry term that refers to the quality of electricity, namely how well all aspects of the electricity are within acceptable ranges. 

In this article I will introduce my experiment, show how it is built, and then I’ll share my observations and what I have learned so far.

Thanks to the folks on /r/signalidentification for showing interest and encouraging me to write this article. 

### **How it started**

Cyber security and the power grid are intertwined; we rely on the power grid now more than ever. It touches every aspect of our lives, from charging our phones to charging our cars. Its continuous reliability and resilience is critical to our day to day lives. Not only are faults and outages a significant concern but so are other things - attacks. Of course the obvious scenario of a  power plant being "hacked" is well known but consider this: As a shared medium between many of our private devices, it (the outlets in your house or business) presents a path for devices to both communicate covertly (covert channel)  and eavesdrop on other devices and their operations (side-channel). More and more devices are connected every day. Today the risks are low and may not be of any concern to most people, but I find the topic fascinating. I want to learn more and get ahead of the risks *before* they arise so that *if* they do arise, I will be well informed and ready to help. 

### **Early Goals**

In the beginning, I had simple goals. I wanted to measure the voltage and frequency of the power from an outlet with as best accuracy as possible. I also thought it would be interesting to visualize any minute harmonics also riding on the AC waveform but didn’t know how yet. I knew I needed an AD converter (to convert analog measurements into digital form, for  computer analysis). I considered using a HackRF or RTLSDR but those are tailored for extremely wide bandwidth with lower dynamic range bits. And I know that because of the nature of the power system (power gets stepped down repeatedly at each stage of the system until it gets to the home) that most higher frequency harmonics would be eliminated due to inductive coupling so instruments with excessive bandwidth for the task would not be useful. So I focused on a much simpler AD converter – a USB sound card.

The average sound card (USB or not) can take analog measurements 48000-96000 timer per second, with 16-bits of dynamic range(each 16 bit reading can range from 0 to 65535 or steps of 0.000015 which is quite remarkable really). That’s perfect if you want to measure frequencies below 24Khz or take voltage readings a few times a second (up to 60 times a second).

To put that into perspective, a 60Hz "signal" such as that coming out of the power outlet, can be measured with incredible accuracy - 800 samples per revolution (picture a sine wave made up of 800 dots). At a sample rate of 96kHz that number doubles and a single 60Hz waveform is now sampled 1600 times in just 1/60th (0.017) of a second. The 16 bit dynamic range is the big selling point here, because it allows us to measure extremely minute distortions to the waveform. These distortions are where all the interesting stuff happens. Not to mention, quality usb sound cards can be had for $5. Now we’re ready to track down anomalies. 

Anomalies and distortions are also referred to as harmonics. Harmonics come from many sources, mainly from things drawing current and causing slight variations to the waveform.

The fundamental 60Hz frequency itself is not distorted by local events however, that comes straight from the source(s). On a typical power grid there can be dozens of plants adding supply to the system. All of these generation plants have to add power at precisely the same frequency as those already on the grid, otherwise their generator short circuits due to phase mismatch.

Before bringing new power onto the grid, a plant must synchronice with the grid frequency.  <youtube link on generator synchronizing>  the frequency on the grid varies continuously and somewhat unpredictable as I have learned. It is not 60.00Hz all the time. In fact it spends seconds of the day at 60.00 and most of the time above or below that well known frequency. That’s because the ever challenging process of supplying power to meet demand is difficult. Knowing precisely how much power to have ready in the next hour is a hard problem but grid operators do a great job nonetheless. Imperfections in forecasting leads to minute grid frequency fluctuations. For example at 9am when most businesses start to ramp up, large pumps and turbine motors switch on, lights and signs switch on, air conditioning and heaters too. This large addition of load can cause a brief dip in the grid frequency, which must quickly be met by proportional increase in supply from the operators of the plants and grid itself. Imagine frequency tied to a motor that, under heavy load slows down. If frequency drifts too far out of specification (either too high or too low) then parts of the grid disconnect until conditions are once again safe. 

### **Early Results**

The first version of the voltage probe consisted of a transformer, step down circuit, and a rudimentary gnuradio flow graph that i configured to act as an oscilloscope (I dont have such expensive tools like oscilloscopes  so i make do with what i have). The scope view was mostly boring at first but i did notice slight variations at times and this piqued my curiosity further. 

After many more hours of brainstorming I came up with plans for what became my first software flowgraph that was able to cancel some of the 60Hz fundamental frequency.

<image of fixed 800 sample add delay>

The output of this new flow graph was significantly more interesting. I could see things happening in real time. Micro events that only spanned one or a few cycles were frequent. It was time to listen to the output. 

The output varied widely in amplitude and was hard to listen to. Fast forward 10 more hours of experimentation and now we have automatic gain control and a rail filter to prevent loud pops in the headphones. Now it started to really sound clear. But the audio still faded in and out for some reason and had many disturbances. 

<flowgraph using fixed 800 sample delay>

Fast forward another 20 hours of experimenting and brainstorming and come to find out two things were at play: 1. The hard coded 60hz cancellation only worked when the fundamental crossed 60.000Hz which was random at best and varied over time  2. My power supply was introducing fluctuations and voltage swings. 

I switched to a better power supply and added a small bank of supercapacitors for filtering. That took care of problem #2 but what about the varying frequency?

I built a custom gnuradio dsp block that calculates the fundamental frequency down to the sample count and used it for two things. 1. Record instantaneous frequency of the grid. And 2. To target and mute the fundamental frequency. When you do this all you are left with are the interesting harmonics and distortions. This block (gr-powerquality) was the key and plays a crucial role in all aspects of the project now. 

In a later move, i improved accuracy even further by upsampling the sample rate from 48 kHz up to 480 kHz into the getfreqcpp block. This improved measurements by two decimal places. Additional upsampling did not prove useful because now the main source of fluctuation was the sound card crystal clock itself. And upsampling puts significant load on the cpu so its a balance of cpu and accuracy. I made these parameters tunable in the acpq.py config.yml.

### **Goals of the experiment**

1. High resolution voltage, frequency, current measurement. 

2. Easy visualization of current and historical readings

3. Assess the quality of the power being measured. 

4. Study anomalies in depth

5. Search for signs of out of band communications.

6. Live streaming audio feed

### **Status of the experiment**

The acpq experiment is running steadily now, collecting voltage, current, and frequency readings every 1s in elasticsearch and  recording any spikes or sags lasting 1/10 of a second or more. An additional high resolution streaming audio feed also enables me to listen from my computer or mobile wherever i may be. A continuous recording of every second of acpq audio for several weeks is also retained

## Challenges

Cancelling out the 60hz fundamental to leave only the interesting harmonics is by far where i spend most of my discretionary project time. The method currently in use is effective but crude. It introduces a lot of small attenuations to various multiples of 60hz. Chances are if we can clean up the mechanism of 60hz frequency cancellation we will uncover more interesting phenomenon. 

<insert dsp stackoverflow discussion about if>

Gnuradio does offer a band reject filter, but when the voltage being measured starts at 120v with sub 1v harmonics the tendency is for either all harmonics to be filtered out, or not enough of 60hz being filtered (which quickly overwhelms agc, muting everything). Also keep in mind that 60hz is never 60hz. It varies continuously by 1Hz or less. Any band reject filter must follow the fundamental frequency precisely in order to maximize the range of harmonics it uncovers. It must also attenuate the fundamental to nil while preserving all other frequencies. 

Maintaining a stable power source can be a challenge but through much trial and error I settled on a <insert power charver info>  the main caveat is that the capacitor bank is such high capacitance that in the event of a power outage it will drain and when power is restored it will blow the fuse on the 5v charger port. This happened once already. Maybe i need a diode somewhere? 

## **About**

### **About the author**

I’m and engineer, programmer, hacker, and father. I like to learn and explore my environment. Often, I find myself on exotic adventures of science, math, and engineering.

I would love to hear about your projects, especially if you build your own acpq sensor. Post your recordings on soundcloud or youtube and let's analyze them together. 

### **Other projects**

Mobile pq recorder

For collecting samples while out and about and for quantitatively measuring radiated power line energy and finding faults/shorts. 


Whats next?

I would like to improve the part of the experiment that suppresses the fundamental frequency. I also have a long list of features that I would like to add. Things like capturing a rotating log of raw wav recordings from the voltage sensors for later analysis and application improvement. 

I would also like to improve the getfreqcpp block that calculates the precise frequency. It currently does a crude calculation of counting the number of samples between zero crossings but it would be better to use trigonometry to model the sine wave and calculate the precise frequency of the wave. 

I would also like to run the audio through a fft with 24 bins or so and log to elk the amplitude of each bin every n seconds. With this information i can analyze events that come and go and maybe even model ground faults in the system (presents itself as wide band noise). At night i often hear ground faulting that starts when supply is higher than demand, causing the system voltage rises high enough to induce arcing throughout the system. I’ll provide some examples of the tell tale signs of arcing. 

Another avenue i was exploring for a while but lost steam is increasing the frequency stability of the soundcard by upgrading the crystal to a tcxo. Initial hardware experiments showed that it is a trivial upgrade and brings the frequency stability from <>ppm to around <>ppm. Although this sounds nicd it hasn't yet been necessary because sound cards are consistent and still show fluctuations in the frid frequency even though they may be off by 1/100hz which has so far been negligible. <insert photos of the modified sound card and a link to the soundcard>

I also want to explore collecting data on ambient ac radiation and analyzing it for precise frequency. This could be used to tell where you are in 3d space when compared against other known sensor stations. Also due to the randomness of frequency fluctuations it can be used to pinpoint the precise time of day right down to the millisecond or better. 

I also want to explore synchronization techniques for multiple sensor sites. The purpose being to aggregate multiple sites in order to improve gain and eliminate most local noise sources. I have some ideas about synchronizing feeds from multiple sources  with varying clocks (if they all had GPSDO time reference it would be easy but expensive). This could also be used to measure events with extreme precision and triangulate their source and determine other attributes about them in 3d space. 






