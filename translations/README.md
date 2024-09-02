# About translating A2plus Workbench

**Note**: all commands **must** be run in `A2plus/translations/` directory.

## 1. Creating file for missing locale

To create a file for a new language with all **A2plus** translatable strings execute:

```shell
python3 update_ts.py -c
```

## 2. Renaming file

Now you can rename new `A2plus.ts` file by:

- appending the locale code, example: `A2plus_it.ts` for Italy or
- using command:

    ```shell
    pylupdate5 -verbose ../*.py -ts A2plus_it.ts
    ```

As of 31/08/2024 the supported locales on FreeCAD
(according to `FreeCADGui.supportedLocales()`) are 43:

```python
{'English': 'en', 'Afrikaans': 'af', 'Arabic': 'ar', 'Basque': 'eu',
'Belarusian': 'be', 'Bulgarian': 'bg', 'Catalan': 'ca',
'Chinese Simplified': 'zh-CN', 'Chinese Traditional': 'zh-TW', 'Croatian': 'hr',
'Czech': 'cs', 'Dutch': 'nl', 'Filipino': 'fil', 'Finnish': 'fi', 'French': 'fr',
'Galician': 'gl', 'Georgian': 'ka', 'German': 'de', 'Greek': 'el', 'Hungarian': 'hu',
'Indonesian': 'id', 'Italian': 'it', 'Japanese': 'ja', 'Kabyle': 'kab',
'Korean': 'ko', 'Lithuanian': 'lt', 'Norwegian': 'no', 'Polish': 'pl',
'Portuguese': 'pt-PT', 'Portuguese, Brazilian': 'pt-BR', 'Romanian': 'ro',
'Russian': 'ru', 'Serbian': 'sr', 'Serbian, Latin': 'sr-CS', 'Slovak': 'sk',
'Slovenian': 'sl', 'Spanish': 'es-ES', 'Spanish, Argentina': 'es-AR',
'Swedish': 'sv-SE', 'Turkish': 'tr', 'Ukrainian': 'uk', 'Valencian': 'val-ES',
'Vietnamese': 'vi'}
```

## 3. Translating

To edit your language file open your file in `Qt Linguist` from `qt5-tools`
or in a text editor like `xed`, `mousepad`, `gedit`, `nano`, `vim`/`nvim`,
`geany` etc. and translate it.

## 4. Updating translations

To update all language files from source files (for developers only)
you should use this command:

```shell
python3 update_ts.py -u
```

## 5. Compiling translations

To convert all `.ts` files to `.qm` files (merge) you can use this command:

```shell
python3 update_ts.py -m
```

If you are a translator that wants to update only their language file
to test it on **FreeCAD** before doing a PR you can use this command:

```shell
lrelease A2plus_it.ts
```

This will update the `.qm` file for your language (Italian in this case).

## 6. Sending translations

Now you can contribute your translated `.ts` file to **A2plus** repository

<https://github.com/kbwbe/A2plus>

## More information

You can read more about translating external workbenches here:

<https://wiki.freecad.org/Translating_an_external_workbench>
