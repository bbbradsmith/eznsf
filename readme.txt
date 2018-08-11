      ---------------------------------------------
     /   EEEEE   ZZZZZ   N   N    SSSS   FFFFF   /
    /   E          Z    NN  N   S       F       /
   /   EEE       Z     N N N    SSS    FFF     /
  /   E        Z      N  NN       S   F       /
 /   EEEEE   ZZZZZ   N   N   SSSS    F       /
---------------------------------------------

 EZNSF is a tool for transforming NSF music files into NES ROMs
 
 Version 1.0
 Written by Brad Smith, 2016-12-05


Prerequisites:

 1. Python 3
      Available here: https://www.python.org/downloads/
 2. CC65 assembler and linker
      Available here: http://cc65.github.io/cc65/
      A windows version of CC65's assembler and linker are included in the tools folder.
      Users with other platforms can adapt the python script to use another version of CC65.
 3. NES Screen Tool
      Available here: https://shiru.untergrund.net/software.shtml
      The screen tool is helpful if you wish to modify the graphics produced by the ROM,
      but it is not needed for simply building ROMs.

Directions:

 1. Create a suitable NSF (see below for requirements).
 2. Edit album.txt with track times and names and other info.
 3. Run eznsf.py to build a ROM as "temp/output.nes".
    If there are any errors, look at the output from eznsf.py and try to fix them.
    Make sure to run eznsf.py from a command line or shell where you can read its result.
    (The included "eznsf.bat" will open a command window and pause to show the output.)

 
NSF Requirements:

 * No expansion sound.
 * Standard engine rate only (60/50 Hz)
 * NSF may not bankswitch F000
 * NSF may not use RAM (or clear it during init) in the range $600-7FF
 * NSF may not use zero page (or clear it) in the range $FC-FF
 * NSF may not depend on WRAM present at $6000-7FFF

 This program was primarily intended for use with Famitracker, which
 should normally obey all of these requirements since at least 0.4.5 if not earlier.
 It can potentially work with many other NSFs.

Notes:

 The produced ROM will use mapper 31 by default, which is a relatively new creation.
 Many old emulators will not support this. Recent versions of the following will:
   * FCEUX: http://www.fceux.com/
   * MESS: http://www.mess.org/
   * BizHawk: http://tasvideos.org/BizHawk.html
   * Nintendulator: http://www.qmtpro.com/~nes/nintendulator/
   * puNES: http://forums.nesdev.com/viewtopic.php?t=6928
   * Everdrive N8: http://krikzz.com/store/home/31-everdrive-n8-nes.html

 If the NSF does not require bankswitching (many NSFs under 32k), it may be possible to
 build as the simple NROM mapper 0, which is supported by all emulators.
 Simply create a line that says "NROM = 1" in your album.txt file.
 The NROM version will require about 3kb of empty space, so the build may fail if not
 enough room can be found. An example is included as "album_nrom.txt".

 This tool also uses the track times and names to produce an NSFe file in the output
 directory. An NSFe is like an NSF but with playlist features like individual track
 names and times. If undesired you can turn this extra step off in eznsf.py by
 setting "output_nsfe = False" near the top of the file.

 NSFs with the "dual region" bit set will attempt to auto-detect the system region on
 startup, and will pass the appropriate value to the NSF INIT function when tracks are played.
 Otherwise, the detection will be omitted and the region speciied in the NSF header will be used.

 This program is open source, and I give permission to modify and reuse it in any way you like.
 I encourage experimentation. This is hopefully intended as a learning example, and not just as
 a tool.

 The eznsf.py script can be run with two command line arguments. The first argument is the name
 of the album.txt file (if omitted it will use "album.txt"). The second argument is the output
 folder (if omitted it will use "temp").

 The sample music is from the Classic Chips album of classical music arranged for NES:
 http://rainwarrior.ca/music/classic_chips.html

 The graphics in this are configurable with album.txt, and by editing their definitions in that file.
 Take a look at the comments and experiment to see what they do. Use the NES Screen Tool
 to modify the example CHR/NAM/PAL files.

 Contact me if you have questions or comments.
 http://rainwarrior.ca

--- end of file ---
