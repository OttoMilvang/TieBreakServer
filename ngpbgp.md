# ngpbgp
## 🚀 Compute rank for Norwegian NGP / BGP from tournamentService file


- **Downlaod project**

- **Install python 3, min version 3.10**

- **run ngpbgp.py**

## 🦋 Command line parameters
- **-i** or **--input-file**  - Tournament file
- **-o** or **--output-file** - Output file, use *-* for stdout
- **-e** or **--event-number** - In files with multiple event, tournaments are numbered 1,2,3, ... use 0 for passthrough
- **-d** or **--delimiter** - Predefined delimiters B=blank, T=tab, S=Semicolon, C=comma, default is JSON output
- **-t** or **--tie-break** - List of Rank order specifiers, default is PTS BH/C1 BH ARO
- **-s** or **--split** - Split groups with mulitples classes
- **-l** or **--listmode** - Just list file header and group size

## 👷 Rank order specifiers
The Rank order specifiers has the form
**TB:PS#Mn-optlist**
- **TB** - required, TieBreak name
- **:PS** - Point system name for team competitions, <br>MP=match points(default), <br>GP=game points
- **/Mn** - Modifier<br>C=cut, <br>M=medial, <br>L=limit, <br>n=number
- **-optlist** -<br>
-P - forfeited games, either wins or losses, are considered as played games against the scheduled opponent <br>
-U - all unplayed rounds are considered as Draws - against themself (DAT) to compute the participant's TB<br>
-V - the article 14.6 is ignored, i.e., the least significant value is cut, regardless of the surroundings<br>

**Examples**<br>
**PTS**  - Points<br>
**BH:GP/C1** - Buchholz cut-1 calculated on game points <br>
**DE-P** - Direct encounter, forfeited games, either wins or losses, are considered as played games against the scheduled opponent <br>
**PTS BH/C1 BH ARO** - Points, Buchholz-Cut1, Buchholz, Average Rating of opponents  <br>
