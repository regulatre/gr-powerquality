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

#ifndef INCLUDED_POWERQUALITY_PQ_RAILS_IMPL_H
#define INCLUDED_POWERQUALITY_PQ_RAILS_IMPL_H

#include <powerquality/pq_rails.h>

namespace gr {
  namespace powerquality {

    class pq_rails_impl : public pq_rails
    {
     private:
      int nudgeTippingPoint;

      bool printQualityNextTime;

      int samp_rate;

      // raw input samples just stored for local use.
      float *sampleBuffer;
      int sampleBufferPosition;

      // inverted buffer contains a copy of all the same samples as sampleBuffer but multiplied by -1.
      float *sampleBufferInverted;

      // absolute time offset, set to 0 upon startup, incremented periodically in a somewhat accurate but not completely accurate manner.
      // time in this case is measured in seconds.
      float absoluteTimeOffset;

      // pipeline delay definitions. Will be set initially in the constructor.
      int pipelineADelay;
      int pipelineBDelay;
      int pipelineCDelay;
      float pipelineAMagnitude;
      float pipelineBMagnitude;
      float pipelineCMagnitude;
      float pipelineBMagnitudeUnmuted;
      int pipelineSampleCount;        // will continuously be incremented and reset each time we analyze the pipelines.
      int pipelineSampleLimit;        // Re-calculate pipeline delays every N samples, specified by this variable, calculated in the constructor based on samp_rate.
      float muteQuality;              // an arbitrary number representing the quality of muting. Basically a ratio of unmuted to muted audio. Higher is better.

      int nudge;                      // this gets nudged up and down, eventually triggering a change to wavelength if appropriate.


      // The message handling destination
      pmt::pmt_t pmt_out;


      void initPrivateVars();
      void resetPipelineMagnitudes();
      int getDelayedPosition(int position,int delayBySamples);

      float getSample(int delayBySamples);
      float getSampleInverted(int delayBySamples);
      void calculatePipelineSums();
      void storeSample(float sampleValue);
      void setPipelineDelay(int centerPipelineDelaySamples);
      std::string doNudge(int nudgeNumber);
      float getMuteQuality();
      std::string reCalculateBestDelay();







     public:
      pq_rails_impl(int center_freq, int min_freq, int max_freq, int new_samp_rate);
      ~pq_rails_impl();

      // Where all the action really happens
      int work(int noutput_items,
         gr_vector_const_void_star &input_items,
         gr_vector_void_star &output_items);
    };

  } // namespace powerquality
} // namespace gr

#endif /* INCLUDED_POWERQUALITY_PQ_RAILS_IMPL_H */

