#! /bin/bash

PATH=/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/root/bin
LOGFILE="/tmp/streamer-log.txt"

# Just stream the audio to VLC. 

while : ; do 
	./acSoundOnlyStreamSource-adaptiveFrequency-stereo.py | vlc -vvv -I dummy fd://0 --demux=rawaud --rawaud-channels=2 --rawaud-samplerate=48000 --sout "#transcode{acodec=mp3,ab=192,channels=2,samplerate=48000}:std{access=http,mux=ts,dst=0.0.0.0:2020}"  vlc://quit  2>&1 | tee -a $LOGFILE
	echo "= = = = = = `date` Streaming exited. restarting in 5 seconds."
	sleep 5
done




