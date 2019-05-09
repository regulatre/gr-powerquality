#!/usr/bin/env python

#
# Useful Queue database commands
#   CREATE VIEW view_lengthchecker AS select *,LENGTH(data) 'ld' from ack_queue_default WHERE ld < 10;
#   DELETE FROM ack_queue_default WHERE _id IN (SELECT _id FROM view_lengthchecker);

import argparse

# for config.yml
import yaml
import requests
from requests.auth import HTTPBasicAuth
# For exit codes
import sys
# For renaming queue directory
import os
import signal


from datetime import datetime


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
from gnuradio import zeromq

from elasticsearch import Elasticsearch

# import persistqueue
# from persistqueue import FIFOSQLiteQueue

elasticSearch = {}
import json
import time
import socket
import certifi
import psutil

import threading
import time

# Custom Blocks
import powerquality


from LightMQ import LightMQ
from SimpleDataLog import SimpleDataLog

import pmt
import json

import requests



SETTINGS = {}
ARGS = {}
# To be set to getEpochMillis() soon enough.
startTimeSeconds = 0

biasStats = {"biasresetcounter": 0, "running_avg": -1, "running_min": -1, "running_max": -1}


parser = argparse.ArgumentParser(prog='acpq',description="AC Power Quality Monitoring Script")
parser.add_argument('-c', '--config', help='Configuration File Path & Filename',required=False, default="./config.yml")
parser.add_argument('-p', '--port', help='Raw Samples Service - Tap Port',required=False, default="5555")
parser.add_argument('-D', '--debug', help='Enable debug messages to stdout',required=False)


def terminateApplication(message):
    print ("TERMINATING APPLICATION. Message=" + message)
    try:
        print ("(TODO)Writing queue to disk...")
        messageQueue.saveToDisk()
        print ("(TODO)DONE writing queue to disk...")
    except Exception as ex:
        pass

    os.kill(os.getpid(), signal.SIGTERM)


def parseArgs():
    global ARGS

    # Parse commandline args. Prints help/usage and terminate application if anything goes wrong
    ARGS = parser.parse_args()
    print "Parsed commandline args. They are: " + str(ARGS)
    # Sanity Checks
    # If something doesn't check out, run argsFailed()

def debug_enabled():
    global ARGS
    if ARGS.debug:
        return True
    else:
        return False


# Come here if parsing of commandline args failed, or if they are in some way invalid.
def argsFailed():
    parser.print_help()
    terminateApplication("args failed")


# Returns a 2-digit month number
def getMonthString():
    dateMonthNumberString = "" + str(datetime.today().month)
    dateMonthNumberString = dateMonthNumberString.zfill(2)
    return dateMonthNumberString


def getYearString():
    dateYearNumberString = "" + str(datetime.today().year)
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

def getEpochSeconds():
  return long(time.time())

def getEpochMillis():
    # time.time() returns a float, expressed in terms of seconds, but multiplying by 1000 gives us a pretty accurate milliseconds.
    return int(round(time.time() * 1000))

def getUniqueLogID():
  return str(getEpochMillis())

def getProcessRss():
    process_memory_info = psutil.Process().memory_full_info()
    rss = process_memory_info.rss
    return rss


# Returns number of seconds since application started up.
def getUptimeSeconds():
    global startTimeSeconds
    if (startTimeSeconds == 0):
        print "WARNING: initializing startTimeSeconds for the first time."
        startTimeSeconds = getEpochMillis() / 1000
    return (getEpochMillis()/1000) - startTimeSeconds

def getUptimeMinutes():
    uptimeSeconds = getUptimeSeconds()
    uptimeMinutes = uptimeSeconds / 60
    return uptimeMinutes



def getProbeType():
    return SETTINGS["probe"]["probe_model"]

def getLogTemplate():
    return {
        "logger": {
            "name": SETTINGS["logging"]["logger_name"],
            "hostname": getHostName(),
            "model": SETTINGS["logging"]["logger_model"],
            "location": SETTINGS["logging"]["logger_location"]
        },

        "probe": {
            "name": SETTINGS["probe"]["probe_name"],
            "model": SETTINGS["probe"]["probe_model"],
            "location": SETTINGS["probe"]["probe_location"],
        },

    }


# Convenience function for checking on a particular setting.
#def setting_acfreq_enabled():
#    if "disable_acfreq_calculation" in SETTINGS["probe"] and SETTINGS["probe"]["disable_acfreq_calculation"] is True:
#        return False
#    return True

# Fields currently availble in each message from getfreq:
# thisWaveLenSamples
# lastWaveLenSamples
# wavelenSamplesAvg
# positiveWaveSampleLength
# negativeWaveSampleLength
# fullWaveRMS
# halfwaveRMSNegative
# halfwaveRMSPositive
# peakPositive
# peakNegative
# peakToPeak
# Instantiate a block right here in the code in order to have a place to receive messages.
class message_consumer(gr.sync_block):
    def __init__(self):
        gr.sync_block.__init__(
            self,
            name="message consumer",
            in_sig=None,
            out_sig=None
        )
        self.msg_list = []
        self.message_port_register_in(pmt.intern('in_port'))
        self.set_msg_handler(pmt.intern('in_port'),
                             self.handle_msg)
        self.messageQueue = LightMQ({"persistencepath": "./pq-acpq", "maxqueuelength": 999999})
        self.messageCount = 0


    def handle_msg(self, msg):
        self.messageCount = self.messageCount + 1
        # Create a new PMT from long value and put in list
        # print ("INBOUND MESSAGE!!!!!")
        # theVal = str(pmt.from_long(pmt.to_long(msg)))
        # FAILS theVal = pmt.from_symbol(pmt.to_symbol(msg))
        theJsonString = pmt.symbol_to_string(msg)
        # print ("Message Content = " + theVal)

        if ARGS.debug and self.messageCount % 120 == 0:
            print ("SAMPLED PMT from GETFREQ (1/120): " + theJsonString)

        try:
            theJsonObject = json.loads(theJsonString)
            # print ("PYTHON RECEIVED GOOD JSON FROM BLOCK: " + json.dumps(theJsonObject))
            theJsonObject['time_generated'] = getEpochMillis()
            # theJsonObject['pq_timestamp'] = getEpochMillis()
            self.messageQueue.put(theJsonObject)
        except Exception as e:
            print("Message from getfreqcpp was NOT JSON: " + theJsonString)
            print (e)

    def getObjectQueue(self):
        return self.messageQueue



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

        # for averaging block stuff
        self.last_sampled_wavelength = 1

        # Input source parameters.
        self.audioSource = SETTINGS["input"]["input_type"]

        # Frequency calculation parameters
        self.freq_getfreq_alpha = float(SETTINGS["calibration"]["freq_getfreq_alpha"])
        self.freq_interpolation = float(SETTINGS["calibration"]["freq_interpolation"])
        self.freq_interpolation_multiplier = float(SETTINGS["calibration"]["freq_interpolation_multiplier"])


        self.current_readings = self.getDefaultReadings()



        # AC Volts
        self.blocks_throttle_0 = blocks.throttle(gr.sizeof_float * 1, samp_rate, True)
        # self.blocks_rms_volts = blocks.rms_ff(self.voltage_calculation_rms_alpha)
        # self.blocks_moving_average_volts = blocks.moving_average_ff(self.voltage_rms_average_length, self.voltage_rms_average_scale, self.voltage_rms_max_iter)
        # self.probe_rms_volts = blocks.probe_signal_f()


        # AC Frequency
        # if (setting_acfreq_enabled() is True):
        self.probe_avgwave = blocks.probe_signal_f()
        self.upsampler = filter.fractional_resampler_ff(0, self.freq_interpolation)
        self.getfreq_block = powerquality.getfreqcpp(self.freq_getfreq_alpha)

        # Streaming support - Permit access to the raw samples to ZeroMQ clients.
        self.zeromq_pub_sink_0 = zeromq.pub_sink(gr.sizeof_float, 1, SETTINGS["tap_rawsamples"]["zmq_bind_uri"], SETTINGS["tap_rawsamples"]["zmq_timeout"], True, -1)

        # TODO: Connect the streaming blocks

        # self.blocks_multiply_const_vxx_0 = blocks.multiply_const_vff((-1, ))
        # self.blocks_delay_0 = blocks.delay(gr.sizeof_float*1, self.fundamental_wavelength_samples)
        # self.blocks_add_xx_0 = blocks.add_vff(1)

        # Bias detection - these parameters are tuned to 48khz samp rate: (1 * samp_rate / 60, .00125, 4000)
        if ("bias" in SETTINGS and "bias_avg_num_waves" in SETTINGS["bias"]):
            bias_avg_num_waves = SETTINGS["bias"]["bias_avg_num_waves"]
        else:
            bias_avg_num_waves = 1
        # Calculate the number of samples associated with n wavelengths specified in settings or the default.
        avgBiasNumSamples = bias_avg_num_waves * samp_rate / 60
        self.blocks_bias_moving_average = blocks.moving_average_ff(avgBiasNumSamples, 1.0/avgBiasNumSamples, 4000)
        self.probe_bias = blocks.probe_signal_f()


        ### Calibrate the blocks based on settings from config file
        # self.set_rms_alpha(asdfasdfasdfasdf from settings)

        # Instantiate the message consumer that we'll use to get json messages from the getfreq block
        self.msgConsumer = message_consumer()

        ##################################################
        # RMS Volts Connections
        ##################################################

        # self.connect((self.blocks_rms_volts, 0), (self.blocks_moving_average_volts, 0))
        # self.connect((self.blocks_moving_average_volts, 0), (self.probe_rms_volts, 0))

        # Set up a variable with a default value. Below we'll override the value depending on whether we are reading from file or audio device.
        self.sourceOfSamplesBlock = self.blocks_throttle_0

        # Select input source - wav file or sound card.
        if (self.audioSource == "wav"):
            # Variable source type: wav file
            # self.wavfile_input = blocks.wavfile_source('./samples/sample.wav', False)
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
        # self.connect((self.sourceOfSamplesBlock , 0), (self.blocks_rms_volts, 0))
        # Hz flow
        print "CONNECTIONS: Defining the frequency calculation flow"
        self.connect((self.sourceOfSamplesBlock , 0), (self.upsampler, 0))
        self.connect((self.upsampler, 0), (self.getfreq_block, 0))
        self.connect((self.getfreq_block, 0), (self.probe_avgwave, 0))

        # Raw Tap port Tap flow
        print "CONNECTIONS: Connecting raw samples tap (ZMQ)"
        self.connect((self.sourceOfSamplesBlock , 0), (self.zeromq_pub_sink_0, 0))

        # Bias Detection flow
        self.connect((self.sourceOfSamplesBlock, 0), (self.blocks_bias_moving_average, 0))
        self.connect((self.blocks_bias_moving_average, 0), (self.probe_bias, 0))

        # Connect our message consumer block to the message output of the getfreq block so we can get messages from it.
        self.msg_connect((self.getfreq_block, 'out'), (self.msgConsumer, 'in_port'))


    def startThreads(self):
        print ("STARTING THREADS!")
        # Gather probe readings periodically.
        proball_thread = threading.Thread(target=self.probe_all_thread)
        proball_thread.daemon = True
        proball_thread.start()

        # Calculate bias readings using this thread. Keep it separate from the others because the 1/10s interval shouldn't be touched, whereas the other thread interval can be set by config file.
        probe_bias_thread = threading.Thread(target=self.biasCalculationThread)
        probe_bias_thread.daemon = True
        probe_bias_thread.start()

        debug_print_thread = threading.Thread(target=self.periodic_logging_thread)
        debug_print_thread.daemon = True
        debug_print_thread.start()

        # This thread simply pulls items off of the message queue and sends them to QLk
        dequeue_elk_messages_thread = threading.Thread(target=self.thread_dequeueElkMessages)
        dequeue_elk_messages_thread.daemon = True
        dequeue_elk_messages_thread.start()

        # termianteIfCircuitbreakerBroken()
        health_thread = threading.Thread(target=thread_healthchecks)
        health_thread.daemon = True
        health_thread.start()



        # This function should be called with the probed average sample value each time it is probed (10 times a second by default).
    # The results of the running average are saved in the current_readings variable, which gets sent to Elasticsearch periodically.
    def setCurrentBiasLevel(self,currentBiasLevel):
        global biasStats

        biasStats["biasresetcounter"] = biasStats["biasresetcounter"] + 1
        # The modulo here should remain equal to the time interval such that we reset bias stats every 1 second.
        biasStats["biasresetcounter"] = biasStats["biasresetcounter"] % 10

        # If the modulo rolled over then it's time to reset stats, but first, make move the calculated values into variables where they can be picked up.
        if (biasStats["biasresetcounter"] == 0):
            # Effectively turns reported readings into micro instead of raw. Better for Elasticsearch becuase Kibana hates small decimals.
            scaling_factor = 1000000

            # Save the tallied up values before resetting them
            self.current_readings["bias_min"] = round(biasStats["running_min"] * scaling_factor)
            self.current_readings["bias_max"] = round(biasStats["running_max"] * scaling_factor)
            self.current_readings["bias_avg"] = round(biasStats["running_avg"] * scaling_factor)
            # biasStats["avg"] = biasStats["running_avg"]
            # biasStats["min"] = biasStats["running_min"]
            # biasStats["max"] = biasStats["running_max"]

            # Reset running counters for new use.
            biasStats["running_avg"] = currentBiasLevel
            biasStats["running_min"] = currentBiasLevel
            biasStats["running_max"] = currentBiasLevel

        # Calculate min
        if (currentBiasLevel < biasStats["running_min"]):
            biasStats["running_min"] = currentBiasLevel

        # Calculate max
        if (currentBiasLevel > biasStats["running_min"]):
            biasStats["running_ax"] = currentBiasLevel

        # Calculate average
        # (Crude calcualtion method, subject to floating point rounding error becuase only two samples are averaged but it's good enough.)
        biasStats["running_avg"] = (biasStats["running_avg"] + currentBiasLevel) / 2



    def biasCalculationThread(self):
        # number of seconds to pause between each reading.
        time_period = 10

        while True:
            try:
                # Sleep first, so even if following code triggers an exception the sleep still happens, preventing a tight loop.
                time.sleep(1.0 / time_period)
                val = self.probe_bias.level()
                self.setCurrentBiasLevel(val)
            except AttributeError:
                continue


    def getDefaultReadings(self):

        ret = {
            # "timespanmillis": -1,
            "frequency": -1,
            "frequencymin": 60,
            "frequencymax": 60,
            "frequencychangecount":0,
            "bias_min": -1,
            "bias_max": -1,
            "bias_avg": -1
        }

        if (getProbeType() == "RMSVOLTS"):
            ret["rmsvolts"] = -1
            ret["rmsvoltsmin"] = 999
            ret["rmsvoltsmax"] = -1
            # ret["numvoltagespikes"] = -1
            # ret["numvoltagesags"] = -1

        if (getProbeType() == "RMSCURRENT"):
            ret["rmscurrent"]   = -1
            ret["rmscurrentmin"]= -1
            ret["rmscurrentmax"] =-1



        return ret


    def thread_dequeueElkMessages(self):
        while True:
            self.sendQueuedReadingsToELK()
            # TODO: move this to config file
            time.sleep(5.0)


    # TODO: Queueing. Keep it simple - create an object, key=getUniqueLogID, value=dumps (same as body).
    def queueOneReading(self):
        fullMessage = getLogTemplate()
        # Putting timestamp in the payload DOES NOT work as you would expect. nor does setting timestamp= on the index/create function. All are ignored :(
        fullMessage["pq_timestamp"] = getEpochMillis()
        # Adding our own timestamp field for comparison with @timestamp to track when it blows away @timestamp, namely when we're unqueueing saved readings after an outage.
        fullMessage["timestamp"] = getEpochMillis()
        fullMessage["processrss"] = getProcessRss()
        fullMessage["uptimemins"] = getUptimeMinutes()
        fullMessage["reading"] = self.current_readings


        # Sanity check: Don't send results until after a brief warm-up period. averages, flow graph stuff, needs to settle in.
        # sensible default, with option to override it in config file.
        warmup_seconds = 20
        if ("warmup_seconds" in SETTINGS["logging"]):
            warmup_seconds = SETTINGS["logging"]["warmup_seconds"]

        if (getUptimeSeconds() < warmup_seconds):
            remainingSeconds = warmup_seconds - getUptimeSeconds()
            print "WARMUP period not yet elapsed. Skipping one transmit interval to Elasticsearch. remaining seconds = " + str(remainingSeconds)
            return

        if (ARGS.debug):
            print "Queueing one reading: " + json.dumps(fullMessage)

        messageQueue.put(fullMessage)
        datalog.writeJsonLog(fullMessage)



    # "Run the queue" - send items to ELK.
    def sendQueuedReadingsToELK(self):


        if "logstashurl" in SETTINGS["logging"]:
            logstashurl = SETTINGS["logging"]["logstashurl"]
        else:
            logstashurl = ""

        if ("elk_enabled" in SETTINGS["logging"]):
            elk_enabled = SETTINGS["logging"]["elk_enabled"]
        else:
            print("WARNING: Config file is missing parameter logging.elk_enabled (boolean). Defaulting to True")
            elk_enabled = True


        if ("max_sends_per_cycle" in SETTINGS["logging"]):
            max_send_per_run = int(SETTINGS["logging"]["max_sends_per_cycle"])
        else:
            print ("WARNING: Config file is missing parameter logging.max_sends_per_cycle. Defaulting to 10.")
            max_send_per_run = 10

        indexName = "power_quality-" + getYearString() + "." + getMonthString()


        if (ARGS.debug):
            print ("Processing a batch of queued items. Queue size is " +str(messageQueue.qsize()) + " batch size is " + str(max_send_per_run))

        # Create an HTTP session, which we'll open, make multiple requests/posts, then close it.
        httpRequestSession = requests.Session()
        for i in range (max_send_per_run):

            # Nothing to do.
            if messageQueue.qsize() < 1:
                return

            # read the next item in the queue. It won't be removed from queue until we ACK it after processing.
            current_item = messageQueue.peek()

            if (ARGS.debug):
                print ("Queue size: " + str(messageQueue.qsize()))


            # if (ARGS.debug):
            #     print ("DEBUG: Pulled currentItem off the top of the list and it is this: " + json.dumps(current_item))
            if (elk_enabled != True):
                # Elk not enalbed.
                # print ("elk_enabled=False so not sending this to ELK: " + json.dumps(current_item))
                messageQueue.pop()
                # print ("Queue size after consumption: " + str(messageQueue.qsize()))
                continue

            # Try sending it
            try:
                # Default: elk=enabled, but can be set to False in the config file to disable sending of data to elk.

                # Calculate how long the message was waiting in the queue.
                epochtimenow = getEpochMillis()
                queue_time_ms = epochtimenow - current_item["pq_timestamp"]
                # Add the queue time metric to the payload of the message being indexed.
                current_item["queue_time_ms"] = queue_time_ms
                # Tried setting id= parameter to None to switch underlying middleware to POST not PUT but timestamp STILl ignored.
                # current_item["id"] = getUniqueLogID()

                # Print an informative message if item was queued longer than 10 seconds.
                if queue_time_ms > 10000:
                    print ("Dequeueing item that has been queued for " + str(queue_time_ms) + " ms. Queue size is now " + str(messageQueue.qsize()))
                #     print ("Message was queued. Queue Time calculation: " + str(epochtimenow) + "-" + str(
                #         current_item["pq_timestamp"]) + "=" + str(queue_time_ms))


                if len(logstashurl) > 0:
                    if ARGS.debug: 
                        print ("logstash url present, dequeueing to logstash")

                    # Post it to the Elasticsearch HTTP receiver.
                    # TODO: keep the connection open and stream multiple readings to the same HTTP connection.
                    httpresp = httpRequestSession.post(logstashurl, json=current_item, timeout=5)


                    # Only pop it off the queue if the post was successful. (HTTP 200, "ok" in the body).
                    if httpresp.status_code == 200:
                        messageQueue.pop()
                        if ARGS.debug:
                            print ("SUCCESS - POSTED one reading to logstashurl")
                    else:
                        if ARGS.debug:
                            print ("WARNING: ERROR posting one reading to logstashurl. status code=" + str(httpresp.status_code) + " body=" + httpresp.text)

                    continue


                elastic_response = elasticSearch.index(index=indexName, doc_type='post',
                                                       id=("" + str(current_item["pq_timestamp"])),
                                                       body=json.dumps(current_item))
                if (ARGS.debug):
                    print ("DEBUG: ELK responded... response attributes:"
                           + " queue_time_ms=" + str(queue_time_ms)
                           + " created=" + str(elastic_response["created"])
                           + " result=" + str(elastic_response["result"])
                           + " response_object=" + str(elastic_response))

                # Was the index request successful?
                if (elastic_response["result"] == "updated" or elastic_response["result"] == "created"):
                    messageQueue.pop()
                    # self.elk_send_queue.pop(0)
                else:
                    print ("Unexpected response from server. not dequeueing item. Elastic said: " + json.dumps(elastic_response))
                    print ("After NOT consuming that failed item, the queue size stands at " + str(messageQueue.qsize()))

            except Exception as ex:
                # print("Error sending data to index. Unable to send queued readings at this time. elkError=", sys.exc_info()[0])
                print("Error sending data to index. Unable to send queued readings at this time. elkError=" + str(ex) + " Queue size is " + str(messageQueue.qsize()))
                # send was NOT successful. Bail out of this function to give things (networking stack mostly) a moment to settle down and reconnect.
                return


    def get_samp_rate(self):
        return self.samp_rate

    def set_samp_rate(self, samp_rate):
        self.samp_rate = samp_rate
        self.blocks_throttle_0.set_sample_rate(self.samp_rate)

    # def set_rms_alpha(self, newAlpha):
    #     print "Setting rms_volts alpha to " + str(newAlpha)
    #     self.rms_alpha = newAlpha
    #     # self.blocks_rms_volts.set_alpha(self.rms_alpha)

    def get_probed_rms_volts(self):
        return self.probed_rms_volts

    # Apply the conversion factors specified in the config file to convert voltage sample values into actual voltage reading
    def convertSampleToReading(self, sampleReading):
        convertedReading = sampleReading * self.average_rms_slope + self.average_rms_intercept
        convertedReading = round(convertedReading,3)
        return convertedReading

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

    # Run this function to update the parameters of the averaging block to match the current frequency wavelength. We take the average of N samples, where N is the calculated wavelength of the signal.
    def set_new_volts_rms_average_parameters(self, newWavelen):
        # TODO: update the averaging block, set new scale and length based on the newly provided frequency newFreq.
        newLength = int(round(newWavelen))
        newScale = 1.0 / newLength
        if debug_enabled():
            pass
            # print("set_new_volts_rms_average_parameters(): wavelen=" + str(newWavelen) + " avglen=" + str(newLength) + " scale=" + str(newScale))

        # self.blocks_moving_average_volts.set_length_and_scale(newLength, newScale)

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

        if "read_period" in SETTINGS["logging"]:
            read_period = SETTINGS["logging"]["read_period"]
        else:
            read_period = 1
            print("WARNING: MISSING config parameter logging.read_period - periodic logging thread is defaulting to " + str(read_period))

        print ("periodic_logging_thread Starting up. We will pause " + str(read_period) + " seconds between readings.")

        while True:
            # print str(self.current_readings)
            self.queueOneReading()
            self.reset_accumulators()
            # run the queue - at least one item (the current one) will be queued. If connection problems then more will be queued.
            # TODO: The following sleep should look at config file parameter for sleep duration.
            time.sleep(read_period)

    def probe_all_thread(self):
        while True:
            self.consumeBlockReadings()
            # if setting_acfreq_enabled() is True:
            #     self.probe_frequency()
            # self.probe_rms_volts_reading()
            time.sleep(1.0 / (self.probe_interval))

    # Called by a task thread. reads queued readings received from the getfreq block which also does so much more.
    def consumeBlockReadings(self):
        while self.msgConsumer.getObjectQueue().qsize() > 0:
            thisQueuedMessageObject = self.msgConsumer.getObjectQueue().peek()

            # TODO: do min/max/avg Volts calculations BETTER using min/max data from the block.
            # TODO: make use of the wealth of fields now available from getfreq for detecting power anomalies. see the message block class at the top for field list.

            # TODO: Reintroduce usage of this variable float(SETTINGS["calibration"]["voltage_calculation_rms_alpha"]) 

            # set frequency
            myFreq = (self.samp_rate * self.freq_interpolation_multiplier) / float(thisQueuedMessageObject["wavelenSamplesAvg"])
            self.set_current_frequency(myFreq)

            # set voltage
            thisReadingVolts = self.convertSampleToReading(float(thisQueuedMessageObject["fullWaveRMS"]))
            thisRawReading   = float(thisQueuedMessageObject["fullWaveRMS"])
            self.set_current_reading(thisReadingVolts,thisRawReading)

            # Consume this JSON message from the queue.
            self.msgConsumer.getObjectQueue().pop()

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
    if "logtarget" in SETTINGS["logging"]:
        esTarget = SETTINGS["logging"]["logtarget"]
        print "Initializing Elasticsearch. Endpoint=" + esTarget
        elasticSearch = Elasticsearch(esTarget,ca_certs=certifi.where())
    else:
        elasticSearch = 0


def getQueueNamePath():
    global SETTINGS
    defaultQueuePath = "./pq-mq"

    if "message_queue" in SETTINGS and "queuename" in SETTINGS["message_queue"]:
        return SETTINGS["message_queue"]["queuename"]
    else:
        # Default value, should be overridden in config
        print("WARNING: missing setting name message_queue.queuename. Defaulting to " + str(defaultQueuePath) + " This is where the persistent queue will be stored.")
        return defaultQueuePath


def thread_healthchecks():
    while True:
        terminateIfCircuitbreakersBroken()
        time.sleep(5.0)

# given circuit breakers defined in the config file, terminate the app if any breakers are broken. This prevents a runaway process.
def terminateIfCircuitbreakersBroken():
    # Get RSS
    currentRssBytes = getProcessRss()
    # determine max RSS allowed
    if ("circuit_breakers" in SETTINGS and "rss_max_megabytes" in SETTINGS["circuit_breakers"]):
        maxRssBytes = SETTINGS["circuit_breakers"]["rss_max_megabytes"] * (1000*1000)
    else:
        print("WARNING: config file missing parameter circuit_breakers.rss_max_megabytes. Defaulting to 512MB")
        maxRssBytes = 128*(1000*1000)

    if (currentRssBytes > maxRssBytes):
        # terminate app if RSS above threshold
        terminateApplication("ERROR: TERMINATING application due to RSS circuit breaker - currentRss=" + str(currentRssBytes) + " threshold=" + str(maxRssBytes))
    else:
        if ARGS.debug:
            print("DEBUG: RSS OK: " + str(currentRssBytes) + " < " + str(maxRssBytes))


# After having read the config file, use this function to fill in any critical missing variables with sensible defaults.
def setSensibleDefaults(settingsObject):
    if ("datalog" not in settingsObject):
        print("WARNING: config file missing datalog section")
        settingsObject["datalog"] = {}

    if "filename" not in settingsObject["datalog"]:
        print("WARNING: config file missing datalog filename")
        settingsObject["datalog"]["filename"] = "/tmp/pq-datalog.txt"

    if "oldfilename" not in settingsObject["datalog"]:
        print("WARNING: config file missing datalog oldfilename")
        settingsObject["datalog"]["oldfilename"] = "/tmp/pq-datalog-old.txt"

    if "maxmegabytes" not in settingsObject["datalog"]:
        print("WARNING: config file missing datalog maxmegabytes")
        settingsObject["datalog"]["maxmegabytes"] = 50

    return settingsObject

def main(top_block_cls=testVolts, options=None):
    global SETTINGS
    global messageQueue
    global datalog

    # Parse commandline arguments
    print "Note! This application shares the config.yml file with the streamer."
    parseArgs()

    # Parse the config file
    SETTINGS = readSettings(ARGS.config)
    setSensibleDefaults(SETTINGS)

    queuePath = getQueueNamePath()
    messageQueue = LightMQ({"persistencepath": queuePath, "maxqueuelength": 999999})

    # Instantiate the data logger. This logs json objects to a text file for data science ingestion
    datalog = SimpleDataLog({"filename":     SETTINGS["datalog"]["filename"],
                             "oldfilename":  SETTINGS["datalog"]["oldfilename"],
                             "maxmegabytes": SETTINGS["datalog"]["maxmegabytes"]})

    # Perform initial configuration tasks now that config data is available, before main processing starts up.
    preStartTasks()

    # Perform cleanups associated with queue database in case it failed.
    # cleanQueueDatabase(queuePath)

    tb = top_block_cls()
    tb.start()
    # Pause a moment while flowgraph starts up before starting threads
    time.sleep(2)
    tb.startThreads()
    tb.wait()


if __name__ == '__main__':
    main()
