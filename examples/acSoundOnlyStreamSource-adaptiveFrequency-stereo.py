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
from gnuradio import fft
from gnuradio.fft import window


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
# for terminating
import os
import math
import copy

# For getting host name.
import socket


import signal
import json

from KafkaPq import KafkaPq
import random
from gnuradio import zeromq

# Will be overwritten by calls to parseArgs()
ARGS = {}

# to be initialized during startup.
kafka = False


parser = argparse.ArgumentParser(prog='streamer',description="VLC Streaming of fundamentally muted baseband audio")
parser.add_argument('-c', '--config', help='Configuration File Path & Filename',required=False, default="./config.yml")
parser.add_argument('-D', '--debug', help='Enable debug messages to stdout',required=False)

def getEpochMillis():
    # time.time() returns a float, expressed in terms of seconds, but multiplying by 1000 gives us a pretty accurate milliseconds.
    return int(round(time.time() * 1000))

def getBlankStats():
    return {
        "lastreadandreset": getEpochMillis(),
        "freq": -1,
        "wavelen": -1, # Wavelength, in samples, 8000 = 60=Hz because 48 Khz is upsampled to 480K, then measured.
        "noise_rms_micro_ch1": -1,  # RMS noise reading, times 1,000,000 so units becomes micro. (left channel)
        "noise_rms_micro_ch2": -1,   # ^^ for channel 2 (right channel)
        "noise_rms_log10_ch1": -1,
        "noise_rms_log10_ch2": -1,
        "err_rps_thread_exceptions": 0,
        "err_fpb_thread_exceptions": 0
    }

# Stats
STATS = getBlankStats()

# To be set false on termination, to ensure that threads stop running.
THREADS_ENABLED=True


def terminateApplication(message):
    global THREADS_ENABLED
    THREADS_ENABLED = False
    log("TERMINATING APPLICATION. Message=" + message)
    os.kill(os.getpid(), signal.SIGTERM)


def log(yourMessage):
    # python2 syntax
    print >> sys.stderr, yourMessage
    # Python3: print yourMessage, file=sys.stderr

    if kafka == False:
        return

    try:
        logMessage = {
            "timestamp": getEpochMillis(),
            "msg": yourMessage
        }
        sendKafka("pq.streamer.logs",json.dumps(logMessage))
    except Exception as e:
        err = e
        pass


def setStat(statName,statValue):
    STATS[statName] = statValue
    # log("STAT: " + statName + " = " + str(statValue))

def getStat(statName):
    if (statName in STATS):
      return STATS[statName]
    else:
      return 0

def incrementStat(statName):
    if (statName in STATS):
        STATS[statName] = STATS[statName] + 1
    else:
        STATS[statName] = 1

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
    # os._exit(25)

def getConfigValue(keyname,defaultValue=-1):
    if keyname in SETTINGS["streamer"]:
        return SETTINGS["streamer"][keyname]
    else:
        return defaultValue


def configValueExists(keyname):
    return keyname in SETTINGS["streamer"]

def initializeKafka():
    global kafka

    kafkaSettings = {
        "broker_list": getConfigValue("kafka_broker_list"),
        "message_send_timeout_seconds": getConfigValue(("kafka_message_send_timeout_seconds",1))
    }

    log("Initializing connection to kafka...")
    kafka = KafkaPq(kafkaSettings)
    log("Kafka connection open?")


def isKafkaEnabled():
    if (configValueExists("kafka_enabled") != True or getConfigValue("kafka_enabled") != True):
        return False
    return True


def sendKafka(topicName,topicMessage):
    global kafka

    # Support kafka on/off switch in the config file.
    if isKafkaEnabled() != True:
        return;

    if (kafka == False):
        initializeKafka()

    # TODO: error handling (what if kafka not available on startup? What if the connection to kafka goes down?


    # log("Sending to Kafka: " + topicName + " this: " + topicMessage)
    kafka.sendMsg(topicName,topicMessage)


def getBlankFftStatsVariables():
    return {
        "exceptions": 0,
        "samplecount": 0,
        # Avglevel goes down when a small number of bins spike.
        "avglevel": -1,
        "fft_0_snr": -1,
        "fft_1_snr": -1,
        "fft_2_snr": -1,
        "fft_3_snr": -1,
        "fft_4_snr": -1,
        "fft_5_snr": -1,
        "fft_6_snr": -1,
        "fft_7_snr": -1
    }

FFTSTATS = getBlankFftStatsVariables()

def getHostname():
    return socket.gethostname()


APP_START_TIME = getEpochMillis()
def getAppUptimeMinutes():
    global APP_START_TIME
    uptimeMillis = getEpochMillis() - APP_START_TIME
    return round((uptimeMillis / (1000.0*60.0)),1)


def getStats():
    global STATS
    global FFTSTATS

    fullStats = {
        "timestamp": getEpochMillis(),
        "hostname": getHostname(),
        "sourcename": SETTINGS["streamer"]["sourcename"],
        "appuptimemins": getAppUptimeMinutes(),
        "stats": STATS,
        "fft": FFTSTATS
    }

    # Add/update the timestamp field, so the stats are timestamped.
    return fullStats


def readAndResetAnalysisVariables():
    global FFTSTATS

    # myAnalysisVariables = copy.copy(analysis_variables)

    bins = ""
    # log("DEBUG: Building an FFT string")
    for binnum in range(16):
        bins = bins + str(FFTSTATS["fft_" + str(binnum) + "_snr"]) + " "


    # log("DEBUG: About to print FFT analysis variables")
    if SETTINGS["streamer"]["debug_messages_fft"] == True:
        log(
                " FFT: errors=" + str(FFTSTATS["exceptions"]) +
                " samples=" + str(FFTSTATS["samplecount"]) +
                " avg=" + str(FFTSTATS["avglevel"]) +
                " first bins: " + bins)
    # print (json.dumps(analysis_variables))
    # log("DEBUG: Resetting analysis variables")
    FFTSTATS = getBlankFftStatsVariables()

    # return myAnalysisVariables

def kafkaPublishAllStats():
    sendKafka(SETTINGS["streamer"]["kafka_topic_allstats"], json.dumps(getStats(), sort_keys=True))

def processOneSnapshot(vectorDataChunk):

    bigaverage = 0
    # input magnitudes within the vectorDataChunk each get multiplied by this factor, to bring them into integer domain
    multiplier = 10000

    for thisDataElement in vectorDataChunk:
        thisDataElement = thisDataElement * multiplier
        bigaverage = (bigaverage + thisDataElement) / 2

    # For keeping track of which bin we're in.
    binNum = 0
    # We'll keep track of avglevel for purposes of comparing one reporting to the next.
    avgLevel = 0
    # sys.stdout.write("len=" + str(len(vectorDataChunk)) + "\n")
    # log("Processing one snapshot. About to loop")
    for thisDataElement in vectorDataChunk:
        thisDataElement = thisDataElement * multiplier
        thisDataElement = int(round(thisDataElement))

        # initial setting. instead of starting at 0 which wouldn't make sense for an average.
        if avgLevel == 0:
            avgLevel = thisDataElement

        avgLevel = (avgLevel + thisDataElement) / 2


        # # Calculate the log ratio of the bin above average.
        fftElementName = "fft_" + str(binNum) + "_snr"

        # log("DEBUG: Processing one snapshot. element name=" + fftElementName)

        try:

            elementSnr = thisDataElement / bigaverage
            # Avoid log domain exception by weeding out samples with value 0. Should FFT->MAG^^2 ever send us a zero though!?!?

            # If the analysis variables were just reset and have no data yet, then initialize it.
            if FFTSTATS["avglevel"] == -1:
                FFTSTATS[fftElementName] = elementSnr
            else:
                FFTSTATS[fftElementName] = (FFTSTATS[fftElementName] + elementSnr) / 2

            # Round the number to a reasonable decimal place.
            FFTSTATS[fftElementName] = round(FFTSTATS[fftElementName], 3)

        except Exception as easdfasdf:
            FFTSTATS["exceptions"] = FFTSTATS["exceptions"] + 1
            e = easdfasdf
            log("Exception " + str(e) + " while taking log10 of " + str(thisDataElement) + " /" + str(bigaverage))

        # log("DEBUG: Updating analysis variable...")
        FFTSTATS["samplecount"] = FFTSTATS["samplecount"] + 1
        # log("DEBUG: DONE Updating analysis variable...")

        binNum = binNum + 1
        # End of the for-loop.

    # Always set avg level after looping through a full set.
    if FFTSTATS["avglevel"] == -1:
        # set initial value after having been reset
        FFTSTATS["avglevel"] = avgLevel
    else:
        # running average
        FFTSTATS["avglevel"] = (FFTSTATS["avglevel"] + avgLevel) / 2

    # TODO: Make his more tuneable. It can be time based if we divide out sample count by fft vector size etc.

    # About 220 samples per second. So 32767 yields updates about every 2.5 minutes.
    # 4096 yields updates every ...?
    if FFTSTATS["samplecount"] % (4096) == 0:
        # NOT IT. incorrect checksum for freed object - object was probably modified after being freed

        # Log some metrics that will help us better understand the modulo tuning value.
        millisSinceLastReset=getEpochMillis() - getStat("lastreadandreset")
        secondsSinceLastReset=millisSinceLastReset/1000
        secondsSinceLastReset = round(secondsSinceLastReset,1)
        setStat("lastreadandreset",getEpochMillis())
        setStat("secondssincereset",secondsSinceLastReset)

        kafkaPublishAllStats()
        readAndResetAnalysisVariables()

    # END OF processOneSnapshot()


class testAudioStreamPort(gr.top_block):

    def __init__(self):
        gr.top_block.__init__(self, "Testaudiostreamport")
        self.freq_wavelength = 8000

        ##################################################
        # Variables
        ##################################################
        self.samp_rate = samp_rate = 48000
        self.fundamental_wavelength_samples = fundamental_wavelength_samples = 800
        self.freq_wavelength = freq_wavelength = 8000
        self.myVectorLength = myVectorLength = 32
        self.lowpass_cutoff_freq = 4000
        self.n_keep = (self.samp_rate/2)/self.lowpass_cutoff_freq

        # allow the rms post suppression thread to track if changes aren't happening, which suggests a dead flowgraph.
        self.rmspostsup_nochange_count = 0

        ##################################################
        # Blocks
        ##################################################
        self.probe_avg_frequency = blocks.probe_signal_f()

        if ("getfreq_alpha" in SETTINGS["streamer"]):
            myGetfreqAlpha = SETTINGS["streamer"]["getfreq_alpha"]
        else:
            myGetfreqAlpha = 0.1

        self.powerquality_getfreqcpp_0 = powerquality.getfreqcpp(myGetfreqAlpha)
        self.fractional_interpolator_xx_0_0 = filter.fractional_interpolator_ff(0, 0.1)
        self.fractional_interpolator_xx_0 = filter.fractional_interpolator_ff(0, 0.1)
        self.blocks_wavfile_sink_0 = blocks.wavfile_sink('/dev/stdout', 2, samp_rate, 16)
        self.blocks_throttle_0_0 = blocks.throttle(gr.sizeof_float*1, samp_rate*10,True)
        self.blocks_throttle_0 = blocks.throttle(gr.sizeof_float*1, samp_rate*10,True)
        self.blocks_multiply_const_vxx_1 = blocks.multiply_const_vff((-1, ))
        self.blocks_multiply_const_vxx_0 = blocks.multiply_const_vff((-1, ))
        # self.blocks_getfreq_average_value = blocks.moving_average_ff(1000, 0.001, 40)
        self.blocks_keep_one_in_n_0_0 = blocks.keep_one_in_n(gr.sizeof_float*1, 10)
        self.blocks_keep_one_in_n_0 = blocks.keep_one_in_n(gr.sizeof_float*1, 10)
        self.blocks_delay_1 = blocks.delay(gr.sizeof_float*1, int(round(freq_wavelength)))
        self.blocks_delay_0 = blocks.delay(gr.sizeof_float*1, int(round(freq_wavelength)))
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




        # Left channel TCP connection
        # log("Connecting to " + getConfigValue("pqserver") + ":" + str(getConfigValue("left_channel_tap_port")))
        # self.blocks_socket_pdu_left_inputchannel = blocks.socket_pdu(
        #     "TCP_CLIENT",
        #     getConfigValue("pqserver"),
        #     str(getConfigValue("left_channel_tap_port")),
        #     10000, # this arg is unused because we are client
        #     False) # this arg is unused because we are client
        # self.blocks_pdu_to_tagged_stream_left = blocks.pdu_to_tagged_stream(
        #     blocks.float_t,
        #     SETTINGS["networking_tap1"]["length_tag_name"])

        self.zeromq_sub_source_left  = zeromq.sub_source(gr.sizeof_float, 1, SETTINGS["streamer"]["zmq_server_uri_left_channel"], 5000, True, -1)

        # optimization: if left and right channels are specified as the same source then make a single connection to the source.
        if SETTINGS["streamer"]["zmq_server_uri_left_channel"] == SETTINGS["streamer"]["zmq_server_uri_right_channel"]:
            self.zeromq_sub_source_right = self.zeromq_sub_source_left
            log("Optimization: Only making a single connection to PQ server since left and right streamer channels have same ZMQ URI.")
        else:
            # Connection URI/address to server is different for left and right channel so make a second connection for right channel.
            self.zeromq_sub_source_right = zeromq.sub_source(gr.sizeof_float, 1, SETTINGS["streamer"]["zmq_server_uri_right_channel"], 5000, True, -1)


        # self.msg_connect((self.blocks_socket_pdu_left_inputchannel,"pdus"),(self.blocks_pdu_to_tagged_stream_left,"pdus"))
        #
        # # Right Channel TCP connection
        # log("Connecting to " + getConfigValue("pqserver") + ":" + str(getConfigValue("right_channel_tap_port")))
        # self.blocks_socket_pdu_right_inputchannel = blocks.socket_pdu(
        #     "TCP_CLIENT",
        #     getConfigValue("pqserver"),
        #     str(getConfigValue("right_channel_tap_port")),
        #     10000, # this arg is unused because we are client
        #     False) # this arg is unused because we are client
        # self.blocks_pdu_to_tagged_stream_right = blocks.pdu_to_tagged_stream(
        #     blocks.float_t,
        #     SETTINGS["networking_tap1"]["length_tag_name"])
        # self.msg_connect((self.blocks_socket_pdu_right_inputchannel, "pdus"), (self.blocks_pdu_to_tagged_stream_right, "pdus"))

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
        self.connect((self.zeromq_sub_source_left, 0), (self.fractional_interpolator_xx_0, 0))
        self.connect((self.zeromq_sub_source_right, 0), (self.fractional_interpolator_xx_0_0, 0))
        self.connect((self.blocks_add_xx_0, 0), (self.blocks_keep_one_in_n_0, 0))
        self.connect((self.blocks_add_xx_1, 0), (self.blocks_keep_one_in_n_0_0, 0))
        self.connect((self.blocks_delay_0, 0), (self.blocks_multiply_const_vxx_0, 0))
        self.connect((self.blocks_delay_1, 0), (self.blocks_multiply_const_vxx_1, 0))
        self.connect((self.blocks_keep_one_in_n_0, 0), (self.analog_agc2_xx_0, 0))
        self.connect((self.blocks_keep_one_in_n_0_0, 0), (self.analog_agc2_xx_1, 0))
        self.connect((self.powerquality_getfreqcpp_0, 0), (self.probe_avg_frequency, 0))
        self.connect((self.blocks_multiply_const_vxx_0, 0), (self.blocks_add_xx_0, 1))
        self.connect((self.blocks_multiply_const_vxx_1, 0), (self.blocks_add_xx_1, 1))
        self.connect((self.blocks_throttle_0, 0), (self.blocks_add_xx_0, 0))
        self.connect((self.blocks_throttle_0, 0), (self.blocks_delay_0, 0))
        self.connect((self.blocks_throttle_0, 0), (self.powerquality_getfreqcpp_0, 0))
        self.connect((self.blocks_throttle_0_0, 0), (self.blocks_add_xx_1, 0))
        self.connect((self.blocks_throttle_0_0, 0), (self.blocks_delay_1, 0))
        self.connect((self.fractional_interpolator_xx_0, 0), (self.blocks_throttle_0, 0))
        self.connect((self.fractional_interpolator_xx_0_0, 0), (self.blocks_throttle_0_0, 0))
        # self.connect((self.powerquality_getfreqcpp_0, 0), (self.blocks_getfreq_average_value, 0))

        ### Define FFT related blocks LEFT-CHANNEL ONLY FOR NOW.
        self.fft_vxx_0 = fft.fft_vfc(myVectorLength, True, (window.blackmanharris(myVectorLength)), 1)
        self.blocks_stream_to_vector_0 = blocks.stream_to_vector(gr.sizeof_float*1, myVectorLength)
        self.blocks_keep_one_in_n_0 = blocks.keep_one_in_n(gr.sizeof_float*1, self.n_keep)
        self.blocks_complex_to_mag_squared_0 = blocks.complex_to_mag_squared(myVectorLength)
        self.blocks_throttle = blocks.throttle(gr.sizeof_float * 1, self.samp_rate, True)
        self.blocks_fft_vector_sink_0 = blocks.vector_sink_f(self.myVectorLength)

        ### Connect FFT BLOCKS.
        # Down-sample / decimate the input. We pick up the flowgraph after AGC but before the rail.
        self.connect((self.analog_agc2_xx_0, 0), (self.blocks_keep_one_in_n_0, 0))
        # Convert the stream to a vector in preparation for FFT
        self.connect((self.blocks_keep_one_in_n_0, 0), (self.blocks_stream_to_vector_0, 0))
        # Perform FFT analysis of the stream.
        self.connect((self.blocks_stream_to_vector_0, 0), (self.fft_vxx_0, 0))
        # Send FFT data (phase and magnitude) into a mag^2 block to get strength of each bin
        self.connect((self.fft_vxx_0, 0), (self.blocks_complex_to_mag_squared_0, 0))
        # Send the final result (magnitudes in each fft bin) into vector sink.
        # self.connect((self.blocks_complex_to_mag_squared_0, 0), (self.blocks_fft_vector_sink_0, 0))
        self.connect((self.blocks_complex_to_mag_squared_0, 0), (self.blocks_fft_vector_sink_0, 0))



    # See if making a copy of the vector contents before referencing it actually helps avoid the malloc error.
    # Added skipread arg only for https://github.com/gnuradio/gnuradio/issues/1764 - to use random data instead of data read from the vector.
    def getFftVectorCopyAndResetIt(self):
        # Consume the contents of the vector now that we've read it. Otherwise we keep reading the same data over and over as it gets concatenated.
        # log("DEBUG: Before resetting vector sink")

        # lock to prepare for reconfigure... https://lists.gnu.org/archive/html/discuss-gnuradio/2011-05/msg00493.html

        # self.disconnect((self.blocks_complex_to_mag_squared_0, 0), (self.blocks_fft_vector_sink_0, 0))
        # Backup reference
        # self.blocks_fft_vector_sink_0_old = self.blocks_fft_vector_sink_0
        duplicateVectorData = copy.deepcopy(self.blocks_fft_vector_sink_0.data())

        self.blocks_fft_vector_sink_0.reset()

        # log("DEBUG: OLD vector sink has size: " + str(len(self.blocks_fft_vector_sink_0.data())))
        # create new
        # self.blocks_fft_vector_sink_0 = blocks.vector_sink_f(self.myVectorLength)
        # log("DEBUG: New vector sink has size: " + str(len(self.blocks_fft_vector_sink_0.data())))

        # self.connect((self.blocks_complex_to_mag_squared_0, 0), (self.blocks_fft_vector_sink_0, 0))
        # self.lock()
        # self.unlock()

        # log("DEBUG: Vector is disconnected 0. len=" + str(len(self.blocks_fft_vector_sink_0.data())))
        # time.sleep(1.0)
        # log("DEBUG: Vector is disconnected 1. len=" + str(len(self.blocks_fft_vector_sink_0.data())))
        # time.sleep(1.0)
        # log("DEBUG: Vector is disconnected 2. len=" + str(len(self.blocks_fft_vector_sink_0.data())))
        # time.sleep(1.0)
        # log("DEBUG: Vector is disconnected 3. len=" + str(len(self.blocks_fft_vector_sink_0.data())))
        # time.sleep(1.0)

        # log("DEBUG: After resetting vector sink")
        # log("DEBUG: probeFftDataThread(): SLEEPING after processing took " + str(elapsedSnapshotProcessingTime) + " ms.")

        return duplicateVectorData


    def probeFftDataThread(self):
        # # Sleep while the flow graph starts up. Without waiting we would get attribute errors.
        # time.sleep(5)

        loopNum = 0
        while True:
            # log("DEBUG: probeFftDataThread(): AWAKE")
            loopNum = loopNum + 1
            # dataVal = self.probeFft.data()
            # try:

            # Get a COPY of the vector contents, then reset it.
            vectorDataChunk = self.getFftVectorCopyAndResetIt()


            if (len(vectorDataChunk) == 0):
                time.sleep(0.1)

                continue;

            numSnapshots = len(vectorDataChunk) / self.myVectorLength
            # log ("TODO: Break up the current data chunk size of " + str(len(vectorDataChunk)) + " into " + str(numSnapshots) + " snapshots.")

            # if numSnapshots > 1:
            #     print ("Here comes " + str(numSnapshots) + " snapshots...")

            snapshotProcessingStartTime = getEpochMillis()
            for snapshotNum in range(numSnapshots):
                # print ("Snapshot#" + str(snapshotNum) + " array offset=" + str(snapshotNum * myVectorLength) + " end offset=" + str(myVectorLength / 2))
                # Build a single FFT frame, discarding the right half (mirrored portion).
                startOffset = snapshotNum * self.myVectorLength
                endOffset = startOffset + self.myVectorLength / 2
                thisSnapshot = vectorDataChunk[startOffset:endOffset]
                # log("DEBUG: NOT Processing one snapshot. Does the app still crash even without processing the snapshot? If so then that function is not to blame.")

                # NOT IT. error for object 0x7f89f642aec8: incorrect checksum for freed object - object was probably modified after being freed
                processOneSnapshot(thisSnapshot)

            elapsedSnapshotProcessingTime = getEpochMillis() - snapshotProcessingStartTime
            setStat("snapshotprocessingtime",elapsedSnapshotProcessingTime)

            time.sleep(0.1)

    # This function will be started as a thread, taking samples from the RMS noise from each channel.
    def probe_rmsPostSuppression(self):
        global THREADS_ENABLED


        # set random initial values 
        self.lastch1reading = 0.123
        self.lastch2reading = 0.456

        newch1reading = 0
        newch2reading = 0

        while THREADS_ENABLED==True:
            # log("DEBUG: probe_rmsPostSuppression(): AWAKE")
            try:

                # Special logic added to help the flow graph terminate. This addresses the issue of the flowgraph not stopping when the output pipe is terminated.
                rawch1reading = self.probe_rmsPostSuppression_ch1.level()
                rawch2reading = self.probe_rmsPostSuppression_ch2.level()
                if (rawch1reading > 0 and rawch2reading > 0):
                  newch1reading = round(rawch1reading*1000*1000,3)
                  newch2reading = round(rawch2reading*1000*1000,3)
                  setStat("noise_rms_micro_ch1", newch1reading)
                  setStat("noise_rms_micro_ch2", newch2reading)
                  setStat("noise_rms_log10_ch1", round(math.log10(rawch1reading),3))
                  setStat("noise_rms_log10_ch2", round(math.log10(rawch2reading),3))
                  # log("Good reading.")
                else:
                  log("probe_rmsPostSuppression(): Throwing out bad readings " + str(newch1reading) + " / " + str(newch2reading))
                
                # Special logic added to help the flow graph terminate. This addresses the issue of the flowgraph not stopping when the output pipe is terminated. 
                if (newch1reading == self.lastch1reading and newch2reading == self.lastch2reading):
                    self.rmspostsup_nochange_count = self.rmspostsup_nochange_count + 1

                    log("probe_rmsPostSuppression(): WARNING: possible dead flowgraph. post-suppression thread probes seem to be stuck on the same reading. will terminate if it continues.")

                    if self.rmspostsup_nochange_count > getConfigValue("rmspostsup_nochange_count_max",60):
                        log("probe_rmsPostSuppression(): ERROR: Probed rms micro readings didn't change so there must be a problem. Terminating flowgraph (using sigterm signal to kill toe PID because flowgraphs crash in a weird way!")
                        terminateApplication("RMS Micro readings didn't change. Flowgraph must be dead")
                else:
                    self.rmspostsup_nochange_count = 0

                self.lastch1reading = newch1reading
                self.lastch2reading = newch2reading

            except Exception as e:
                err = e
                log("probe_rmsPostSuppression(): EXCEPTION: " + str(err))
                incrementStat("err_rps_thread_exceptions")
            # log("DEBUG: probe_rmsPostSuppression(): SLEEPING...")
            time.sleep(SETTINGS["streamer"]["harmonic_rms_thread_interval"])
        log("probe_rmsPostSuppression() Thread has terminated. THREADS_ENABLED=" + str(THREADS_ENABLED))

    # Average Frequency probe
    def frequency_measurement_thread(self):
        global THREADS_ENABLED
        # initialize this to something nonsense that should change immediately.
        self.last_frequency_wavelength = 8888
        max_freq_nochange_count = getConfigValue("max_freq_nochange_count",300)
        while THREADS_ENABLED==True:
            # log("DEBUG: frequency_measurement_thread(): AWAKE...")
            try:
                val = self.probe_avg_frequency.level()

                # Sanity check: After observing a 8-hour span of wildly inaccurate frequency calculations, I'm adding this circuit breaker.
                if val < 7000 or val > 9000:
                    terminateApplication("FATAL: Wildly inaccurate frequency wavelength was sampled from the frequency probe. wavelen wamples (expect 8000) was " + str(val))

                setStat("wavelen",round(val,3))

                # To calculate frequency, take 10x sampe rate (we interpolate the signal before getfreq to increase resolution of Hz measurement)
                hz = (self.samp_rate*10)/val
                hz = round(hz,3)
                setStat("freq", hz)
                if SETTINGS["streamer"]["debug_messages_fft"] == True:
                    log("Hz=" + str(hz))
                self.set_average_frequency_reading(val)
                if val == self.last_frequency_wavelength:
                    self.last_frequency_samecount = self.last_frequency_samecount + 1
                    log("WARNING: frequency_measurement_thread(): Frequency hasn't changed in " + str(self.last_frequency_samecount) + " iterations.")
                    if self.last_frequency_samecount > max_freq_nochange_count:
                        log("ERROR: frequency_measurement_thread(): Frequency measurement was stuck. Assuming flowgraph is dead. Terminating application NOW.")
                        terminateApplication("Dead Current Probe and or flowgraph")
                else:
                    self.last_frequency_samecount = 0
                self.last_frequency_wavelength = val
            except Exception as e:
                err = e
                log("EXCEPTION in Hz probe thread frequency_measurement_thread(): " + str(err))
                incrementStat("err_freq_thread_exceptions")
                if getStat("err_freq_thread_exceptions") > 10:
                    terminateApplication("FATAL: frequency Measurement Thread encountered too many exceptions. terminating streamer (it will restart)")
                else:
                    log("Total exceptions so far: " + str(getStat("err_freq_thread_exceptions")))

            # log("DEBUG: frequency_measurement_thread(): SLEEPING...")
            time.sleep(1)
        log("frequency_measurement_thread - has terminated. THREADS_ENABLED=" + str(THREADS_ENABLED))

    def startThreads(self):
        self.last_frequency_samecount = 0

        # log("DEBUG: strtThreads(): RMS POST SUPPRESSION THREAD IS DISABLED...")
        log ("Starting RMS post-suppression analysis thread");
        # NOT IT. Python(86100,0x70000eab9000) malloc: *** error for object 0x7f94bf9042b8: incorrect checksum for freed object - object was probably modified after being freed.
        # Start a thread to poll both of hte post-suppression RMS voltage probes
        rmsPostSuppressionThreadHandle = threading.Thread(target=self.probe_rmsPostSuppression)
        rmsPostSuppressionThreadHandle.daemon = True
        rmsPostSuppressionThreadHandle.start()

        # Start a thread that monitors the frequency
        log ("Starting Hz tracker thread");
        freq_measurement_thread_handle = threading.Thread(target=self.frequency_measurement_thread)
        freq_measurement_thread_handle.daemon = True
        freq_measurement_thread_handle.start()

        # log("DEBUG: FFT THREAD IS ENABLED. IT CRASHES A LOT WITH THIS ERROR: Python(88553,0x700008aec000) malloc: *** error for object 0x7f9584c3d4a8: incorrect checksum for freed object - object was probably modified after being freed.")
        log("Starting FFT Thread")
        fftThread = threading.Thread(target=self.probeFftDataThread)
        fftThread.daemon = True
        fftThread.start()


    # def set_postSuppressionRMS(self, currentReading):
    #     self.current

    def get_samp_rate(self):
        return self.samp_rate

    def set_samp_rate(self, samp_rate):
        self.samp_rate = samp_rate
        # BH - Don't let the throttle block throttle data from ZMQ - it messes up the buffering capabilities. This effectively uses the zmq producer's clock. that's ok!
        self.blocks_throttle_0_0.set_sample_rate(self.samp_rate*10+8000)
        self.blocks_throttle_0.set_sample_rate(self.samp_rate*10+8000)

    def get_fundamental_wavelength_samples(self):
        return self.fundamental_wavelength_samples

    def set_fundamental_wavelength_samples(self, fundamental_wavelength_samples):
        self.fundamental_wavelength_samples = fundamental_wavelength_samples

    def get_func_probe_b(self):
        return self.freq_wavelength

    def set_average_frequency_reading(self, func_probe_b):
        self.freq_wavelength = func_probe_b
        self.blocks_delay_1.set_dly(int(round(self.freq_wavelength)))
        self.blocks_delay_0.set_dly(int(round(self.freq_wavelength)))

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
    global THREADS_ENABLED

    log("Note! This application shares the config.yml file with acpq.py. Streamer cofiguration is located in the streamer section of the config.")
    parseArgs()
    SETTINGS = readSettings(ARGS.config)

    tb = top_block_cls()
    tb.start()
    time.sleep(2)
    tb.startThreads()
    
    tb.wait()
    log("Disabling threads...")
    THREADS_ENABLED=False
    log("Stopping flowgraph...")
    tb.stop()
    log("Waiting for flowgraph to stop")
    tb.wait()
    log("All main() function is complete. no code left to execute. Only threads may be running after this line")



if __name__ == '__main__':
    main()
