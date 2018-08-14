import argparse
import sys
from multiprocessing import Pool

from flora_tools.codegen.codegen import CodeGen
from flora_tools.flocklab.measure_gloria import MeasureGloriaExperiment
from flora_tools.flocklab.measure_links import MeasureLinksExperiment
from flora_tools.sim.sim import Sim
from flora_tools.toolchain.bootloader import Bootloader
from flora_tools.toolchain.eclipse_patcher import EclipsePatcher
from flora_tools.toolchain.platforms import Platform
from flora_tools.toolchain.programmer import Programmer
from flora_tools.trace_visualizer.server import VisualizationServer


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


def run_simulation(output_path, event_count: int = None, time_limit: float = None, seed: int = 0):
    sim = Sim(output_path=output_path, event_count=event_count, time_limit=time_limit, seed=seed)
    sim.run()


def flocklab_measure_links(register_test, local):
    measure_links_experiment = MeasureLinksExperiment(local=local, register_test=register_test)


def flocklab_measure_gloria(ack, register_test, local):
    measure_gloria_experiment = MeasureGloriaExperiment(ack=ack, local=local, register_test=register_test)


def start_server():
    VisualizationServer()


def generate_code(flora_path):
    code_gen = CodeGen(flora_path)


def main():
    parser = argparse.ArgumentParser(description='Executable flora_tools utilities', prog='flora_tools')
    parser.add_argument('command', help='Execute given command',
                        choices=['program', 'program_all', 'patch_eclipse', 'run_simulation', 'flocklab_measure_links',
                                 'flocklab_measure_gloria', 'generate_code', 'start_server'])
    parser.add_argument('-d', '--path', help='Set the path to the Flora main repository folder or .hex/.binary file')
    parser.add_argument('-p', '--port', help='Set the serial port (e.g. "COM5" or "/dev/ttyUSB0")')
    parser.add_argument('-t', '--time', type=float,
                        help='Set the time limit for events that get executed by the simulation')
    parser.add_argument('-s', '--seed', type=int, default=0,
                        help='Set the random number generators seed for reproducible results')
    parser.add_argument('-c', '--event_count', type=int,
                        help='Set the maximum number of events that get executed by the simulation')
    parser.add_argument('-a', '--ack', action='store_true',
                        help='Runs Gloria measurements with Ack enabled')
    parser.add_argument('-r', '--register-test', action='store_true',
                        help='Runs Gloria measurements by requesting a test slot on FlockLab')
    parser.add_argument('-l', '--local', action='store_true',
                        help='Runs Gloria measurements only with locally attached serial devices.')
    args = parser.parse_args()

    if args.command == 'program':
        if args.port is None:
            parser.error("Port is required")
            sys.exit()
        program_device(args.path, args.port)
    elif args.command == 'program_all':
        if args.path is None:
            parser.error("program_all requires --path to find the firmware binaries.")
        else:
            program_all_devices(args.path)
    elif args.command == 'patch_eclipse':
        if args.path is None:
            parser.error("patch_eclipse requires --path to find Atollic TrueStudio project files.")
        else:
            patch_eclipse(args.path)
    elif args.command == 'run_simulation':
        if args.path is None:
            parser.error("run_simulation requires --path as simulation output directory.")
        else:
            run_simulation(args.path, event_count=args.event_count, time_limit=args.time, seed=args.seed)
    elif args.command == 'flocklab_measure_links':
        flocklab_measure_links(args.register_test, args.local)
    elif args.command == 'flocklab_measure_gloria':
        flocklab_measure_gloria(args.ack, args.register_test, args.local)
    elif args.command == 'generate_code':
        if args.path is None:
            parser.error("generate_code requires --path of Flora project.")
        else:
            generate_code(args.path)
    elif args.command == 'start_server':
        start_server()


if __name__ == '__main__':
    main()
