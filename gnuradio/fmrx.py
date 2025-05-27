#!/usr/bin/env python3
# -*- coding: utf-8 -*-

#
# SPDX-License-Identifier: GPL-3.0
#
# GNU Radio Python Flow Graph
# Title: FM reception
# Author: Kentaro1043
# GNU Radio version: 3.10.12.0

from PyQt5 import Qt
from gnuradio import qtgui
from gnuradio import analog
from gnuradio import blocks
from gnuradio import filter
from gnuradio.filter import firdes
from gnuradio import gr
from gnuradio.fft import window
import sys
import signal
from PyQt5 import Qt
from argparse import ArgumentParser
from gnuradio.eng_arg import eng_float, intx
from gnuradio import eng_notation
import osmosdr
import time
import threading



class fmrx(gr.top_block, Qt.QWidget):

    def __init__(self):
        gr.top_block.__init__(self, "FM reception", catch_exceptions=True)
        Qt.QWidget.__init__(self)
        self.setWindowTitle("FM reception")
        qtgui.util.check_set_qss()
        try:
            self.setWindowIcon(Qt.QIcon.fromTheme('gnuradio-grc'))
        except BaseException as exc:
            print(f"Qt GUI: Could not set Icon: {str(exc)}", file=sys.stderr)
        self.top_scroll_layout = Qt.QVBoxLayout()
        self.setLayout(self.top_scroll_layout)
        self.top_scroll = Qt.QScrollArea()
        self.top_scroll.setFrameStyle(Qt.QFrame.NoFrame)
        self.top_scroll_layout.addWidget(self.top_scroll)
        self.top_scroll.setWidgetResizable(True)
        self.top_widget = Qt.QWidget()
        self.top_scroll.setWidget(self.top_widget)
        self.top_layout = Qt.QVBoxLayout(self.top_widget)
        self.top_grid_layout = Qt.QGridLayout()
        self.top_layout.addLayout(self.top_grid_layout)

        self.settings = Qt.QSettings("gnuradio/flowgraphs", "fmrx")

        try:
            geometry = self.settings.value("geometry")
            if geometry:
                self.restoreGeometry(geometry)
        except BaseException as exc:
            print(f"Qt GUI: Could not restore geometry: {str(exc)}", file=sys.stderr)
        self.flowgraph_started = threading.Event()

        ##################################################
        # Variables
        ##################################################
        self.samp_rate = samp_rate = 48000
        self.freq = freq = 80e6

        ##################################################
        # Blocks
        ##################################################

        self._freq_msgdigctl_win = qtgui.MsgDigitalNumberControl(lbl='', min_freq_hz=70e6, max_freq_hz=100e6, parent=self, thousands_separator=",", background_color="black", fontColor="white", var_callback=self.set_freq, outputmsgname='freq')
        self._freq_msgdigctl_win.setValue(80e6)
        self._freq_msgdigctl_win.setReadOnly(False)
        self.freq = self._freq_msgdigctl_win

        self.top_layout.addWidget(self._freq_msgdigctl_win)
        self.osmosdr_source_0 = osmosdr.source(
            args="numchan=" + str(1) + " " + "hackrf=0"
        )
        self.osmosdr_source_0.set_sample_rate((samp_rate*50))
        self.osmosdr_source_0.set_center_freq( freq, 0)
        self.osmosdr_source_0.set_freq_corr(0, 0)
        self.osmosdr_source_0.set_dc_offset_mode(0, 0)
        self.osmosdr_source_0.set_iq_balance_mode(0, 0)
        self.osmosdr_source_0.set_gain_mode(False, 0)
        self.osmosdr_source_0.set_gain(50, 0)
        self.osmosdr_source_0.set_if_gain(20, 0)
        self.osmosdr_source_0.set_bb_gain(20, 0)
        self.osmosdr_source_0.set_antenna('', 0)
        self.osmosdr_source_0.set_bandwidth(1e6, 0)
        self.low_pass_filter_0 = filter.fir_filter_ccf(
            5,
            firdes.low_pass(
                1,
                (samp_rate*50),
                250e3,
                50e3,
                window.WIN_HAMMING,
                6.76))
        self.blocks_wavfile_sink_0 = blocks.wavfile_sink(
            '/Users/kentaro/source/repos/github.com/Kentaro1043/sdr-m3u-tuner/test.wav',
            2,
            samp_rate,
            blocks.FORMAT_WAV,
            blocks.FORMAT_PCM_16,
            False
            )
        self.analog_wfm_rcv_pll_0 = analog.wfm_rcv_pll(
        	demod_rate=(samp_rate*10),
        	audio_decimation=10,
        	deemph_tau=(75e-6),
        )


        ##################################################
        # Connections
        ##################################################
        self.msg_connect((self.freq, 'valueout'), (self.freq, 'valuein'))
        self.connect((self.analog_wfm_rcv_pll_0, 0), (self.blocks_wavfile_sink_0, 0))
        self.connect((self.analog_wfm_rcv_pll_0, 1), (self.blocks_wavfile_sink_0, 1))
        self.connect((self.low_pass_filter_0, 0), (self.analog_wfm_rcv_pll_0, 0))
        self.connect((self.osmosdr_source_0, 0), (self.low_pass_filter_0, 0))


    def closeEvent(self, event):
        self.settings = Qt.QSettings("gnuradio/flowgraphs", "fmrx")
        self.settings.setValue("geometry", self.saveGeometry())
        self.stop()
        self.wait()

        event.accept()

    def get_samp_rate(self):
        return self.samp_rate

    def set_samp_rate(self, samp_rate):
        self.samp_rate = samp_rate
        self.low_pass_filter_0.set_taps(firdes.low_pass(1, (self.samp_rate*50), 250e3, 50e3, window.WIN_HAMMING, 6.76))
        self.osmosdr_source_0.set_sample_rate((self.samp_rate*50))

    def get_freq(self):
        return self.freq

    def set_freq(self, freq):
        self.freq = freq
        self.osmosdr_source_0.set_center_freq( self.freq, 0)




def main(top_block_cls=fmrx, options=None):

    qapp = Qt.QApplication(sys.argv)

    tb = top_block_cls()

    tb.start()
    tb.flowgraph_started.set()

    tb.show()

    def sig_handler(sig=None, frame=None):
        tb.stop()
        tb.wait()

        Qt.QApplication.quit()

    signal.signal(signal.SIGINT, sig_handler)
    signal.signal(signal.SIGTERM, sig_handler)

    timer = Qt.QTimer()
    timer.start(500)
    timer.timeout.connect(lambda: None)

    qapp.exec_()

if __name__ == '__main__':
    main()
