#! /bin/bash


# Create a new (or overwrite existing) template called "power_quality_template"
# This template applies automatically to any index with the name pattern power_quality-*
#

. ./config


if [ "$ELK_BASE_URL" == "" ] ; then
    echo "ERROR: Missing important variable ELK_BASE_URL. Missing config file or config file missing parameter(s). Press ^C to abort."
    sleep 99999999
fi

echo "Deleting template..."
curl -XDELETE $ELK_BASE_URL/_template/power_quality_template; echo

echo "Applying template..."
curl -XPUT $ELK_BASE_URL/_template/power_quality_template -d '
{ "template": "power_quality-*",
  "mappings" : {
      "power_quality": {
            "properties": {

                "@timestamp" : {
                    "type" : "date",
                    "format" : "epoch_millis"
                },

                "timestamp" : {
                    "type" : "date",
                    "format" : "epoch_millis"
                },

                "ts6" : {
                    "type" : "date",
                    "format" : "epoch_millis"
                },

                "queue_time_ms" : {
                    "type" : "integer",
                    "index" : "not_analyzed"
                },


                /* describes the logger device/application */
                "logger": {
                    "properties": {

                        "name": {
                            "type": "string",
                            "index": "not_analyzed"
                        },

                        "hostname": {
                            "type": "string",
                            "index": "not_analyzed"
                        },

                        "model": {
                            "type": "string",
                            "index": "not_analyzed"
                        },

                        "location": {
                            "type": "string",
                            "index": "not_analyzed"
                        }

                    }
                },


                /* describes the probe */
                "probe": {
                    "properties": {

                        "name": {
                            "type": "string",
                            "index": "not_analyzed"
                        },

                        "model": {
                            "type": "string",
                            "index": "not_analyzed"
                        },

                        "location": {
                            "type": "string",
                            "index": "not_analyzed"
                        }

                    }
                },

                "reading": {
                    "properties": {

                        "timespanmillis": {
                            "type": "long",
                            "index": "not_analyzed"
                        },

                        "rmscurrent": {
                            "type": "double",
                            "index": "not_analyzed"
                        },

                        "rmscurrentprobereading": {
                            "type": "double",
                            "index": "not_analyzed"
                        },

                        "rmscurrentmin": {
                            "type": "double",
                            "index": "not_analyzed"
                        },

                        "rmscurrentmax": {
                            "type": "double",
                            "index": "not_analyzed"
                        },

                        "rmsvolts": {
                            "type": "double",
                            "index": "not_analyzed"
                        },

                        "rmsvoltsprobereading": {
                            "type": "double",
                            "index": "not_analyzed"
                        },

                        "rmsvoltsmin": {
                            "type": "double",
                            "index": "not_analyzed"
                        },

                        "rmsvoltsmax": {
                            "type": "double",
                            "index": "not_analyzed"
                        },

                        "numvoltagespikes": {
                            "type": "integer",
                            "index": "not_analyzed"
                        },

                        "numvoltagesags": {
                            "type": "integer",
                            "index": "not_analyzed"
                        },

                        "frequency": {
                            "type": "double",
                            "index": "not_analyzed"
                        },

                        "frequencymin": {
                            "type": "double",
                            "index": "not_analyzed"
                        },

                        "frequencymax": {
                            "type": "double",
                            "index": "not_analyzed"
                        },

                        "bias_min": {
                            "type": "double",
                            "index": "not_analyzed"
                        },

                        "bias_max": {
                            "type": "double",
                            "index": "not_analyzed"
                        },

                        "bias_avg": {
                            "type": "double",
                            "index": "not_analyzed"
                        },


                        "frequencychangecount": {
                            "type": "integer",
                            "index": "not_analyzed"
                        }


                    }
                } /* End of reading attribute */
            } /* End of power_quality properties attribute */
        } /* End of power_quality section */
    } /* End of mappings section*/
}' ; echo

# Get version? (version is an allowed key name but completely ignored by elasticsearch at this time (5.6)
# curl -XGET $ELK_BASE_URL'/_template/power_quality_template?filter_path=*.version' ; echo



