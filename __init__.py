# ##### BEGIN GPL LICENSE BLOCK #####

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

# ##### END GPL LICENSE BLOCK #####

# <pep8-80 compliant>

from bpy_extras.io_utils import (
    ImportHelper,
    ExportHelper,
    axis_conversion,
)
from bpy.props import (
    BoolProperty,
    FloatProperty,
    StringProperty,
)
import bpy

bl_info = {
    "name": "Autodesk 3DS format",
    "author": "Bob Holcomb, Campbell Barton",
    "blender": (3, 0, 0),
    "location": "File > Import-Export",
    "description": "Import-Export 3DS, meshes, uvs, materials, textures, "
                   "cameras & lamps",
    "warning": "",
    "wiki_url": "http://wiki.blender.org/index.php/Extensions:2.6/Py/"
                "Scripts/Import-Export/Autodesk_3DS",
    "support": 'OFFICIAL',
    "category": "Import-Export"}

if "bpy" in locals():
    import importlib
    if "import_3ds" in locals():
        importlib.reload(import_3ds)
    if "export_3ds" in locals():
        importlib.reload(export_3ds)


class IO3DSOrientationHelper:
    """Orientation helper class for import/export operators."""
    axis_forward: bpy.props.EnumProperty(
        name="Forward",
        items=(('X', "X Forward", ""),
               ('Y', "Y Forward", ""),
               ('Z', "Z Forward", ""),
               ('-X', "-X Forward", ""),
               ('-Y', "-Y Forward", ""),
               ('-Z', "-Z Forward", "")),
        default='Y',
    )

    axis_up: bpy.props.EnumProperty(
        name="Up",
        items=(('X', "X Up", ""),
               ('Y', "Y Up", ""),
               ('Z', "Z Up", ""),
               ('-X', "-X Up", ""),
               ('-Y', "-Y Up", ""),
               ('-Z', "-Z Up", "")),
        default='Z',
    )


class Import3DS(bpy.types.Operator, ImportHelper, IO3DSOrientationHelper):
    """Import from 3DS file format (.3ds)"""
    bl_idname = "import_scene.autodesk_3ds"
    bl_label = 'Import 3DS/I3D'
    bl_options = {'UNDO'}

    filename_ext = ".3ds"
    filter_glob = StringProperty(default="*.3ds;*.i3d", options={'HIDDEN'})

    constrain_size = FloatProperty(
        name="Size Constraint",
        description="Scale the model by 10 until it reaches the "
        "size constraint (0 to disable)",
        min=0.0, max=1000.0,
        soft_min=0.0, soft_max=1000.0,
        default=10.0,
    )
    use_image_search = BoolProperty(
        name="Image Search",
        description="Search subdirectories for any associated images "
        "(Warning, may be slow)",
        default=True,
    )
    use_apply_transform = BoolProperty(
        name="Apply Transform",
        description="Workaround for object transformations "
        "importing incorrectly",
        default=True,
    )

    def execute(self, context):
        from . import import_3ds

        keywords = self.as_keywords(ignore=("axis_forward",
                                            "axis_up",
                                            "filter_glob",
                                            ))

        global_matrix = axis_conversion(from_forward=self.axis_forward,
                                        from_up=self.axis_up,
                                        ).to_4x4()
        keywords["global_matrix"] = global_matrix

        return import_3ds.load(self, context, **keywords)


class Export3DS(bpy.types.Operator, ExportHelper, IO3DSOrientationHelper):
    """Export to 3DS file format (.3ds)"""
    bl_idname = "export_scene.autodesk_3ds"
    bl_label = 'Export 3DS'

    filename_ext = ".3ds"
    filter_glob = StringProperty(
        default="*.3ds",
        options={'HIDDEN'},
    )

    use_selection = BoolProperty(
        name="Selection Only",
        description="Export selected objects only",
        default=False,
    )

    def execute(self, context):
        from . import export_3ds

        keywords = self.as_keywords(ignore=("axis_forward",
                                            "axis_up",
                                            "filter_glob",
                                            "check_existing",
                                            ))
        global_matrix = axis_conversion(to_forward=self.axis_forward,
                                        to_up=self.axis_up,
                                        ).to_4x4()
        keywords["global_matrix"] = global_matrix

        return export_3ds.save(self, context, **keywords)


def menu_func_export(self, context):
    self.layout.operator(Export3DS.bl_idname,
                         text="3D Studio (.3ds) BROKEN")


def menu_func_import(self, context):
    self.layout.operator(Import3DS.bl_idname,
                         text="3D Studio (.3ds) EXPERIMENTAL")


def register():
    bpy.utils.register_class(Import3DS)
    bpy.utils.register_class(Export3DS)
    bpy.types.TOPBAR_MT_file_import.append(menu_func_import)
    bpy.types.TOPBAR_MT_file_export.append(menu_func_export)


def unregister():
    bpy.utils.unregister_class(Import3DS)
    bpy.utils.unregister_class(Export3DS)
    bpy.types.TOPBAR_MT_file_import.remove(menu_func_import)
    bpy.types.TOPBAR_MT_file_export.remove(menu_func_export)


if __name__ == "__main__":
    register()
