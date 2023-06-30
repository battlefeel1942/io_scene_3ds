# helper_functions.py

import bpy


def deselect_all_objects():
    if bpy.ops.object.select_all.poll():
        bpy.ops.object.select_all(action='DESELECT')
    else:
        scn = bpy.context.scene
        for obj in scn.objects:
            obj.select_set(False)
