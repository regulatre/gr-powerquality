#! /bin/bash

PQ_OUTPUT_DIR="/mnt/video/acSound"
RETAINDAYS="7"
LOGFILE="/tmp/vlc-recorder-log.txt"
RUNTIME="300"
FILEPREFIX="acSound-"
PQ_STREAM_URL="http://192.168.1.100:2020"


# Read local variable overrides
. ./config

mkdir -p $PQ_OUTPUT_DIR || exit 4


purge() {
	if [ ! -d "$PQ_OUTPUT_DIR" ] ; then
		echo "ERROR - PQ_OUTPUT_DIR $PQ_OUTPUT_DIR DOESNT EXIST."
		exit 2
	fi
	
	cd $PQ_OUTPUT_DIR || return

	cd $PQ_OUTPUT_DIR && find $PQ_OUTPUT_DIR -mtime +$RETAINDAYS -name "acSound*.mp3" -exec rm -v {} \;
	cd $PQ_OUTPUT_DIR && find $PQ_OUTPUT_DIR -mtime +$RETAINDAYS -name "acSound*spectrogram.png" -exec rm -v {} \;

	cd $PQ_OUTOUT_DIR && NUMFAILS=$(find $PQ_OUTPUT_DIR  -size -1 -name "*.mp3" | xargs rm -v| wc -l 2>/dev/null)

	echo "NUMFAILS=$NUMFAILS if this is more than zero, consider writing code to kill the vlc process to force it to be restarted."

}

makeVisual() {
	FILEPATH="$1"
	sox "$FILEPATH" -n spectrogram -x 10000 -o "$FILEPATH-spectrogram.png"
}

recordOne() {
	OUTFILEPATH=$1
	
	echo "Starting new file: $OUTFILEPATH"
	STARTTIME=$(date +%s)
	# Notice the run time is 10 seconds longer than the period at which we start new recordsing? This overlap ensures that we don't have gaps in coverage.
	cvlc -v --run-time=310  -I DUMMY "$PQ_STREAM_URL" --sout "#file{dst=$OUTFILEPATH}" vlc://quit 2>&1 | cat >> $LOGFILE
	ENDTIME=$(date +%s)
	ELAPSED=$(($ENDTIME - $STARTTIME))
	if [ $ELAPSED -lt 200 ] ; then
		echo "WARNING: ELAPSED WAS LESS THAN EXPECTED. Actual=$ELAPSED. Check $LOGFILE for more details." | tee -a $LOGFILE
		# sleep 60
		return 0 
	else
		# Happy path. Short sleep time between creating new valid files.
		# sleep 1
		return 1
	fi
}

while : ; do 
	date >> $LOGFILE
	THISFILENAME="${FILEPREFIX}`date +%y%m%d-%H%M%S-UTC`.mp3"
	OUTFILEPATH="$PQ_OUTPUT_DIR/$THISFILENAME"

	recordOne "$OUTFILEPATH"  & 
	sleep 300

	echo "Purging old files..." | tee -a $LOGFILE
	purge
	echo "Creating visuals (in the background)" | tee -a $LOGFILE
	makeVisual "$OUTFILEPATH" &
done




