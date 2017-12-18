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

namespace gr {
  namespace powerquality {

    int samplesSinceLastDownCross = 0;
    float avgSamplesPerZeroDown = 1;
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


        // Do <+signal processing+>
        for (int i=0; i < noutput_items; i++) {

            // Did we just cross the axis in the down direction?
            if ((lastSampleValue >= 0) && (in[i] < 0)) {
                // make two copies of the current value.
                float oldAvg = avgSamplesPerZeroDown;
                float newAvg = avgSamplesPerZeroDown;

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

                // This gets used as denominator in calculations so don't let it be zero.
                if (avgSamplesPerZeroDown == 0) { avgSamplesPerZeroDown = 1; }

                samplesSinceLastDownCross = 0;
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

