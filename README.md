# A2plus
Another assembly workbench for FreeCAD, following and extending [Hamish's Assembly 2 workbench](https://github.com/hamish2014/FreeCAD_assembly2)

This workbench project has been started as a fork of Hamish's Assembly 2 workbench, which is not maintained at
moment of writing this. A2plus can be used with FreeCAD v0.16, v0.17 and v0.18 including support for importing parts from external files.

This workbench tries to implement a new constraint solving algorithm to avoid some problems that
occurred with the original solver. It is still under development and experimental at this moment but is showing some potential.

The main goal of A2plus is to create a very simple, easy to use, and not over-featured workbench for
FreeCAD assemblies. Using the KISS principle: KEEP IT SIMPLE, STUPID


What are the differences between Assembly 2 and A2plus ?
--------------------------------------------------------

Similar is:

* the workflow and kind of user interface, so users of Assembly 2 can use it in an intuitive way
* Same as Assembly 2 it mainly aims at importing external files to the assembly.

Different is:
* A new designed solving algorithm, able to solve some more complicated relations.
* Different and in future more constraints, internally with different names. 
* No animation for degrees of freedom, as difficult for new solver type.
* No parts list at moment. Export to office spreadsheats planned for future versions.
* No collision check of parts at moment. Planned for future versions
* Some new small features as visibility helpers (isolate and show only selected parts, transparency of whole assembly)


Is A2plus compatible with Assembly 2 ?
--------------------------------------

No. A2plus would have to handle everything in same way as Assembly 2, including bugs, exact orientations, etc.
You have to assemble existing projects again.


Releases of A2plus available ?
------------------------------

Not at moment. A2plus is in very early alpha state, but already functional for small projects.

Known Issues:
-------------
Weak point is, same as in Assembly 2, updating / reimporting parts from external files.
Constraints will break. You should delete constraints of parts before reimporting them.
After that please constrain these parts again.

This behaviour is due to FreeCAD's lack of topolocigal naming and is difficult to handle at moment.
Some work will be done in future to improve this behaviour.


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

You can follow the tool-tips in the workbench's toolbar. They describe exactly what to do in which order.

Current Features like shown in the workbench's toolbar:
* Add a part from external file (Shift+A) - 
    Begin and continue here with adding (importing existing files) .fcstd parts
* Update parts imported into the assembly - 
    Use this to refresh changed parts already assembled
* Move part - 
    Just move selected part
* Duplicate part - 
    Adds one or more previously imported part into assembly
* Edit - 
    Opens the selected assembly part to be changed in a new tab
* Add a point-to-point identity {pointIdentityConstraint} - 
    Fix a point vertex to another point vertex
* Add a point-on-line match {pointOnLineConstraint} - 
    Fix a point vertex to a line vertex
* Add a point-on-plane match {pointOnPlaneConstraint} - 
    Fix a point vertex to be on a plane
* Add a circular-to-circular edge match {circularEdgeConstraint} - 
    Fix one circular edge to another. You can choose a special direction (aligned, opposed or none). 
    An offset can be applied
* Add a plane-to-plane parallelism {planeParallel} - 
    Adjust selected planes to be parallel. You can choose a special direction (aligned, opposed)
* Add a plane-to-plane offset {planeConstraint} - 
    Makes planes parallel and offers to give an offset value and direction (aligned, opposed,none)
* Add an axis-to-axis identity {axialConstraint} - 
    Makes cylindrical objects or two axes to be axially aligned
* Add an angle between planes {angledPlanesConstraint} - 
    Selected planes make the latter object to be rotated by your edited 'angle' value.
    Keep the angle between aprox 0.1° and 179.9° or use workarounds. 
* Add a spherical constraint between objects - 
    Select spheres to be aligned or vertex/sphere or vertex/vertex
* Solve A2plus constraints - 
    Manually invoke the A2pus solver (especially when AutoSolve is OFF)
* Delete constraints - 
    Remove all constraints of selected part in one step
* View constrained element - 
    Show all elements for a Tree view selected constraint
* SAS Create or refresh simple shape of complete assembly - 
    the newly created compound can be found in tree vies
* Toggle transparency of assembly - 
    The whole assembly will get transparent
* Show only selected items (or all if none selected) - 
    Just another visibility helper
* Toggle AutoSolve - 
    Normally the solver defaults to and works with AutoSolve, but for larger
    assemblies one may chose OFF and solve manually, as it saves computation time.
