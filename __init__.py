# SEE __init__.license

import bpy
from bpy.props import BoolProperty, FloatProperty, EnumProperty, StringProperty
from bpy_extras.io_utils import ImportHelper, ExportHelper, axis_conversion

# Global constants
EXT_3DS = ".3ds"
FILTER_GLOB = f"*{EXT_3DS};*.i3d"

bl_info = {
    "name": "Autodesk 3DS format - Community update",
    "author": "Bob Holcomb, Campbell Barton, github:Battlefeel1942",
    "version": (0, 1, 0),
    "blender": (3, 0, 0),
    "location": "File > Import-Export",
    "description": "Import-Export 3DS, meshes, uvs, materials, textures, cameras & lamps",
    "warning": "",
    "wiki_url": "http://wiki.blender.org/index.php/Extensions:2.6/Py/"
                "Scripts/Import-Export/Autodesk_3DS",
    "support": 'COMMUNITY',
    "category": "Import-Export"}

if "bpy" in locals():
    import importlib
    modules = ['import_3ds', 'export_3ds']
    for module in modules:
        if module in locals():
            importlib.reload(locals()[module])


class Import3DSProperties:
    constrain_size: FloatProperty(
        name="Size Constraint",
        description="Scale the model by 10 until it reaches the size constraint (0 to disable)",
        min=0.0, max=1000.0,
        soft_min=0.0, soft_max=1000.0,
        default=10.0,
    )

    use_image_search: BoolProperty(
        name="Image Search",
        description="Search subdirectories for any associated images (Warning, may be slow)",
        default=True,
    )

    use_apply_transform: BoolProperty(
        name="Apply Transform",
        description="Workaround for object transformations importing incorrectly",
        default=True,
    )


class Export3DSProperties:
    use_selection: BoolProperty(
        name="Selection Only",
        description="Export selected objects only",
        default=False,
    )


class OrientationProperties:
    axis_forward: EnumProperty(
        name="Forward",
        items=(('X', "X Forward", ""),
               ('Y', "Y Forward", ""),
               ('Z', "Z Forward", ""),
               ('-X', "-X Forward", ""),
               ('-Y', "-Y Forward", ""),
               ('-Z', "-Z Forward", "")),
        default='Y',
    )

    axis_up: EnumProperty(
        name="Up",
        items=(('X', "X Up", ""),
               ('Y', "Y Up", ""),
               ('Z', "Z Up", ""),
               ('-X', "-X Up", ""),
               ('-Y', "-Y Up", ""),
               ('-Z', "-Z Up", "")),
        default='Z',
    )


class Import3DS(bpy.types.Operator, ImportHelper, Import3DSProperties, OrientationProperties):
    bl_idname = "import_scene.autodesk_3ds"
    bl_label = 'Import'
    bl_options = {'UNDO'}

    filename_ext = EXT_3DS
    filter_glob = StringProperty(
        default=FILTER_GLOB,
        options={'HIDDEN'},
    )

    def execute(self, context):
        from . import import_3ds

        keywords = self.as_keywords(
            ignore=("axis_forward", "axis_up", "filter_glob"))

        keywords["global_matrix"] = axis_conversion(
            from_forward=self.axis_forward, from_up=self.axis_up).to_4x4()

        return import_3ds.load(self, context, **keywords)


class Export3DS(bpy.types.Operator, ExportHelper, Export3DSProperties, OrientationProperties):
    bl_idname = "export_scene.autodesk_3ds"
    bl_label = 'Export'

    filename_ext = EXT_3DS
    filter_glob = StringProperty(
        default=FILTER_GLOB,
        options={'HIDDEN'},
    )

    def execute(self, context):
        from . import export_3ds

        keywords = self.as_keywords(
            ignore=("axis_forward", "axis_up", "filter_glob", "check_existing"))

        keywords["global_matrix"] = axis_conversion(
            to_forward=self.axis_forward, to_up=self.axis_up).to_4x4()

        return export_3ds.save(self, context, **keywords)


def menu_func_export(self, context):
    self.layout.operator(Export3DS.bl_idname, text="3D Studio (.3ds) BROKEN")


def menu_func_import(self, context):
    self.layout.operator(
        Import3DS.bl_idname, text="3D Studio (.3ds) IN DEVELOPMENT ¯\_(ツ)_/¯")


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
