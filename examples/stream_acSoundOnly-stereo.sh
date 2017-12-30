#! /bin/bash

PATH=/opt/local/bin:/opt/local/sbin:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/root/bin:/opt/local/bin/:/bin

if [ "$PYTHONPATH" = "" ] ; then 
	PYTHONPATH=/opt/local/Library/Frameworks/Python.framework/Versions/2.7/lib/python2.7/site-packages/:/opt/local/Library/Frameworks/Python.framework/Versions/2.7/lib/python2.7/site-packages/wx-3.0-osx_cocoa:/usr/local/lib/python2.7/site-packages/:/opt/local/lib/python2.7/site-packages/
fi

LOGFILE="/tmp/streamer-log.txt"
VLCPATH=`which vlc`

for I in /Applications/VLC.app/Contents/MacOS/VLC /usr/bin/vlc `which vlc` ; do 
	if [ -r $I ] ; then
		VLCPATH=$I
	fi
done

# Just stream the audio to VLC. 

while : ; do 
	echo "Using this python: `which python2.7`"
	python ./acSoundOnlyStreamSource-adaptiveFrequency-stereo.py | $VLCPATH -vvv -I dummy fd://0 --demux=rawaud --rawaud-channels=2 --rawaud-samplerate=48000 --sout "#transcode{acodec=mp3,ab=192,channels=2,samplerate=48000}:std{access=http,mux=ts,dst=0.0.0.0:2020}"  vlc://quit  2>&1 | tee -a $LOGFILE
	echo "= = = = = = `date` Streaming exited. restarting in 5 seconds."
	sleep 5
done




