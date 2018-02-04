#!/usr/bin/env python
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
# for config.yml
import yaml
import argparse
# for printing to stderr
import sys

# Will be overwritten by calls to parseArgs()
ARGS = {}


parser = argparse.ArgumentParser(prog='streamer',description="VLC Streaming of fundamentally muted baseband audio")
parser.add_argument('-c', '--config', help='Configuration File Path & Filename',required=False, default="./config.yml")
parser.add_argument('-D', '--debug', help='Enable debug messages to stdout',required=False)

def getBlankStats():
    return {
        "noise_rms_micro_ch1": -1,  # RMS noise reading, times 1,000,000 so units becomes micro. (left channel)
        "noise_rms_micro_ch2": -1   # ^^ for channel 2 (right channel)
    }

# Stats
STATS = getBlankStats()


def log (yourMessage):
    # python2 syntax
    print >> sys.stderr, yourMessage
    # Python3: print yourMessage, file=sys.stderr

def setStat(statName,statValue):
    STATS[statName] = statValue
    log("STAT: " + statName + " = " + str(statValue))


def parseArgs():
    global ARGS

    # Parse commandline args. Prints help/usage and terminate application if anything goes wrong
    ARGS = parser.parse_args()
    log("Parsed commandline args. They are: " + str(ARGS))
    # Sanity Checks
    # If something doesn't check out, run argsFailed()

# Come here if parsing of commandline args failed, or if they are in some way invalid.
def argsFailed():
    parser.print_help()
    sys.exit()

def getConfigValue(keyname):
    return SETTINGS["streamer"][keyname]

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

        # This function will be started as a thread, taking samples from the RMS noise from each channel.
        def probe_rmsPostSuppression():
            while True:
                setStat("noise_rms_micro_ch1",self.probe_rmsPostSuppression_ch1.level()*1000*1000)
                setStat("noise_rms_micro_ch2",self.probe_rmsPostSuppression_ch2.level()*1000*1000)
                time.sleep(SETTINGS["streamer"]["harmonic_rms_thread_interval"]) # TODO: Move this setting to the configuration file.

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
        self.fractional_interpolator_xx_0_0 = filter.fractional_interpolator_ff(0, 0.1)
        self.fractional_interpolator_xx_0 = filter.fractional_interpolator_ff(0, 0.1)
        self.blocks_wavfile_sink_0 = blocks.wavfile_sink('/dev/stdout', 2, samp_rate, 16)
        self.blocks_throttle_0_0 = blocks.throttle(gr.sizeof_float*1, samp_rate*10,True)
        self.blocks_throttle_0 = blocks.throttle(gr.sizeof_float*1, samp_rate*10,True)
        self.blocks_multiply_const_vxx_1 = blocks.multiply_const_vff((-1, ))
        self.blocks_multiply_const_vxx_0 = blocks.multiply_const_vff((-1, ))
        self.blocks_getfreq_average_value = blocks.moving_average_ff(1000, 0.001, 40)
        self.blocks_keep_one_in_n_0_0 = blocks.keep_one_in_n(gr.sizeof_float*1, 10)
        self.blocks_keep_one_in_n_0 = blocks.keep_one_in_n(gr.sizeof_float*1, 10)
        self.blocks_delay_1 = blocks.delay(gr.sizeof_float*1, int(round(func_probe_b)))
        self.blocks_delay_0 = blocks.delay(gr.sizeof_float*1, int(round(func_probe_b)))
        self.blocks_add_xx_1 = blocks.add_vff(1)
        self.blocks_add_xx_0 = blocks.add_vff(1)

        # Calculation of RMS power post-suppression (amplitude of harmonics), also will vary based on effectiveness of the muting.
        rmsPostSuppressionAlpha = SETTINGS["streamer"]["rmsPostSuppressionAlpha"] # TODO: tune this
        rmsPostSuppressionAverageLength = SETTINGS["streamer"]["rmsPostSuppressionAverageLength"] # TODO: tune this
        rmsPostSuppressionAverageScale = SETTINGS["streamer"]["rmsPostSuppressionAverageScale"] # TODO: tune this
        log("TODO: Tune the Post suppression Alpha value for both RMS and average RMS. Or even remove the averaging if possible.")
        # Channel 1: Define the blocks needed to calculate and probe the average RMS harmonic power
        self.blocks_rmsPostSuppression_ch1 = blocks.rms_ff(rmsPostSuppressionAlpha)
        self.blocks_averagePostSuppression_ch1 = blocks.moving_average_ff(rmsPostSuppressionAverageLength,rmsPostSuppressionAverageScale,4000) # TODO: tune this
        self.probe_rmsPostSuppression_ch1 = blocks.probe_signal_f()
        # Channel 2: Define the blocks needed to calculate and probe the average RMS harmonic power
        self.blocks_rmsPostSuppression_ch2 = blocks.rms_ff(rmsPostSuppressionAlpha)
        self.blocks_averagePostSuppression_ch2 = blocks.moving_average_ff(rmsPostSuppressionAverageLength,rmsPostSuppressionAverageScale,4000) # TODO: tune this
        self.probe_rmsPostSuppression_ch2 = blocks.probe_signal_f()
        # channel 1: Connect the RMS harmonic blocks
        self.connect((self.blocks_rmsPostSuppression_ch1,0),(self.blocks_averagePostSuppression_ch1,0))
        self.connect((self.blocks_averagePostSuppression_ch1,0),(self.probe_rmsPostSuppression_ch1,0))
        # Channel 2: Connect the RMS harmonic blocks
        self.connect((self.blocks_rmsPostSuppression_ch2,0),(self.blocks_averagePostSuppression_ch2,0))
        self.connect((self.blocks_averagePostSuppression_ch2,0),(self.probe_rmsPostSuppression_ch2,0))

        # Connect Channels 1 and 2 to the larger flow.
        self.connect((self.blocks_keep_one_in_n_0,0),(self.blocks_rmsPostSuppression_ch1,0))
        self.connect((self.blocks_keep_one_in_n_0_0,0),(self.blocks_rmsPostSuppression_ch2,0))
        # Start a thread to poll both of hte post-suppression RMS voltage probes
        proball_thread = threading.Thread(target=probe_rmsPostSuppression)
        proball_thread.daemon = True
        proball_thread.start()


        # Left channel TCP connection
        self.blocks_socket_pdu_left_inputchannel = blocks.socket_pdu(
            "TCP_CLIENT",
            getConfigValue("pqserver"),
            str(getConfigValue("left_channel_tap_port")),
            10000, # this arg is unused because we are client
            False) # this arg is unused because we are client
        self.blocks_pdu_to_tagged_stream_left = blocks.pdu_to_tagged_stream(
            blocks.float_t,
            SETTINGS["networking_tap1"]["length_tag_name"])
        self.msg_connect((self.blocks_socket_pdu_left_inputchannel,"pdus"),(self.blocks_pdu_to_tagged_stream_left,"pdus"))

        # Right Channel TCP connection
        self.blocks_socket_pdu_right_inputchannel = blocks.socket_pdu(
            "TCP_CLIENT",
            getConfigValue("pqserver"),
            str(getConfigValue("right_channel_tap_port")),
            10000, # this arg is unused because we are client
            False) # this arg is unused because we are client
        self.blocks_pdu_to_tagged_stream_right = blocks.pdu_to_tagged_stream(
            blocks.float_t,
            SETTINGS["networking_tap1"]["length_tag_name"])
        self.msg_connect((self.blocks_socket_pdu_right_inputchannel, "pdus"), (self.blocks_pdu_to_tagged_stream_right, "pdus"))

        self.analog_rail_ff_1 = analog.rail_ff(-0.8, 0.8)
        self.analog_rail_ff_0 = analog.rail_ff(-0.8, 0.8)
        # myDecay of 1e-2 (0.01) sounds great when input voltage to the Pi is clean (dirty rectifier voltage can introduce periodic bumps and thumbs that mess up AGC).
        # myDecay of 0.1: pretty quick. Useful for exposing the thumb phenomenon that I'm currently investigating. 1e-2 (0.01) gets drown down due to thump but thump not very audible.

        # Sensible default
        myDecay = 1e-2
        # Allow overriding in config file.
        if ("agc_decay_rate" in SETTINGS["streamer"]):
            myDecay = SETTINGS["streamer"]["agc_decay_rate"]
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
        self.connect((self.blocks_pdu_to_tagged_stream_left, 0), (self.fractional_interpolator_xx_0, 0))
        self.connect((self.blocks_pdu_to_tagged_stream_right, 0), (self.fractional_interpolator_xx_0_0, 0))
        self.connect((self.blocks_add_xx_0, 0), (self.blocks_keep_one_in_n_0, 0))
        self.connect((self.blocks_add_xx_1, 0), (self.blocks_keep_one_in_n_0_0, 0))
        self.connect((self.blocks_delay_0, 0), (self.blocks_multiply_const_vxx_0, 0))
        self.connect((self.blocks_delay_1, 0), (self.blocks_multiply_const_vxx_1, 0))
        self.connect((self.blocks_keep_one_in_n_0, 0), (self.analog_agc2_xx_0, 0))
        self.connect((self.blocks_keep_one_in_n_0_0, 0), (self.analog_agc2_xx_1, 0))
        self.connect((self.blocks_getfreq_average_value, 0), (self.probe_b, 0))
        self.connect((self.blocks_multiply_const_vxx_0, 0), (self.blocks_add_xx_0, 1))
        self.connect((self.blocks_multiply_const_vxx_1, 0), (self.blocks_add_xx_1, 1))
        self.connect((self.blocks_throttle_0, 0), (self.blocks_add_xx_0, 0))
        self.connect((self.blocks_throttle_0, 0), (self.blocks_delay_0, 0))
        self.connect((self.blocks_throttle_0, 0), (self.powerquality_getfreqcpp_0, 0))
        self.connect((self.blocks_throttle_0_0, 0), (self.blocks_add_xx_1, 0))
        self.connect((self.blocks_throttle_0_0, 0), (self.blocks_delay_1, 0))
        self.connect((self.fractional_interpolator_xx_0, 0), (self.blocks_throttle_0, 0))
        self.connect((self.fractional_interpolator_xx_0_0, 0), (self.blocks_throttle_0_0, 0))
        self.connect((self.powerquality_getfreqcpp_0, 0), (self.blocks_getfreq_average_value, 0))


    def set_postSuppressionRMS(self, currentReading):
        self.current

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

def readSettings(configFileName):
    log("Loading settings from " + configFileName)
    # Read settings from configuration file
    with open(configFileName, "r") as myfile:
        fileContents = myfile.read()
    log("Settings loaded.")
    return yaml.load(fileContents)

def main(top_block_cls=testAudioStreamPort, options=None):
    global SETTINGS
    global ARGS

    log("Note! This application shares the config.yml file with acpq.py. Streamer cofiguration is located in the streamer section of the config.")
    parseArgs()
    SETTINGS = readSettings(ARGS.config)

    tb = top_block_cls()
    tb.start()
    try:
        runtime = 60*60*8
        log("Running for " + str(runtime) + " Seconds and then terminating.")
        time.sleep(runtime)
        # raw_input('Press Enter to quit: ')
    except EOFError:
        pass
    tb.stop()
    tb.wait()


if __name__ == '__main__':
    main()
