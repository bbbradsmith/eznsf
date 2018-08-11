;
; EZNSF
;
; bradsmith, 2016
; http://rainwarrior.ca

;
; ram usage
;

.segment "OAM"
.align 256
oam:          .res 256

.segment "ZEROPAGE"
ptr:          .res 2 ; pointer for indirect addressing
nmi_count:    .res 1 ; incremented by NMI handler
gamepad:      .res 1 ; gamepad poll result

.segment "BSS"
pal:          .res 1 ; 0 = NTSC (60 fps), 1 = PAL (50 fps)
fps:          .res 1 ; reflects NTSC/PAL
frame:        .res 1 ; counts 0 to fps to measure a second
sec0:         .res 1 ; display timer
sec1:         .res 1
min0:         .res 1
min1:         .res 1
title_choose: .res 1 ; title screen selection
track_choose: .res 1 ; track selection
play_through: .res 1 ; 0 = stop at end of track, 1 = stop at end of album
play_paused:  .res 1 ; 0 = playing, 1 = paused, 2 = stopped
play_len:     .res 2 ; seconds in track
play_secs:    .res 2 ; seconds played so far
gamepad_last: .res 1 ; gamepad from last poll
gamepad_new:  .res 1 ; new buttons this poll
temp:         .res 2

;
; useful definitions
;

PAD_A      = $01
PAD_B      = $02
PAD_SELECT = $04
PAD_START  = $08
PAD_U      = $10
PAD_D      = $20
PAD_L      = $40
PAD_R      = $80

.macro PPU_LATCH addr
	lda $2002
	lda #>(addr)
	sta $2006
	lda #<(addr)
	sta $2006
.endmacro

.define PPU_TILE(ax,ay) ($2000+(ay*32)+ax)

.macro PTR_LOAD addr
	lda #<(addr)
	sta ptr+0
	lda #>(addr)
	sta ptr+1
.endmacro

; shorthand for lda/sta
.macro STB addr, val
	lda val
	sta addr
.endmacro

;
; generated data
;

.segment "CODE"
.include "enums.sh"
.include "tables.sh"

;
; title
;

.proc title_sprite
	jsr oam_clear
	STB oam+(0*4)+1, #eConst::SPRITE_CHOOSE
	STB oam+(0*4)+2, #2
	lda title_choose
	bne @choose_info
@choose_start:
	STB oam+(0*4)+3, #eCoord::TITLE_START_X
	STB oam+(0*4)+0, #eCoord::TITLE_START_Y-1
	rts
@choose_info:
	STB oam+(0*4)+3, #eCoord::TITLE_INFO_X
	STB oam+(0*4)+0, #eCoord::TITLE_INFO_Y-1
	rts
.endproc

.proc mode_title
	lda #eScreen::TITLE
	jsr load_screen
	PPU_LATCH PPU_TILE(eCoord::TITLE_TITLE_X, eCoord::TITLE_TITLE_Y)
	PTR_LOAD dString::title
	jsr ppu_string
	PPU_LATCH PPU_TILE(eCoord::TITLE_ARTIST_X, eCoord::TITLE_ARTIST_Y)
	PTR_LOAD dString::artist
	jsr ppu_string
	PPU_LATCH PPU_TILE(eCoord::TITLE_COPYRIGHT_X, eCoord::TITLE_COPYRIGHT_Y)
	PTR_LOAD dString::copyright
	jsr ppu_string
@loop:
	jsr title_sprite
	jsr render_on
	jsr gamepad_poll
	lda gamepad_new
	and #(PAD_L | PAD_R | PAD_U | PAD_D | PAD_SELECT)
	beq @move_end
		lda title_choose
		eor #1
		sta title_choose
		jmp @loop
	@move_end:
	lda gamepad_new
	and #(PAD_START | PAD_A | PAD_B)
	beq @loop
		lda title_choose
		bne :+
			jmp mode_tracks
		:
			jmp mode_info
		;
	;
.endproc

;
; info
;

.proc mode_info
	lda #eScreen::INFO
	jsr load_screen
	INFO_ADDR = PPU_TILE(eCoord::INFO_X, eCoord::INFO_Y)
	lda #>INFO_ADDR
	sta temp+1
	sta $2006
	lda #<INFO_ADDR
	sta temp+0
	sta $2006
	PTR_LOAD dString::info
	:
		; print lines until a 0 is reached
		jsr ppu_string
		lda (ptr), Y
		beq :+
		jsr ppu_temp_line
		jmp :-
	:
	jsr oam_clear
@loop:
	jsr render_on
	jsr gamepad_poll
	lda gamepad_new
	beq @loop
	jmp mode_title
.endproc

;
; tracks
;

.proc track_sprite
	jsr oam_clear
	STB oam+(0*4)+1, #eConst::SPRITE_CHOOSE
	STB oam+(0*4)+2, #2
	STB oam+(0*4)+3, #(eCoord::TRACKS_TRACK_X-2)*8
	lda track_choose
	asl
	asl
	asl
	clc
	adc #(eCoord::TRACKS_TRACK_Y*8)-1
	sta oam+(0*4)+0
	rts
.endproc

.proc mode_tracks
	; silence
	lda #0
	sta $4015
	sta $4011
	; load the screen
	lda #eScreen::TRACKS
	jsr load_screen
	PPU_LATCH PPU_TILE(eCoord::TRACKS_TITLE_X, eCoord::TRACKS_TITLE_Y)
	PTR_LOAD dString::title
	jsr ppu_string
	PPU_LATCH PPU_TILE(eCoord::TRACKS_ARTIST_X, eCoord::TRACKS_ARTIST_Y)
	PTR_LOAD dString::artist
	jsr ppu_string
	PPU_LATCH PPU_TILE(eCoord::TRACKS_COPYRIGHT_X, eCoord::TRACKS_COPYRIGHT_Y)
	PTR_LOAD dString::copyright
	jsr ppu_string
	TRACK_ADDR = PPU_TILE(eCoord::TRACKS_TRACK_X, eCoord::TRACKS_TRACK_Y)
	lda #>TRACK_ADDR
	sta temp+1
	sta $2006
	lda #<TRACK_ADDR
	sta temp+0
	sta $2006
	ldx #0
	:
		lda dTrack::string_table+0, X
		sta ptr+0
		lda dTrack::string_table+1, X
		sta ptr+1
		inx
		inx
		jsr ppu_string
		cpx #(eNSF::TRACKS * 2)
		bcs :+
		jsr ppu_temp_line
		jmp :-
	:
@loop:
	lda gamepad
	sta gamepad_last
	jsr track_sprite
	jsr render_on
	jsr gamepad_poll
	lda gamepad_new
	and #(PAD_L | PAD_U)
	beq :+
		lda track_choose
		beq @move_end
		dec track_choose
		jmp @move_end
	:
	lda gamepad_new
	and #(PAD_R | PAD_D)
	beq :+
		lda track_choose
		cmp #(eNSF::TRACKS-1)
		bcs @move_end
		inc track_choose
		jmp @move_end
	:
@move_end:
	lda gamepad_new
	and #(PAD_SELECT)
	beq :+
		jmp mode_title
	:
	lda gamepad_new
	and #(PAD_A | PAD_START)
	beq :+
		lda #1
		sta play_through
		jmp mode_play
	:
	lda gamepad_new
	and #(PAD_B)
	beq :+
		lda #0
		sta play_through
		jmp mode_play
	:
	jmp @loop
.endproc

;
; play
;

.proc play_sprite
	; timer
	lda min1
	clc
	adc #eConst::SPRITE_ZERO
	sta oam+(0*4)+1
	lda min0
	clc
	adc #eConst::SPRITE_ZERO
	sta oam+(1*4)+1
	lda sec1
	clc
	adc #eConst::SPRITE_ZERO
	sta oam+(3*4)+1
	lda sec0
	clc
	adc #eConst::SPRITE_ZERO
	sta oam+(4*4)+1
	; playback indicator
	lda play_paused
	cmp #2
	bcc :+
		lda #eConst::SPRITE_STOP
		jmp @indicator
	:
	cmp #1
	bcc :+
		lda #eConst::SPRITE_PAUSE
		jmp @indicator
	:
	lda play_through
	beq :+
		lda #eConst::SPRITE_PLAY_ALL
		jmp @indicator
	:
		lda #eConst::SPRITE_PLAY
		;jmp @indicator
	@indicator:
	sta oam+(5*4)+1
	rts
.endproc

.proc play_sprite_init
	; position all 6 sprites
	STB temp, #eCoord::PLAY_TIME_X+(0*8)
	ldx #0
	:
		lda #eCoord::PLAY_TIME_Y-1
		sta oam+0, X
		lda #2
		sta oam+2, X
		lda temp
		sta oam+3, X
		clc
		adc #8
		sta temp
		inx
		inx
		inx
		inx
		cpx #(6*4)
		bcc :-
	lda temp
	sta oam+(5*4)+3
	STB oam+(2*4)+1, #eConst::SPRITE_COLON
	jmp play_sprite
.endproc

.proc mode_play
	; silence
	lda #0
	sta $4015
	sta $4011
	; load the screen
	lda #eScreen::PLAY
	jsr load_screen
	PPU_LATCH PPU_TILE(eCoord::PLAY_TRACK_X, eCoord::PLAY_TRACK_Y)
	lda track_choose
	asl
	tax
	lda dTrack::string_table+0, X
	sta ptr+0
	lda dTrack::string_table+1, X
	sta ptr+1
	jsr ppu_string
	jsr play_sprite_init
	jsr play_init
@loop:
	jsr play_sprite
	jsr render_on
	jsr play_play
	jsr gamepad_poll
	lda play_paused
	cmp #2
	bcs @stopped
@playing:
	lda gamepad_new
	and #(PAD_START)
	beq :+
		lda play_paused
		eor #1
		jsr play_pause
	:
	lda gamepad_new
	and #(PAD_B)
	beq :+
		lda #0
		jsr play_pause
		lda #0
		sta play_through
	:
	lda gamepad_new
	and #(PAD_A)
	beq :+
		lda #0
		jsr play_pause
		lda #1
		sta play_through
	:
	;jmp @shared
@shared:
	lda gamepad_new
	and #(PAD_SELECT)
	beq :+
		jmp mode_tracks
	:
	lda gamepad_new
	and #(PAD_L | PAD_U)
	beq :+
		lda track_choose
		beq :+
		dec track_choose
		jmp mode_play
	:
	lda gamepad_new
	and #(PAD_R | PAD_D)
	beq :+
		lda track_choose
		cmp #(eNSF::TRACKS-1)
		bcs :+
		inc track_choose
		jmp mode_play
	:
	jmp @loop
@stopped:
	lda play_through
	beq :+
	@play_next:
		lda track_choose
		cmp #(eNSF::TRACKS-1)
		bcs :+
		; auto-advance to next track
		inc track_choose
		jmp mode_play
	:
	lda gamepad_new
	and #(PAD_START)
	beq :+
		jmp mode_play
	:
	lda gamepad_new
	and #(PAD_B)
	beq :+
		lda #0
		sta play_through
		jmp mode_play
	:
	lda gamepad_new
	and #(PAD_A)
	beq :+
		lda #1
		sta play_through
		jmp mode_play
	:
	jmp @shared
.endproc

;
; player
;

.proc play_init
	; NSF pre-initialize
	; RAM init
	lda #0
	tax
	:
		sta $00, X
		inx
		cpx #$FC
		bcc :-
	;lda #0
	tax
	:
		sta $0200, X
		sta $0300, X
		sta $0400, X
		sta $0500, X
		inx
		bne :-
	; APU init
	;lda #0
	;tax
	:
		sta $4000, X
		inx
		cpx #$14
		bcc :-
	STB $4015, #$0F
	STB $4017, #$40
	; player init
	lda #0
	sta frame
	sta sec0
	sta sec1
	sta min0
	sta min1
	sta play_paused
	sta play_secs+0
	sta play_secs+1
	lda track_choose
	asl
	tax
	lda dTrack::length_table+0, X
	sta play_len+0
	lda dTrack::length_table+1, X
	sta play_len+1
	; call NSF INIT
	ldx track_choose
	lda dTrack::song_table, X
	jmp ramcode_nsf_init
.endproc

.proc play_play
	lda play_paused
	beq :+
		rts
	:
	jsr ramcode_nsf_play
	inc frame
	lda frame
	cmp fps
	bcc @second_end
		; increment timer display
		lda #0
		sta frame
		inc sec0
		lda sec0
		cmp #10
		bcc :+
		lda #0
		sta sec0
		inc sec1
		lda sec1
		cmp #6
		bcc :+
		lda #0
		sta sec1
		inc min0
		lda min0
		cmp #10
		bcc :+
		lda #0
		sta min0
		inc min1
		lda min1
		cmp #10
		bcc :+
		lda #9
		sta min1
		sta min0
		sta sec0
		lda #5
		sta sec1
		:
		; increment track timer
		inc play_secs+0
		bne :+
			inc play_secs+1
		:
		lda play_secs+0
		cmp play_len+0
		lda play_secs+1
		sbc play_len+1
		bcc @second_end
		lda play_len+0
		sta play_secs+0
		lda play_len+1
		sta play_secs+1
		; stop and silence
		lda #2
		sta play_paused
		lda #0
		sta $4015
	@second_end:
	rts
.endproc

; A = pause
.proc play_pause
	cmp play_paused
	bne :+
		rts
	:
	cmp #0
	bne @pause
@unpause:
	lda #$0F
	sta $4015
	lda #0
	sta play_paused
	rts
@pause:
	lda #0
	sta $4015
	lda #1
	sta play_paused
	rts
.endproc

.segment "RAMCODE"

.if (MAPPER = 31)
ramcode_reset:
	lda #$FF
	sta $5FFF
	jmp vec_reset
ramcode_nmi:
	inc nmi_count
ramcode_irq:
	rti
.endif

; A = track to play
.proc ramcode_nsf_init
	.if (::MAPPER = 31)
		pha
		; setup NSF banks
		.repeat 8, I
			STB $5FF8+I, dNSF::bank+I
		.endrepeat
		pla
	.endif
	ldx pal
	ldy #0
	jsr eNSF::INIT
	jmp ramcode_return
.endproc

.proc ramcode_nsf_play
	.if (::MAPPER = 31)
		; restore NSF high bank
		lda #eNSF::BANK_F000
		sta $5FFF
	.endif
	lda #0
	tax
	tay
	jsr eNSF::PLAY
	jmp ramcode_return
.endproc

.proc ramcode_return
	.if (::MAPPER = 31)
		; restore EZNSF to bank $F000
		lda #$FF
		sta $5FFF
	.endif
	rts
.endproc

.segment "CODE"

.import __RAMCODE_SIZE__
.import __RAMCODE_LOAD__
.import __RAMCODE_RUN__

.proc load_ramcode
	.assert (__RAMCODE_SIZE__ < 256), error, "RAMCODE segment is too large."
	.assert (__RAMCODE_SIZE__ > 0), error, "RAMCODE segment empty."
	ldx #0
	:
		lda __RAMCODE_LOAD__, X
		sta __RAMCODE_RUN__, X
		inx
		cpx #<__RAMCODE_SIZE__
		bcc :-
	rts
.endproc

;
; main
;

.proc main
	; clear second nametable (never used)
	PPU_LATCH $2400
	ldy #4
	lda #0
	tax
	:
		sta $2007
		inx
		bne :-
		dey
		bne :-
	jmp mode_title
.endproc

;
; various helpful functions
;

; auto-incrementing read
; ptr = pointer to be read from
; Y = 0
.proc read_ptr
	lda (ptr), Y
	inc ptr+0
	bne :+
		inc ptr+1
	:
	cmp #0
	rts
.endproc

; A = ePPU index to a PPU data chunk
; data will be unpacked and written directly to $2007
.proc ppu_unpack
	asl
	tax
	lda dPPU::data_table+0, X
	sta ptr+0
	lda dPPU::data_table+1, X
	sta ptr+1
	; RLE format
	; 1. 0 = RLE data follow, 1-255 = this many bytes of uncompressed data follows (return to 1)
	; 2. 0 = data stream is finished, 1-255 = this any bytes of the same byte follows
	; 3. byte to repeated number of times specified in 2, return to 1
	ldy #0
	@rle_loop:
		jsr read_ptr
		beq @compressed
	@uncompressed:
		tax
		:
			jsr read_ptr
			sta $2007
			dex
			bne :-
		jmp @rle_loop
	@compressed:
		jsr read_ptr
		beq @finished
		tax
		jsr read_ptr
		:
			sta $2007
			dex
			bne :-
		jmp @rle_loop
	@finished:
		rts
.endproc

; ptr = null or newline terminated string to write to screen
.proc ppu_string
	ldy #0
	:
		jsr read_ptr
		beq :+
		cmp #13 ; newline
		beq :+
		sta $2007
		jmp :-
	:
	rts
.endproc

; A = eScreen to load
.proc load_screen
	sta temp
	jsr load_ppu_banks
	jsr render_off
	; palettes first so they'll be within vblank
	PPU_LATCH $3F00
	ldx temp
	lda dScreen::pal0_table, X
	jsr ppu_unpack
	ldx temp
	lda dScreen::pal1_table, X
	jsr ppu_unpack
	PPU_LATCH $0000
	ldx temp
	lda dScreen::chr0_table, X
	jsr ppu_unpack
	ldx temp
	lda dScreen::chr1_table, X
	jsr ppu_unpack
	PPU_LATCH $2000
	ldx temp
	lda dScreen::name_table, X
	jsr ppu_unpack
	rts
.endproc

.proc oam_clear
	lda #$FF
	ldx #0
	:
		sta oam, X
		inx
		inx
		inx
		inx
		bne :-
	rts
.endproc

.proc ppu_temp_line
	lda temp+0
	clc
	adc #<32
	sta temp+0
	lda temp+1
	adc #>32
	sta temp+1
	sta $2006
	lda temp+0
	sta $2006
	rts
.endproc

.proc wait_nmi
	lda #%10000000
	sta $2000 ; ensure NMI is running before waiting on it
	lda nmi_count
	:
		cmp nmi_count
		beq :-
	rts
.endproc

.proc render_off
	jsr wait_nmi
	lda #0
	sta $2001
	rts
.endproc

.proc render_on
	jsr wait_nmi
	; update sprites
	lda #0
	sta $2003
	lda #>oam
	sta $4014
	; set scroll
	lda $2002
	lda #0
	sta $2005
	sta $2005
	; turn on rendering
	lda #%00011110
	sta $2001
	rts
.endproc

;
; gamepad
;

.proc gamepad_poll
	; remember last state
	lda gamepad
	sta gamepad_last
	; latch the current controller state
	lda #1
	sta $4016
	lda #0
	sta $4016
	; store high bit in gamepad to mark end of read
	lda #%10000000
	sta gamepad
	; read 8 bits from controller port
	:
		lda $4016
		and #%00000011
		cmp #%00000001
		ror gamepad
	bcc :-
	; DPCM conflict may have corrupted first read, test again to make sure
@reread:
	lda gamepad
	pha ; store previous read on the stack
	lda #1
	sta $4016
	lda #0
	sta $4016
	lda #%10000000
	sta gamepad
	:
		lda $4016
		and #%00000011
		cmp #%00000001
		ror gamepad
	bcc :-
	pla ; pop the first read to compare
	cmp gamepad
	bne @reread
	; store buttons pressed this frame
	lda gamepad_last
	eor gamepad
	and gamepad
	sta gamepad_new
	rts
.endproc

;
; vector handlers
;

.proc vec_reset
	; standard startup
	sei       ; set interrupt flag (unnecessary, unless reset is called from code)
	cld       ; disable decimal mode
	ldx #$40
	stx $4017 ; disable APU IRQ
	ldx #$ff
	txs       ; set up stack
	ldx #$00
	stx $2000 ; disable NMI
	stx $2001 ; disable render
	stx $4010 ; disable DPCM IRQ
	stx $4015 ; mute APU
	;
	bit $2002 ; clear vblank flag
	; wait for vblank
	:
		bit $2002
		bpl :-
	; clear memory
	ldx #$00
	:
		lda #$00
		sta $0000, X
		sta $0100, X
		sta $0200, X
		sta $0300, X
		sta $0500, X
		sta $0600, X
		sta $0700, X
		lda #$FF ; OAM clear
		sta $0400, X
		inx
		bne :-
	; wait for second vblank
	:
		bit $2002
		bpl :-
	; PPU is now warmed up, NES is ready to go!
	jsr load_ramcode
	; detect NTSC/PAL
	lda $2002
	lda #%10000000
	sta $2000
	jsr detect_region
	bne :+
		lda #60
		sta fps
		lda #0
		jmp :++
	:
		lda #50
		sta fps
		lda #1
	:
	sta pal
	; leave NMI on forever and begin
	jmp main
.endproc

vec_nmi:
	inc nmi_count
vec_irq:
	rti

;
; mapper 31
;

.if (MAPPER = 31)

dPPU::data_base = $8000
INES_CHR = 0 ; CHR RAM

.segment "CODE"
.proc load_ppu_banks
	; prepare PPU data at the correct location
	ldx #eNSF::BANKS
	stx $5FF8
	inx
	stx $5FF9
	inx
	stx $5FFA
	inx
	stx $5FFB
	inx
	stx $5FFC
	inx
	stx $5FFD
	inx
	stx $5FFE
	rts
.endproc

.segment "NSF_F000"
.incbin NSF_F000

.segment "NSF_VECTORS"
.addr ramcode_nmi
.addr ramcode_reset
.addr ramcode_irq

;
; mapper 0
;

.else

.segment "CODE"
ppu_nrom:
	.incbin PPU_NROM_BIN
	dPPU::data_base = ppu_nrom

.segment "TILES"
	.incbin NROM_CHR0
	.incbin NROM_CHR1
	INES_CHR = 1

.segment "NSF"
nsf_nrom:
	.incbin NSF_NROM_BIN
	.assert (nsf_nrom = $8000), error, "nsf_nrom.bin loaded at the wrong address?"

.segment "CODE"
.proc load_ppu_banks
	rts
.endproc

.endif

;
; region detection
;

.if (eNSF::REGION & 2) ; dual region NSF should auto-detect for region
	.segment "ALIGN"
	.proc detect_region
		; region detect based on code by Damian Yerrick
		; http://wiki.nesdev.com/w/index.php/Detect_TV_system
		.align 32
		ldx #0
		ldy #0
		lda nmi_count
		@wait1:
			cmp nmi_count
			beq @wait1
			lda nmi_count
		@wait2:
			inx
			bne :+
				iny
			:
			cmp nmi_count
			beq @wait2
		tya
		sec
		sbc #10
		; result is 0 for NTSC, otherwise PAL, Dendy, or Unknown
		rts
	.endproc
.else
	.segment "CODE"
	.proc detect_region
		lda #(eNSF::REGION & 1)
		rts
	.endproc
.endif

;
; vectors
;

.segment "VECTORS"
.addr vec_nmi
.addr vec_reset
.addr vec_irq

;
; header
;

.segment "HEADER"
INES_MAPPER = MAPPER
INES_MIRROR = 1
INES_SRAM   = 0
.byte 'N', 'E', 'S', $1A ; ID
.byte BANKS / 4 ; 16k iNES units divided into 4k banks
.byte INES_CHR ; CHR RAM if using mapper 31, CHR ROM if NROM
.byte INES_MIRROR | (INES_SRAM << 1) | ((INES_MAPPER & $f) << 4)
.byte (INES_MAPPER & %11110000)
.byte $0, $0, $0, $0, $0, $0, $0, $0 ; padding

; end of file
