# A2plus
Another assembly workbench for FreeCAD, following and extending [Hamish's Assembly 2 workbench](https://github.com/hamish2014/FreeCAD_assembly2)

This workbench project has been started as a fork of Hamish's Assembly 2 workbench, which is not maintained at
moment of writing this. A2plus can be used with FreeCAD v0.16, v0.17 and v0.18 including support for importing parts from external files.

This workbench tries to implement a new constraint solving algorithm to avoid some problems that
occurred with the original solver. It is still under development and experimental at this moment but is showing some potential.

The main goal of A2plus is to create a very simple, easy to use, and not over-featured workbench for
FreeCAD assemblies. Using the KISS principle: KEEP IT SIMPLE, STUPID

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
Pre-requisite: FreeCAD >= v0.16+

Download the git repository as a ZIP on to you local drive.

Refer to the corresponding tutorial on the FreeCAD-Homepage:
http://www.freecadweb.org/wiki/How_to_install_additional_workbenches

Unzip the downloaded repository within your Mod/ folder. A A2plus-folder should appear
within you Mod/ folder.

If you a familiar with `git` you can `git clone https://github.com/kbwbe/A2plus.git` directly in to your Mod/ folder.

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

As your first steps learning this workbench, please have look at tutorials related to Hamish's Assembly 2. A2plus is very similar.
