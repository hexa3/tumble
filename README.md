# tumble

its a dice but the pips act like real little discs. tilt it and they roll around, shake it and they bounce off the walls. when u stop shaking it picks a random number, the pips jump into that face and a motor goes thud.

it does d4, d6, d8, d10, d12, d20 and d100. double tap the face to switch.

tumble is the sequel to tinydie mk i (an attiny412 with 7 leds on a coin cell). when it turns on the pips start in the mk i's "7" pattern, and theres a gold outline of the old chip on the back cuz i love that little guy.

## whats inside

its 3 boards stacked up, 50x50mm each:

- **face**: 121 tiny leds in an 11x11 grid, run by an is31fl3733b
- **core**: the brain. an 8 pin stm32g041j6, a lis3dh accelerometer, a drv2605l with a buzzy motor, and an avalanche noise thing for randomness
- **base**: usb-c, battery charging, an mcp2221a for usb serial, a max17048 battery gauge and the battery

## is it actually fair

ya and u can check it urself. the noise goes through health tests (sp 800-90b) so it cant be stuck, then gets mixed into a blake2s pool that feeds chacha20, and the rolls come out of that. if the noise thing dies it switches to the chips own random generator and a little dot shows up in the corner.

plug it into usb and open serial at 115200:

```
raw N       dumps N raw noise samples
roll N S    rolls an S sided die N times, reseeding before each one
health      shows if the noise is ok
```

## building it

**firmware** (`firmware/`): its platformio. the so-8 chip isnt in platformio so theres my own board file in `boards/tumble_g041j6.json`. heads up: the debug pins turn into other stuff after boot, so u only have 2 seconds after reset to plug in a programmer.

**boards** (`hardware/`): run `build.sh`. it makes all 3 boards, runs drc (stops if anything fails), and spits out gerbers, boms, jlc files and pictures into `hardware/release/`. u need kicad 10 and the system python.

## what i still need to do

build it :)
