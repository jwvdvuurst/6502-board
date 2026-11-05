// Mechanical as65 -> ca65 port. Original sources stay unmodified.
const fs = require('fs');
const path = require('path');
const root = __dirname;
let src = fs.readFileSync(path.join(root,'vendor/tinybasic/mytb.asm'),'utf8');
src = src.replace(/KIM\s+equ\s+FALSE/, 'KIM equ TRUE').replace(/XKIM\s+equ\s+TRUE/, 'XKIM equ FALSE')
 .replace(/DISK_ACCESS\s+equ\s+TRUE/, 'DISK_ACCESS equ FALSE');
// Replace all platform-vector blocks with this board's ROM ABI.
const first = src.indexOf('\tif\tKIM');
const last = src.search(/^cold2\t/m);
src = src.slice(0,first) + `OUTCH jmp console_putc
GETCH jmp basic_getc
CRLF jmp console_newline
OUTHEX jmp print_hex
MONITOR jmp monitor
` + src.slice(last);
src = src.replace(/org\s+\$0040/, '; zero page allocated by linker')
 .replace(/org\s+\$0200/, '; ROM allocated by linker')
 .replace(/org\s+PROGEND/, '; workspace allocated by linker')
 .replace(/ProgramStart\s+equ\s+\*/, 'ProgramStart equ $0400');
// Limit insertion before the upstream move loop (it also copies one sentinel byte).
src = src.replace(/(jsr\s+getLineLength[^\n]*\n)/, `$1
        clc
        lda PROGRAMEND
        adc lineLength
        lda PROGRAMEND+1
        adc #0
        cmp #$78
        bcc board_room
        lda #0
        ldx #3
        jmp iErr2
board_room:
`);
let support = fs.readFileSync(path.join(root,'vendor/tinybasic/support.asm'),'utf8');
support = support.replace(/\tif ProgramStart < \$2000[\s\S]*?\tendif/, '        lda #$ff\n        sta HighMem\n        lda #$77\n        sta HighMem+1');
// Prevent the original 80-byte input buffer overflowing at 256 characters.
support = support.replace(/(ldx\s+getlinx\s*\n)(\s*sta\s+LINBUF,x)/, '$1        cpx #79\n        bcs getline1\n$2');
function convert(s) {
 return s.split(/\r?\n/).map(line => {
  if (line.startsWith(';')) return line;
  if (line === 'LET;') return '';
  if (/^\s*(list|nolist|end)\s*$/i.test(line)) return '';
  line = line.replace(/\binclude\s+"support.asm"/, '.include "basic-support.inc"')
    .replace(/(?<!\.)\binclude\s+"([^"]+)"/, '.include "$1"')
    .replace(/\bbss\b(?=\s*(;|$))/, '.segment "ZEROPAGE"');
  line = line.replace(/\bcode\b(?=\s*(;|$))/, '.segment "CODE"')
   .replace(/\bequ\b/, '=')
   .replace(/\bds\b/, '.res').replace(/\bdb\b/, '.byte').replace(/\bdw\b/, '.word')
   .replace(/\bendif\b/, '.endif').replace(/\belse\b/, '.else')
   .replace(/^(\s*)if\b/, '$1.if')
   .replace(/^(\w+)\s+macro\s*(.*)$/, '.macro $1 $2').replace(/\bendm\b/, '.endmacro');
  line=line.replace(/#(\w+)&\$ff/g,'#<$1').replace(/#(\w+)(>>8|\/256)/g,'#>$1')
   .replace(/\.byte\s+\(addr-\*\)-1/, '.byte <((addr-*)-1)');
  // as65 permits labels without colons; ca65 needs them except assignments/macros.
  if (/^[A-Za-z_]\w*\s+/.test(line) && !/^\w+\s*=/.test(line)) line=line.replace(/^(\w+)(\s+)/,'$1:$2');
  if (/^\w+$/.test(line)) line += ':';
  return line;
 }).join('\n');
}
let output=convert(src);
const workspace=output.lastIndexOf('.segment "ZEROPAGE"');
output=output.slice(0,workspace)+output.slice(workspace).replace('.segment "ZEROPAGE"','.segment "BSS"');
fs.mkdirSync(path.join(root,'build'),{recursive:true});
for (const [file,data] of Object.entries({'basic.inc':output,'basic-support.inc':convert(support),'IL.inc':convert(fs.readFileSync(path.join(root,'vendor/tinybasic/IL.inc'),'utf8')),'basic.il':convert(fs.readFileSync(path.join(root,'vendor/tinybasic/basic.il'),'utf8'))})) fs.writeFileSync(path.join(root,'build',file),data);
