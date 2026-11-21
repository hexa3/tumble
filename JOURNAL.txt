how it went

sat 14 nov, night (5h)

set up the project for the tiny 8 pin chip. platformio didnt even have it so i made my own board file. got i2c and the accelerometer talking.

the whole thing with the mk i was it used an 8 pin chip, so i made that a rule for tumble too. picked the stm32g041j6 in so-8 and went bare metal on cmsis. the catch is u only get 6 pins to use: one for the noise adc, one for the uart to the usb chip, two for i2c (and the led driver, accelerometer, motor driver and battery gauge all share that one bus), and the two debug pins, which i also need for the noise switch and the accelerometer interrupt. so thats two pins short, which i fixed on monday.

what i did:

wrote my own board json cuz the so-8 version isnt in platformio
got the clock up to 64mhz with a 1ms tick
made an i2c bus interface so the drivers never touch registers directly. one of the best calls in the whole project cuz later the entire app could run with zero hardware
i2c at 400khz and a basic lis3dh driver
first bug!! i2c kept timing out. the timeout loop was 4000 and at 64mhz that runs out before a slow transfer finishes. bumped it to 40000
single wire uart for the usb bridge

one annoying thing: putting the uart on pa2 also eats the reset pin, so i have to set it to gpio in the option bytes over swd one time. havent done it yet cuz no boards yet.

sun 15 nov, afternoon (2.5h)

made the pips into physics discs. first demo at like 2:25pm, tilt it and they roll!! then spent ages making it feel right cuz they were floaty and shaking slammed them into the walls.

the big idea: each pip feels the opposite of what the accelerometer reads. thats literally what a loose ball in a box feels, so tilting AND shaking both just work with no special cases. tilt has a gentle gain so the pips drift, and shake has a big one so they get thrown.

what i did:

7 pips as discs bouncing in an 11x11 box
drew them with a soft edge so u can see them move even less than one led, plus a cheap gamma curve so dim pixels never vanish
is31fl3733 led driver
FIRST DEMO. tilt it and the pips roll!!
the accelerometer numbers were 16x too big. turns out its 12 bit and left justified so u gotta divide by 16
pips felt floaty so i doubled the drag
pips can hit each other now
shaking slammed everything into the walls so i halved the shake strength and it felt way better

nothing bounces forever cuz every hit loses some energy. every hit also reports how hard it was, which i used later for the motor ticks.

sun 15 nov, night (4.5h)

did all the randomness stuff til 2:30am. hashing, chacha20, health checks on the noise. the idea is u can actually check its fair instead of just trusting me.

how it works: raw noise from the avalanche thing goes through the sp 800-90b health tests (they check the noise isnt stuck or repeating), then gets mixed into a blake2s pool with the chips own random generator and the accelerometer's noisy bits. once theres enough entropy it makes a new chacha20 key from the pool + the old key, and the rolls come out of that.

what i did:

blake2s and chacha20
my blake2s was WRONG. it was compressing the last block too early. i only caught it by checking against the official test vector. the output still looked totally random which is kinda scary
the pool, reseeding and fair rolls (no number more likely than another)
the two health tests
dice rolled 0 to 5 instead of 1 to 6 lol
tried removing the old key from the reseed to test a thought, put it straight back. chaining the old key in is the whole point
adc to read the noise, and the chips own generator as a backup

im being careful about how much i trust the noise. each sample only counts as half a bit until i measure the real thing. if the noise source dies the backup takes over so the die still works, and a little dot shows up to say somethings wrong.

mon 16 nov (3.5h)

made the actual dice part. it lands, picks a number, pips spring into place. added double tap to change dice.

also solved the pins problem. for the first 2 seconds after it turns on, the two debug pins stay debug pins so i can plug in a programmer. after that they switch to the noise switch and the accelerometer interrupt. the noise source cant turn on during those 2 seconds, so it just uses the backup generator.

the whole app has zero hardware in it. u give it accelerometer readings 200 times a second and it gives back the leds, how hard to buzz, and whether to sleep. so it could run on my laptop too.

what i did:

settle mode: the pips spring into the right face and the extra ones fade out
the debug pin switch after boot
the state machine: show, tumble, settle, back to show, plus mode, fade and sleep
it counted as a shake way too easily so i made it less sensitive
made it land a bit faster
little 3x5 digits for the dice that arent d6
double tap to switch dice
couldnt get to d100. i wrapped the modes with % 6 but theres 7 dice

shaking while its settling starts a new roll. the result stays up 8 seconds, fades out, then it sleeps.

tue 17 nov, morning (3.5h)

motor ticks when pips hit stuff and a big thud when it lands. made it sleep and wake up when u pick it up.

what i did:

drv2605l motor driver
little ticks when pips hit things (not too often so it doesnt buzz nonstop) and a full power thud when it lands
the motor freaked out cuz the register is signed. capped it at 127
made the build print memory usage cuz 32kb of flash is TIGHT
accelerometer wake on motion
deep sleep that wakes up on the accelerometer
turns out it never actually went to sleep, i left a fake stub in there. fixed for real now
if u put it face down it goes straight to sleep

before sleeping it turns everything off or into low power. it stays awake while usb is plugged in.

tue 17 nov, night (2h)

battery gauge, a little warning dot, and a serial thing so u can dump raw noise and test the randomness urself. firmware done!

what i did:

max17048 battery gauge
under 5% the corner dot blinks and it wont roll
dim corner dot if the noise source dies
the serial commands: raw (dumps noise samples), roll (rolls a bunch of times with a reseed before each), health (shows if the noise is ok) and dfu (empty for now lol)

fun trick: the usb chip only holds the serial line high when its powered, so that same line tells the die if usb is plugged in. no extra pin needed.

firmware done at about 21 hours.

wed 18 nov, night (5h)

started on the boards. i didnt want to draw them by hand so i wrote python that makes the kicad files for me.

the rule: nothing gets placed or routed by hand. ever.

what i did:

a tiny reader and writer for kicads file format
a parts list with digikey prices, where each part says how much i checked it so i know what to double check before ordering
schematic writer, everything connects by label
pcb builder: footprints, placing, tracks, vias, board outline, silkscreen. the vias and outline part took the longest
files were huge so i cut the decimals
footprints kicad doesnt have, like the spring pins, a tiny package for the accelerometer, the motor pads and the gold dots

thu 19 nov (11h)

woke up at 5am and just went. ported my old router from tinydie v1, built all 3 boards, made the gerbers and stuff for jlc and released it at 3:46pm. 28 commits in one day lol

first the router. its an a* router on a grid that hates turns and vias. new for tumble: rectangle boards, keep out zones, and it can start from copper thats already there, so i lay the neat buses first and a* just fills the gaps. drc wanted a bit more space between holes so i bumped that.

then the stuff all 3 boards share. 50x50mm with round corners, 4 mounting holes, and ten spring pins in the exact same spots on every board so they connect when stacked.

then the face board, the hardest one. 11 leds at the normal 2.54mm spacing dont fit, so i went to 2.4mm. the grid is woven: rows on the top (u can see them on the face) and columns on the bottom, and every single line is placed by code, not the router. then the led driver didnt fit under the leds so EVERY board went from 45mm to 50mm. one line change tho cuz theyre all generated.

core and base went way faster. core has everything on top facing the leds so the bottom stays flat for the battery. base has usb-c and the battery bay, and the back is the caseback with 6 gold pads laid out like the "6" face for programming, plus the mk i outline.

last was the fab stuff:

cheaper lcsc parts where i could
jlc part picks and a list of stuff i have to hand solder
gerbers, bom and pick and place files
forgot the board outline in the gerbers. jlc wouldnt have known what shape to cut
the kicad project template never got committed so nobody else couldve built it
the usb chip was missing its label in the jlc bom
a build script that makes all 3 boards, runs drc, exports everything and renders pictures
RELEASED. all 3 boards
