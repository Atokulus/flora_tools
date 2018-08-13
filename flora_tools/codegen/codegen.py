import os

import numpy as np
from jinja2 import Environment, PackageLoader

import gloria
import lwb_round
import flora_tools.lwb_slot as lwb_slot
from flora_tools.gloria import GloriaTimings
import flora_tools.radio_configuration as radio_configuration
from flora_tools.radio_configuration import RADIO_CONFIGURATIONS, RadioModem, BAND_FREQUENCIES, BAND_GROUPS, \
    BAND_FREQUENCIES_US915, BAND_GROUPS_US915, RadioConfiguration
from radio_math import RadioMath
from sim import lwb_link_manager, lwb_stream, cad_sync
from sim.sim_gloria import MAX_ACKS


class CodeGen:
    def __init__(self, path):
        self.path = path

        if not os.path.exists(self.path):
            os.makedirs(self.path)

        self.env = Environment(
            loader=PackageLoader('flora_tools', 'codegen/templates'),
            block_start_string='<%',
            block_end_string='%>',
            variable_start_string='%%',
            variable_end_string='%%',
            comment_start_string='<#',
            comment_end_string='#>',
        )

        self.env.globals.update(human_time=self.human_time, modulation_name=self.modulation_name)

        self.generate_all()

    def generate_all(self):
        self.generate_radio_constants()
        self.generate_gloria_constants()
        self.generate_lwb_constants()
        self.generate_lwb_round_constants()

    def generate_radio_constants(self):
        target = './lib/radio/radio_constants.c'
        self.create_folder(target)

        template = self.env.get_template('radio_constants.c')

        configurations = [({
                               'modem': config['modem'].c_name,
                               'bandwidth': config['bandwidth'],
                               'datarate': config['datarate'],
                               'coderate': config['coderate'],
                               'preamble_len': config['preamble_len'],
                           } if config['modem'] is RadioModem.LORA else
                           {
                               'modem': config['modem'].c_name,
                               'bandwidth': config['bandwidth'],
                               'datarate': config['datarate'],
                               'preamble_len': config['preamble_len'],
                               'fdev': config['fdev'],
                           }
                           ) for config in RADIO_CONFIGURATIONS]

        radio_toas = []
        payloads = range(256)
        for mod, config in enumerate(RADIO_CONFIGURATIONS):
            math = RadioMath(RadioConfiguration(mod))
            radio_toas.append([gloria.GloriaTimings.timer_ticks(math.get_message_toa(payload)) for payload in payloads])

        rendered = template.render(configurations=configurations, bands=BAND_FREQUENCIES, band_groups=BAND_GROUPS,
                                   bands_us915=BAND_FREQUENCIES_US915, band_groups_us915=BAND_GROUPS_US915,
                                   radio_toas=radio_toas)

        self.write_render_to_file(rendered, target)

        target = './lib/radio/radio_constants.h'
        self.create_folder(target)


        template = self.env.get_template('radio_constants.h')

        constants = {'RADIO_DEFAULT_BAND': radio_configuration.RADIO_DEFAULT_BAND,
                     'RADIO_DEFAULT_BAND_US915': radio_configuration.RADIO_DEFAULT_BAND_US915,
                     'HS_TIMER_SCHEDULE_MARGIN': radio_configuration.HS_TIMER_SCHEDULE_MARGIN}

        rendered = template.render(**constants)
        self.write_render_to_file(rendered, target)

    def generate_gloria_constants(self):
        target = './lib/protocol/gloria/gloria_constants.h'
        self.create_folder(target)

        template = self.env.get_template('gloria_constants.h')

        constants = {
            'GLORIA_HEADER_LENGTH': lwb_slot.GLORIA_HEADER_LENGTH,
            'GLORIA_ACK_LENGTH': gloria.GLORIA_ACK_LENGTH,
            'GLORIA_CLOCK_DRIFT': GloriaTimings.timer_ticks(gloria.GLORIA_CLOCK_DRIFT),
            'GLORIA_CLOCK_DRIFT_PLUSMINUS': gloria.GLORIA_CLOCK_DRIFT / 2 * 1E6,
            'TIMER_FREQUENCY': "{} MHz".format(gloria.TIMER_FREQUENCY / 1E6),
            'GLORIA_BLACK_BOX_SYNC_DELAY': GloriaTimings.timer_ticks(gloria.BLACK_BOX_SYNC_DELAY),
            'GLORIA_MAX_ACKS': MAX_ACKS,
            'GLORIA_RADIO_SLEEP_TIME': GloriaTimings.timer_ticks(GloriaTimings(0).sleep_time),
            'GLORIA_RADIO_WAKEUP_TIME': GloriaTimings.timer_ticks(GloriaTimings(0).wakeup_time),
        }

        rendered = template.render(**constants)

        self.write_render_to_file(rendered, target)

        target = './lib/protocol/gloria/gloria_constants.c'
        self.create_folder(target)

        template = self.env.get_template('gloria_constants.c')
        gloria_timings = [GloriaTimings(modulation).get_timings() for modulation in range(10)]

        rendered = template.render(gloria_timings=gloria_timings)

        self.write_render_to_file(rendered, target)

    def generate_lwb_constants(self):
        target = './lib/protocol/lwb/lwb_constants.h'
        self.create_folder(target)
        template = self.env.get_template('lwb_constants.h')
        lwb_constants = {
            'LWB_SCHEDULE_GRANULARITY': GloriaTimings.timer_ticks(lwb_slot.LWB_SCHEDULE_GRANULARITY),
            'LWB_SYNC_PERIOD': GloriaTimings.timer_ticks(lwb_slot.LWB_SYNC_PERIOD),
            'GLORIA_HEADER_LENGTH': lwb_slot.GLORIA_HEADER_LENGTH,
            'LWB_CONTENTION_HEADER_LENGTH': lwb_slot.LWB_CONTENTION_HEADER_LENGTH,
            'LWB_DATA_HEADER_LENGTH': lwb_slot.LWB_DATA_HEADER_LENGTH,
            'LWB_MAX_DATA_PAYLOAD': lwb_slot.LWB_MAX_DATA_PAYLOAD,
            'LWB_SLOT_SCHEDULE_HEADER_LENGTH': lwb_slot.LWB_SLOT_SCHEDULE_HEADER_LENGTH,
            'LWB_SLOT_SCHEDULE_ITEM_LENGTH': lwb_slot.LWB_SLOT_SCHEDULE_ITEM_LENGTH,
            'LWB_ROUND_SCHEDULE_ITEM': lwb_slot.LWB_ROUND_SCHEDULE_ITEM,
            'LWB_ROUND_SCHEDULE_ITEM_COUNT': lwb_slot.LWB_ROUND_SCHEDULE_ITEM_COUNT,
            'LWB_ROUND_SCHEDULE_LENGTH': lwb_slot.LWB_ROUND_SCHEDULE_LENGTH,
        }
        rendered = template.render(**lwb_constants)
        self.write_render_to_file(rendered, target)

        target = './lib/protocol/lwb/lwb_constants.c'
        self.create_folder(target)
        template = self.env.get_template('lwb_constants.c')

        lwb_slot_times = []
        payloads = range(256)
        for mod in range(len(lwb_slot.RADIO_MODULATIONS)):
            lwb_slot_times.append([gloria.GloriaTimings.timer_ticks(
                lwb_slot.LWBSlot.create_empty_slot(mod, payload, False).total_time
            ) for payload in payloads])

        lwb_slot_acked_times = []
        for mod in range(len(lwb_slot.RADIO_MODULATIONS)):
            lwb_slot_acked_times.append([gloria.GloriaTimings.timer_ticks(
                lwb_slot.LWBSlot.create_empty_slot(mod, payload, False).total_time
            ) for payload in payloads])

        lwb_constants = {
            'gloria_default_power_levels': lwb_slot.GLORIA_DEFAULT_POWER_LEVELS,
            'gloria_retransmission_counts': lwb_slot.GLORIA_RETRANSMISSIONS_COUNTS,
            'gloria_hop_counts': lwb_slot.GLORIA_HOP_COUNTS,
            'lwb_modulations': lwb_slot.RADIO_MODULATIONS,
            'lwb_powers': lwb_slot.RADIO_POWERS,
            'lwb_slot_times': lwb_slot_times,
            'lwb_slot_acked_times': lwb_slot_acked_times,
            'lwb_max_slot_counts': lwb_round.LWB_MAX_SLOT_COUNT,
            'lwb_initial_stream_request_slot_counts': lwb_round.LWB_INITIAL_STREAM_REQUEST_SLOT_COUNT,
            'lwb_max_stream_request_slot_counts': lwb_round.LWB_MAX_STREAM_REQUEST_SLOT_COUNT,
        }
        rendered = template.render(**lwb_constants)

        self.write_render_to_file(rendered, target)

    def generate_lwb_round_constants(self):
        target = './lib/protocol/lwb/lwb_round_constants.c'
        self.create_folder(target)
        template = self.env.get_template('lwb_round_constants.c')

        lwb_round_constants = {
            'lwb_max_slot_count': lwb_round.LWB_MAX_SLOT_COUNT,
            'lwb_max_stream_request_slot_count': lwb_round.LWB_MAX_STREAM_REQUEST_SLOT_COUNT,
            'lwb_initial_stream_request_slot_count': lwb_round.LWB_INITIAL_STREAM_REQUEST_SLOT_COUNT,
            'lwb_min_stream_request_slot_count': lwb_round.LWB_MIN_STREAM_REQUEST_SLOT_COUNT,
        }

        rendered = template.render(**lwb_round_constants)
        self.write_render_to_file(rendered, target)

        target = './lib/protocol/lwb/lwb_round_constants.h'
        self.create_folder(target)
        template = self.env.get_template('lwb_round_constants.h')

        lwb_round_constants = {
            'LWB_LINK_UPGRADE_COUNTER': lwb_link_manager.LWB_LINK_UPGRADE_COUNTER,
            'LWB_LINK_DOWNGRADE_COUNTER': lwb_link_manager.LWB_LINK_DOWNGRADE_COUNTER,

            'LWB_STREAM_MAX_TTL': lwb_stream.LWB_STREAM_MAX_TTL,
            'LWB_STREAM_MAX_REQUEST_TRIALS': lwb_stream.LWB_STREAM_MAX_REQUEST_TRIALS,
            'LWB_STREAM_DEACTIVATION_BACKDROP': lwb_stream.LWB_STREAM_DEACTIVATION_BACKDROP,
            'LWB_STREAM_MAX_BACKDROP_RANGE': lwb_stream.LWB_STREAM_MAX_BACKDROP_RANGE,
            'LWB_STREAM_INITIAL_BACKDROP_RANGE': lwb_stream.LWB_STREAM_INITIAL_BACKDROP_RANGE,

            'CAD_SYNC_MAX_BACKOFF_EXPONENT': cad_sync.CAD_SYNC_MAX_BACKOFF_EXPONENT,
        }

        rendered = template.render(**lwb_round_constants)
        self.write_render_to_file(rendered, target)

    def create_folder(self, file):
        if not os.path.exists(os.path.join(self.path, os.path.dirname(file))):
            os.makedirs(os.path.join(self.path, os.path.dirname(file)))

    def write_render_to_file(self, render, file):
        with open(os.path.join(self.path, file), "w") as fh:
            fh.write(render)
            print("Written {}".format(file))

    @staticmethod
    def human_time(ticks: int) -> str:
        PREFIXES = ['', 'm', 'µ', 'n']
        realtime = ticks / gloria.TIMER_FREQUENCY
        if ticks != 0:
            order = np.ceil(np.ceil(-np.log10(realtime)) / 3)
            order = int(np.clip(order, 0, len(PREFIXES) - 1))
            realtime *= np.power(10, order * 3)
        else:
            order = 0

        formatted_time = "{:.3f} {}s".format(realtime, PREFIXES[order])

        return formatted_time

    @staticmethod
    def modulation_name(index: int) -> str:
        return RadioConfiguration(index).modulation_name
