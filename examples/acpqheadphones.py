#!/usr/bin/env python2
# -*- coding: utf-8 -*-
##################################################
# GNU Radio Python Flow Graph
# Title: Acpqheadphones
# Generated: Thu Aug 17 09:20:56 2017
##################################################


# 
# To get this to run on a Raspbery PI (without Alsa Invalid Argument error) I had to configure ~/.gnuradio/config.conf as so: 
#	$ cat ~/.gnuradio/config.conf 
#	[audio_alsa]
#	default_input_device = hw:1
#	default_output_device = hw:1
#	#period_time = 0.010                      # in seconds (default)
#	period_time = 0.100                      # in seconds
#	nperiods = 4                 # total buffering = period_time * nperiods
#	verbose = true
#
# Yes, even the verbose line seems to be important. Race condition?


# 
# 

from gnuradio import analog
from gnuradio import audio
from gnuradio import blocks
from gnuradio import eng_notation
from gnuradio import gr
from gnuradio.eng_option import eng_option
from gnuradio.filter import firdes
from optparse import OptionParser

from time import sleep


class acpqheadphones(gr.top_block):

    def __init__(self):
        gr.top_block.__init__(self, "Acpqheadphones")

        ##################################################
        # Variables
        ##################################################
        self.samp_rate = samp_rate = 48000

        ##################################################
        # Blocks
        ##################################################
        self.blocks_wavfile_sink_0 = blocks.wavfile_sink('pq.wav', 2, samp_rate, 16)
        self.blocks_multiply_const_vxx_0 = blocks.multiply_const_vff((-1, ))
        self.blocks_delay_0 = blocks.delay(gr.sizeof_float*1, 800)
        self.blocks_add_xx_0 = blocks.add_vff(1)
        self.audio_source_0 = audio.source(samp_rate, 'hw:1', True)
        self.audio_sink_0 = audio.sink(samp_rate, 'hw:1', True)
        self.analog_rail_ff_0 = analog.rail_ff(-0.8, 0.8)
        self.analog_agc2_xx_0 = analog.agc2_ff(1e-1, 0.5, 0.01, 1.0)
        self.analog_agc2_xx_0.set_max_gain(65536)

        ##################################################
        # Connections
        ##################################################
        self.connect((self.analog_agc2_xx_0, 0), (self.analog_rail_ff_0, 0))
        self.connect((self.analog_rail_ff_0, 0), (self.audio_sink_0, 0))
        self.connect((self.audio_source_0, 0), (self.blocks_add_xx_0, 0))
        self.connect((self.audio_source_0, 0), (self.blocks_delay_0, 0))
        self.connect((self.audio_source_0, 0), (self.blocks_wavfile_sink_0, 0))
        self.connect((self.blocks_add_xx_0, 0), (self.analog_agc2_xx_0, 0))
        self.connect((self.blocks_add_xx_0, 0), (self.blocks_wavfile_sink_0, 1))
        self.connect((self.blocks_delay_0, 0), (self.blocks_multiply_const_vxx_0, 0))
        self.connect((self.blocks_multiply_const_vxx_0, 0), (self.blocks_add_xx_0, 1))

    def get_samp_rate(self):
        return self.samp_rate

    def set_samp_rate(self, samp_rate):
        self.samp_rate = samp_rate


def main(top_block_cls=acpqheadphones, options=None):

    tb = top_block_cls()
    tb.start()
    #try:
    #    raw_input('Press Enter to quit: ')
    #except EOFError:
    #    pass

    sleepTime=60
    print("Sleeping for " + str(sleepTime) + " seconds.")
    sleep(sleepTime)
    print ("Sleep complete.")
    tb.stop()
    # tb.wait()


if __name__ == '__main__':
    main()
