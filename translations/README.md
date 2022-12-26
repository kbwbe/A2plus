# About translation A2plus Workbench.

Note: all command must be run in "A2plus/translations/" directory.

## 1. For create new language file with all A2plus strings:

$ python3 update_ts.py -c

## 2. Now you can rename new A2plus.ts file to 'A2plus_"you language two or four letters".ts' file ('A2plus_it.ts' for Italy) or use command:

$ pylupdate5 -verbose ../*.py -ts A2plus_it.ts

## 3. For edit your language file open this file in 'QT Linguist' or in text editor - 'xed', 'mousepad', 'gedit' etc.
And translate it.


## 4. For update all language files (for developers only) from source files you can use this command:

$ python3 update_ts.py -u


## 5. For convert all .ts files to .qm files (merge) you can use this command:

$ python3 update_ts.py -m


## 6. Now you can upload your translated .ts file to A2plus site:
https://github.com/kbwbe/A2plus

### More information:
https://wiki.freecad.org/Translating_an_external_workbench
