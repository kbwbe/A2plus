# About translating A2plus Workbench

A2plus Workbench supported 10 locales:

English:            en,
Chinese Simplified: zh-CN,
French:             fr,
German:             de,
Lithuanian:         lt,
Portuguese:         pt-PT,
Portuguese, Brazilian: pt-BR,
Russian:            ru,
Spanish:            es-ES,
Spanish, Argentina: es-AR,

You can add your own language in this list!
Join to us!


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
pylupdate6 --verbose ../*.py --ts A2plus_it.ts
```

## 3. Translating

To edit your language file open your file in `Qt Linguist` from `qt6-tools`
or in a text editor like `xed`, `mousepad`, `gedit`, `nano`, `vim`/`nvim`,
`geany` etc and translate it.

## 4. Sending translations

Now you can contribute your translated `.ts` file to **A2plus** repository

<https://github.com/kbwbe/A2plus>


For developers only:

## 5. Updating translations

To update all language files from source files you should use this command:

```shell
python3 update_ts.py -u
```

## 6. Compiling translations

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

## More information

You can read more about translating external workbenches here:

<https://wiki.freecad.org/Translating_an_external_workbench>
