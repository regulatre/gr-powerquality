/* -*- c++ -*- */
/* 
 * Copyright 2017 <+YOU OR YOUR COMPANY+>.
 * 
 * This is free software; you can redistribute it and/or modify
 * it under the terms of the GNU General Public License as published by
 * the Free Software Foundation; either version 3, or (at your option)
 * any later version.
 * 
 * This software is distributed in the hope that it will be useful,
 * but WITHOUT ANY WARRANTY; without even the implied warranty of
 * MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
 * GNU General Public License for more details.
 * 
 * You should have received a copy of the GNU General Public License
 * along with this software; see the file COPYING.  If not, write to
 * the Free Software Foundation, Inc., 51 Franklin Street,
 * Boston, MA 02110-1301, USA.
 */

#ifdef HAVE_CONFIG_H
#include "config.h"
#endif

#include <gnuradio/io_signature.h>
#include "getfreqcpp_impl.h"

// ZeroMQ. Used for passing JSON messages from this block to the parent. Gnuradio message passing (specifically the string type) leaks memory.
// #include <zmq.hpp>

// brew install zmqpp / apt-get install libzmq3-dev /
// TODO: Implenent ZeroMQ instead of JSON! (String message passing is subject to memory leak) https://gist.github.com/kuenishi/1709739

// ** the following aren't needed thanks to gnuradio pulling them in for us.
// for math functions
//#include <cmath>
//#include <string>
//using namespace std;

#include <stdio.h>

namespace gr {
  namespace powerquality {

    int samplesSinceLastDownCross = 0;
    int positiveWaveSampleLength = 0;// positive half-wave wavelength, in samples,
    int negativeWaveSampleLength = 0;// negative half-wave wavelength, in samples,
    float avgSamplesPerZeroDown = 1;
    int lastSamplesSinceLastDownCross = 0;
    float lastSampleValue = 0;
    // For averaging - higher alpha means new samples have greater impact on the average.
    // TODO: create a setter for alpha
    float alpha = 0.5;

    // maximum number of samples to jump per calculated cycle. This new logic prevents pops and single errors from upsetting the average.
    // tuning of this variable is somewhat unclear. a value of 1 seems to correspond to jumps of about 0.001 - 0.007 Hz.
    float bigChangeThreshold = 1;
    float correctedChangeSizeForBigChanges = 1;

    float bigGapSize = 10;

    // how many cycles in a row need to be larger than the gap before its time to jump to that new number instead of slowly averaging our way to it.
    float maxBigGaps = 10;

    // number of cycles the gap between measured and current average differe by bigGapSize or more.
    // When this number gets high enough, we'll initiate a large jump by setting the average to the currently measured value.
    // This effectively shortcuts a long convergence.
    float consecutiveBigGaps = 0;

    //
    bool ENABLE_WAVE_METRICS = true;
    // samp_rate is defined elsewhere and available to us here.

    // characteristics of the current full wave
    float sumFullWaveSquares = 0;
    float sumHalfWaveSquaresPositive = 0;
    float sumHalfWaveSquaresNegative = 0;
    float sumHalfWaveSquares = 0; // will accumulate every half wave. Then it will be placed into either the positive or negative variable above.
    float waveSum = 0;
    float waveMin = 0;
    float waveMax = 0;
    float numFullWaveClips = 0;
    int processId = -1;

    // The message handling destination
    pmt::pmt_t polymorphicMessageDestination;



    std::string calculateWaveCrossingMetrics (float lastSample, float currentSample) {
        char retJsonString[512];
        // note the peak min, peak max,
        // calculate root of the square sums
        // reset the counters

        float rootOfSquares = sqrt(sumHalfWaveSquares);


        // Determine whether the crossing was positive or negative, and generate an appropriate response payload accordingly.
        if (lastSample > currentSample) {
            // Crossed downward, This is when we do most of the calculation work.

            // take the half-wave square sums and put them into the negative variable.
            sumHalfWaveSquaresPositive = sumHalfWaveSquares;
            sumHalfWaveSquares = 0;

            // the first half of the wave was already added when the wave sloped upward. Now on the downward slope add the second half of the waveform and then reset it after use.
            sumFullWaveSquares = sumHalfWaveSquaresPositive + sumHalfWaveSquaresNegative;

            std::string jsonTemplate;
             jsonTemplate = jsonTemplate +        "{" +
                                                  "\"thisWaveLenSamples\": %i, " +
                                                  "\"lastWaveLenSamples\": %i, " +
                                                  "\"wavelenSamplesAvg\": \"%f\", " +
                                                  "\"numFullWaveClips\": %i, " +
                                                  "\"positiveWaveSampleLength\": %i, " +
                                                  "\"negativeWaveSampleLength\": %i, " +
                                                  "\"fullWaveRMS\": \"%f\", " +
                                                  "\"halfwaveRMSNegative\": \"%f\", " +
                                                  "\"halfwaveRMSPositive\": \"%f\", " +
                                                  "\"peakPositive\": \"%f\", " +
                                                  "\"peakNegative\": \"%f\", " + // remember to exclude a comma on the last item.
                                                  "\"peakToPeak\": \"%f\" " + // remember to exclude a comma on the last item.
                                                  " }";

            // Compose a JSON string that we will transmit via the gnuradio message bus.
            sprintf (retJsonString, jsonTemplate.c_str(),
                samplesSinceLastDownCross,          // this wave's wavelength, in samples
                lastSamplesSinceLastDownCross,      // Last wave's wavelength, in samples
                avgSamplesPerZeroDown,              // Best running calculation of fundamental wavelength.
                numFullWaveClips,                   // number of times the waveform hit max/min bounds and was presumably clipped.
                positiveWaveSampleLength,           // wavelength of positive half-wave
                negativeWaveSampleLength,           // wavelength of negative half-wave
                sqrt(sumFullWaveSquares),           // RMS full wave
                sqrt(sumHalfWaveSquaresPositive),   // RMS positive half-wave
                sqrt(sumHalfWaveSquaresNegative),   // RMS negative half-wave
                waveMax,                            // peak positive this wavelength
                waveMin,                            // peak negative this wavelength
                waveMax - waveMin                   // peak to peak
                );
                // todo: add full wave RMS, min peak, max peak, peak-to-peak distance, and each half wave RMS, positive to negative ratio *1000, etc.

            // reset the full wave accumulator.
            sumFullWaveSquares = 0;

            // Reset the Clipping counter
            numFullWaveClips = 0;

            // reset half-wave accumulators. full wave accumulators get reset in the above up/downslow decision.
            sumHalfWaveSquaresPositive = 0;
            sumHalfWaveSquaresNegative = 0;
            waveSum = 0;
            waveMin = 0;
            waveMax = 0;

            return (retJsonString);
        } else {
            // take the half-wave square sums and put them into the negative variable.
            sumHalfWaveSquaresNegative = sumHalfWaveSquares;
            sumHalfWaveSquares = 0;
            // we're "half way into the full wave" so for this half-wave return no json message. On the downward slope.
            return ("");

        }



    }


    getfreqcpp::sptr
    getfreqcpp::make(float initialAlpha)
    {
      return gnuradio::get_initial_sptr
        (new getfreqcpp_impl(initialAlpha));
    }

    /*
     * The private constructor
     */
    getfreqcpp_impl::getfreqcpp_impl(float initialAlpha)
      : gr::sync_block("getfreqcpp",
              gr::io_signature::make(1,1, sizeof(float)),
              gr::io_signature::make(1,1, sizeof(float)))
    {
                alpha = initialAlpha;
                polymorphicMessageDestination = pmt::string_to_symbol("out");
                message_port_register_out(polymorphicMessageDestination);

                processId = ::getpid(); // Get the Process id. We'll be using it for ZMQ IPC stuff. Distinguishing IPC pipes by PID.

                //  Initialize ZeroMQ. We'll be sending JSON messages via ZMQ.
//                zmq::context_t zmqContext (1);
//                zmq::socket_t zmqSocket (zmqContext , ZMQ_PUB);
//                //socket.bind ("tcp://*:5555");
//                zmqSocket.bind ("ipc:///tmp/getfreqcpp"); // TODO: include process ID in the IPC file name.
//                std::stringstream ss;
//                zmq::message_t zmqPacket((void*)ss.str().c_str(), ss.str().size()+1, NULL);
//                zmqSocket.send(zmqPacket);



                printf ("[getfreqcpp]: Initialized\n");
    }

    /*
     * Our virtual destructor.
     */
    getfreqcpp_impl::~getfreqcpp_impl()
    {
    }

    int
    getfreqcpp_impl::work(int noutput_items,
        gr_vector_const_void_star &input_items,
        gr_vector_void_star &output_items)
    {
        const float *in = (const float *) input_items[0];
        float *out = (float *) output_items[0];

        std::string crossingData;


        // Do <+signal processing+>
        for (int i=0; i < noutput_items; i++) {


            if (ENABLE_WAVE_METRICS == true) {
                // Store each sample in our local buffer.
//                sampleBufferPosition++; sampleBufferPosition %= samp_rate*2;
//                sampleBuffer[sampleBufferPosition] = in[i];

                // calculate sum of squares
                sumHalfWaveSquares = sumHalfWaveSquares + in[i] * in[i];

                // calculate wave sum
                waveSum = waveSum + in[i];

                // calculate wave peak positive direction
                if (in[i] > 0 && in[i] > waveMax) {
                    waveMax = in[i];
                }

                // calculate wave peak negative direction
                if (in[i] < 0 && in[i] < waveMin) {
                    waveMin = in[i];
                }

                if (in[i] == -1 || in[i] == 1) {
                    numFullWaveClips++;
                }
            }


            // did we just cross the axis in the positive direction?
            if ((lastSampleValue < 0) && (in[i] >= 0)) {

                // this assignment works because we're about half way into the wave, and we just crossed upward.
                negativeWaveSampleLength = samplesSinceLastDownCross;

		// Even though crossingData is "" for all positive crossings at this time, we still call the method so that metrics can be calculated.
                crossingData = calculateWaveCrossingMetrics(lastSampleValue,in[i]);
		// The following block is never executed at this time. We do those calculations at the time of negative crossing.
                /*
		 * if ((ENABLE_WAVE_METRICS == true) && (crossingData.length() > 0)) {
        	    pmt::pmt_t messageString;
                    messageString = pmt::string_to_symbol(crossingData.c_str());
                    message_port_pub(polymorphicMessageDestination, messageString);
                    printf ("Crossed positive, data: %s\n",crossingData.c_str());
                }
		*/
		

            }

            // Did we just cross the axis in the negative direction?
            if ((lastSampleValue > 0) && (in[i] <= 0)) {
                // make two copies of the current value.
                float oldAvg = avgSamplesPerZeroDown;
                float newAvg = avgSamplesPerZeroDown;

                // every down crossing we will calculate number of samples since the last half-wave crossing
                positiveWaveSampleLength = samplesSinceLastDownCross - negativeWaveSampleLength;

                // calculate the new average, which will become the new value if it's within bounds. We'll check that next.
                newAvg = (1-alpha) * avgSamplesPerZeroDown + alpha * samplesSinceLastDownCross;
                // don't allow a single measurement to monopolize the average. only budge it by a little bit at a time. This method smooths out single sample upsets.
                // smooth out big positive change
                if (newAvg - oldAvg > bigChangeThreshold) {
                    // pull the average UP a tiny bit.
                    avgSamplesPerZeroDown = (1-alpha) * avgSamplesPerZeroDown + alpha * (avgSamplesPerZeroDown + correctedChangeSizeForBigChanges);
                    // avgSamplesPerZeroDown = oldAvg + 1;
                } else if (oldAvg - newAvg > bigChangeThreshold) {
                    // smooth out big negative change
                    // avgSamplesPerZeroDown = oldAvg - 1;
                    // pull the average down a tiny bit.
                    avgSamplesPerZeroDown = (1-alpha) * avgSamplesPerZeroDown + alpha * (avgSamplesPerZeroDown - correctedChangeSizeForBigChanges);
                } else {
                    // otherwise it's a normal calculation.
                    avgSamplesPerZeroDown = newAvg;
                }



                // fast start-up.
                if ((samplesSinceLastDownCross - avgSamplesPerZeroDown > bigGapSize) || (avgSamplesPerZeroDown - samplesSinceLastDownCross > bigGapSize) ) {
                    consecutiveBigGaps++;

                    if (consecutiveBigGaps > maxBigGaps) {
                        // JUMP to the currently calculated value, to short circuit a painfully slow startup.
                        avgSamplesPerZeroDown = samplesSinceLastDownCross;
                    }
                } else {
                    consecutiveBigGaps = 0;
                }

                // At this point the latest zero crossing (wavelength) calculations have been made.

                crossingData = calculateWaveCrossingMetrics(lastSampleValue,in[i]);
                if ((ENABLE_WAVE_METRICS == true) && (crossingData.length() > 0)) {
                    pmt::pmt_t messageString;
                    messageString = pmt::string_to_symbol(crossingData.c_str());
                    message_port_pub(polymorphicMessageDestination, messageString);
                    // printf ("WAVEFORM DATA: %s\n",crossingData.c_str());
                }

                // Reset things

                // This gets used as denominator in calculations so don't let it be zero.
                if (avgSamplesPerZeroDown == 0) { avgSamplesPerZeroDown = 1; }

                lastSamplesSinceLastDownCross = samplesSinceLastDownCross;
                samplesSinceLastDownCross = 0;
            }

            // Prevent zeros in the output. It makes for divide by zero in flowgraphs and is very difficult to work around.
            if (avgSamplesPerZeroDown == 0) {
                avgSamplesPerZeroDown = 1;
            }
            out[i] = avgSamplesPerZeroDown;

            lastSampleValue = in[i];
            samplesSinceLastDownCross++;
        }


      // Tell runtime system how many output items we produced.
      return noutput_items;
    }


  } /* namespace powerquality */
} /* namespace gr */

