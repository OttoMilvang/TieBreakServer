# TieBreakServer
## 🚀 Install Tie-Break Server


- **Downlaod project**

- **Install python 3, min version 3.8**<br>
3.8 becase this is the last python distribution that runs on Win7

- **python pairingchecker.py**
- **python tiebreakchecker.py**
- **python tournamentgenerator.py**

## 🦋 Common command line parameters
- **-i \<file\>** or **--input-file \<file\>**  - Tournament file
- **-o \<file\>** or **--output-file \<file\>** - Output file, use *-* for stdout
- **-f \<fileformat\>** or **--file-format \<fileformat\>** - TRF for <A HREF="https://www.fide.com/FIDE/handbook/C04Annex2_TRF16.pdf">FIDE TRF-16/TRF-25</A>, JCH for Chess-JSON, TS for Tournament Service files
- **-b** or **--encoding** - character encoding <A HREF="https://docs.python.org/3/library/codecs.html#standard-encodings"> (ascii, utf-8, latin-1, ...)</A>
- **-e \<number\>** or **--event-number \<number\>** - In files with multiple event, tournaments are numbered 1,2,3, ... use 0 for passthrough
- **-c** or **--check** - Check tie-break calculation
- **-n \<number\>** or **--number-of-rounds \<number\>** - Number of rounds in Tie-break calculation
- **-d \<delimiter\>** or **--delimiter  \<delimiter\>** - Predefined delimiters @=Check-status B=blank, T=tab, S=Semicolon, C=comma, default is JSON output

## 🦋 Pairingchecker

### 👷 Command line parameters

- **-a** or **--analyze** - Analyze pairing
- **-p** or **--pairing** - Do pairing
- **-m \<method\>** or **--method \<method\>** - dutch (| berger not implemented)
- **-t \<w | b\>** or **--top-color \<w | b\>** - Color on top board")
- **-u \<list\>** or **--unpaired \<list\>** - list of competiters that shall not be paired for next round
- **-x \<list\>** or **--experimental \<list\>** - list of kewords, "weighted" - use weighted


### 👷 Examples

- python pairingchecker.py -i \<infile\> -o \<outfile\> -p -dT <br>
Pair the next round of the tournament 
- python pairingchecker.py -i \<infile\> -c -dT <br>
Check all rounds of the inputfile for correct pairing, output to terminal
- python pairingchecker.py -i \<infile\> -c -a -p -n \<round\> -dT -x weighted<br>
Check round \<n\> with weighted algorithm and write detailed pairing


## 🦋 Tiebreakchecker

### 👷 Command line parameters

- **-t \<list\>** or **--tie-break \<list\>** - List of Rank order specifiers, default read from tournament file
- **-p** or **--pre-determined** - Use rules as tournament has pre-defined pairing
- **-s** or **--swiss** - Use rules as tournament is a swiss tournament
- **-r** or **--rank** - Print result in rank order
- **-u \<number\>** or **--unrated \<number\>** - Set rating for unrated players 

### 👷 Rank order specifiers
The Rank order specifiers has the form
**TB:PS/Mn-optlist**
- **TB** - required, TieBreak name
- **:PS** - Point system name for team competitions, <br>MP=match points(default), <br>GP=game points
- **#Mn** - Modifier<br>C=cut, <br>M=medial, <br>L=limit, <br>n=number
- **-optlist** -<br>
<A HREF="https://fide-tec.gacrux.no:9001/tbs/tiebreaklist.html">Open  full TB-list</A>

### 👷 Examples

- python tiebreakchecker.py -i \<infile\> -o \<outfile\> -c -dT -t PTS GH:GP/C1 DE/P<br>
Print tiebreak values for the given tiebreaks

## 🦋 Tournamentgenerator

### 👷 Command line parameters

- **-g \<number\>** or **--generate \<number\>** - Generate \<number\> tournaments 
- **-p \<number\>** or **--players \<number\>** - Number of players in the tournament
- **-n \<number\>** or **--number-of-rounds \<number\>** - Number of rounds
- **-t \<w | b\>** or **--top-color \<w | b\>** - Color on top board")
- **-r \<args\>** or **--rating \<list\>** - List of 3 numbers, \<higest rating\> \<step rating\> \<sigma\>
- **-s \<args\>** or **--statistics \<list\>** - List of 3 numbers,  \<rate zpb\> \<rate hpb\>  \<rate forfeited\> 
- **-x \<list\>** or **--experimental \<list\>** - list of kewords, "weighted" - use weighted

### 👷 Examples

 - python tournamentgenerator.py -n 9 -x weighted -p 15 -r 2200 10 50.0 -s 0.02 0.10 0.04 -o C:/temp/t_n9_p15_d10_s50/T%d.trf -g 10000<br>
 This will create directory C:/temp/t_n9_p15_d10_s50 and generate 10000 tournamen numbered T0000.trf to T9999.trf<br>
 Top color will alternate unless -t flag say otherwise  
