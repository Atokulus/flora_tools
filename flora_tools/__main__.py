import argparse
import sys
from multiprocessing import Pool

from flora_tools.sim.sim import Sim
from flora_tools.toolchain.bootloader import Bootloader
from flora_tools.toolchain.eclipse_patcher import EclipsePatcher
from flora_tools.toolchain.platforms import Platform
from flora_tools.toolchain.programmer import Programmer


def program_all_devices(flora_path):
    bootloaders = Bootloader.get_all()

    if len(bootloaders):
        with Pool(len(bootloaders)) as p:
            arguments = [{'flora_path': flora_path, 'bootloader': bootloader} for bootloader in bootloaders]
            p.map(Programmer.program_on_bootloader, arguments)
            print("Programming finished.")


def program_device(firmware_path, port):
    Programmer.program_device(firmware_path, port)


def patch_eclipse(flora_path):
    devkit_patcher = EclipsePatcher(flora_path, Platform.DEVKIT)
    devkit_patcher.patch()
    comboard_patcher = EclipsePatcher(flora_path, Platform.COMBOARD)
    comboard_patcher.patch()
    comboard_patcher = EclipsePatcher(flora_path, Platform.COMBOARD_STM32L433CC)
    comboard_patcher.patch()


def run_simulation(output_path, event_count: int = None, time_limit: float = None):
    sim = Sim(output_path=output_path, event_count=event_count, time_limit=time_limit)
    sim.run()


def generate_code(flora_path):
    pass


def main():
    parser = argparse.ArgumentParser(description='Executable flora_tools utilities', prog='flora_tools')
    parser.add_argument('command', help='Execute given command',
                        choices=['program', 'program_all', 'patch_eclipse', 'run_simulation', 'generate_code'])
    parser.add_argument('path', help='Set the path to the Flora main repository folder or .hex/.binary file')
    parser.add_argument('-p', '--port', help='Set the serial port (e.g. "COM5" or "/dev/ttyUSB0")')
    parser.add_argument('-t', '--time', type=float,
                        help='Set the time limit for events that get executed by the simulation')
    parser.add_argument('-c', '--event_count', type=int,
                        help='Set the maximum number of events that get executed by the simulation')
    args = parser.parse_args()

    if args.command == 'program':
        if args.port is None:
            parser.error("Port is required")
            sys.exit()
        program_device(args.path, args.port)
    elif args.command == 'program_all':
        program_all_devices(args.path)
    elif args.command == 'patch_eclipse':
        patch_eclipse(args.path)
    elif args.command == 'run_simulation':
        run_simulation(args.path, event_count=args.event_count, time_limit=args.time)
    elif args.command == 'generate_code':
        generate_code(args.path)


if __name__ == '__main__':
    main()
