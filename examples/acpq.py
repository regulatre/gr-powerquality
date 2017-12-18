#!/usr/bin/env python


import argparse

# for config.yml
import yaml
# for placing HTTPs requests to EM7 and Scoreboard.
import requests
from requests.auth import HTTPBasicAuth
# For exit codes
import sys

import datetime

from gnuradio import audio
from gnuradio import filter
from gnuradio import blocks
from gnuradio import eng_notation
from gnuradio import gr
from gnuradio.eng_option import eng_option
from gnuradio.filter import firdes
from optparse import OptionParser

from gnuradio import analog
from gnuradio import blocks
from gnuradio import eng_notation
from gnuradio import gr
from gnuradio.eng_option import eng_option
from gnuradio.filter import firdes
from optparse import OptionParser

from elasticsearch import Elasticsearch

elasticSearch = {}
import json
import time
import socket
import certifi

import threading
import time

# Custom Blocks
import powerquality

SETTINGS = {}
ARGS = {}
# To be set to getEpochMillis() soon enough.
startTimeSeconds = 0


parser = argparse.ArgumentParser(prog='acpq',description="AC Power Quality Monitoring Script")
parser.add_argument('-c', '--config', help='Configuration File Path & Filename',required=False, default="./config.yml")
parser.add_argument('-p', '--port', help='Raw Samples Service - Tap Port',required=False, default="5555")
parser.add_argument('-D', '--debug', help='Enable debug messages to stdout',required=False)


def parseArgs():
    global ARGS

    # Parse commandline args. Prints help/usage and terminate application if anything goes wrong
    ARGS = parser.parse_args()
    print "Parsed commandline args. They are: " + str(ARGS)
    # Sanity Checks
    # If something doesn't check out, run argsFailed()


# Come here if parsing of commandline args failed, or if they are in some way invalid.
def argsFailed():
    parser.print_help()
    sys.exit()

# Returns a 2-digit month number
def getMonthString():
    dateMonthNumberString = "" + str(datetime.datetime.today().month)
    dateMonthNumberString = dateMonthNumberString.zfill(2)
    return dateMonthNumberString

def getYearString():
    dateYearNumberString = "" + str(datetime.datetime.today().year)
    return dateYearNumberString


def readSettings(configFileName):
    print "Loading settings from " + configFileName
    # Read settings from configuration file
    with open(configFileName, "r") as myfile:
        fileContents = myfile.read()
    print "Settings loaded."
    return yaml.load(fileContents)


def getHostName():
    return socket.gethostname()

def getEpochMillis():
    return long(time.time()*1000)

# Returns number of seconds since application started up.
def getRuntimeSeconds():
    global startTimeSeconds
    if (startTimeSeconds == 0):
        print "WARNING: initializing startTimeSeconds for the first time."
        startTimeSeconds = getEpochMillis() / 1000
    return (getEpochMillis()/1000) - startTimeSeconds

def getUniqueLogID():
    return "" + str(getEpochMillis())

def getProbeType():
    return SETTINGS["probe"]["probe_model"]

class testVolts(gr.top_block):
    def __init__(self):
        gr.top_block.__init__(self, "Testvolts")

        ##################################################
        # Variables - Some get overridden after block definition before connections.
        ##################################################
        self.samp_rate = samp_rate = 48000
        # Initial wavelength assumption, which must be calibrated carefully.
        self.fundamental_wavelength_samples = 800
        # self.probed_rms_volts = probed_rms_volts = 0

        # Things from config file
        # self.avg_length = avg_length = 10000
        self.probe_interval = probe_interval = float(SETTINGS["display"]["probe_interval"])
        self.rms_alpha = rms_alpha = 1

        # Calibration (Conversion) parameters, to convert from sample domain to volts/current domain.
        self.average_rms_slope =     float(SETTINGS["calibration"]["average_rms_slope"])
        self.average_rms_intercept = float(SETTINGS["calibration"]["average_rms_intercept"])

        # RMS Block parameters
        self.voltage_calculation_rms_alpha = float(SETTINGS["calibration"]["voltage_calculation_rms_alpha"])

        # Averaging block parameters
        self.voltage_rms_average_length =  int(SETTINGS["calibration"]["voltage_rms_average_length"])
        self.voltage_rms_average_scale =  float(SETTINGS["calibration"]["voltage_rms_average_scale"])
        self.voltage_rms_max_iter = int(SETTINGS["calibration"]["voltage_rms_max_iter"])

        # Input source parameters.
        self.audioSource = SETTINGS["input"]["input_type"]

        # Frequency calculation parameters
        self.freq_getfreq_alpha = float(SETTINGS["calibration"]["freq_getfreq_alpha"])
        self.freq_interpolation = float(SETTINGS["calibration"]["freq_interpolation"])
        self.freq_interpolation_multiplier = float(SETTINGS["calibration"]["freq_interpolation_multiplier"])

        # ELK send queue. Normally empty but if things are failing, data will queue until it can be sent.
        self.elk_send_queue = []

        self.logTemplate = {
            "logger": {
                "name":     SETTINGS["logging"]["logger_name"],
                "hostname": getHostName(),
                "model":     SETTINGS["logging"]["logger_model"],
                "location": SETTINGS["logging"]["logger_location"]
            },

            "probe": {
                "name":     SETTINGS["probe"]["probe_name"],
                "model":     SETTINGS["probe"]["probe_model"],
                "location": SETTINGS["probe"]["probe_location"],
            },

        }

        self.current_readings = self.getDefaultReadings()


        ##################################################
        # Define the blocks
        ##################################################
        self.probe_rms_volts = blocks.probe_signal_f()
        self.probe_avgwave = blocks.probe_signal_f()


        # Gather probe readings periodically.
        proball_thread = threading.Thread(target=self.probe_all_thread)
        proball_thread.daemon = True
        proball_thread.start()

        debug_print_thread = threading.Thread(target=self.periodic_logging_thread)
        debug_print_thread.daemon = True
        debug_print_thread.start()


        # Sound card and wav file variables will be instantiated shortly, during block connection.


        # AC Volts
        self.blocks_throttle_0 = blocks.throttle(gr.sizeof_float * 1, samp_rate, True)
        self.blocks_rms_volts = blocks.rms_ff(self.voltage_calculation_rms_alpha)
        self.blocks_moving_average_volts = blocks.moving_average_ff(self.voltage_rms_average_length, self.voltage_rms_average_scale, self.voltage_rms_max_iter)

        # AC Frequency
        self.upsampler = filter.fractional_resampler_ff(0, self.freq_interpolation)
        self.wavfile_input = blocks.wavfile_source('./samples/sample.wav', False)
        self.getfreq_block = powerquality.getfreqcpp(self.freq_getfreq_alpha)

        # Streaming support
        print "Initializing streaming server blocks."
        self.blocks_tcp_server_sink_0 = blocks.tcp_server_sink(gr.sizeof_float*1, '0.0.0.0', int(ARGS.port), True)
        self.blocks_multiply_const_vxx_0 = blocks.multiply_const_vff((-1, ))
        self.blocks_delay_0 = blocks.delay(gr.sizeof_float*1, self.fundamental_wavelength_samples)
        self.blocks_add_xx_0 = blocks.add_vff(1)



        ### Calibrate the blocks based on settings from config file
        self.set_rms_alpha(float(SETTINGS["calibration"]["voltage_calculation_rms_alpha"]))

        ##################################################
        # RMS Volts Connections
        ##################################################

        self.connect((self.blocks_moving_average_volts, 0), (self.probe_rms_volts, 0))
        self.connect((self.blocks_rms_volts, 0), (self.blocks_moving_average_volts, 0))

        # Set up a variable with a default value. Below we'll override the value depending on whether we are reading from file or audio device.
        self.sourceOfSamplesBlock = self.blocks_throttle_0

        # Select input source - wav file or sound card.
        if (self.audioSource == "wav"):
            # Variable source type: wav file
            self.input_wav_filename = SETTINGS["input"]["input_wav_filename"]
            self.wavfile_input = blocks.wavfile_source(self.input_wav_filename, True)

            # wav input requires throttle block. Then we connect things to the throttle block directly instead of the wav source.
            self.connect((self.wavfile_input, 0), (self.blocks_throttle_0, 0))

            self.sourceOfSamplesBlock = self.blocks_throttle_0

        else:
            # Variable source type: sound device.
            self.soundcard_device_name = ""
            if (SETTINGS["input"]["input_sound_device"]):
                self.soundcard_device_name = SETTINGS["input"]["input_sound_device"]

            self.soundcard_input = audio.source(samp_rate, self.soundcard_device_name, True)

            # no throttle block needed in the case of sound card

            self.sourceOfSamplesBlock = self.soundcard_input



        # Volts flow
        print "CONNECTIONS: Defining the voltage calculation flow"
        self.connect((self.sourceOfSamplesBlock , 0), (self.blocks_rms_volts, 0))
        # Hz flow
        print "CONNECTIONS: Defining the frequency calculation flow"
        self.connect((self.sourceOfSamplesBlock , 0), (self.upsampler, 0))
        # TCP port Tap flow
        print "CONNECTIONS: Connecting TCP/IP port tap flow"
        self.connect((self.sourceOfSamplesBlock , 0), (self.blocks_tcp_server_sink_0, 0))


        # Streaming flow - add+accumulator -> tcp server.
        # TODO: This is processor intensive, so make it selectable from commandline option.
        # TODO: Actually, due to the lack of a TCP WAV streaming block, we should just stream baseband unaltered and let a separate process decode and also do data logging and things like that.
        if (1==0):
            print "CONNECTIONS: Creating a TCP server to enable access to the audio filter"
            self.connect((self.blocks_add_xx_0, 0), (self.blocks_tcp_server_sink_0, 0))
            print "CONNECTIONS: Setting up the audio filtering flow"
            self.connect((self.blocks_delay_0, 0), (self.blocks_multiply_const_vxx_0, 0))
            self.connect((self.blocks_multiply_const_vxx_0, 0), (self.blocks_add_xx_0, 1))
            self.connect((self.sourceOfSamplesBlock, 0), (self.blocks_add_xx_0, 0))
            self.connect((self.sourceOfSamplesBlock, 0), (self.blocks_delay_0, 0))
        # blocks_tcp_server_sink_0



        ##################################################
        # AC Frequency connections
        ##################################################
        self.connect((self.getfreq_block, 0), (self.probe_avgwave, 0))
        self.connect((self.upsampler, 0), (self.getfreq_block, 0))

    def getDefaultReadings(self):

        ret = {
            # "timespanmillis": -1,
            "frequency": -1,
            "frequencymin": 60,
            "frequencymax": 60,
            "frequencychangecount":0,
        }

        if (getProbeType() == "RMSVOLTS"):
            ret["rmsvolts"] = -1
            ret["rmsvoltsmin"] = 999
            ret["rmsvoltsmax"] = -1
            ret["numvoltagespikes"] = -1
            ret["numvoltagesags"] = -1

        if (getProbeType() == "RMSCURRENT"):
            ret["rmscurrent"]   = -1
            ret["rmscurrentmin"]= -1
            ret["rmscurrentmax"] =-1



        return ret



    # TODO: Queueing. Keep it simple - create an object, key=getUniqueLogID, value=dumps (same as body).
    def sendCurrentReadingsToELK(self):
        fullMessage = self.logTemplate
        fullMessage["@timestamp"] = getEpochMillis()
        fullMessage["reading"] = self.current_readings

        # TODO: IF we start calling this function many times per second then it would make sense to not calculate the index every time.
        # 'power_quality-2017.07'
        #          power_quality-    2017               .    07

        # # Sanity checks
        # if self.current_readings["frequency"] < 10:
        #     print "WARNING: sendCurrentReadingsToELK() is rejecting one message due to absurd frequency reading of " + str(self.current_readings["frequency"])
        #     return
        # update: lifted the above sanity chceck as the getfreqcpp block has improved significantly in reliability.


        # Sanity check: Don't send results until after a brief warm-up period. averages, flow graph stuff, needs to settle in.
        if (getRuntimeSeconds() < 20):
            remainingSeconds = 20 - getRuntimeSeconds()
            print "WARMUP period not yet elapsed. Skipping one transmit interval to Elasticsearch. remaining seconds = " + str(remainingSeconds)
            return

        if (ARGS.debug):
            print "Sending to ES: " + json.dumps(fullMessage)

        self.elk_send_queue.append(fullMessage)

        if (len(self.elk_send_queue) > 1) or (ARGS.debug):
            print ("Queued one reading. Queue now contains " + str(len(self.elk_send_queue)) + " items.")




    # "Run the queue" - send items to ELK.
    def sendQueuedReadingsToELK(self):

        if ("max_sends_per_cycle" in SETTINGS["logging"]):
            max_send_per_run = int(SETTINGS["logging"]["max_sends_per_cycle"])
        else:
            print ("WARNING: Config file is missing parameter logging.max_sends_per_cycle. Defaulting to 10.")
            max_send_per_run = 10

        indexName = "power_quality-" + getYearString() + "." + getMonthString()

        # Figure out how many items we'll be processing. no more than the allowed max.
        num_items_this_run = max_send_per_run
        if (len(self.elk_send_queue) < max_send_per_run):
            num_items_this_run = len(self.elk_send_queue)


        for i in range (num_items_this_run):
            # read the next item in the queue
            current_item = self.elk_send_queue[0]

            # Try sending it
            try:
                elasticSearch.index(index=indexName, doc_type='post', id=getUniqueLogID(), body=json.dumps(current_item ))
                # TODO Check within the response to look for some sign that it was definitely certainly for sure successful.
                # successful send? Woohoo! pop it off the left side of the list.
                self.elk_send_queue.pop()
                if (len(self.elk_send_queue) > 1):
                    print ("Successfully sent one queued reading, there are " + str(len(self.elk_send_queue)) + " more left in the queue!")
            except:
                print("Error sending data to index. Unable to send queued readings at this time. elkError=", sys.exc_info()[0])
                # send was NOT successful. Bail out of this function so when connection is restored we start at the beginning of the queue.
                return


    def get_samp_rate(self):
        return self.samp_rate

    def set_samp_rate(self, samp_rate):
        self.samp_rate = samp_rate
        self.blocks_throttle_0.set_sample_rate(self.samp_rate)

    def set_rms_alpha(self, newAlpha):
        print "Setting rms_volts alpha to " + str(newAlpha)
        self.rms_alpha = newAlpha
        self.blocks_rms_volts.set_alpha(self.rms_alpha)

    def get_probed_rms_volts(self):
        return self.probed_rms_volts

    # Apply the conversion factors specified in the config file to convert voltage sample values into actual voltage reading
    def convertSampleToReading(self, sampleReading):
        return sampleReading * self.average_rms_slope + self.average_rms_intercept

    def set_getAvgwaveLevel(self, getAvgwaveLevel):
        self.getAvgwaveLevel = getAvgwaveLevel


    def set_current_reading(self, reading, rawReading):
         # Keep track of min/max values observed. These get reset by reset_accumulators() each time after sending the readings to elasticsearch.

        if (getProbeType() == "RMSVOLTS"):

            if (reading < self.current_readings["rmsvoltsmin"]):
                self.current_readings["rmsvoltsmin"] = reading
            if (reading > self.current_readings["rmsvoltsmax"]):
                self.current_readings["rmsvoltsmax"] = reading

            # Set current actual reading values.
            self.current_readings["rmsvolts"] = reading
            self.current_readings["rmsvoltsprobereading"] = rawReading

        if (getProbeType() == "RMSCURRENT"):
            if (reading < self.current_readings["rmscurrentmin"]):
                self.current_readings["rmscurrentmin"] = reading
            if (reading > self.current_readings["rmscurrentmax"]):
                self.current_readings["rmscurrentmax"] = reading

            # Set current actual reading values.
            self.current_readings["rmscurrent"] = reading
            self.current_readings["rmscurrentprobereading"] = rawReading

    def set_current_frequency(self,hz):
        # Keep track of min/max values observed. These get reset by reset_accumulators() each time after sending the readings to elasticsearch.
        if (hz < self.current_readings["frequencymin"]):
            self.current_readings["frequencymin"] = hz
        if (hz > self.current_readings["frequencymax"]):
            self.current_readings["frequencymax"] = hz

        # Did the frequency change? TODO: better things with frequency changes.
        if (hz != self.current_readings["frequency"]):
            self.current_readings["frequencychangecount"] = int(self.current_readings["frequencychangecount"]) + 1

        # Set current actual reading values.
        self.current_readings["frequency"] = hz


    def periodic_logging_thread(self):
        while True:
            # print str(self.current_readings)
            self.sendCurrentReadingsToELK()
            self.reset_accumulators()
            # run the queue - at least one item (the current one) will be queued. If connection problems then more will be queued.
            self.sendQueuedReadingsToELK()
            # TODO: The following sleep should look at config file parameter for sleep duration.
            time.sleep(1)

    def probe_all_thread(self):
        while True:
            self.probe_frequency()
            self.probe_rms_reading()
            time.sleep(1.0 / (self.probe_interval))

    def probe_frequency(self):
        frequency = self.probe_avgwave.level()
        try:
            self.set_getAvgwaveLevel(frequency)
            if frequency > 0:
                myFreq = (self.samp_rate * self.freq_interpolation_multiplier) / frequency
                self.set_current_frequency(myFreq)
        except AttributeError:
            pass

    def probe_rms_reading(self):
        rmsreading = self.probe_rms_volts.level()
        self.set_current_reading(self.convertSampleToReading(rmsreading), rmsreading)

    # Run this each time the readings are sent to elasticsearch, to reset any accumulator variables.
    def reset_accumulators(self):
        self.current_readings["frequencychangecount"] = 0
        self.current_readings["frequencymax"] = self.current_readings["frequency"]
        self.current_readings["frequencymin"] = self.current_readings["frequency"]

        if (getProbeType() == "RMSVOLTS"):
            self.current_readings["rmsvoltsmin"] = self.current_readings["rmsvolts"]
            self.current_readings["rmsvoltsmax"] = self.current_readings["rmsvolts"]

        if (getProbeType() == "RMSCURRENT"):
            self.current_readings["rmscurrentmin"] = self.current_readings["rmscurrent"]
            self.current_readings["rmscurrentmax"] = self.current_readings["rmscurrent"]


# This gets called after config file and commandline args have been parsed. Do things like initializing variables.
def preStartTasks():
    global elasticSearch

    startTimeSeconds = getEpochMillis() / 1000

    # Initialize Elasticsearch Logging.
    esTarget = SETTINGS["logging"]["logtarget"]
    print "Initializing Elasticsearch. Endpoint=" + esTarget
    elasticSearch = Elasticsearch(esTarget)



def main(top_block_cls=testVolts, options=None):
    global SETTINGS

    # Parse commandline arguments
    parseArgs()

    # Parse the config file
    SETTINGS = readSettings(ARGS.config)

    # Perform initial configuration tasks now that config data is available, before main processing starts up.
    preStartTasks()

    tb = top_block_cls()
    tb.start()
    tb.wait()


if __name__ == '__main__':
    main()
