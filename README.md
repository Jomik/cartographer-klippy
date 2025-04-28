# Cartographer3D WIP

> [!CAUTION]
> This is currently being alpha tested and is not ready for production use.
> Use at your own risk.

## Upgrading

You can upgrade via Update Manager in [Mainsail](https://docs.mainsail.xyz/) or [Fluidd](https://docs.fluidd.xyz/).
Alternatively upgrade by using pip to install the latest version of the plugin from [pypi](https://pypi.org/project/cartographer3d-plugin/).

```sh
 ~/klippy-env/bin/pip install --upgrade cartographer3d-plugin
```

## Install

This will attempt to install the cartographer plugin.
Default assumes that klipper is in `~/klipper` and the klippy venv is in `~/klippy-env`.
This should be standard on [KIAUH](https://github.com/dw-0/kiauh) and [MainsailOS](https://docs-os.mainsail.xyz/).

```sh
curl -s -L https://raw.githubusercontent.com/Cartographer3D/cartographer3d-plugin/refs/heads/main/scripts/install.sh | bash -s
```

### Customize paths

```sh
curl -s -L https://raw.githubusercontent.com/Cartographer3D/cartographer3d-plugin/refs/heads/main/scripts/install.sh | bash -s -- --klipper ~/klipper --klippy-env ~/klippy-env
```

### View script options

```sh
curl -s -L https://raw.githubusercontent.com/Cartographer3D/cartographer3d-plugin/refs/heads/main/scripts/install.sh | bash -s -- --help
```

## Uninstall

```sh
curl -s -L https://raw.githubusercontent.com/Cartographer3D/cartographer3d-plugin/refs/heads/main/scripts/install.sh | bash -s -- --uninstall
```

## Macros

`PROBE`, `PROBE_ACCURACY`, `QUERY_PROBE`, `TOUCH`, `TOUCH_ACCURACY` and `TOUCH_HOME`.

`Z_OFFSET_APPLY_PROBE` is supported for baby-stepping z offset.
`BED_MESH_CALIBRATE` has a default `METHOD=scan` which does the rapid scan.

### Calibration

`SCAN_CALIBRATE` to calibrate the frequency response from the probe.
Initial calibration must be done manual.
Once `TOUCH` is calibrated,
a second calibration can be done with `SCAN_CALIBRATE METHOD=touch`.

`TOUCH_CALIBRATE` requires that the printer is home.

`TOUCH_AXIS_TWIST_COMPENSATION` for using touch to calculate twist compensation

## Configuration

### Moonraker

Add this section to `moonraker.conf`

```conf
[update_manager cartographer_alpha]
type: python
channel: dev
virtualenv: ~/klippy-env
project_name: cartographer3d-plugin
is_system_service: False
managed_services: klipper
info_tags: desc=Cartographer Alpha
```

### Klipper config

Include this in your `printer.cfg`

```cfg
[stepper_z]
endstop_pin: probe:z_virtual_endstop

[mcu cartographer] # See https://www.klipper3d.org/Config_Reference.html#mcu
serial: ...
canbus_uuid: ...
restart_method: command

[cartographer]
mcu: cartographer
x_offset: ...
y_offset: ...
verbose: yes # For extra output

[temperature_sensor cartographer]
sensor_type: temperature_mcu
sensor_mcu: cartographer
min_temp: 5
max_temp: 105

[temperature_sensor cartographer_coil]
sensor_type: cartographer_coil
min_temp: 5
max_temp: 140
```
