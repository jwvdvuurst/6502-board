.setcpu "65C02"
.segment "CODE"
; Link at $0400, load with L, execute with G 0400. Console preserves X/Y.
 ldx #0
loop:
 lda message,x
 beq done
 jsr $E000
 inx
 bra loop
done:
 rts
message: .byte "HELLO FROM A LOADED PROGRAM!",13,0
