/* -*- c++ -*- */
/* 
 * Copyright 2018 <Brad Hein>.
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
#include "pq_rails_impl.h"

#include <stdio.h>
#include <math.h> // for fabs
#include <string>

using namespace std;

namespace gr {
  namespace powerquality {


    void pq_rails_impl::resetPipelineMagnitudes() {
        pipelineAMagnitude=0;
        pipelineBMagnitude=0;
        pipelineCMagnitude=0;
        pipelineBMagnitudeUnmuted=0;
    }

    static void msg (char *themessage) {
        printf ("[pq_rails] %s\n", themessage);
    }

    // This function can be used by various functions to calculate the "delayed" index of a sample within one of the ring buffers.
    // we assume the number of elements in the buffer is equivalent to samp_rate.
    int pq_rails_impl::getDelayedPosition(int position,int delayBySamples) {

        int delayedPosition;

        // avoid doing a modulo. Not working as expected. -5 % 48000 is -5?? need it to be 48000-1 -5
        if (position - delayBySamples >= 0) {
            // easy path - current position is at a higher index than the delayed sample.
            delayedPosition = (position - delayBySamples) % samp_rate;
        } else {
            // Current sample is at a low index, but delayed sample is at a higher index, due to the nature of the wrapping of the ring buffer.
            delayedPosition = (position - delayBySamples);
            delayedPosition = samp_rate + delayedPosition;
        }

        return delayedPosition;
    }

    /**
     * Retrieve a single sample from the sample buffer. Allow for a delay to be specified.
     * So instead of grabbing current sample, you can get the sample value n samples ago.
     **/
    float pq_rails_impl::getSample(int delayBySamples) {
        return sampleBuffer[getDelayedPosition(sampleBufferPosition,delayBySamples)];
    }

    float pq_rails_impl::getSampleInverted(int delayBySamples) {
        return sampleBufferInverted[getDelayedPosition(sampleBufferPosition,delayBySamples)];
    }


    // fire this function against each sample to calculate the current cancellation sum/magnitude and store it.
    // the pipeline with the lowest magnitude at the time of periodic review will be the favored one, whether it's B (current) or the A or C rails.
    void pq_rails_impl::calculatePipelineSums() {
//        pipelineAMagnitude += fabs(getSample(0) + getSampleInverted(pipelineADelay));
//        pipelineBMagnitude += fabs(getSample(0) + getSampleInverted(pipelineBDelay)); // represents current output.
//        pipelineCMagnitude += fabs(getSample(0) + getSampleInverted(pipelineCDelay));
        // NEW: get samples of 1+ N away. add that one to ensure that were getting the latest sample and not the OLDEST (ring buffer, element ahead of current is oldes).
        // actually make that 100, becuase 1 doesn't give us enough room to be dialed above or below far enough.
        pipelineAMagnitude        += pow(getSample(100) + getSampleInverted(100+pipelineADelay),2);
        pipelineBMagnitude        += pow(getSample(100) + getSampleInverted(100+pipelineBDelay),2); // represents current output.
        pipelineBMagnitudeUnmuted += pow(getSample(100),2);
        pipelineCMagnitude        += pow(getSample(100) + getSampleInverted(100+pipelineCDelay),2);

//        // get rid of NaN?
//        if (pipelineAMagnitude < 0) {
//            pipelineAMagnitude = 0;
//        }
//        if (pipelineBMagnitude < 0) {
//            pipelineBMagnitude = 0;
//        }
//        if (pipelineCMagnitude < 0) {
//            pipelineCMagnitude = 0;
//        }
    }


    /**
     * Store a sample in the incoming sample buffer.
     **/
    void pq_rails_impl::storeSample(float sampleValue) {
        sampleBuffer[sampleBufferPosition] = sampleValue;
        sampleBufferInverted[sampleBufferPosition] = sampleValue * -1;

        // increment and modulo the position.
        sampleBufferPosition++;
        sampleBufferPosition%=samp_rate;

        // calculate the new pipeline sums.
        calculatePipelineSums();
    }


    /**
     * This gets called when the delay (calcualted frequency) changes
     */
    void pq_rails_impl::setPipelineDelay(int centerPipelineDelaySamples) {
        pipelineADelay = centerPipelineDelaySamples - 1;
        pipelineBDelay = centerPipelineDelaySamples;
        pipelineCDelay = centerPipelineDelaySamples + 1;

//        printf ("[pq_rails]: uptime=%f,freq=%f,wavelen=%i samples.\n",absoluteTimeOffset,(1.0f * samp_rate)/centerPipelineDelaySamples,centerPipelineDelaySamples);
        printQualityNextTime = true;
    }



    /**
     * return true if a nudge occurred. False otherwise.
     */
    string pq_rails_impl::doNudge(int nudgeNumber) {
        string statusString;
        // <moved to global> int nudgeTippingPoint = 10; // 3 is ok but results in oscillations at times.

        // time between nudges would be no less than
        // nudgeTippingPoint * (samp_rate/pipelineSampleLimit) samples.
        // so if pipelineSampleLimit is 4 wavelengths then that's 10 * (480000/(32000)) = 150

        // reset nudging if we're hitting zeros in between nudges.
        if (nudgeNumber == 0) {
            nudge = 0;
            return (char *)"";
        }

        nudge = nudge + nudgeNumber;


        if (printQualityNextTime == true) {
            // printf ("[pq_rails]: uptime=%f,nudge=%i,muteQuality=%f,freq=%f,wavelen=%i\n",absoluteTimeOffset,nudge,muteQuality,(1.0f * samp_rate)/pipelineBDelay,pipelineBDelay);
            char stringBuf[256];
            sprintf (stringBuf, "{ \"uptime\": %i, \"nudge\": %i, \"muteQuality\": %i, \"freq\": \"%f\", \"wavelen\": %i, \"pipelineBMagnitudeUnmuted\": \"%f\", \"pipelineBMagnitude\": \"%f\" }",(int)absoluteTimeOffset,nudge,(int)muteQuality,(1.0f * samp_rate)/pipelineBDelay,pipelineBDelay,pipelineBMagnitudeUnmuted*1000, pipelineBMagnitude*1000);
            statusString = string(stringBuf);
            // printf ("C++ JSON: %s\n", statusString.c_str());
            // printf ("The length of the C++ JSON is %i\n",statusString.length() );
            printQualityNextTime = false;
        }


        if (nudge >= nudgeTippingPoint) {
            setPipelineDelay(pipelineBDelay + 1);
            nudge = 0;
            return statusString;
        }

        if (nudge <= 0-nudgeTippingPoint) {
            setPipelineDelay(pipelineBDelay - 1);
            nudge = 0;
            return statusString;
        }

        return statusString;
    }

    float pq_rails_impl::getMuteQuality() {
        return pipelineBMagnitudeUnmuted / pipelineBMagnitude; // applies to last iteration at any given time.
    }

    // Analyze pipeline magnitudes,
    string pq_rails_impl::reCalculateBestDelay() {

//        float ratio_b_a = pipelineBMagnitude / pipelineAMagnitude;
//        float ratio_b_c = pipelineBMagnitude / pipelineCMagnitude;
//        float distance_a_c = fabs(pipelineAMagnitude - pipelineCMagnitude);
//        float a_minus_b = pipelineBMagnitude - pipelineAMagnitude;
//        float c_minus_b = pipelineBMagnitude - pipelineCMagnitude;
//        float pointerNeedle = a_minus_b * -1 + c_minus_b;

        // mute quality, 1,000,000 is awesome, 100 is passing, and less than 5 is debatable whether it's worth it to mute anything.
        muteQuality =  getMuteQuality();

        // nudge
        int nudgeNumber = 0;
        if (pipelineAMagnitude < pipelineBMagnitude) {
            nudgeNumber = -1;
        }

        if (pipelineCMagnitude < pipelineBMagnitude) {
            nudgeNumber = 1;
        }

        string nudgeData = doNudge(nudgeNumber);
//
//        // TODO: Put this back above the nudging.
//        printf ("[pq_rails] pipelineBDelay=%i mag_a=%f mag_b=%f mag_c=%f ratio_b_a=%f ratio_b_c=%f  pipelineSampleCount=%i totalNudge=%i muteQuality=%f\n",
//            pipelineBDelay,
//            pipelineAMagnitude,
//            pipelineBMagnitude,
//            pipelineCMagnitude,
//            ratio_b_a,
//            ratio_b_c,
//            pipelineSampleCount,
//            nudge,
//            muteQuality
//            );

        // having analyzed the pipelines, reset their magnitude sums.
        resetPipelineMagnitudes();

        return nudgeData;
    }

    pq_rails::sptr
    pq_rails::make(int center_freq, int min_freq, int max_freq, int new_samp_rate)
    {
      return gnuradio::get_initial_sptr
        (new pq_rails_impl(center_freq, min_freq, max_freq, new_samp_rate));
    }

    /*
     * The private constructor
     */
    pq_rails_impl::pq_rails_impl(int center_freq, int min_freq, int max_freq, int new_samp_rate)
      : gr::sync_block("pq_rails",
              gr::io_signature::make(1,1, sizeof(float)),
              gr::io_signature::make(1,1, sizeof(float)))
    {


        nudgeTippingPoint = 5;  // 10 is a very stable value, but tends to be slow to adapt to rapid freq changes.
        printQualityNextTime = false;
        //samp_rate = -1; // Keep a copy of the sample rate. This gets set in the constructor. Specified by the user as block parameter.
        sampleBufferPosition = 0;
        absoluteTimeOffset = 0;
        pipelineSampleCount = 0;
        muteQuality = 0;
        nudge = 0;
        // TODO: Do something useful with the min/max freq - these are useful for extremely low power settings where fundamental might be lower power than harmonics.


        samp_rate = new_samp_rate;
        printf ("[pq_rails] sample rate is %i\n", samp_rate);
        // initialize sample buffers
        sampleBuffer         = new float[samp_rate];
        sampleBufferInverted = new float[samp_rate];
        // Initialize the pipeline delays.
        int wavelength = samp_rate / center_freq;
        setPipelineDelay(wavelength);
        // initialize the pipeline running magnitude accumulators.
        resetPipelineMagnitudes();
        pipelineSampleLimit = wavelength * 4; // TODO: ponder deeply over this calculation.

        printf ("[pq_rails]: Initializing message passing port...\n");
        pmt_out = pmt::string_to_symbol("out");
        message_port_register_out(pmt_out);

        printf ("[pq_rails]: Initialized\n");
    }

    /*
     * Our virtual destructor.
     */
    pq_rails_impl::~pq_rails_impl()
    {
    }

    int
    pq_rails_impl::work(int noutput_items,
        gr_vector_const_void_star &input_items,
        gr_vector_void_star &output_items)
    {
      const float *in = (const float *) input_items[0];
      float *out = (float *) output_items[0];

      // Do <+signal processing+>
      for (int i = 0; i < noutput_items; i++) {
        pipelineSampleCount++;
        storeSample(in[i]);// this function also re-calculates pipeline sums.

        if (pipelineSampleCount >= pipelineSampleLimit) {
            // increment time offset, in seconds.
            absoluteTimeOffset = absoluteTimeOffset + ((float)pipelineSampleCount)*((float)1/(float)samp_rate);
            string nudgeData = reCalculateBestDelay();
            pipelineSampleCount = 0;

            // if a nudge occurred, then nudgeData will contain a JSON string with information to be passed out of the block as a message.
            if (nudgeData.length() > 0) {
                // printf ("DEBUG: PMT STUFF, String=%s\n",nudgeData.c_str());
                pmt::pmt_t str1 = pmt::string_to_symbol(nudgeData.c_str());
                message_port_pub(pmt_out, str1);
            }

        }

        // new: Trying to delay the output by about one wavelength (==pipelineSampleLimit) so we arne't chasing our tail.
        out[i] = getSample(100) + getSampleInverted(100 + pipelineBDelay); // TODO: Ponder deeply about delaying this by a number of samples. Otherwise we are delaying by a value that was calculated N wavelengths ago. constantly old data.
//          out[i] = in[i] * 2;
      }

      // Tell runtime system how many output items we produced.
      return noutput_items;
    }


  } /* namespace powerquality */
} /* namespace gr */

