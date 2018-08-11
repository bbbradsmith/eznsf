#!/usr/bin/env python3
import sys

if sys.version_info[0] < 3:
    print("Python 3 required.")
    sys.exit(1)

#
# EZNSF
#
# bradsmith, 2016
# http://rainwarrior.ca
#

import os
import datetime
import shlex
import subprocess

album = "album.txt"
outdir = "temp"
ca65 = "tools/ca65.exe"
ld65 = "tools/ld65.exe"
output_nsfe = True

def errmsg(msg):
    print("Error: " + msg)
    sys.exit(1)

if len(sys.argv) > 1:
    album = sys.argv[1]
if len(sys.argv) > 2:
    outdir = sys.argv[2]
if len(sys.argv) > 3:
    errmsg("Error: Too many arguments on command line.\n" + \
        "Usage: eznsf.py [album] [directory]")

now_string = datetime.datetime.now().strftime("%a %b %d %H:%M:%S %Y")

nsf_file = ""
nsf_nrom = 0
nsf_title = ""
nsf_artist = ""
nsf_copyright = ""
nsf_tracks = []
nsf_screens = []
nsf_info = []
nsf_coord = []
nsf_const = []

# STEP 0: create output directory and remove files to be generated

try:
    os.makedirs(outdir)
except OSError:
    if not os.path.isdir(outdir):
        raise

for file in os.listdir(outdir):
    if \
          file.endswith(".bin") \
       or file.endswith(".sh") \
       or file.endswith(".o") \
       or file.endswith(".nes") \
       or file.endswith(".map") \
       or file.endswith(".lab") \
       or file.endswith(".nsfe") \
       :
        path = os.path.join(outdir,file)
        try:
            os.remove(path)
        except:
            errmsg("Unable to remove temporary file: " + path)

# STEP 1: parse album file

try:
    album_lines = open(album,"rt").readlines()
except:
    errmsg("Unable to read album file: " + album)

for i in range(len(album_lines)):
    def line_error(msg):
        errmsg(("Line %d: " % (i+1)) + msg)
    l = album_lines[i]
    # strip comments
    comment = l.find("#")
    if comment >= 0:
        l = l[0:comment]
    # strip trailing whitespace and newline
    l = l.rstrip()
    # process line
    try:
        tokens = shlex.split(l)
    except Exception as e:
        line_error("shlex parsing error: " + str(e))
    if (len(tokens) < 1):
        continue # skip blank lines
    c = tokens[0]
    if c == "NSF":
        nsf_file = l[l.find(c)+len(c)+1:] # line to end
    elif c == "NROM":
        if len(tokens) != 2:
            line_error("NROM expects one argument.")
        if tokens[1] != "0" and tokens[1] != "1":
            line_error("NROM expects 0 or 1.")
        nsf_nrom = int(tokens[1])
    elif c == "TITLE":
        nsf_title = l[l.find(c)+len(c)+1:] # line to end
    elif c == "ARTIST":
        nsf_artist = l[l.find(c)+len(c)+1:] # line to end
    elif c == "COPYRIGHT":
        nsf_copyright = l[l.find(c)+len(c)+1:] # line to end
    elif c == "TRACK":
        if len(tokens) < 3:
            line_error("TRACK expects a time and song argument.")
        time = tokens[1]
        tnum = tokens[2]
        track = l[l.find(tnum,l.find(time)+len(time))+len(tnum)+1:] # line to end
        time_mins = "0"
        time_secs = time
        colon = time.find(":")
        if colon >= 0:
            time_mins = time[0:colon]
            time_secs = time[colon+1:]
        try:
            mins = int(time_mins)
            secs = int(time_secs)
            num = int(tnum)
            if (num < 1):
                line_errot("TRACK song number may not be less than 1.")
            nsf_tracks.append((track,num-1,mins,secs))
        except:
            line_error("Unable to read time or track argument for TRACK.")
    elif c == "SCREEN":
        if len(tokens) != 7:
            line_error("SCREEN expects 6 arguments.")
        nsf_screens.append((tokens[1],tokens[2],tokens[3],tokens[4],tokens[5],tokens[6]))
    elif c == "INFO":
        nsf_info.append(l[l.find(c)+len(c)+1:]) # line to end
    elif c == "COORD":
        if len(tokens) != 4:
            line_error("COORD expects 3 arguments.")
        coord = tokens[1]
        try:
            coord_x = int(tokens[2])
            coord_y = int(tokens[3])
            nsf_coord.append((coord,coord_x,coord_y))
        except:
            line_error("Unable to read number argument for COORD.")
    elif c == "CONST":
        if len(tokens) != 3:
            line_error("CONST expects 2 arguments.")
        ct = tokens[1]
        try:
            cv = int(tokens[2])
            nsf_const.append((ct,cv))
        except:
            line_error("Unable to read number argument for CONST.")
    else:
        line_error("Unknown statement type.")
    #print("%d: %s" % (i+1, l)) # diagnostic

print("album info:")
print("  file: " + nsf_file)
print("  title: " + nsf_title)
print("  artist: " + nsf_artist)
print("  copyright: " + nsf_copyright)
print("  tracks: %d" % len(nsf_tracks))
print("  screens: %d" % len(nsf_screens))
print("  info lines: %d" % len(nsf_info))
print("  coordinates: %d" % len(nsf_coord))
print("  constants: %d" % len(nsf_const))
print()

# STEP 2: parse and package NSF

try:
    nsf = open(nsf_file,"rb").read()
except:
    errmsg("Unable to read NSF file: " + nsf_file)

if len(nsf) < 0x80:
    errmsg("NSF file too small: " + nsf_file)

nsf_bank = [ 0,0,0,0,0,0,0,0 ]
nsf_banks = 0
nsf_load_addr = nsf[0x08] + (nsf[0x09] << 8)
nsf_init_addr = nsf[0x0A] + (nsf[0x0B] << 8)
nsf_play_addr = nsf[0x0C] + (nsf[0x0D] << 8)
nsf_region = nsf[0x7A]
nsf_banked = False

for i in range(8):
    b = nsf[0x70+i]
    nsf_bank[i] = b
    if b != 0:
        nsf_banked = True

if not nsf_banked and nsf_load_addr < 0x8000:
    errmsg("NSF LOAD address below $8000. WRAM or FDS not supported: " + nsf_file)

nsf_rom_padding = 0

if nsf_banked:
    nsf_rom_padding = nsf_load_addr & 0x0FFF
    if nsf_nrom != 0:
        errmsg("NSF requires bankswitching, cannot be used with NROM: " + nsf_file)
else:
    nsf_rom_padding = nsf_load_addr - 0x8000
    for i in range(8):
        nsf_bank[i] = i

nsf_highest_bank = 0
for i in range(8):
    if nsf_bank[i] > nsf_highest_bank:
        nsf_highest_bank = nsf_bank[i]

nsf_f000 = nsf_bank[7]
nsf_rom = bytearray([0] * nsf_rom_padding) + nsf[0x80:]

print("NSF:")
print("  LOAD: %04X" % nsf_load_addr)
print("  INIT: %04X" % nsf_init_addr)
print("  PLAY: %04X" % nsf_play_addr)
print("  ROM size: %d bytes" % len(nsf_rom))
print()

def output_banks(prefix,data,trim=-1,minbanks=0):
    banks = 0
    extent = max(len(data),minbanks * 0x1000)
    while (banks * 0x1000) < extent:
        bank = banks
        of = os.path.join(outdir,prefix + ("%02X.bin" % bank))
        try:
            offset = bank * 0x1000
            s = data[offset : offset + 0x1000]
            if len(s) < 0x1000:
                s += bytearray([0] * (0x1000 - len(s))) # pad up to 4k
            if bank == trim:
                s = s[0:len(s)-6] # trim to make space for vectors
            open(of,"wb").write(s)
            print("Output: " + of)
        except:
            errmsg("Unable to write file: " + of)
        banks += 1
    return banks

if nsf_nrom != 0:
    # NROM mode = single binary blob
    of = os.path.join(outdir,"nsf_nrom.bin")
    try:
        open(of,"wb").write(nsf_rom)
        print("Output: " + of)
    except:
        errmsg("Unable to write file: " + of)
else:
    nsf_banks = output_banks("nsf_",nsf_rom,nsf_f000,nsf_highest_bank+1)
    print("NSF 4k banks: %d" % nsf_banks)
print()

# STEP 3: parse and package screen data

def unpack_ppu(rle):
    data = bytearray()
    run = 0
    command = 0
    # command:
    # 0 = read new RLE packet
    # 1 = read RLE length
    # 2 = read RLE byte and emit
    # 3 = read uncompressed bytes
    # 4 = end of stream reached
    for b in rle:
        if command == 0:
            if b == 0:
                command = 1
            else:
                run = b
                command = 3
        elif command == 1:
            if b == 0:
                command = 4
                break # end of stream
            else:
                run = b
                command = 2
        elif command == 2:
            data = data + bytearray([b] * run)
            command = 0
        elif command == 3:
            data.append(b)
            run -= 1
            if (run < 1):
                command = 0
        else:
            errmsg("Internal problem in RLE verificaiton.")
    if command != 4:
        errmsg("RLE end of stream reached without marker.")
    return data

def pack_ppu(data):
    # RLE compression
    # 1. 0 = RLE to follow
    #    1-255 = 1-255 uncompressed bytes to follow, return to 1.
    # 2. 0 = end of stream
    #    1-255 = number of repeated bytes to follow
    # 3. byte to be repeated, return to 1.

    # helper functions to compress an RLE or non-RLE chunk of the stream
    def emit_compressed(s):
        output = bytearray()
        # ensure that s is all the same byte before we RLE compress
        for sb in s:
            if sb != s[0]:
                errmsg("Internal problem in RLE compressor!")
        # emit compressed packets
        while (len(s) > 0):
            emit = min(len(s),255)
            output.append(0)
            output.append(emit)
            output.append(s[0])
            s = s[emit:]
        return output
    def emit_uncompressed(s):
        output = bytearray()
        # emit uncompressed packets
        while (len(s) > 0):
            emit = min(len(s),255)
            output.append(emit)
            output += s[0:emit]
            s = s[emit:]
        return output

    # do the compression
    rle = bytearray()
    run = bytearray()
    running = False
    for d in data:
        run.append(d)
        rl = len(run)
        if running:
            if d != run[rl-2]:
                rle += emit_compressed(run[0:rl-1])
                run = run[rl-1:]
                running = False
        else:
            if rl >= 4:
                if d == run[rl-2] and d == run[rl-3] and d == run[rl-4]:
                    rle += emit_uncompressed(run[0:rl-4])
                    run = run[rl-4:]
                    running = True
    # any unfinished data left in the buffer should be emitted
    if running:
        rle += emit_compressed(run)
    else:
        rle += emit_uncompressed(run)
    # mark end of stream
    rle.append(0)
    rle.append(0)
    # verify:
    unpacked = unpack_ppu(rle)
    if len(unpacked) != len(data):
        #compare_rle(data,unpacked,rle) # diagnostic
        errmsg("RLE packing verification failed; length mismatch.")
    for i in range(0,len(data)):
        if unpacked[i] != data[i]:
            #compare_rle(data,unpacked,rle) # diagnostic
            errmsg("RLE packing verification failed.")
    # ready
    return rle

def compare_rle(data,unpacked,packed):
    def printbin(s,name):
        print("data %s, size: %d" % (name,len(s)))
        os = ""
        pos = 0
        line_len = 32
        o = 0
        for b in s:
            os += (" %02X " % b)
            o += 1
            if (o >= line_len):
                print (("%04X: " % pos) + os)
                os = ""
                pos += o
                o = 0
        if (o > 0):
            print(("%04X: " % pos) + os)
    printbin(data,"data")
    printbin(unpacked,"unpacked")
    printbin(packed,"packed")          

ppu_files = {}
ppu_offsets = {}
ppu_data = bytearray()

nrom_chr0 = ""
nrom_chr1 = ""

print("PPU data compression:")
for s in nsf_screens:
    for i in range(1,6):
        f = s[i]
        if nsf_nrom != 0:
            if i == 2:
                if nrom_chr0 == "":
                    nrom_chr0 = f
                elif nrom_chr0 != f:
                    errmsg("All NROM screens must use the same two CHR pages.")
            elif i == 3:
                if nrom_chr1 == "":
                    nrom_chr1 = f
                elif nrom_chr1 != f:
                    errmsg("All NROM screens must use the same two CHR pages.")
        if f in ppu_files:
            continue
        ppu_files[f] = len(ppu_files)

ppu_offset = 0
ppu_files_immutable = sorted(ppu_files.items())
for (f,i) in ppu_files_immutable:
    try:
        data = open(f,"rb").read()
    except:
        errmsg("Unable to read file: " + f)
    packed = pack_ppu(data)
    ppu_offsets[f] = ppu_offset
    if (nrom_chr0 == f) or (nrom_chr1 == f):
        packed = bytearray([0,0])
    ppu_offset += len(packed)
    ppu_data += packed
    print("Compressed: %-20s from %4d / %4d bytes" % (f,len(packed),len(data)))

if nsf_nrom != 0:
    # NROM mode = single binary blob
    of = os.path.join(outdir,"ppu_nrom.bin")
    try:
        open(of,"wb").write(ppu_data)
        print("Output: " + of)
    except:
        errmsg("Unable to write file: " + of)
else:
    ppu_banks = output_banks("ppu_",ppu_data)
    print("PPU 4k banks: %d" % ppu_banks)
    if (ppu_banks > 7):
        errmsg("Too many PPU banks! Maximum: 7")
print()

# STEP 4: generate enums and tables

# compute needed banks for building
if nsf_nrom == 0:
    needed_banks = nsf_banks + ppu_banks + 1
    padded_banks = 1
    while padded_banks < needed_banks:
        padded_banks *= 2
else:
    padded_banks = int(32 / 4)

def ppu_file_enum(s):
    so = ""
    for c in s:
        so += c if ((c>='a' and c<='z') or (c>='A' and c<='Z')) else "_"
    return so

s = ""
s += "; automatically generated by eznsf.py\n"
s += "; " + now_string + "\n"
s += "\n"
s += "MAPPER = %d\n" % (0 if (nsf_nrom != 0) else 31)
s += "BANKS = %d ; 4k bank count\n" % padded_banks
if (nsf_nrom != 0):
    s += ".define NROM_CHR0 \"%s\"\n" % nrom_chr0
    s += ".define NROM_CHR1 \"%s\"\n" % nrom_chr1
    s += ".define PPU_NROM_BIN \"%s/ppu_nrom.bin\"\n" % outdir
    s += ".define NSF_NROM_BIN \"%s/nsf_nrom.bin\"\n" % outdir
else:
    s += ".define NSF_F000 \"%s/nsf_%02X.bin\"\n" % (outdir,nsf_f000)
s += "\n"
s += ".enum eNSF\n"
s += "\tINIT = $%04X\n" % nsf_init_addr
s += "\tPLAY = $%04X\n" % nsf_play_addr
s += "\tREGION = %d\n" % nsf_region
s += "\tTRACKS = %d\n" % len(nsf_tracks)
s += "\tBANK_F000 = $%02X\n" % nsf_f000
if (nsf_nrom == 0):
    s += "\tBANKS = $%02X\n" % nsf_banks
s += ".endenum\n"
s += "\n"
s += ".enum eScreen\n"
for i in range(len(nsf_screens)):
    s += "\t%-20s = %2d\n" % (nsf_screens[i][0],i)
s += ".endenum\n"
s += "\n"
s += ".enum ePPU\n"
i = 0
for (k,v) in ppu_files_immutable:
    s += "\t%-20s = %2d\n" % (ppu_file_enum(k),i)
    i += 1
s += ".endenum\n"
s += "\n"
s += ".enum eCoord\n"
for coord in nsf_coord:
    s += "\t%-30s = %d\n" % (coord[0] + "_X", coord[1])
    s += "\t%-30s = %d\n" % (coord[0] + "_Y", coord[2])
s += ".endenum\n"
s += "\n"
s += ".enum eConst\n"
for c in nsf_const:
    s += "\t%-30s = %d\n" % (c[0], c[1])
s += ".endenum\n"
s += "\n"
s += "; end of file\n"

#print(s) # diagnostic
of = os.path.join(outdir,"enums.sh")
try:
    open(of,"wt").write(s)
    print("Output: " + of)
except:
    errmsg("Unable to write file: " + of)

s = ""
s += "; automatically generated by eznsf.py\n"
s += "; " + now_string + "\n"
s += "\n"
s += ".scope dString\n"
s += "\ttitle:     .asciiz \"" + nsf_title     + "\"\n"
s += "\tartist:    .asciiz \"" + nsf_artist    + "\"\n"
s += "\tcopyright: .asciiz \"" + nsf_copyright + "\"\n"
for i in range(0,len(nsf_tracks)):
    s += "\ttrack_%02d:  .asciiz \"%s\"\n" % (i,nsf_tracks[i][0])
s += "\tinfo:\n"
for si in nsf_info:
    s += "\t\t.byte \"%s\",13\n" % si
s += "\t\t.byte 0\n"
s += ".endscope\n"
s += "\n"
s += ".scope dNSF\n"
s += "\tbank: .byte $%02X" % nsf_bank[0]
for i in range(1,8):
    s += ", $%02X" % nsf_bank[i]
s += "\n"
s += ".endscope\n"
s += "\n"
s += ".scope dTrack\n"
s += "\tstring_table:\n"
for i in range(len(nsf_tracks)):
    s += "\t\t.addr dString::track_%02d ; %s\n"  % (i,nsf_tracks[i][0])
s += "\tsong_table:\n"
for i in range(len(nsf_tracks)):
    s += "\t\t.byte %3d ; %s\n"  % (nsf_tracks[i][1],nsf_tracks[i][0])
s += "\tlength_table:\n"
for i in range(len(nsf_tracks)):
    s += "\t\t.word (%2d * 60) + %2d ; %s\n"  % (nsf_tracks[i][2],nsf_tracks[i][3],nsf_tracks[i][0])
s += ".endscope\n"
s += "\n"
s += ".scope dScreen\n"
s += "\tname_table:\n"
for i in range(len(nsf_screens)):
    s += "\t\t.byte ePPU::%-25s ; %s\n" % (ppu_file_enum(nsf_screens[i][1]),nsf_screens[i][0])
s += "\tchr0_table:\n"
for i in range(len(nsf_screens)):
    s += "\t\t.byte ePPU::%-25s ; %s\n" % (ppu_file_enum(nsf_screens[i][2]),nsf_screens[i][0])
s += "\tchr1_table:\n"
for i in range(len(nsf_screens)):
    s += "\t\t.byte ePPU::%-25s ; %s\n" % (ppu_file_enum(nsf_screens[i][3]),nsf_screens[i][0])
s += "\tpal0_table:\n"
for i in range(len(nsf_screens)):
    s += "\t\t.byte ePPU::%-25s ; %s\n" % (ppu_file_enum(nsf_screens[i][4]),nsf_screens[i][0])
s += "\tpal1_table:\n"
for i in range(len(nsf_screens)):
    s += "\t\t.byte ePPU::%-25s ; %s\n" % (ppu_file_enum(nsf_screens[i][5]),nsf_screens[i][0])
s += ".endscope\n"
s += "\n"
s += ".scope dPPU\n"
s += "\tdata_table:\n"
i = 0
for (k,v) in ppu_files_immutable:
    s += "\t\t.addr data_base + $%04X ; %-20s = %d\n" % (ppu_offsets[k],ppu_file_enum(k),i)
    i += 1
s += ".endscope\n"
s += "\n"
s += "; end of file\n"

#print(s) # diagnostic
of = os.path.join(outdir,"tables.sh")
try:
    open(of,"wt").write(s)
    print("Output: " + of)
except:
    errmsg("Unable to write file: " + of)

print()

# STEP 5: build the code

def execute(args):
    print("Run: " + " ".join(args))
    print()
    proc = subprocess.Popen(args, stderr=subprocess.STDOUT, stdout=subprocess.PIPE)
    proc.wait()
    for l in proc.stdout:
        print (l.decode().rstrip())
    return proc.returncode

link_object = os.path.join(outdir,"eznsf.o")

#assemble
if (0 != execute([ca65, "eznsf.s", "-I", outdir, "-g", "-o", link_object])):
    print()
    errmsg("Assemble of eznsf.s has failed!")

#link
ld65_debug = [ "-m", os.path.join(outdir,"eznsf.map"), "-Ln", os.path.join(outdir,"eznsf.lab") ]
if nsf_nrom != 0:
    if (0 != execute([ld65, "-o", os.path.join(outdir,"eznsf.nes"), "-C", "eznsf_nrom.cfg"] + ld65_debug + [link_object])):
        print()
        errmsg("Link of eznsf.nes has failed!")
else:
    if (0 != execute([ld65, "-o", os.path.join(outdir,"eznsf.bin"), "-C", "eznsf.cfg"] + ld65_debug + [link_object])):
        print()
        errmsg("Link of eznsf.bin has failed!")
    if (0 != execute([ld65, "-o", os.path.join(outdir,"f000.bin"), "-C", "eznsf_f000.cfg"] + [link_object])):
        print()
        errmsg("Link of f000.bin has failed!")
    if (0 != execute([ld65, "-o", os.path.join(outdir,"header.bin"), "-C", "eznsf_header.cfg"] + [link_object])):
        print()
        errmsg("Link of header.bin has failed!")

    # concatenate banks into the ROM file
    def readbin(f,seg):
        try:
            b = open(f,"rb").read()
        except:
            errmsg("Unable to read file: " + f)
        print ("Segment %03X: %s" % (seg & 0xFFF, f))
        return b

    print("Concatenating %d banks..." % padded_banks)
    output_nes = bytearray()
    output_nes += readbin(os.path.join(outdir,"header.bin"),-1)
    seg = 0
    for i in range(nsf_banks):
        if i == nsf_f000:
            output_nes += readbin(os.path.join(outdir,"f000.bin"), seg)
        else:
            output_nes += readbin(os.path.join(outdir,"nsf_%02X.bin" % i), seg)
        seg += 1
    for i in range(ppu_banks):
        output_nes += readbin(os.path.join(outdir,"ppu_%02X.bin" % i), seg)
        seg += 1
    for i in range(padded_banks - (nsf_banks + ppu_banks)):
        output_nes += readbin(os.path.join(outdir,"eznsf.bin"), seg)
        seg += 1

    # output the file
    try:
        of = os.path.join(outdir,"eznsf.nes")
        open(of,"wb").write(output_nes)
        print("Output: " + of)
    except:
        errmsg("Unable to write file: " + of)
    print()

# STEP 6: assemble NSFE

# reorganize list by track number
nsfe_tracks = {}
for (t,n,m,s) in nsf_tracks:
    nsfe_tracks[n] = (t,m,s)

if (output_nsfe):
    def fourcc(s):
        fcc = bytearray()
        for i in range(4):
            fcc.append(ord(s[i]))
        return fcc

    def packword(w):
        w = w & 0xFFFF
        wb = bytearray()
        wb.append(w & 255)
        wb.append(w >> 8)
        return wb

    def packlong(l):
        l = l & 0xFFFFFFFF
        lb = bytearray()
        lb.append(l & 255)
        lb.append((l >> 8) & 255)
        lb.append((l >> 16) & 255)
        lb.append(l >> 24)
        return lb

    def packstring(s):
        sb = bytearray(s.encode(encoding="utf-8"))
        sb.append(0)
        return sb
        
    def nsfe_chunk(fcc,data):
        chunk = bytearray()
        chunk += packlong(len(data))
        chunk += fourcc(fcc)
        chunk += data
        return chunk

    song_count = nsf[0x06]

    nsfe_rom = bytearray()
    nsfe_rom += fourcc("NSFE")

    nsfe_info = bytearray()
    nsfe_info += packword(nsf_load_addr)
    nsfe_info += packword(nsf_init_addr)
    nsfe_info += packword(nsf_play_addr)
    nsfe_info.append(nsf_region)
    nsfe_info.append(nsf[0x7B]) # Expansion
    nsfe_info.append(song_count)
    nsfe_info.append(nsf[0x07]-1) # Starting song
    nsfe_rom += nsfe_chunk("INFO",nsfe_info)

    if nsf_banked:
        nsfe_rom += nsfe_chunk("BANK",bytearray(nsf_bank))

    nsfe_rom += nsfe_chunk("DATA",nsf[0x80:])

    nsfe_auth = bytearray()
    nsfe_auth += packstring(nsf_title)
    nsfe_auth += packstring(nsf_artist)
    nsfe_auth += packstring(nsf_copyright)
    nsfe_auth += packstring("eznsf.py")
    nsfe_rom += nsfe_chunk("auth",nsfe_auth)

    nsfe_plst = bytearray()
    for (t,n,m,s) in nsf_tracks:
        nsfe_plst.append(n)
    nsfe_rom += nsfe_chunk("plst",nsfe_plst)

    nsfe_time = bytearray()
    for ti in range(0,song_count):
        if ti in nsfe_tracks:
            (t,m,s) = nsfe_tracks[ti]
            nsfe_time += packlong(1000 * ((m*60) + s))
        else:
            nsfe_time += packlong(-1)
    nsfe_rom += nsfe_chunk("time",nsfe_time)

    nsfe_tlbl = bytearray()
    for ti in range(0,song_count):
        if ti in nsfe_tracks:
            (t,m,s) = nsfe_tracks[ti]
            nsfe_tlbl += packstring(t)
        else:
            nsfe_tlbl.append(0)
    nsfe_tlbl.append(0)
    nsfe_rom += nsfe_chunk("tlbl",nsfe_tlbl)

    nsfe_rom += nsfe_chunk("text",packstring("eznsf.py"))

    nsfe_rom += nsfe_chunk("NEND",bytearray())

    of = os.path.join(outdir,"eznsf.nsfe")
    try:
        open(of,"wb").write(nsfe_rom)
        print("Output: " + of)
    except:
        errmsg("Unable to write file: " + of)
    print()

# STEP OFF!

print("Success!")
sys.exit(0)
