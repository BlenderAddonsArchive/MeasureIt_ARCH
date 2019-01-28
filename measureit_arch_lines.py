# ##### BEGIN GPL LICENSE BLOCK #####
#
#  This program is free software; you can redistribute it and/or
#  modify it under the terms of the GNU General Public License
#  as published by the Free Software Foundation; either version 2
#  of the License, or (at your option) any later version.
#
#  This program is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#  GNU General Public License for more details.
#
#  You should have received a copy of the GNU General Public License
#  along with this program; if not, write to the Free Software Foundation,
#  Inc., 51 Franklin Street, Fifth Floor, Boston, MA 02110-1301, USA.
#
# ##### END GPL LICENSE BLOCK #####


# ----------------------------------------------------------
# File: measureit_arch_main.py
# Main panel for different MeasureitArch general actions
# Author: Kevan Cress
#
# ----------------------------------------------------------

import bpy

import bmesh
from bmesh import from_edit_mesh

import bgl
import gpu
from gpu_extras.batch import batch_for_shader

from bpy.types import PropertyGroup, Panel, Object, Operator, SpaceView3D
from bpy.props import IntProperty, CollectionProperty, FloatVectorProperty, BoolProperty, StringProperty, \
                      FloatProperty, EnumProperty
from bpy.app.handlers import persistent
# noinspection PyUnresolvedReferences
from .measureit_arch_geometry import *
from .measureit_arch_render import *
from .measureit_arch_main import get_smart_selected, get_selected_vertex

# ------------------------------------------------------------------
# Define property group class for individual line Data
# ------------------------------------------------------------------
class SingleLineProperties(PropertyGroup):
    pointA: IntProperty(name = "pointA",
                        description = "first vertex index of the line")
                        
    pointB: IntProperty(name = "pointB",
                        description = "Second vertex index of the line")

bpy.utils.register_class(SingleLineProperties)

# ------------------------------------------------------------------
# Define property group class for line data
# ------------------------------------------------------------------

class LineProperties(PropertyGroup):
    lineStyle: IntProperty(name="lineStyle",
                        description="Dimension Style to use",
                        min = 0)
    
    lineColor: FloatVectorProperty(name="lineColor",
                        description="Color for Lines",
                        default=(0.1, 0.1, 0.1, 1.0),
                        min=0.0,
                        max=1,
                        subtype='COLOR',
                        size=4) 

    lineWeight: IntProperty(name="lineWeight",
                        description="Lineweight",
                        min = 1,
                        max = 10)

    lineVis: BoolProperty(name="lineVis",
                        description="Line show/hide",
                        default=True)

    lineFree: BoolProperty(name="lineFree",
                        description="This line is free and can be deleted",
                        default=False)

    numLines: IntProperty(name="numLines",
                        description="Number Of Single Lines")

    lineDrawHidden: BoolProperty(name= "lineDrawHidden",
                        description= "Draw Hidden Lines",
                        default= False)
    
    lineSettings: BoolProperty(name= "lineSettings",
                        description= "Show Line Settings",
                        default=False)

    lineHiddenColor: FloatVectorProperty(name="lineHiddenColor",
                        description="Color for Hidden Lines",
                        default=(0.2, 0.2, 0.2, 1.0),
                        min=0.0,
                        max=1,
                        subtype='COLOR',
                        size=4) 

    lineHiddenWeight: IntProperty(name="lineHiddenWeight",
                        description="Hidden Line Lineweight",
                        default= 1,
                        min = 0,
                        max = 10)
    
    lineHiddenDashScale: IntProperty(name="lineHiddenDashScale",
                        description="Hidden Line Dash Scale",
                        default= 10,
                        min = 0)

    isOutline: BoolProperty(name= "isOutline",
                        description= "Line Group Is For Drawing Outlines",
                        default=False)
    #collection of indicies                        
    singleLine: CollectionProperty(type=SingleLineProperties)

# Register
bpy.utils.register_class(LineProperties)



# ------------------------------------------------------------------
# Define object class (container of lines)
# MeasureitArch
# ------------------------------------------------------------------
class LineContainer(PropertyGroup):
    line_num: IntProperty(name='Number of Line Groups', min=0, max=1000, default=0,
                                description='Number total of line groups')
    # Array of segments
    line_groups: CollectionProperty(type=LineProperties)


bpy.utils.register_class(LineContainer)
Object.LineGenerator = CollectionProperty(type=LineContainer)


class AddLineButton(Operator):
    bl_idname = "measureit_arch.addlinebutton"
    bl_label = "Add"
    bl_description = "(EDITMODE only) Add a new measure segment between 2 vertices (select 2 vertices or more)"
    bl_category = 'MeasureitArch'

    # ------------------------------
    # Poll
    # ------------------------------
    @classmethod
    def poll(cls, context):
        o = context.object
        if o is None:
            return False
        else:
            if o.type == "MESH":
                if bpy.context.mode == 'EDIT_MESH':
                    return True
                else:
                    return False
            else:
                return False

    # ------------------------------
    # Execute button action
    # ------------------------------
    def execute(self, context):
        if context.area.type == 'VIEW_3D':
            # Add properties
            scene = context.scene
            mainobject = context.object
            mylist = get_smart_selected(mainobject)
            if len(mylist) < 2:  # if not selected linked vertex
                mylist = get_selected_vertex(mainobject)

            if len(mylist) >= 2:
                if 'LineGenerator' not in mainobject:
                    mainobject.LineGenerator.add()

                lineGen = mainobject.LineGenerator[0]
                lGroup = lineGen.line_groups.add()

                # Set values
                lGroup.lineStyle = scene.measureit_arch_default_style
                lGroup.lineWidth = 2     
                lGroup.lineColor = scene.measureit_arch_default_color
                
                for x in range (0, len(mylist)-1, 2):
                    sLine = lGroup.singleLine.add()
                    sLine.pointA = mylist[x]
                    sLine.pointB = mylist[x+1]
                    lGroup.numLines +=1

                lineGen.line_num += 1


                # redraw
                context.area.tag_redraw()
                return {'FINISHED'}
            else:
                self.report({'ERROR'},
                            "MeasureIt-ARCH: Select at least two vertices for creating measure segment.")
                return {'FINISHED'}
        else:
            self.report({'WARNING'},
                        "View3D not found, cannot run operator")

        return {'CANCELLED'}


class MeasureitArchLinesPanel(Panel):
    bl_idname = "obj_lines"
    bl_label = "Object Lines"
    bl_space_type = "PROPERTIES"
    bl_region_type = "WINDOW"
    bl_context = "object"
    
    @classmethod
    def poll(cls, context):
        if 'LineGenerator' in bpy.context.object:
            return True
        else:
            return False
        
    def draw(self, context):
         scene = context.scene
         if context.object is not None:
            if 'LineGenerator' in context.object:
                layout = self.layout
                layout.use_property_split = True
                layout.use_property_decorate = False
                # -----------------
                # loop
                # -----------------
                
                mp = context.object.LineGenerator[0]
                if mp.line_num > 0:
                    row = layout.row(align = True)
                    #row.operator("measureit_arch.expandallsegmentbutton", text="Expand all", icon="ADD")
                    #row.operator("measureit_arch.collapseallsegmentbutton", text="Collapse all", icon="REMOVE")
                    for idx in range(0, mp.line_num):
                        add_line_item(layout, idx, mp.line_groups[idx])

                    row = layout.row()
                    #row.operator("measureit_arch.deleteallsegmentbutton", text="Delete all", icon="X")
    
# -----------------------------------------------------
# Add line options to the panel.
# -----------------------------------------------------
def add_line_item(layout, idx, line):
    scene = bpy.context.scene
    if line.lineSettings is True:
        box = layout.box()
        row = box.row(align=True)
    else:
        row = layout.row(align=True)


    if line.lineVis is True:
        icon = "VISIBLE_IPO_ON"
    else:
        icon = "VISIBLE_IPO_OFF"

    row.prop(line, 'lineVis', text="", toggle=True, icon=icon)
    row.prop(line, 'lineSettings', text="",toggle=True, icon='PREFERENCES')
    row.prop(line, 'isOutline', text="", toggle=True, icon='SEQ_CHROMA_SCOPE')
    row.prop(line, 'lineDrawHidden', text="", toggle=True, icon='MOD_WIREFRAME')
    row.prop(line, 'lineColor', text="" )
    row.prop(line, 'lineWeight', text="")
    op = row.operator("measureit_arch.deletelinebutton", text="", icon="X")
    op.tag = idx  # saves internal data
    
    if line.lineSettings is True:
        row = box.row(align=True)
        
        op = row.operator('measureit_arch.addtolinegroup', text="Add Line", icon='ADD')
        op.tag = idx
        op = row.operator('measureit_arch.removefromlinegroup', text="Remove Line", icon='REMOVE')
        op.tag = idx
        col = box.column()
        col.prop(line, 'lineWeight', text="Lineweight" )
        if line.lineDrawHidden is True:
            col = box.column()
            col.prop(line, 'lineHiddenColor', text="Hidden Line Color")
            col.prop(line, 'lineHiddenWeight',text="Hidden Line Weight")
            col.prop(line, 'lineHiddenDashScale',text="Dash Scale")
        

class DeleteLineButton(Operator):

    bl_idname = "measureit_arch.deletelinebutton"
    bl_label = "Delete Line"
    bl_description = "Delete a Line"
    bl_category = 'MeasureitArch'
    tag= IntProperty()

    # ------------------------------
    # Execute button action
    # ------------------------------
    def execute(self, context):
        # Add properties
        mainObj = context.object
        mp = mainObj.LineGenerator[0]
        ms = mp.line_groups[self.tag]
        ms.lineFree = True
        # Delete element
        mp.line_groups.remove(self.tag)
        mp.line_num -= 1
        # redraw
        context.area.tag_redraw()
        
        for window in bpy.context.window_manager.windows:
            screen = window.screen

            for area in screen.areas:
                if area.type == 'VIEW_3D':
                    area.tag_redraw()
                    context.area.tag_redraw()
                    return {'FINISHED'}
                
        return {'FINISHED'}

class AddToLineGroup(Operator):   
    bl_idname = "measureit_arch.addtolinegroup"
    bl_label = "Add Selection to Line Group"
    bl_description = "Add Selection to Line Group"
    bl_category = 'MeasureitArch'
    tag= IntProperty()

    # ------------------------------
    # Poll
    # ------------------------------
    @classmethod
    def poll(cls, context):
        o = context.object
        if o is None:
            return False
        else:
            if o.type == "MESH":
                if bpy.context.mode == 'EDIT_MESH':
                    return True
                else:
                    return False
            else:
                return False


    # ------------------------------
    # Execute button action
    # ------------------------------
    def execute(self, context):
         for window in bpy.context.window_manager.windows:
            screen = window.screen

            for area in screen.areas:
                if area.type == 'VIEW_3D':
                    # get selected

                    mainobject = context.object
                    mylist = get_smart_selected(mainobject)
                    if len(mylist) < 2:  # if not selected linked vertex
                        mylist = get_selected_vertex(mainobject)

                    if len(mylist) >= 2:

                        lineGen = mainobject.LineGenerator[0]
                        lGroup = lineGen.line_groups[self.tag]
                        

                        for x in range (0, len(mylist)-1, 2):
                            if lineExists(lGroup,mylist[x],mylist[x+1]) is False:

                                sLine = lGroup.singleLine.add()
                                sLine.pointA = mylist[x]
                                sLine.pointB = mylist[x+1]
                                lGroup.numLines +=1
                                #print("line made" + str(sLine.pointA) + ", " +str(sLine.pointB))

                                # redraw
                                context.area.tag_redraw()
                        return {'FINISHED'}

class RemoveFromLineGroup(Operator):   
    bl_idname = "measureit_arch.removefromlinegroup"
    bl_label = "Remove Selection from Line Group"
    bl_description = "Remove Selection from Line Group"
    bl_category = 'MeasureitArch'
    tag= IntProperty()

    # ------------------------------
    # Poll
    # ------------------------------
    @classmethod
    def poll(cls, context):
        o = context.object
        if o is None:
            return False
        else:
            if o.type == "MESH":
                if bpy.context.mode == 'EDIT_MESH':
                    return True
                else:
                    return False
            else:
                return False


    # ------------------------------
    # Execute button action
    # ------------------------------
    def execute(self, context):
        for window in bpy.context.window_manager.windows:
            screen = window.screen

            for area in screen.areas:
                if area.type == 'VIEW_3D':
                    # get selected

                    mainobject = context.object
                    mylist = get_smart_selected(mainobject)

                    if len(mylist) < 2:  # if not selected linked vertex
                        mylist = get_selected_vertex(mainobject)

                    if len(mylist) >= 2:

                        lineGen = mainobject.LineGenerator[0]
                        lGroup = lineGen.line_groups[self.tag]
                        idx = 0
                        for sLine in lGroup.singleLine:
                            for x in range (0, len(mylist), 2):
                                if sLineExists(sLine,mylist[x],mylist[x+1]):
                                    #print("checked Pair: (" + str(mylist[x]) +   "," + str(mylist[x+1]) + ")" )
                                    #print("A:" + str(sLine.pointA) + "B:" + str(sLine.pointB) ) 
                                    lGroup.singleLine.remove(idx) 
                                    lGroup.numLines -= 1     
                            idx +=1
  
                        # redraw
                        context.area.tag_redraw()
                        return {'FINISHED'}

def sLineExists(sLine,a,b):
    if (sLine.pointA == a and sLine.pointB == b):
        return True
    elif (sLine.pointA == b and sLine.pointB == a):
        return True
    else:
        return False

def lineExists(lGroup,a,b):
    for sLine in lGroup.singleLine:
        if (sLine.pointA == a and sLine.pointB == b):
            return True
        elif (sLine.pointA == b and sLine.pointB == a):
            return True
    return False