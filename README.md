# About `flora_tools`

The `flora_tools` package provides the tools and means for developing on the new PermaSense DPP2-LoRa communication boards 
with `flora` firmware, facilitating the LoRa radio SX1262 from Semtech.

Module | Description
------ | -----------
`flora_tools`             | General resources, such as the static calculation of Time-on-Air, Gloria & LWB figures, <br />basic interfacing via serial/UART, and interface for the Tektronix oscilloscope to measure the timings precisely
`flora_tools.analysis`    | Jupyter notebooks for condensed visual representation.
`flora_tools.codegen`     | Codegenerator for `flora` firmware project
`flora_tools.experiments` | All scripted experiments, utilizing e.g. the oscilloscope
`flora_tools.sim`         | The simulation server for the protocol layers
`flora_tools.stm32loader` | The script which implements the STM32's UART ROM-bootloader protocol
`flora_tools.toolchain`   | The scripts for flashing and maintaining the firmware projects
`flora_tools.trace_visualizer` | Web-based trace visualizer for simulation (reads `.json` trace file)

# Installation Guide

Install Python3.7+ and pip 10.0+. E.g. if your are using Ubuntu 18.04, run `sudo apt install python 3.7`. Then you can install the pip package `flora-tools`

```sh
python -m pip install flora-tools
```

If you run into problems, try `python3.7 -m pip` or `pip3`, as there are still many old distributions around. Also, if the Pip packages in question might not be available prebuilt from PyPi for Windows, try https://www.lfd.uci.edu/~gohlke/pythonlibs

### Run the Script ###

Use 

```sh
python -m flora-tools  # With a dash!
```

or just

```
flora_tools  # With an underscore!
```

### Development ### 

Do not install the Python package from PyPi, but rather clone this repository and run

```sh
git submodule update --init --recursive
python -m pip install -e .
```

inside the top folder (where `setup.py` is located). You can edit the source files and the module will reflect the changes automatically.

The python package is generated and uploaded according to (https://packaging.python.org/tutorials/packaging-projects/).
Do not forget to clone the git submodules as well.


## Patch Atollic TrueStudio Eclipse Project Files
As there are no external include paths and symbols configured in a freshly generated Atollic TrueStudio project, the project's XML files have to be patched.

Just run

```sh
python -m flora-tools patch_eclipse -d path/to/flora_repository
```

## Convert ELF to Base64

Just run

```sh
python -m flora-tools convert_elf -d path/to/flora_repository
```

To convert all flora firmware `.elf` files to `.base64` for inclusion into FlockLab's XML test files.


## Mass programming/flashing DevKits (STM32L476RG) and Comboards (STM32L443CC, STM32L433CC) with built-in ROM UART-Bootloader

Using the `stm32loader` library for Python 3 (originally by *florisla*), all SX126xDVK1xAS devkits and DPP-Comboard modules can be programmed simultaneously. The library is available as a git submodule inside the `flora-tools` python package.

Ensure you have closed all your serial-port connections to your DevKits or ComBoards.

You can now either put the MCU into bootloader mode by pullin BOOT0-pin high (connect with VCC), set the J502 & J503 solder bridges on the DPP carrier board, or use the dedicated FlOS CLI command `system bootloader` inside *flora CLI* to jump directly into the ROM bootloader. All variant are supported automatically by the command below.

Check that you have compiled and built your Atollic project correctly and have a `*.hex` or `*.binary` file inside the `Outputs` folder. Then run the following command with the correct path (i.e. where the `platform` and `lib` folder are located).:

```sh
python -m flora-tools program_all -d path/to/flora_repository
```

## Programming single Device
```sh
python -m flora-tools program -d path/to/firmware(.hex/.binary) -p COM1
```

## Simulation

To run the simulation use

```bash
python -m flora-tools run_simulation -d ./output -t 300
```

Which runs the simulation for 300 seconds and saves the `simulation_trace.json` inside the `output` folder.

To evaluate the trace file, run

```bash
python -m flora-tools start_server
```

And open `http://127.0.0.1:5000/` in a modern ECMAscript 7/2016 compliant browser (e.g. Chrome 69 as of September 2018).

Select the `simulation_trace.json` file to open in the web application. You can zoom and pan the view by mouse. Select 
a time interval via the right mouse button to get some statistics (all trace rectangles have to be 
fully enclosed by the selection).

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

### Update Targets
You have to update the serial device names inside `flora_tools/bench.py`

#### Windows

On Windows the paths might look like

```python
DEVKIT_A_PORT = "COM5"
DEVKIT_B_PORT = "COM12"
DEVKIT_C_PORT = "COM12"
DEVKIT_D_PORT = "COM5"
```

Use the *Device Manager* to list all serial ports.

#### Linux

On Linux the paths might look like

```python
DEVKIT_A_PORT = "/dev/ttyUSB0"
DEVKIT_B_PORT = "/dev/ttyUSB1"
DEVKIT_C_PORT = "/dev/ttyUSB2"
DEVKIT_D_PORT = "/dev/ttyUSB3"
```

Run 

```bash
ls -l /sys/bus/usb-serial/devices
``` 

to list all USB-based serial ports. 

### Run an Experiment

You can write your own Python script. E.g. 

```python
from flora_tools.bench import TimingBench
from flora_tools.experiments.measure_time_tx2sync import MeasureTimeTx2Sync

if __name__ == "__main__":
    with TimingBench(devkit_count=2) as bench:
        MeasureTimeTx2Sync().run(bench)
```

which will run measurements regarding `HeaderValid`/`SyncwordDetected` IRQ synchronization offset and accuracy which can be analyzed inside `flora_tools/analysis/analyze_time.ipynb`.

For this example you have to connect the `NSS` line of DevKit A and `DIO1` IRQ line of DevKit B to the oscilloscope (channel 1 & 2 respectively).

See the master thesis's appendix ('Timing Measurements') for further information regarding the different tests and connection. 
See https://os.mbed.com/components/SX126xDVK1xAS/#Pinout regarding the pinout of the development kits.

## FlockLab Integration

You can register a new test with the `flora_tools.flocklab.FlockLab` class (see the source).

### Measure Links

A test and measurement setup for the different transmission modes regarding pure single-hop communication is available (`flora_tools/flocklab/measure_links.py`), which builds a connectivity map (`flora_tools/analyze_links.ipynb`).

Run 

```bash 
python -m flora-tools flocklab_measure_links
```

Several options are available:

Option | Description
------ | -----------
`-r` | Register a test on the FlockLab and schedule the measurements.
`-l` | Also run tests with locally connected development kits.

To visualize the connectivity map, copy the serial log of FlockLab to the designated data file (i.e. `flora_tools/data/MeasureFlockLabLinks_serial.csv`), open `flora_tools/analyze_flocklab_gloria.ipynb` inside Jupyter.

### Measure Gloria

A test and measurement setup for the different transmission modes regarding Gloria floods is available (`flora_tools/flocklab/measure_gloria.py`), which builds 
a connectivity map (`flora_tools/analyze_flocklab_gloria.ipynb`).

Run 

```bash 
python -m flora-tools flocklab_measure_gloria
```

Several options are available:

Option | Description
------ | -----------
`-a` | Enable Gloria Ack (a random destination node will be selected for every flood).
`-r` | Register a test on the FlockLab and schedule the measurements.
`-l` | Also run tests with locally connected development kits.

To visualize the connectivity map, copy the serial log of FlockLab to the designated data file (i.e. `flora_tools/data/MeasureFlockLabGloria_serial.csv` 
or `flora_tools/data/MeasureFlockLabGloriaAck_serial.csv`), open `flora_tools/analyze_flocklab_gloria.ipynb` inside Jupyter.

## Contact
The latest version of flora-tools is available on PyPI and GitHub. The online documentation will be available in the future on Read The Docs and includes a changelog. For bug reports please create an issue on GitHub. If you have questions, suggestions, etc. feel free to send me an email to mw@technokrat.ch.

##License
This software is licensed under the MIT license.

© 2018 Markus Wegmann
