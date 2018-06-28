# A2plus
Another assembly workbench for FreeCAD, following and extending Hamish's Assembly 2 workbench

It is for use with FreeCAD v0.16, v0.17 and v0.18 with support for importing parts from external files.
This workbench project has been started as a fork of Hamish's Assembly 2 workbench, which is not maintained at
moment of writing this.

The workbench project tries to implement a new constraint solving algorithm to avoid some problems 
occured with original solver. It is still under development and experimental now, but shows some potential.

Main goal of A2plus is to create a very simple, easy to use and not overfeatured workbench for 
FreeCAD assemblies. Using the KISS principle: DO IT SIMPLE, STUPID

Linux Installation Instructions
-------------------------------
FreeCAD-version of your choice has to be installed before
Use commandline bash to install A2plus

```bash
$ sudo apt-get install git python-numpy python-pyside
$ mkdir ~/.FreeCAD/Mod
$ cd ~/.FreeCAD/Mod
$ git clone https://github.com/kbwbe/A2plus.git
```

Once installed, use git to easily update to the latest version:

```bash
$ cd ~/.FreeCAD/Mod/A2plus
$ git pull
$ rm *.pyc
```

Windows Installation Instructions
---------------------------------
FreeCAD-version of your choice has to be installed before

Download the git repository as ZIP

Refer to the corresponding tutorial on the FreeCAD-Homepage:
http://www.freecadweb.org/wiki/index.php?title=How_to_install_additional_workbenches

Unzip the downloaded repository within your Mod-folder. A A2plus-folder should apear
in your Mod-folder

Mac Installation Instructions
-----------------------------
(borrowed from Hamish2014)

* download the git repository as ZIP
* assuming FreeCAD is installed in "/Applications/FreeCAD/v 0.17", 
    go to "/Applications/FreeCAD/v 0.17" in the Browser, and select FreeCAD.app
* right-click and select "Show Package Contents", a new window will appear with a folder named "Contents"
* single-click on the folder "Contents" and select the folder "Mod"
* in the folder "Mod" create a new folder named "A2plus"
* unzip downloaded repository in the folder "Contents/Mod/A2plus"


Usage of A2plus workbench:
--------------------------
(Work in progress)

For first steps you can have look at tutorials related to Hamish's Assembly 2. Usage of A2plus is very similar


