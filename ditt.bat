tiebreakchecker.py -c -i "..\test\GrandMommysCup01.trf" -t PTS PTS:GP EDE BH/C1 BH SB -d T -v > gc01.txt
tiebreakchecker.py -c -i "..\test\MommysCup01.trf" -t PTS PTS:GP EDE BH/C1 BH SB -d T -v > mc01.txt
windiff mc01.txt gc01.txt
