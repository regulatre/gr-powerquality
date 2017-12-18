#!/usr/bin/env python2
# -*- coding: utf-8 -*-
##################################################
# GNU Radio Python Flow Graph
# Title: Testautocancellation
# Generated: Sat Jul 15 10:05:02 2017
##################################################

from gnuradio import analog
from gnuradio import audio
from gnuradio import blocks
from gnuradio import eng_notation
from gnuradio import filter
from gnuradio import gr
from gnuradio.eng_option import eng_option
from gnuradio.filter import firdes
from optparse import OptionParser
import powerquality
import threading
import time


class testAutoCancellation(gr.top_block):

    def __init__(self):
        gr.top_block.__init__(self, "Testautocancellation")

        ##################################################
        # Variables
        ##################################################
        self.samp_rate = samp_rate = 48000
        self.func_getfreq = func_getfreq = 800*10

        ##################################################
        # Blocks
        ##################################################
        self.probe_getfreq = blocks.probe_signal_f()

        def _func_getfreq_probe():
            while True:
                val = self.probe_getfreq.level()
                try:
                    self.set_func_getfreq(val)
                except AttributeError:
                    pass
                time.sleep(1.0 / (1))
        _func_getfreq_thread = threading.Thread(target=_func_getfreq_probe)
        _func_getfreq_thread.daemon = True
        _func_getfreq_thread.start()

        self.fractional_interpolator_xx_0 = filter.fractional_interpolator_ff(0, 0.1)
        self.blocks_wavfile_sink_0 = blocks.wavfile_sink('/dev/stdout', 1, samp_rate, 16)
        self.blocks_multiply_const_vxx_1 = blocks.multiply_const_vff((-1, ))
        self.blocks_keep_one_in_n_0 = blocks.keep_one_in_n(gr.sizeof_float*1, 10)
        self.blocks_delay_1 = blocks.delay(gr.sizeof_float*1, int(func_getfreq))
        self.blocks_add_xx_1 = blocks.add_vff(1)
        self.audio_source_0 = audio.source(samp_rate, 'hw:1', True)
        self.analog_rail_ff_0 = analog.rail_ff(-0.8, 0.8)
        self.analog_agc2_xx_1 = analog.agc2_ff(1e-1, 1e-2, 0.1, 1.0)
        self.analog_agc2_xx_1.set_max_gain(65536)
        self.powerquality_getfreqcpp_0 = powerquality.getfreqcpp(0.1)

        ##################################################
        # Connections
        ##################################################
        self.connect((self.powerquality_getfreqcpp_0, 0), (self.probe_getfreq, 0))
        self.connect((self.analog_agc2_xx_1, 0), (self.analog_rail_ff_0, 0))
        self.connect((self.analog_rail_ff_0, 0), (self.blocks_wavfile_sink_0, 0))
        self.connect((self.audio_source_0, 0), (self.fractional_interpolator_xx_0, 0))
        self.connect((self.blocks_add_xx_1, 0), (self.blocks_keep_one_in_n_0, 0))
        self.connect((self.blocks_delay_1, 0), (self.blocks_add_xx_1, 1))
        self.connect((self.blocks_keep_one_in_n_0, 0), (self.analog_agc2_xx_1, 0))
        self.connect((self.blocks_multiply_const_vxx_1, 0), (self.blocks_delay_1, 0))
        self.connect((self.fractional_interpolator_xx_0, 0), (self.powerquality_getfreqcpp_0, 0))
        self.connect((self.fractional_interpolator_xx_0, 0), (self.blocks_add_xx_1, 0))
        self.connect((self.fractional_interpolator_xx_0, 0), (self.blocks_multiply_const_vxx_1, 0))

    def get_samp_rate(self):
        return self.samp_rate

    def set_samp_rate(self, samp_rate):
        self.samp_rate = samp_rate

    def get_func_getfreq(self):
        return self.func_getfreq

    def set_func_getfreq(self, func_getfreq):
        self.func_getfreq = func_getfreq
        self.blocks_delay_1.set_dly(int(self.func_getfreq))


def main(top_block_cls=testAutoCancellation, options=None):

    tb = top_block_cls()
    tb.start()
    try:
        raw_input('Press Enter to quit: ')
    except EOFError:
        pass
    tb.stop()
    tb.wait()


if __name__ == '__main__':
    main()
