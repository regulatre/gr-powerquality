#! /bin/bash

LOGFILE="/home/pi/acpqheadphones.txt"


cd /home/pi


msg () {
  echo "`date` $*" | tee -a $LOGFILE
}

runPythonApp() {
	mv -v /home/pi/pq.wav /home/pi/pq-$(date +%Y-%m-%d-%H-%m-%S)-RECOVERED.wav
	msg "starting python app"
	/home/pi/git/gr-powerquality/examples/acpqheadphones.py  2>&1 | tee -a $LOGFILE
	EXITCODE=$?
	msg "Python app exited with code $EXITCODE"
	mv -v /home/pi/pq.wav /home/pi/pq-$(date +%Y-%m-%d-%H-%m-%S).wav
}

# Return bash true (0) if device is connected and ready.
isAudioDeviceConnected() {
	if /usr/bin/arecord -l | grep USB.Audio.Device ; then
		return 0
	else
		return 1
	fi
}


runAndRestartIfFails() {
	while : ; do 
		if ! isAudioDeviceConnected ; then
			msg "USB Audio device not connected. Pausing a bit."
			sleep 5
			continue
		fi 
		# :> /tmp/anyerrors
		msg "killing old python2 processes"
		killall python2
		msg "Starting python application..."
		STARTTIME=$(date +%s)
		runPythonApp
		ENDTIME=$(date +%s)
		ELAPSED=$(( $ENDTIME - $STARTTIME ))
		msg "Python application terminated after $ELAPSED seconds"
		msg "Cleaning up junk wav files from failed executions (gnuradio block bug)"
		find ./pq*wav -size -2 | xargs rm -v 2>&1 | tee -a $LOGFILE
		sleep 1
	done
}


runAndRestartIfFails



