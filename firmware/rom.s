.setcpu "65C02"
; Monitor private zero page; BASIC owns $40-$87 (linker checked).
ptr=$00
endptr=$02
screenptr=$04
source=$06
count=$08
cursor=$0A
column=$0C
savedchar=$0D
bank=$0E
index=$0F
value=$10
recordlen=$12
recordtype=$13
checksum=$14
loadaddr=$15
linebuf=$0200
recordbuf=$0280
VIA=$C100
ORB=VIA
VIA_ORA=VIA+15
DDRB=VIA+2
DDRA=VIA+3
ACR=VIA+11
PCR=VIA+12
IFR=VIA+13
IER=VIA+14

.segment "CODE"
; Stable callable ROM API, all routines preserve X/Y. A/flags clobbered.
; $E000 putc(A), $E003 getc()->A, $E006 refresh, $E009 monitor,
; $E00C cold BASIC. Enter programs via monitor G; RTS returns to monitor.
 jmp console_putc
 jmp console_getc
 jmp screen_flush
 jmp monitor
 jmp basic_cold

reset:
 sei
 cld
 ldx #$FF
 txs
 stz bank
 stz $C000
 lda #$7F
 sta IER
 sta IFR
 stz ACR
 stz VIA_ORA
 stz DDRB
 lda #1
 sta DDRA
 lda #$0C                 ; CA2 manual low, CB1 falling edge
 sta PCR
 jsr screen_clear
 jsr screen_flush
 lda #<banner
 ldy #>banner
 jsr print_string
 jmp monitor

; Four-phase handshake. No timeout: hold the request safely if Pico is absent.
; CB1 rising ACK means data valid, falling ACK means bus released.
bus_begin:
 lda #$1C
 sta PCR
 lda #$10
 sta IFR
 lda #$1E                 ; CA2 high, CB1 rising
 sta PCR
@wait:
 lda IFR
 and #$10
 beq @wait
 rts
bus_end:
 lda #$0E                 ; select falling edge while request still high
 sta PCR
 lda #$10
 sta IFR
 lda #$0C                 ; drop request
 sta PCR
@wait:
 lda IFR
 and #$10
 beq @wait
 lda #$10
 sta IFR
 rts
bus_send:
 pha
 stz VIA_ORA
 lda #$FF
 sta DDRB
 pla
 sta ORB
 jsr bus_begin
 jmp bus_end
bus_receive:
 stz DDRB
 lda #1
 sta VIA_ORA
 jsr bus_begin
 lda ORB                 ; read while Pico holds ACK high/data stable
 pha
 jsr bus_end
 pla
 rts

console_getc:
 phx
 phy
 jsr cursor_send
 jsr bus_receive
 ply
 plx
 rts
basic_getc:
 jsr console_getc
 cmp #$1B
 bne :+
 jmp monitor
:
 cmp #$7F
 bne :+
 lda #8
:
 cmp #10
 bne :+
 lda #13
:
 pha
 cmp #13
 beq @done
 jsr console_putc
@done:
 pla
 rts

screen_clear:
 lda #<$7800
 sta screenptr
 lda #>$7800
 sta screenptr+1
 lda #$20
 ldy #0
@loop:
 sta (screenptr),y
 inc screenptr
 bne :+
 inc screenptr+1
:
 ldx screenptr+1
 cpx #$7F
 bne @loop
 ldx screenptr
 cpx #$D0
 bne @loop
 stz cursor
 stz cursor+1
 stz column
 rts

console_putc:
 phx
 phy
 cmp #13
 beq @newline
 cmp #10
 beq @done               ; console uses CR; ignore LF in CR/LF strings
 cmp #8
 beq @backspace
 cmp #$20
 bcc @done
 cmp #$7F
 bcs @done
 sta savedchar
 jsr cursor_pointer
 lda savedchar
 ldy #0
 sta (screenptr),y
 jsr cell_send
 inc cursor
 bne :+
 inc cursor+1
:
 inc column
 lda column
 cmp #80
 bne @done
 stz column
 jsr screen_scroll
 jsr cursor_send
 bra @done
@newline:
 lda #80
 sec
 sbc column
 clc
 adc cursor
 sta cursor
 bcc :+
 inc cursor+1
:
 stz column
 jsr screen_scroll
 jsr cursor_send
 bra @done
@backspace:
 lda column
 beq @done
 dec column
 lda cursor
 bne :+
 dec cursor+1
:
 dec cursor
 jsr cursor_pointer
 lda #$20
 ldy #0
 sta (screenptr),y
 jsr cell_send
@done:
 ply
 plx
 rts
cursor_pointer:
 lda cursor
 sta screenptr
 lda cursor+1
 clc
 adc #$78
 sta screenptr+1
 rts

screen_scroll:
 lda cursor+1
 cmp #7
 bcc @done
 bne @scroll
 lda cursor
 cmp #$D0
 bcc @done
@scroll:
 lda #<$7800
 sta screenptr
 lda #>$7800
 sta screenptr+1
 lda #<$7850
 sta source
 lda #>$7850
 sta source+1
 ldy #0
@copy:
 lda (source),y
 sta (screenptr),y
 inc source
 bne :+
 inc source+1
:
 inc screenptr
 bne :+
 inc screenptr+1
:
 lda source+1
 cmp #$7F
 bne @copy
 lda source
 cmp #$D0
 bne @copy
 ldx #80
 lda #$20
@blank:
 sta (screenptr),y
 iny
 dex
 bne @blank
 sec
 lda cursor
 sbc #80
 sta cursor
 lda cursor+1
 sbc #0
 sta cursor+1
 jsr screen_flush
@done:
 rts

; SLIP-framed records recover byte-stream alignment after a partial record.
packet_send:
 cmp #$C0
 beq @end_escape
 cmp #$DB
 beq @escape_escape
 jmp bus_send
@end_escape:
 lda #$DB
 jsr bus_send
 lda #$DC
 jmp bus_send
@escape_escape:
 lda #$DB
 jsr bus_send
 lda #$DD
 jmp bus_send
record_begin:
 pha
 lda #$C0
 jsr bus_send
 pla
 jmp packet_send
record_end:
 lda #$C0
 jmp bus_send
; Cell record $02, cell offset low/high, character. Cursor record $03, low/high.
cell_send:
 pha
 lda #2
 jsr record_begin
 lda screenptr
 jsr packet_send
 lda screenptr+1
 sec
 sbc #$78
 jsr packet_send
 pla
 jsr packet_send
 jmp record_end
cursor_send:
 lda #3
 jsr record_begin
 lda cursor
 jsr packet_send
 lda cursor+1
 jsr packet_send
 jmp record_end

; Frame: $01, 2000 screen bytes, cursor offset low/high. No terminal escapes.
screen_flush:
 phx
 phy
 lda #1
 jsr record_begin
 lda #<$7800
 sta screenptr
 lda #>$7800
 sta screenptr+1
 ldy #0
@loop:
 lda (screenptr),y
 jsr packet_send
 inc screenptr
 bne :+
 inc screenptr+1
:
 lda screenptr+1
 cmp #$7F
 bne @loop
 lda screenptr
 cmp #$D0
 bne @loop
 lda cursor
 jsr packet_send
 lda cursor+1
 jsr packet_send
 jsr record_end
 ply
 plx
 rts

console_newline:
 lda #13
 jmp console_putc
print_string:             ; A/Y = zero-terminated address, X/Y clobbered
 sta ptr
 sty ptr+1
 ldy #0
@next:
 lda (ptr),y
 beq @done
 jsr console_putc
 iny
 bne @next
 inc ptr+1
 bra @next
@done:
 rts
print_hex:
 pha
 lsr
 lsr
 lsr
 lsr
 jsr @nibble
 pla
 and #15
@nibble:
 cmp #10
 bcc :+
 adc #6
:
 adc #'0'
 jmp console_putc

monitor:
 sei
 cld
 ldx #$FF
 txs
@prompt:
 jsr console_newline
 lda #'>'
 jsr console_putc
 lda #' '
 jsr console_putc
 jsr read_line
 ldx #0
 jsr skip_spaces
 lda linebuf,x
 cmp #'B'
 bne :+
 jmp basic_cold
:
 cmp #'H'
 bne :+
 lda #<help
 ldy #>help
 jsr print_string
 jmp @prompt
:
 cmp #'R'
 bne :+
 jsr screen_flush
 jmp @prompt
:
 cmp #'L'
 bne :+
 jsr load_hex
 jmp @prompt
:
 cmp #'K'
 beq @bank
 cmp #'G'
 beq @go
 cmp #'D'
 beq @dump
 jmp @bad
@bank:
 inx
 jsr parse_word
 bcs @bad
 lda value+1
 bne @bad
 lda value
 cmp #16
 bcs @bad
 sta bank
 sta $C000
 bra @prompt
@go:
 inx
 jsr parse_word
 bcs @bad
 lda value
 sta loadaddr
 lda value+1
 sta loadaddr+1
 jsr call_program
 jmp monitor
@dump:
 inx
 jsr parse_word
 bcs @bad
 lda value
 sta loadaddr
 lda value+1
 sta loadaddr+1
 ; 16 bytes, no read from I/O by accident
 cmp #$C0
 bcc :+
 cmp #$E0
 bcc @bad
:
 lda loadaddr+1
 cmp #$BF
 bne :+
 lda loadaddr
 cmp #$F1
 bcs @bad
:
 ldy #0
@bytes:
 lda (loadaddr),y
 jsr print_hex
 lda #' '
 jsr console_putc
 iny
 cpy #16
 bne @bytes
 jmp @prompt
@bad:
 lda #'?'
 jsr console_putc
 jmp @prompt
call_program:
 jmp (loadaddr)

read_line:
 stz index
@next:
 jsr console_getc
 cmp #10
 beq @next
 cmp #13
 beq @done
 cmp #$1B
 beq @cancel
 cmp #8
 beq @back
 cmp #$7F
 beq @back
 cmp #$20
 bcc @next
 cmp #$7F
 bcs @next
 cmp #'a'
 bcc :+
 cmp #'z'+1
 bcs :+
 and #$DF
:
 ldx index
 cpx #127
 bcs @next
 sta linebuf,x
 inc index
 jsr console_putc
 bra @next
@back:
 lda index
 beq @next
 dec index
 lda #8
 jsr console_putc
 bra @next
@cancel:
 stz index
@done:
 ldx index
 stz linebuf,x
 jmp console_newline
skip_spaces:
 lda linebuf,x
 cmp #' '
 bne :+
 inx
 bra skip_spaces
:
 rts
hex_nibble:
 lda linebuf,x
 cmp #'0'
 bcc @bad
 cmp #'9'+1
 bcc @digit
 cmp #'A'
 bcc @bad
 cmp #'F'+1
 bcs @bad
 sec
 sbc #7
@digit:
 sec
 sbc #'0'
 inx
 clc
 rts
@bad:
 sec
 rts
hex_byte:
 jsr hex_nibble
 bcs @done
 asl
 asl
 asl
 asl
 sta savedchar
 jsr hex_nibble
 bcs @done
 ora savedchar
 clc
@done:
 rts
parse_word:
 jsr skip_spaces
 jsr hex_byte
 bcs @done
 sta value+1
 jsr hex_byte
 bcs @done
 sta value
 jsr skip_spaces
 lda linebuf,x
 beq @done
 sec
 rts
@done:
 rts

; Intel HEX type 00/01, max 32 bytes/record. Validate complete record before write.
load_hex:
 lda #<load_message
 ldy #>load_message
 jsr print_string
@record:
 jsr read_line
 ldx #0
 lda linebuf
 cmp #':'
 beq :+
 jmp @error
:
 inx
 jsr hex_byte
 bcc :+
 jmp @error
:
 cmp #33
 bcs @error
 sta recordlen
 sta checksum
 jsr checked_byte
 bcs @error
 sta loadaddr+1
 jsr checked_byte
 bcs @error
 sta loadaddr
 jsr checked_byte
 bcs @error
 sta recordtype
 stz count
@data:
 lda count
 cmp recordlen
 beq @sum
 jsr checked_byte
 bcs @error
 ldy count
 sta recordbuf,y
 inc count
 bra @data
@sum:
 jsr checked_byte
 bcs @error
 lda checksum
 bne @error
 lda linebuf,x
 bne @error
 lda recordtype
 beq @write
 cmp #1
 bne @error
 lda recordlen
 ora loadaddr
 ora loadaddr+1
 bne @error
 rts
@write:
 ; Only fixed user RAM $0400-$77FF. No workspace, screen, banks, I/O or ROM.
 lda loadaddr+1
 cmp #4
 bcc @error
 cmp #$78
 bcs @error
 clc
 lda loadaddr
 adc recordlen
 sta endptr
 lda loadaddr+1
 adc #0
 cmp #$78
 bcc @copy
 bne @error
 lda endptr
 bne @error
@copy:
 ldy #0
@loop:
 cpy recordlen
 beq @record_jump
 lda recordbuf,y
 sta (loadaddr),y
 iny
 bra @loop
@record_jump:
 jmp @record
@error:
 lda #<load_error
 ldy #>load_error
 jmp print_string
checked_byte:
 jsr hex_byte
 bcs @done
 pha
 clc
 adc checksum
 sta checksum
 pla
 clc
@done:
 rts

basic_cold:
 sei
 cld
 ldx #$FF
 txs
 ; Cold entry must work with power-on garbage and after machine-code programs.
 ldx #<(FROM+2-ILTrace-1)
@zp:
 stz z:ILTrace,x
 dex
 bpl @zp
 ldx #<(FreeMem+2-mathStack-1)
@workspace:
 stz mathStack,x
 dex
 cpx #$FF
 bne @workspace
 jmp TBasicCold

banner: .byte "6502 USB BOARD ROM 0.1",13,"H FOR HELP",13,0
help: .byte "B BASIC (COLD); ESC RETURNS TO MONITOR",13
 .byte "D AAAA DUMP 16 BYTES; G AAAA CALL PROGRAM",13
 .byte "K 000N BANK (HEX 0-F); R REFRESH",13
 .byte "L LOAD INTEL HEX (00/01, MAX 32 BYTES/RECORD)",13,0
load_message: .byte "SEND INTEL HEX, CR LINES. ESC THEN CR ABORTS.",13,0
load_error: .byte "LOAD ERROR - PREVIOUS VALID RECORDS RETAINED",13,0

.include "basic.inc"
.assert ILTrace = $40, lderror, "Unexpected BASIC zero page start"
.assert FROM+2 <= $C0, lderror, "BASIC zero page exceeds reservation"
.assert mathStack = $300, lderror, "Unexpected BASIC workspace start"
.assert FreeMem+2 <= $400, lderror, "BASIC workspace overlaps user RAM"
.segment "VECTORS"
.word monitor, reset, monitor

