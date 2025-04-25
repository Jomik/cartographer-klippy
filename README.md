# Cartographer3D

[![codecov](https://codecov.io/gh/Jomik/cartographer-klippy/graph/badge.svg?token=B3APHO301B)](https://codecov.io/gh/Jomik/cartographer-klippy)

## Upgrading

You can upgrade by calling pip to install the latest version of the plugin from [pypi](https://pypi.org/project/jomik-cartographer/).

```sh
 ~/klippy-env/bin/pip install --upgrade jomik-cartographer
```

We are waiting for [Mainsail](https://docs.mainsail.xyz/) and [Fluidd](https://docs.fluidd.xyz/) to release a version with support.
The pull requests have been made and some merged.

## Install

This will attempt to install the cartographer plugin.
Default assumes that klipper is in `~/klipper` and the klippy venv is in `~/klippy-env`.
This should be standard on [KIAUH](https://github.com/dw-0/kiauh) and [MainsailOS](<https://docs-os.mainsail.xyz/>.

```sh
curl -s -L https://raw.githubusercontent.com/Jomik/cartographer-klippy/refs/heads/main/scripts/install.sh | bash -s
```

### Customize paths

```sh
curl -s -L https://raw.githubusercontent.com/Jomik/cartographer-klippy/refs/heads/main/scripts/install.sh | bash -s -- --klipper ~/klipper --klippy-env ~/klippy-env
```

### View script options

```sh
curl -s -L https://raw.githubusercontent.com/Jomik/cartographer-klippy/refs/heads/main/scripts/install.sh | bash -s -- --help
```

## Uninstall

```sh
curl -s -L https://raw.githubusercontent.com/Jomik/cartographer-klippy/refs/heads/main/scripts/install.sh | bash -s -- --uninstall
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
