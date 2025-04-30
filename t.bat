del t1.log
del t2.log
for %%s in (0) do (
for %%t in (0) do (
for %%u in (0,1,2) do (
for %%v in (0,1,2,3,4,5,6,7,8,9) do (
for %%g in (1,2,3,4,5,6,7,8,9,10,11,12,13,14,15,16,17,18,19,20,21) do (
echo t53-10-Swiss-Fiderating-21\T%%s%%t%%u%%v.trfx -n%%g  >> t1.log
python ..\tiebreakchecker\pairingchecker.py -dT -p -i ..\t53-10-Swiss-Fiderating-21\T%%s%%t%%u%%v.trfx -n%%g  >> t1.log
echo t53-10-Swiss-Fiderating-21\T%%s%%t%%u%%v.trfx -n%%g  >> t2.log
python ..\tiebreakchecker\pairingchecker.py -dT -p -i ..\t53-10-Swiss-Fiderating-21\T%%s%%t%%u%%v.trfx -n%%g -x XC14M1 XC16M1  >> t2.log
)
)
)
)
)