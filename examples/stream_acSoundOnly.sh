/usr/bin/python ./acSoundOnlyStreamSource-adaptiveFrequency.py | /usr/bin/cvlc fd://0 --demux=rawaud --rawaud-channels=1 --rawaud-samplerate=48000 --sout "#transcode{acodec=mp3,channels=1,samplerate=48000}:std{access=http,mux=ts,dst=0.0.0.0:2020}"


