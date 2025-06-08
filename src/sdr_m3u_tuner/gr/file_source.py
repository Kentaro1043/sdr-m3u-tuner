#!/usr/bin/env python3
# -*- coding: utf-8 -*-

#
# SPDX-License-Identifier: GPL-3.0
#
# GNU Radio Python Flow Graph
# Title: Audio source from file
# Author: Kentaro1043
# Description: Read audio wav file and sink that data.
# GNU Radio version: 3.10.12.0

from gnuradio import blocks
from gnuradio import gr
from gnuradio.filter import firdes
from gnuradio.fft import window
import sys
import signal
from argparse import ArgumentParser
from gnuradio.eng_arg import eng_float, intx
from gnuradio import eng_notation
from gnuradio import zeromq
import threading




class file_source(gr.top_block):

    def __init__(self):
        gr.top_block.__init__(self, "Audio source from file", catch_exceptions=True)
        self.flowgraph_started = threading.Event()

        ##################################################
        # Variables
        ##################################################
        self.source_file_path = source_file_path = "./test.wav"
        self.pub_address = pub_address = "tcp://127.0.0.1:12345"

        ##################################################
        # Blocks
        ##################################################

        self.zeromq_pub_sink_0 = zeromq.pub_sink(gr.sizeof_float, 1, pub_address, 100, False, (-1), '', True, True)
        self.blocks_wavfile_source_0 = blocks.wavfile_source(source_file_path, True)
        self.blocks_throttle2_0 = blocks.throttle( gr.sizeof_float*1, 48000000, True, 0 if "auto" == "auto" else max( int(float(0.1) * 48000000) if "auto" == "time" else int(0.1), 1) )


        ##################################################
        # Connections
        ##################################################
        self.connect((self.blocks_throttle2_0, 0), (self.zeromq_pub_sink_0, 0))
        self.connect((self.blocks_wavfile_source_0, 0), (self.blocks_throttle2_0, 0))


    def get_source_file_path(self):
        return self.source_file_path

    def set_source_file_path(self, source_file_path):
        self.source_file_path = source_file_path

    def get_pub_address(self):
        return self.pub_address

    def set_pub_address(self, pub_address):
        self.pub_address = pub_address




def main(top_block_cls=file_source, options=None):
    tb = top_block_cls()

    def sig_handler(sig=None, frame=None):
        tb.stop()
        tb.wait()

        sys.exit(0)

    signal.signal(signal.SIGINT, sig_handler)
    signal.signal(signal.SIGTERM, sig_handler)

    tb.start()
    tb.flowgraph_started.set()

    try:
        input('Press Enter to quit: ')
    except EOFError:
        pass
    tb.stop()
    tb.wait()


if __name__ == '__main__':
    main()
