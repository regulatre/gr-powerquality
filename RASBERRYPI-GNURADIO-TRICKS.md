to: Marcus Leech (build-gnuradio script maintainer)
subject: build-gnuradio on a Raspberry Pi
date: 2017-12-28


```
My Raspberry Pi's are running Debian 8 (Raspbian image).

To get gnuradio to compile, I invariably have to modify the build-gnuradio script and replace the version check parameter from 8.3* to 8* and voila, it works.


Sample errored output having not modified the script at all

Unsupported Debian version 8.0

=======================================================================
If you have found this script useful and time-saving, consider a
donation to help me keep build-gnuradio, simple_ra, SIDsuite,
meteor_detector, simple_fm_rcv, and multimode maintained and up to date.
A simple paypal transfer to mleech@ripnet.com is all you need to do.
======================================================================
Send success/fail info to sbrac.org?Thanks


After modification

# diff build-gnuradio-original build-gnuradio-forPi
677c677
<         *8.3*)
---
>         *8*)

Furthermore, I'm also able to use your script on the Raspberry Pi Nano if I make the above change, as well as the following (modify the volk asm file to avoid a certain instruction not supported by the Pi nano):

# diff original---volk_32f_x2_dot_prod_32f_neonasm_opts.s  volk_32f_x2_dot_prod_32f_neonasm_opts.s
46c46,50
<      sbfx       r11, r1, #2, #1 @ check alignment
---
> @ BH https://lists.gnu.org/archive/html/discuss-gnuradio/2016-01/msg00234.html
> @     sbfx       r11, r1, #2, #1 @ check alignment
>      mov    r11,#0
>      tst    r1,#4
>      movne    r11,#15



Keep up the good work - I hope this feedback helps others!
```

