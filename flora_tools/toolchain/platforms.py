from enum import Enum, unique

DEVKIT_FIRMWARE_PATH = "platform/devkit_sx126xdvk1xas/Debug/devkit_sx126xdvk1xas"
COMBOARD_FIRMWARE_PATH = "platform/flora_dpp_comboard/Debug/flora_dpp_comboard"
COMBOARD_STM32L433CC_FIRMWARE_PATH = "platform/flora_dpp_comboard_STM32L433CC/Debug/flora_dpp_comboard"

DEVKIT_CPROJECT_PATH = "platform/devkit_sx126xdvk1xas/.cproject"
COMBOARD_CPROJECT_PATH = "platform/flora_dpp_comboard/.cproject"
COMBOARD_STM32L433CC_CPROJECT_PATH = "platform/flora_dpp_comboard_STM32L433CC/.cproject"

DEVKIT_PROJECT_PATH = "platform/devkit_sx126xdvk1xas/.project"
COMBOARD_PROJECT_PATH = "platform/flora_dpp_comboard/.project"
COMBOARD_STM32L433CC_PROJECT_PATH = "platform/flora_dpp_comboard_STM32L433CC/.project"

DEVKIT_SYMBOLS_DEBUG = [
    'DEBUG',
    'DEVKIT',
]

DEVKIT_SYMBOLS_RELEASE = [
    'DEVKIT',
]

COMBOARD_SYMBOLS_DEBUG = [
    'DEBUG',
    'COMBOARD',
]

COMBOARD_SYMBOLS_RELEASE = [
    'COMBOARD',
]

OPTION_ITEM_TAG = {
    'name': 'listOptionValue',
    'builtIn': 'false',
    'value': "\"${{workspace_loc:/${{ProjName}}/{}}}\""
}

INCLUDE_XPATH = [
    './/toolChain/tool/option[@superClass="com.atollic.truestudio.as.general.incpath"]',
    './/toolChain/tool/option[@superClass="com.atollic.truestudio.gcc.directories.select"]'
]


@unique
class Target(Enum):
    DEBUG = 1
    RELEASE = 2


SYMBOLS_XPATH = {
    Target.DEBUG: './/toolChain[@superClass="com.atollic.truestudio.exe.debug.toolchain"]/tool[@superClass="com.atollic.truestudio.exe.debug.toolchain.gcc"]/option[@superClass="com.atollic.truestudio.gcc.symbols.defined"]',
    # DEBUG
    Target.RELEASE: './/toolChain[@superClass="com.atollic.truestudio.exe.release.toolchain"]/tool[@superClass="com.atollic.truestudio.exe.release.toolchain.gcc"]/option[@superClass="com.atollic.truestudio.gcc.symbols.defined"]'
    # RELEASE
}


@unique
class Platform(Enum):
    DEVKIT = 1
    COMBOARD = 2
    COMBOARD_STM32L433CC = 3

    @staticmethod
    def get_firmware_path(platform):
        if platform is Platform.DEVKIT:
            return DEVKIT_FIRMWARE_PATH
        elif platform is Platform.COMBOARD:
            return COMBOARD_FIRMWARE_PATH
        elif platform is Platform.COMBOARD_STM32L433CC:
            return COMBOARD_STM32L433CC_FIRMWARE_PATH

    @staticmethod
    def get_cproject_path(platform):
        if platform is Platform.DEVKIT:
            return DEVKIT_CPROJECT_PATH
        elif platform is Platform.COMBOARD:
            return COMBOARD_CPROJECT_PATH
        elif platform is Platform.COMBOARD_STM32L433CC:
            return COMBOARD_STM32L433CC_CPROJECT_PATH

    @staticmethod
    def get_project_path(platform):
        if platform is Platform.DEVKIT:
            return DEVKIT_PROJECT_PATH
        elif platform is Platform.COMBOARD:
            return COMBOARD_PROJECT_PATH
        elif platform is Platform.COMBOARD_STM32L433CC:
            return COMBOARD_STM32L433CC_PROJECT_PATH

    @staticmethod
    def get_symbols(platform, target: Target):
        if platform is Platform.DEVKIT:
            if target is Target.DEBUG:
                return DEVKIT_SYMBOLS_DEBUG
            elif target is Target.RELEASE:
                return DEVKIT_SYMBOLS_RELEASE
        elif platform is Platform.COMBOARD:
            if target is Target.DEBUG:
                return COMBOARD_SYMBOLS_DEBUG
            elif target is Target.RELEASE:
                return COMBOARD_SYMBOLS_RELEASE
        elif platform is Platform.COMBOARD_STM32L433CC:
            if target is Target.DEBUG:
                return COMBOARD_SYMBOLS_DEBUG
            elif target is Target.RELEASE:
                return COMBOARD_SYMBOLS_RELEASE
