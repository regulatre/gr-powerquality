/* -*- c++ -*- */

#define POWERQUALITY_API

%include "gnuradio.i"			// the common stuff

//load generated python docstrings
%include "powerquality_swig_doc.i"

%{
#include "powerquality/getfreqcpp.h"
%}


%include "powerquality/getfreqcpp.h"
GR_SWIG_BLOCK_MAGIC2(powerquality, getfreqcpp);
