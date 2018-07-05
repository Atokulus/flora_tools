# Installation Guide

Install Python 3, aswell as the `numpy`, `pyvisa` and `pyserial` library

```sh
pip install numpy && \
pip install pyvisa && \
pip install pyserial && \
```


## Mass programming DevKits (STM32L476RG) and Comboards (STM32L443CC) with built-in ROM UART-Bootloader

Using the `stm32loader` library for Python 3 (by *florisla*), all SX126xDVK1xAS devkits and DPP-Comboard modules can be programmed simultaneously. The library is available as a git submodule inside the `flora_tools` directory, and has been cloned aswell when you cloned the `flora_tools` project.

Ensure you have closed all your serial-port connections to your DevKits or ComBoards.

You can now either put the MCU into bootloader mode by pullin BOOT0-pin high (connect with VCC) or use the dedicated FlOS CLI command `system bootloader` to jump
into the ROM bootloader. The second option is automatically supported by the Python script `programmer.py`. Check that you have compiled and built your Atollic project correctly and have a `.hex` file the `Outputs` folder. Then run:

```sh
	python ./flora_tools/programmer.py
```

## Measurement setup

#### Precise timing measurements

![Setup to measure precise timings](../../../doc/img/measurements-cable_setup.png)

#### FlockLab

To be integrated!


### Measurements over GPIB/LXI/VISA
For a working PyVISA installation for interfacing with the oscilloscope and power analyzers you need to follow this [guide](https://pyvisa.readthedocs.io/en/stable/getting_nivisa.html). For Windows, you can download the following VISA backend driver: (http://www.ni.com/download/ni-visa-18.0/7597/en/)

Use NI MAX to configure all your devices.

### Tektronix MSO4104B oscilloscope

First, upgrade your oscilloscope to the lates firmware version, as the `HORIZONTAL:RECORDLENGTH` command won't work otherwise.

Connect your oscilloscope to LAN via a Ethernet.

Push the `Utility` button and switch to the `Utility Page` `I/O`. Select `Ethernet & LXI`. Disable the `e*Scope Password`. Set the `Network Configuration` (bottom) to `Automatic` to get a DHCP lease.

Add your Tektronix MSO4104B oscilloscope in NI MAX. You have to note down the VISA Resource Name.


