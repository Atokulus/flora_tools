import argparse
from multiprocessing import Pool

from flora_tools.toolchain.bootloader import Bootloader
from flora_tools.toolchain.programmer import Programmer
from flora_tools.toolchain.platforms import Platform

from flora_tools.toolchain.eclipse_patcher import EclipsePatcher


def program_all_devices(flora_path):
    bootloaders = Bootloader.get_all()

    if len(bootloaders):
        with Pool(len(bootloaders)) as p:
            arguments = [{'flora_path': flora_path, 'bootloader': bootloader} for bootloader in bootloaders]
            p.map(Programmer.program_on_bootloader, arguments)
            print("Programming finished.")


def patch_eclipse(flora_path):
    devkit_patcher = EclipsePatcher(flora_path, Platform.DEVKIT)
    devkit_patcher.patch()
    comboard_patcher = EclipsePatcher(flora_path, Platform.COMBOARD)
    comboard_patcher.patch()
    comboard_patcher = EclipsePatcher(flora_path, Platform.COMBOARD_STM32L433CC)
    comboard_patcher.patch()



if __name__ == '__main__':
    parser = argparse.ArgumentParser(description = 'flora_tools main entry')
    parser.add_argument('command', help='Execute given command', choices=['program_all', 'patch_eclipse'])
    parser.add_argument('flora_path', help='Set the path to the Flora main repository folder')
    args = parser.parse_args()

    if args.command == 'program_all':
        program_all_devices(args.flora_path)
    elif args.command == 'patch_eclipse':
        patch_eclipse(args.flora_path)

