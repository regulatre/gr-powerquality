#!/usr/bin/env python2
# -*- coding: utf-8 -*-
##################################################
# GNU Radio Python Flow Graph
# Title: Testaudiostreamport
# Generated: Sun Aug 13 23:28:13 2017
##################################################

from gnuradio import analog
from gnuradio import blocks
from gnuradio import eng_notation
from gnuradio import filter
from gnuradio import gr
from gnuradio.eng_option import eng_option
from gnuradio.filter import firdes
from grc_gnuradio import blks2 as grc_blks2
from optparse import OptionParser
import powerquality
import threading
import time


class testAudioStreamPort(gr.top_block):

    def __init__(self):
        gr.top_block.__init__(self, "Testaudiostreamport")

        ##################################################
        # Variables
        ##################################################
        self.samp_rate = samp_rate = 48000
        self.fundamental_wavelength_samples = fundamental_wavelength_samples = 800
        self.func_probe_b = func_probe_b = 8000

        ##################################################
        # Blocks
        ##################################################
        self.probe_b = blocks.probe_signal_f()

        def _func_probe_b_probe():
            while True:
                val = self.probe_b.level()
                try:
                    self.set_func_probe_b(val)
                except AttributeError:
                    pass
                time.sleep(1)
        _func_probe_b_thread = threading.Thread(target=_func_probe_b_probe)
        _func_probe_b_thread.daemon = True
        _func_probe_b_thread.start()

        self.powerquality_getfreqcpp_0 = powerquality.getfreqcpp(0.01)
        # self.fractional_interpolator_xx_0_0 = filter.fractional_interpolator_ff(0, 0.1)
        self.fractional_interpolator_xx_0 = filter.fractional_interpolator_ff(0, 0.1)
        self.blocks_wavfile_sink_0 = blocks.wavfile_sink('/dev/stdout', 2, samp_rate, 16)
        self.blocks_throttle_0_0 = blocks.throttle(gr.sizeof_float*1, samp_rate*10,True)
        self.blocks_throttle_0 = blocks.throttle(gr.sizeof_float*1, samp_rate*10,True)
        self.blocks_multiply_const_vxx_1 = blocks.multiply_const_vff((-1, ))
        self.blocks_multiply_const_vxx_0 = blocks.multiply_const_vff((-1, ))
        self.blocks_moving_average_xx_0 = blocks.moving_average_ff(1000, 0.001, 40)
        self.blocks_keep_one_in_n_0_0 = blocks.keep_one_in_n(gr.sizeof_float*1, 10)
        self.blocks_keep_one_in_n_0 = blocks.keep_one_in_n(gr.sizeof_float*1, 10)
        self.blocks_delay_1 = blocks.delay(gr.sizeof_float*1, int(round(func_probe_b)))
        self.blocks_delay_0 = blocks.delay(gr.sizeof_float*1, int(round(func_probe_b)))
        self.blocks_add_xx_1 = blocks.add_vff(1)
        self.blocks_add_xx_0 = blocks.add_vff(1)
        #self.blks2_tcp_source_0_0 = grc_blks2.tcp_source(
        #	itemsize=gr.sizeof_float*1,
        #	addr='localhost',
        #	port=5555,
        #	server=False,
        #)
        self.blks2_tcp_source_0 = grc_blks2.tcp_source(
        	itemsize=gr.sizeof_float*1,
        	addr='localhost',
        	port=5555,
        	server=False,
        )
        self.analog_rail_ff_1 = analog.rail_ff(-0.8, 0.8)
        self.analog_rail_ff_0 = analog.rail_ff(-0.8, 0.8)
	# 1e-2 (0.01) sounds great when input voltage to the Pi is clean (dirty rectifier voltage can introduce periodic bumps and thumbs that mess up AGC).
        myDecay = 1e-2
        # 0.1: pretty quick. Useful for exposing the thumb phenomenon that I'm currently investigating. 1e-2 (0.01) gets drown down due to thump but thump not very audible. 
        # myDecay = 0.1
        self.analog_agc2_xx_1 = analog.agc2_ff(0.1, myDecay, 0.1, 1.0)
        self.analog_agc2_xx_1.set_max_gain(65536)
        self.analog_agc2_xx_0 = analog.agc2_ff(0.1, myDecay, 0.1, 1.0)
        self.analog_agc2_xx_0.set_max_gain(65536)

        ##################################################
        # Connections
        ##################################################
        self.connect((self.analog_agc2_xx_0, 0), (self.analog_rail_ff_0, 0))
        self.connect((self.analog_agc2_xx_1, 0), (self.analog_rail_ff_1, 0))
        self.connect((self.analog_rail_ff_0, 0), (self.blocks_wavfile_sink_0, 0))
        self.connect((self.analog_rail_ff_1, 0), (self.blocks_wavfile_sink_0, 1))
        self.connect((self.blks2_tcp_source_0, 0), (self.fractional_interpolator_xx_0, 0))
        # self.connect((self.blks2_tcp_source_0, 0), (self.fractional_interpolator_xx_0_0, 0))
        self.connect((self.blocks_add_xx_0, 0), (self.blocks_keep_one_in_n_0, 0))
        self.connect((self.blocks_add_xx_1, 0), (self.blocks_keep_one_in_n_0_0, 0))
        self.connect((self.blocks_delay_0, 0), (self.blocks_multiply_const_vxx_0, 0))
        self.connect((self.blocks_delay_1, 0), (self.blocks_multiply_const_vxx_1, 0))
        self.connect((self.blocks_keep_one_in_n_0, 0), (self.analog_agc2_xx_0, 0))
        self.connect((self.blocks_keep_one_in_n_0_0, 0), (self.analog_agc2_xx_1, 0))
        self.connect((self.blocks_moving_average_xx_0, 0), (self.probe_b, 0))
        self.connect((self.blocks_multiply_const_vxx_0, 0), (self.blocks_add_xx_0, 1))
        self.connect((self.blocks_multiply_const_vxx_1, 0), (self.blocks_add_xx_1, 1))
        self.connect((self.blocks_throttle_0, 0), (self.blocks_add_xx_0, 0))
        self.connect((self.blocks_throttle_0, 0), (self.blocks_delay_0, 0))
        self.connect((self.blocks_throttle_0, 0), (self.powerquality_getfreqcpp_0, 0))
        self.connect((self.blocks_throttle_0_0, 0), (self.blocks_add_xx_1, 0))
        self.connect((self.blocks_throttle_0_0, 0), (self.blocks_delay_1, 0))
        self.connect((self.fractional_interpolator_xx_0, 0), (self.blocks_throttle_0, 0))
        self.connect((self.fractional_interpolator_xx_0, 0), (self.blocks_throttle_0_0, 0))
        self.connect((self.powerquality_getfreqcpp_0, 0), (self.blocks_moving_average_xx_0, 0))

    def get_samp_rate(self):
        return self.samp_rate

    def set_samp_rate(self, samp_rate):
        self.samp_rate = samp_rate
        self.blocks_throttle_0_0.set_sample_rate(self.samp_rate*10)
        self.blocks_throttle_0.set_sample_rate(self.samp_rate*10)

    def get_fundamental_wavelength_samples(self):
        return self.fundamental_wavelength_samples

    def set_fundamental_wavelength_samples(self, fundamental_wavelength_samples):
        self.fundamental_wavelength_samples = fundamental_wavelength_samples

    def get_func_probe_b(self):
        return self.func_probe_b

    def set_func_probe_b(self, func_probe_b):
        self.func_probe_b = func_probe_b
        self.blocks_delay_1.set_dly(int(round(self.func_probe_b)))
        self.blocks_delay_0.set_dly(int(round(self.func_probe_b)))


def main(top_block_cls=testAudioStreamPort, options=None):

    tb = top_block_cls()
    tb.start()
    try:
        runtime = 60*60*8
        print "Running for " + str(runtime) + " Seconds and then terminating."
        time.sleep(runtime)
        # raw_input('Press Enter to quit: ')
    except EOFError:
        pass
    tb.stop()
    tb.wait()


if __name__ == '__main__':
    main()
