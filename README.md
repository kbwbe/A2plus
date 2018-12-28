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
* No collision check of parts at moment. Planned for future versions
* Some new small features as visibility helpers (isolate and show only selected parts, transparency of whole assembly)


Is A2plus compatible with Assembly 2 ?
--------------------------------------

No. A2plus would have to handle everything in same way as Assembly 2, including bugs, exact orientations, etc.
You have to assemble existing projects again.


Releases of A2plus available ?
------------------------------

There are prereleases available. Please have a look at the releases section of this repository

Known Issues:
-------------
Weak point is, same as in Assembly 2, updating / reimporting parts from external files.
Constraints will break. You should delete constraints of parts before reimporting them.
After that please constrain these parts again.

This behaviour is due to FreeCAD's lack of topolocigal naming and is difficult to handle at moment.
Some work will be done in future to improve this behaviour.

Installation
------------
A2plus can now be installed by FreeCAD's add-on manager.

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


Features of the A2plus workbench
--------------------------------
(work in progress)

Current Features like shown in the workbench's toolbar:

* Add a part from external file (Shift+A) - 
    Begin and continue here with importing existing part or subassembly .fcstd files to the assembly
* Update parts imported into the assembly - 
    Use this to refresh changed parts already assembled
* Move part - 
    Just move selected part
* Duplicate part - 
    Adds one or more previously imported part(s) into assembly (hold Shift for multiple times)
* Convert part to A2plus form - 
    Converts an imported part to internal representation without external dependency
* Edit - 
    Opens the selected assembly part or subassembly in a new tab, to be changed, don't forget
    to save and refresh the assembly
  
* Constraint Tools - 
    Open a dialog to define constraints. Find all constraints in the opening dialog! 
    This is the access to the A2plus constraining possibilities.
  
  Depending on the context, like selected faces, edges, vertices, one or more of the following 
  list of constraints may get selectable:
  (After selecting the constraint, a 'Constraint Properties' dialog will appear to appropriately ask 
  you for details, like offsets, angles and directions.) 
  Below, first selection is meant for the first part of the constraint (parent) and the second 
  for the second part (child). Choices lists, what you can expect to edit in "Constraint Properties"
  and with the "Edit selected constraint" button later  on.
  - Add a point-to-point identity {pointIdentity constraint} - 
    (1. one point vertex, 2. second point vertex)
  - Add a point-on-line match {pointOnLine constraint} - 
    (1. one point vertex, 2. a line vertex/ edge)
  - Add a point-on-plane match {pointOnPlane constraint} - 
    (1. point vertex or center of a circle, 2. a plane)
    Choices: offset
  - Add a sphere-to-sphere constraint {sphereCenterIdent constraint} - 
    (1. first spherical surface or vertex, 2. second spherical surface or vertex)
  - Add a circular-to-circular-edge match {circularEdge constraint} -
    (1. parent's circular edge, 2. child's circular edge)
    Choices: direction (aligned, opposed) +Flip, offset
  - Add an axis-to-axis identity {axisCoincident constraint} -
    (1. first cylinder face/linear edge, 2. second cylinder face/linear edge)
    Choices: direction (aligned, opposed) + Flip, lockRotation
  - Add an axis-to-axis parallelism {axisParallel constraint}
    (1. first cylinder face/linear edge, 2. second cylinder face/linear edge)
    Selected parts will get rotated, but the axis not coincident.
  - Add an axis-to-plane parallelism {axisPlaneParallel constraint}
    (1. first cylinder axis or linear edge, 2. second part's plane face)
  - Add a plane-to-plane parallelism {planesParallel constraint} -
    (1. parent's plane, 2. child's plane)
    Selected planes would be parallel but not coincident.
    Choices: direction (aligned, opposed) +Flip
  - Add a plane-to-plane coincident match {planeCoincident constraint} -
    (1. parent's plane, 2. child's plane)
    Selected planes would be parallel and you have more choices:
    Choices: direction (aligned, opposed) +Flip, offset
  - Add an angle-between-planes {angledPlanes constraint} -
    Selected planes make the latter object to be rotated by your edited 'angle' value.
    Keep the angle between aprox. 0.1° and 179.9° and use planesParallel for 0° and 180°.

* Edit selected constraint - 
  Select a constraint in the treeview and hit this button to edit it's properties
* Delete constraints - 
  Remove all constraints of exactly one selected part in one step
  
* Solve A2plus constraints - 
  Manually invoke the A2pus solver (especially when AutoSolve is OFF) 
* Toggle Autosolve - 
  By pressing this button you can enable or disable automatic solving after a constraint
  has been edited. If Autosolve is disabled you have to start it manually by hitting the
  Solve button. Disabled, this can save computation time.
* Flip direction of last constraint - 
  does exactly what it means for suitable constraints
* Print detailed DOF information to console - 
  shows the degrees-of-freedom for the current constraints' solving state,
  useful for analysing eventually missing constraints
* Generate HTML file with detailed constraining structure - 
  useful to visualize the current constraint dependencies
  
* Show connected elements - 
  highlights the parts connected by a constraint selected in treeview
* Toggle transparency of assembly - 
  The whole assembly will get transparent
* Show only selected items, or all if none selected - 
  Another visibility helper for assembly analysis
  
* Create or refresh simple shape of complete assembly -
  the newly created compound can be found in treeview
* Repair the treeview, if damaged somehow - 
  After pressing this button constraints will be grouped under corresponding parts again
* Create a spreadsheet with logistic/ordering information - 
  Adds a spreadsheet to the treeview, editable by double-click in a new tab for part's info
* Create a spreadsheet with a partlist of this file -
  Adds a spreadsheet to the treeview, editable by double-click in a new tab for assembly's BOM info


Usage hints for the A2plus workbench
------------------------------------
(work in progress)

Have a look on the Feature list above, and...
Please, follow the Tooltips in the workbench's toolbar and in the "Constraint Tools" toolbox. They 
describe what to do in which order.

First steps to create an A2plus assembly:

* Open a new .fcstd file and save it with a name. (If not, you'd be asked for by A2plus.)
* Import a .fcstd file.
* The first imported file gets set as fixed (position) by default. (You can change later.)
* Import a second .fcstd file
* Select some faces or edges or vertices, you want to constrain, and push the "Constraint Tools" button, 
  the Tools menu pops-up,
  alternatively you can push the button first and select the constraint's context afterwards
* Related to the context you'd be asked in the "Constraints Properties" (sub-menu), to edit the
  appropriate parameters, to delete the constraint, to solve and or accept it.
* You can edit once-set "Constraints Properties" at any time later via the "Edit selected constraint" button.


Editing a subassembly:

* As you can also load a subassembly as a .fcstd file, you can also open it via the A2plus edit command,
  to edit it. Please just make sure for higher assembly stages, to reload the changes file(s).

