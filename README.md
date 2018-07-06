# About `flora_tools`

The `flora_tools` package provides the tools and means for developing on the new PermaSense flora DPP2 Comboards, facilitating the LoRa radio SX1262 from Semtech.

Module | Description
------ | -----------
`flora_tools`             | General resources, such as the static calculation of time-on-air, Gloria & LWB figures, <br />basic interfacing via serial/UART, and interface for the Tektronix oscilloscope to measure the timings precisely
`flora_tools.experiments` | All scripted experiments, utilizing e.g. the oscilloscope
`flora_tools.analysis`    | Jupyter notebooks for condensed visual representation.
`flora_tools.sim`         | The simulation server for the protocol layers
`flora_tools.toolchain`   | The scripts for flashing and maintaining the firmware projects
`flora_tools.stm32loader` | The script which implements the STM32's UART ROM-bootloader protocol

# Installation Guide

Install Python3.6+ and pip 10.0+. If your are using Ubuntu 18.04, these are already installed. Then you can install the pip package `flora-tools`

```sh
python -m pip install flora-tools
```

If you run into problems, try `python3 -m pip` or `pip3`, as there are still many old distributions around.

### Run The script ###

Use 

```sh
python -m flora-tools  # With a dash!
```

or just

```
flora_tools  # With an underscore!
```

### Development ### 

Do not install the python package from PyPi, but rather clone this repository and run

```sh
python -m pip install -e .
```

inside the top folder (where `setup.py` is located). You can edit the source files and the module will reflect the changes automatically.

The python package is generated and uploaded according to (https://packaging.python.org/tutorials/packaging-projects/)


## Patch Atollic TrueStudio Eclipse Project Files
As there are no external include paths and symbols configured in a freshly generated Atollic TrueStudio project, the project's XML files have to be patched.

Just run

```sh
python -m flora-tools patch_eclipse path/to/flora_repository
```


## Mass programming/flashing DevKits (STM32L476RG) and Comboards (STM32L443CC, STM32L433CC) with built-in ROM UART-Bootloader

Using the `stm32loader` library for Python 3 (originally by *florisla*), all SX126xDVK1xAS devkits and DPP-Comboard modules can be programmed simultaneously. The library is available as a git submodule inside the `flora-tools` python package.

Ensure you have closed all your serial-port connections to your DevKits or ComBoards.

You can now either put the MCU into bootloader mode by pullin BOOT0-pin high (connect with VCC), set the J502 & J503 solder bridges on the DPP carrier board, or use the dedicated FlOS CLI command `system bootloader` inside *flora CLI* to jump directly into the ROM bootloader. All variant are supported automatically by the command below.

Check that you have compiled and built your Atollic project correctly and have a `*.hex` or `*.binary` file inside the `Outputs` folder. Then run the following command with the correct path (i.e. where the `platform` and `lib` folder are located).:

```sh
	python -m flora-tools program_all path/to/flora_repository
```

## Programming single Device
```sh
	python -m flora-tools program path/to/firmware(.hex/.binary) -p COM1
```

## Measurement setup

### Precise timing measurements

![Setup to measure precise timings](/doc/img/measurements-cable_setup.png)

### Measurements over GPIB/LXI/VISA
For a working PyVISA installation for interfacing with the oscilloscope and power analyzers you need to follow this [guide](https://pyvisa.readthedocs.io/en/stable/getting_nivisa.html). For Windows, you can download the following VISA backend driver: (http://www.ni.com/download/ni-visa-18.0/7597/en/)

Use NI MAX to configure all your devices.

### Tektronix MSO4104B oscilloscope

First, upgrade your oscilloscope to the lates firmware version, as the `HORIZONTAL:RECORDLENGTH` command won't work otherwise.

Connect your oscilloscope to LAN via a Ethernet.

Push the `Utility` button and switch to the `Utility Page` `I/O`. Select `Ethernet & LXI`. Disable the `e*Scope Password`. Set the `Network Configuration` (bottom) to `Automatic` to get a DHCP lease.

Add your Tektronix MSO4104B oscilloscope in NI MAX. You have to note down the VISA Resource Name.

## FlockLab Integration

*To be integrated.*
