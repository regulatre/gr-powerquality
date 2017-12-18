#! /bin/bash


# Create a new (or overwrite existing) template called "power_quality_template"
# This template applies automatically to any index with the name pattern power_quality-*
#

. ./config

curl -XPUT $ELK_BASE_URL/_template/power_quality_template -d '
{ "template": "power_quality-*",
    "mappings" : {

        "power_quality": {

            "properties": {


                "@timestamp" : {
                    "type" : "date",
                    "format" : "epoch_millis"
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

                        "frequencychangecount": {
                            "type": "integer",
                            "index": "not_analyzed"
                        }


                    }
                } /* End of reading attribute */
            } /* End of power_quality properties attribute */
        } /* End of power_quality section */
    } /* End of mappings section*/
}'
