#***************************************************************************
#*                                                                         *
#*   Copyright (c) 2018 Turro75                                              *
#*                                                                         *
#*   Portions of code based on hamish's assembly 2                         *
#*                                                                         *
#*   This program is free software; you can redistribute it and/or modify  *
#*   it under the terms of the GNU Lesser General Public License (LGPL)    *
#*   as published by the Free Software Foundation; either version 2 of     *
#*   the License, or (at your option) any later version.                   *
#*   for detail see the LICENCE text file.                                 *
#*                                                                         *
#*   This program is distributed in the hope that it will be useful,       *
#*   but WITHOUT ANY WARRANTY; without even the implied warranty of        *
#*   MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the         *
#*   GNU Library General Public License for more details.                  *
#*                                                                         *
#*   You should have received a copy of the GNU Library General Public     *
#*   License along with this program; if not, write to the Free Software   *
#*   Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA  02111-1307  *
#*   USA                                                                   *
#*                                                                         *
#***************************************************************************

import FreeCAD, FreeCADGui, Part
from  FreeCAD import Base
from PySide import QtGui, QtCore




'''
Library that defines the DOF of a Rigid, each rigids has several dependencies which define a refPoint(cross point the the axis)
and a refAxisEnd which is a vector that defines the direction, togeher we can define an axis used in the constraint.

This code was possible only after the reading of the Hamish's code on His wonderful Assembly2 Workbench for FreeCAD
This code was possible only after the reading of the Hamish's code on His wonderful WorkFeature Macro for FreeCAD
This code was possible only after the reading of Wikipedia pages on vector math 

'''


#define some reference axis
SystemOrigin = FreeCAD.Vector(0,0,0)

SystemXAxis = FreeCAD.Axis()
SystemXAxis.Base = SystemOrigin
SystemXAxis.Direction = SystemXAxis.Direction.add(FreeCAD.Vector(1,0,0))

SystemYAxis = FreeCAD.Axis()
SystemYAxis.Base = SystemOrigin
SystemYAxis.Direction = SystemYAxis.Direction.add(FreeCAD.Vector(0,1,0))

SystemZAxis = FreeCAD.Axis()
SystemZAxis.Base = SystemOrigin
SystemZAxis.Direction = SystemZAxis.Direction.add(FreeCAD.Vector(0,0,1))


#at the beginning each rigid is able to move along and around all six DOF
PosDOF = [SystemXAxis , SystemYAxis, SystemZAxis]
RotDOF = [SystemXAxis , SystemYAxis, SystemZAxis]
#another array which stores the vertex used in points constraints (pointIdentity, SphericalIdentity, pointOnLine, pointOnPlane)
PointConstraints = []

tolerance = 1e-6  #--> may be equal to parameter accuracy?

#as first some helper functions

#create an axis which is normal to the plane defined by given 2 axes as argument
def normal_2Axis(axisa,axisb,dbg=False):
    #move vectors to origin and normalize
    axis1 = FreeCAD.Axis(axisa)
    axis2 = FreeCAD.Axis(axisb)      
    axis1.Base = SystemOrigin
    axis2.Base = SystemOrigin
    axis1.Direction = axis1.Direction.normalize() #useless?
    axis2.Direction = axis2.Direction.normalize() #useless?
    #create an axis with base at SystemOrigin 
    axisN = FreeCAD.Axis()
    #set the right direction 
    axisN.Direction = axis1.Direction.cross(axis2.Direction)   
    if dbg: print axis1, axis2, axisN  
    return axisN

#create a plane normal to the given axis, return the 2 axis which define that plane 
def make_planeNormal(axisa,dbg=False):
    axis1 = FreeCAD.Axis(axisa)
    axis1.Base = SystemOrigin
    axis1.Direction = axis1.Direction.normalize()    
    planenormal = Part.makePlane(1.0,1.0, axis1.Base, axis1.Direction)
    freeAx1 = FreeCAD.Axis()
    freeAx2 = FreeCAD.Axis()
    freeAx1.Direction = FreeCAD.Vector(planenormal.Vertexes[2].Point)
    freeAx2.Direction = FreeCAD.Vector(planenormal.Vertexes[1].Point)
    if dbg: print planenormal.Vertexes[0].Point, planenormal.Vertexes[1].Point, planenormal.Vertexes[2].Point, planenormal.Vertexes[3].Point
    return [freeAx1,freeAx2]


#check if 2 axes are parallel
def check_ifParallel(axisa,axisb,dbg=False):
    #shift edges to the origin and normalize them
    #move vectors to origin and normalize
    axis1 = FreeCAD.Axis(axisa)
    axis2 = FreeCAD.Axis(axisb)      
    axis1.Base = SystemOrigin
    axis2.Base = SystemOrigin
    axis1.Direction = axis1.Direction.normalize() #useless?
    axis2.Direction = axis2.Direction.normalize() #useless?
    if abs((axis1.Direction.cross(axis2.Direction)).Length) <= tolerance:
        if dbg:print("Parallel Edges" , axis1, axis2 )
        return True
    else:
        if dbg:print("Non Parallel Edges", axis1, axis2 )
        return False


#check if 2 axes are perpendicular
def check_ifPerpendicular(axisa,axisb,dbg=False):
    #shift edges to the origin and normalize them
    #move vectors to origin and normalize
    axis1 = FreeCAD.Axis(axisa)
    axis2 = FreeCAD.Axis(axisb)    
    axis1.Base = SystemOrigin
    axis2.Base = SystemOrigin
    axis1.Direction = axis1.Direction.normalize() #useless?
    axis2.Direction = axis2.Direction.normalize() #useless?
    if abs(axis1.Direction.dot(axis2.Direction)) <= tolerance:
        if dbg:print("Perpendicular Edges" , axis1, axis2 )
        return True
    else:
        if dbg:print("Perpendicular Edges", axis1, axis2 )
        return False

#check if 2 axes are collinear
def check_ifCollinear(axisa,axisb,dbg=False):
    #shift edges to the origin and normalize them
    #move vectors to origin and normalize
    axis1 = FreeCAD.Axis(axisa)
    axis2 = FreeCAD.Axis(axisb)
    if check_ifCoincident(axis1.Base, axis2.Base):
        #same base, if parallel the axis are collinear
        if check_ifParallel(axis1,axis2):
            return True
        else:
            return False 
    baseMove = SystemOrigin.sub(axis1.Base)  
    axis1.Base = SystemOrigin
    axis2.move(baseMove)
    axis1.Direction = axis1.Direction.normalize() #useless?
    axis2.Direction = axis2.Direction.normalize() #useless?
    axis3 = FreeCAD.Axis()
    axis3.Direction = axis2.Base #create an axis with direction base1 to base2 
    
    if check_ifParallel(axis1,axis3) and check_ifParallel(axis2,axis3):
        if dbg:print("Collinear Edges" , axis1, axis2 )
        return True
    else:
        if dbg:print("Non Collinear Edges", axis1, axis2 )
        return False

#check if 2 vertexes are coincident
def check_ifCoincident(Vertex1, Vertex2, dbg=False):
    _X1=Vertex1.x
    _X2=Vertex2.x
    _Y1=Vertex1.y
    _Y2=Vertex2.y
    _Z1=Vertex1.z
    _Z2=Vertex2.z
    if (abs(_Z2 - _Z1) <= tolerance) and (abs(_X2 - _X1) <= tolerance) and (abs(_Y2 - _Y1) <= tolerance):
        if dbg: print "Vertexes Coincident", Vertex1, Vertex2
        return True
    else:
        if dbg: print "Vertexes Not Coincident", Vertex1, Vertex2    
        return False

#check if a point is on an axis
def check_ifPointOnAxis(vertexa, axisa, dbg=False):
    #shift edges to the origin and normalize them
    #move vectors to origin and normalize
    axis1 = FreeCAD.Axis(axisa)
    vertex1 = FreeCAD.Vector(vertexa)    
    _offset = SystemOrigin.sub(axis1.Base)  
    axis1.Base = SystemOrigin
    axis1.Direction = axis1.Direction.normalize() #useless?
    vertex1 = vertex1.sub(_offset) #apply the same offset to the point
    if abs((axis1.Direction.cross(vertex1)).Length) <= tolerance:
        if dbg:print("Point on Axis" , vertex1, axis1 )
        return True
    else:
        if dbg:print("Point not on Axis", vertex1, axis1 )
        return False    



#now that all helper functions are in place let's start to analyse all basic constraints
#constraints in the toolbar are a combination of basic constraints

#start with Axis Alignment which takes an axis as arguments and operates according to the remaining dof
#this basic constraint affects only rotation DOF
def AxisAlignment(axisa , dofrot, dbg=True):
    currentDOFROTnum = len(dofrot)   
    if currentDOFROTnum == 0 : #already locked on rotation so ignore it
        return []
    elif currentDOFROTnum == 1 : #partially locked on rotation so compare to the given axis
        if check_ifCollinear(axisa,dofrot[0]):
            #the axis are collinear, so the constraint is redundant, skip it
            return dofrot
        else:
            #the axis locks permanently the rotation so DOFRot=[]
            return []
    elif currentDOFROTnum == 3 : #no constraints on rotation so the given axis is the one left free
        return [axisa]
    else:
        #this shouldn't happens...ignore it and return the current dofrot
        return dofrot 


#then Lock Rotation which locks the remaining rotation axis when enabled
#this basic constraint affects only rotation DOF
def LockRotation(enabled, dofrot, dbg=True):
    if enabled and (len(dofrot)==1):
        #lock rotation is only read when a dofrot is 1
        return []
    else:
        #nothing to do return the given dofrot
        return dofrot            

#then Angle Alignment which takes an axis as arguments and operates according to the remaining dof
#the axis is the normal of the angled plane, that said it acts exaclty as axis alignment, meybe I'll remove it
#this basic constraint affects only rotation DOF
def AngleAlignment(axisa , dofrot, dbg=True):
    currentDOFROTnum = len(dofrot)   
    if currentDOFROTnum == 0 : #already locked on rotation so ignore it
        return dofrot
    elif currentDOFROTnum == 1 : #partially locked on rotation so compare to the given axis
        if check_ifCollinear(axisa,dofrot[0]):
            #the axis are collinear, so the constraint is redundant, skip it
            return dofrot
        else:
            #the axis locks permanently the rotation so DOFRot=[]
            return []
    elif currentDOFROTnum == 3 : #no constraints on rotation so the given axis is the one left free
        return [axisa]
    else:
        #this shouldn't happens...ignore it and return the current dofrot
        return dofrot 



#Ok not switch on positional constraints

#the first is axis normal on plane to plane distance
#arguments are
#axisa which the axis used in constraint (axial, circular edge, etc...)
#dofpos which is the array of left free positional axes 
def AxisDistance(axisa, dofpos, dbg=False):
    currentDOFPOSnum = len(dofpos)   
    if currentDOFPOSnum == 0 : #already locked on position so ignore it
        return []
    elif currentDOFPOSnum == 1 : #partially locked on position so compare axis free to the given axis
        if check_ifParallel(axisa,dofpos[0]):
            #the axis are parallel, so the constraint is redundant, skip it DOFPOS=1
            return dofpos
        else:
            #the axis locks permanently the position so DOFPOS=0
            return []
    elif currentDOFPOSnum == 2 : #there are 2 axis which define a plane where the plane can slide on
        #calculate the axis normal to the plane defined by the 2 axes left free
        tempNormAxis = normal_2Axis(dofpos[0], dofpos[1])
        #now compare it to the given axis
                  
        if check_ifPerpendicular(axisa,tempNormAxis):            
            #axes are perpendicular so the axis left free is the normal to the plane defined by given axis and tempNormAxis DOFPOS=1
            return [ normal_2Axis(axisa, tempNormAxis)]
        else:           
            #the object is fully constrained DOFPOS=0
            return []
            
    elif currentDOFPOSnum == 3 : # there are no constraints on position, so the rigid can slides along the given axis, DOFPOS=1
        return [axisa]
    
    else:    
        #this shouldn't happens...ignore it and return the current dofrot
        return dofpos 

    
#then plane to plane constraint
#arguments are
#axisa which the axis normal to the plane constrained
#dofpos which is the array of left free positional axes 
def planeOffset(axisa, dofpos, dbg=False):
    currentDOFPOSnum = len(dofpos)   
    if currentDOFPOSnum == 0 : #already locked on position so ignore it
        return []
    elif currentDOFPOSnum == 1 : #partially locked on position so compare to the given axis
        if check_ifParallel(axisa,dofpos[0]):
            #the axis are parallel, so the constraint is redundant as it locks a direction already locked, skip it
            return dofpos
        else:
            #the axis locks permanently the position so DOFPos=[]
            return []
    elif currentDOFPOSnum == 2 : #there are 2 axis which define a plane where the plane can slide on
        #calculate the axis normal to the plane defined by the 2 axes left free
        tempNormAxis = normal_2Axis(dofpos[0], dofpos[1])
        #now compare it to the given axis
        if check_ifParallel(axisa,tempNormAxis):
            #the plane is parallel to the plane where it can slide, so the constraint is redundant, return dofpos as is DOFPOS=2
            return dofpos
        else:      
            #now calculate the axis normal to the plane create by the given axis and the tempNormAxis
            #and return it as last free DOFPOS=1            
            return [ normal_2Axis(axisa, tempNormAxis) ]
            
    elif currentDOFPOSnum == 3 : # there are no constraints on position, so the left axes free are the two axes which define a plane normal to the given axis DOFPOS=2
        return make_planeNormal(axisa)
    
    else:    
        #this shouldn't happens...ignore it and return the current dofrot
        return dofpos      


#this is very tricky...
def PointIdentityPos(pointA, rigidCenterpoint, dofpos, pointconstraints, dbg=True):
    if check_ifCoincident(pointA,rigidCenterpoint):
        #the center of rigid is coincident to the point constrained, the obj can't move anymore DOFPOS=0
        return []
    else:
        #check how many DOF    
        currentDOFPOSnum = len(dofpos) 
        for a in len(pointconstraints):
                if check_ifCoincident(pointA,pointconstraints[a]):
                    #the same point is already constrained so skip it , redundant
                    return dofpos
      
        if currentDOFPOSnum == 0 : #already locked on position so ignore it
            return []
  
        elif currentDOFPOSnum == 1 : #already partially locked, an additional point identity locks the object
            return []  #if the point isn't already constrained, the obj is now fully constrained DOFPOS=0

        elif currentDOFPOSnum == 2 : 
            return []  #if the point isn't already constrained, the obj is now fully constrained DOFPOS=0

        elif currentDOFPOSnum == 3 : 
            #if there is only 1 pointidentity do nothing, as single point constraint doesn't lock anything just store the point
            if len(pointconstraints) == 0:            
                pointconstraints.append(pointA)
                return dofpos
            else: #add the point to the pointconstraint array
                pointconstraints.add(pointA)
                #check again the count of the point constraint
                if len(pointconstraints) == 3:
                    #there are 3 unique points so the object is fully constrained DOFPOS=0
                    return []
                if len(pointconstraints) == 2:
                    #this is a circularedge constraint with an axis with Base on pointA and Direction pointconstraint[0] to pointconstraints[1]
                    #so DOFPOS=0 as circular edge always locks all 3 axes in position
                    return []
        else:
            #this shouldn't happens...ignore it and return the current dofrot
            return dofpos 



#this is very tricky...call it always after PointIdentityPos as pointconstraints is handled only there
def PointIdentityRot(pointA, dofrot, pointconstraints, dbg=True):
    currentDOFROTnum = len(dofrot) 
    for a in len(pointconstraints):
        if check_ifCoincident(pointA,pointconstraints[a]):
            #the same point is already constrained so skip it , redundant
            return dofrot  
    if currentDOFROTnum == 0 : #already locked on rotation so ignore it
        return []
    elif currentDOFROTnum == 1 : #already partially locked, an additional point identity locks the object
        if check_ifPointOnAxis(pointA,dofrot[0]):    #check if the point is on the same direction of the axis left free
            #the point is on the rotation axis left free, it doesn't lock anything
            return dofrot            
        else:
            #the pointidentity locks permanently
            return []
    elif currentDOFROTnum == 3 : #no constraints on rotation the point identity does nothing on its own
        #here I have to insert the point on pointconstraint, only if the point is not coincident to some point already stored in pointconstraint       
        #return back here        
        #if there is only 1 pointidentity do nothing, as single point constraint doesn't lock anything just store the point
        if len(pointconstraints) == 1:            
            return dofrot
        elif len(pointconstraints) >= 3: 
            #there are 3 unique points so the object is fully constrained DOFROT=0
            return []
        elif len(pointconstraints) == 2:
            #this is a circularedge constraint with an axis with Base on pointA and Direction pointconstraint[0] to pointconstraints[1]
            #so DOFROT as circular edge always locks all 3 axes in position
            tmpAxis = FreeCAD.Axis()
            _offset = SystemOrigin.sub(pointconstraints[0]) #calculate the distance from origin
            tmpAxis.Base = SystemOrigin                
            tmpAxis.Direction = pointconstraints[1].sub(_offset)  #the direction from origin
            return AxisAlignment(tmpAxis, dofrot)    
                
    else:
        #this shouldn't happens...ignore it and return the current dofrot
        return dofrot 


#in the end there are the toolbar constraints, those are simply a combination of the one above

#PointIdentity, PointOnLine, PointOnPlane, Spherical Constraints:
#    PointIdentityPos()    needs to know the point constrained as vector, the dofpos array, the rigid center point as vector and 
#                        the pointconstraints which stores all point constraints of the rigid 
#    PointIdentityRot()    needs to know the point constrained as vector, the dofrot array, and 
#                        the pointconstraints which stores all point constraints of the rigid 
# These constraint have to be the last evaluated in the chain of constraints.

#CircularEdgeConstraint:
#    AxisAlignment()    needs to know the axis normal to circle (stored in dep as refpoint and refAxisEnd) and the dofrot array
#    AxisDistance()     needs to know the axis normal to circle (stored in dep as refpoint and refAxisEnd) and the dofpos array    
#    PlaneOffset()      needs to know the axis normal to circle (stored in dep as refpoint and refAxisEnd) and the dofpos array  
#    LockRotation()     need to know if LockRotation is True or False and the array dofrot

#PlanesParallelConstraint:
#    AxisAlignment()    needs to know the axis normal to the plane constrained (stored in dep as refpoint and refAxisEnd) and the dofrot array

#PlaneCoincident:
#    AxisAlignment()    needs to know the axis normal to the plane constrained (stored in dep as refpoint and refAxisEnd) and the dofrot array
#    PlaneOffset()      needs to know the axis normal to the plane constrained (stored in dep as refpoint and refAxisEnd) and the dofpos array  

#AxialConstraint:
#    AxisAlignment()    needs to know the axis normal to circle (stored in dep as refpoint and refAxisEnd) and the dofrot array
#    AxisDistance()     needs to know the axis normal to circle (stored in dep as refpoint and refAxisEnd) and the dofpos array  
#    LockRotation()     need to know if LockRotation is True or False and the array dofrot

#AngleBetweenPlanesConstraint
#    AngleAlignment()   needs to know the axis normal to plane constrained (stored in dep as refpoint and refAxisEnd) and the dofrot array

#some test for helper functions
print
AXIS1=FreeCAD.Axis()
AXIS1.Base = FreeCAD.Vector(2,10,12)
AXIS1.Direction = AXIS1.Direction.add(SystemXAxis.Direction)
AXIS2=FreeCAD.Axis()
AXIS2.Base = FreeCAD.Vector(2,10,12)
AXIS2.Direction = AXIS2.Direction.add(SystemXAxis.Direction)
AXIS3=FreeCAD.Axis()
AXIS3.Base = SystemOrigin
AXIS3.Direction = AXIS3.Direction.add(SystemZAxis.Direction)

#print "Axis Normal to plane defined by 2 axes = " , normal_2Axis(AXIS1,AXIS2)
print AXIS1
print "Axes defining a plane normal to given axis = " , make_planeNormal(AXIS1)
print "test recursive get normal to a plane created by 2axes defined by 1 axis normal= " , normal_2Axis(make_planeNormal(AXIS1)[0], make_planeNormal(AXIS1)[1])
print "Axes Parallel? = " , check_ifParallel(AXIS1,AXIS2)
print "Axes Perpendicular? = " , check_ifPerpendicular(AXIS1,AXIS2)
print "Axes Collinear? = " , check_ifCollinear(AXIS1,AXIS2)
print "Vertexes are Coincident ? = " ,  check_ifCoincident(AXIS1.Base, AXIS2.Base)