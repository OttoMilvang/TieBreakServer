# TieBreakServer
## 🚀 Install Tie-Break Server


- **Downlaod project**

- **Install python 3, min version 3.10**

- **run tiebreakchecker.py**

## 🦋 Command line parameters
- **-i** or **--input-file**  - Tournament file
- **-o** or **--output-file** - Output file, use *-* for stdout
- **-f** or **--file-format** - TRF for <A HREF="https://www.fide.com/FIDE/handbook/C04Annex2_TRF16.pdf">FIDE TRF-16</A>, JCH for Chess-JSON, TS for Tournament Service files
- **-b** or **--encoding** - character encoding <A HREF="https://docs.python.org/3/library/codecs.html#standard-encodings"> (ascii, utf-8, latin-1, ...)</A>
- **-e** or **--event-number** - In files with multiple event, tournaments are numbered 1,2,3, ... use 0 for passthrough
- **-c** or **--check** - Check tie-break calculation
- **-n** or **--number-of-rounds** - Number of rounds in Tie-break calculation
- **-d** or **--delimiter** - Predefined delimiters @=Check-status B=blank, T=tab, S=Semicolon, C=comma, default is JSON output
- **-t** or **--tie-break** - List of Rank order specifiers, default read from tournament file

## 👷 Rank order specifiers
The Rank order specifiers has the form
**TB:PS/Mn-optlist**
- **TB** - required, TieBreak name
- **:PS** - Point system name for team competitions, <br>MP=match points(default), <br>GP=game points
- **#Mn** - Modifier<br>C=cut, <br>M=medial, <br>L=limit, <br>n=number
- **-optlist** -<br>
<A HREF="https://fide-tec.gacrux.no:9001/tbs/tiebreaklist.html">Open  full TB-list</A>

**Examples**<br>
**PTS**  - Points<br>
**BH:GP/C1** - Buchholz cut-1 calculated on game points <br>
**DE/P** - Direct encounter, forfeited games, either wins or losses, are considered as played games against the scheduled opponent <br>
