import os
import time
import struct

import bpy
import mathutils

from . import data_structure_3ds
from . import helper_functions
from . import localspace_variable_names

from .chunk_3ds import Chunk3DS

# Global Variables
BOUNDS_3DS = []
OBJECT_DICTIONARY = {}
OBJECT_MATRIX = {}

SCN = bpy.context.scene


def process_next_chunk(file, previous_chunk, importedObjects, IMAGE_SEARCH):
    from bpy_extras.image_utils import load_image

    contextObName = None
    contextLamp = [None, None]  # object, Data
    contextMaterial = None
    contextMatrix_rot = None  # Blender.mathutils.Matrix(); contextMatrix.identity()
    contextMesh_vertls = None  # flat array: (verts * 3)
    contextMesh_facels = None
    contextMeshMaterials = []  # (matname, [face_idxs])
    contextMeshUV = None  # flat array (verts * 2)

    textureDictionary = {}
    materialDictionary = {}

    # only init once
    object_list = []  # for hierarchy
    object_parent = []  # index of parent in hierarchy, 0xFFFF = no parent
    pivot_list = []  # pivots with hierarchy handling

    def putContextMesh(
        myContextMesh_vertls, myContextMesh_facels, myContextMeshMaterials
    ):
        myContextMesh_facels = myContextMesh_facels or []

        if myContextMesh_vertls:
            bmesh = helper_functions.create_new_mesh(contextObName)
            helper_functions.add_vertices_to_mesh(bmesh, myContextMesh_vertls)
            helper_functions.add_faces_to_mesh(bmesh, myContextMesh_facels)

            uv_faces = (
                helper_functions.add_uv_layer(bmesh)
                if bmesh.polygons and contextMeshUV
                else None
            )

            helper_functions.assign_material(
                bmesh, myContextMeshMaterials, materialDictionary, textureDictionary
            )

            if uv_faces:
                helper_functions.set_uv(bmesh, myContextMesh_facels, contextMeshUV)

            bmesh.validate()
            bmesh.update()

            ob = helper_functions.add_object_to_scene(bmesh, contextObName)
            OBJECT_DICTIONARY[contextObName] = ob
            importedObjects.append(ob)

            helper_functions.set_matrix(ob, contextMatrix_rot)
            if contextMatrix_rot:
                OBJECT_MATRIX[ob] = contextMatrix_rot.copy()

    # a spare chunk
    new_chunk = Chunk3DS()
    temp_chunk = Chunk3DS()

    CreateBlenderObject = False

    def read_texture(new_chunk, temp_chunk, name, mapto):
        new_texture = bpy.data.textures.new(name, type="IMAGE")

        u_scale, v_scale, u_offset, v_offset = 1.0, 1.0, 0.0, 0.0
        extension = "wrap"
        while new_chunk.bytes_read < new_chunk.length:
            helper_functions.read_chunk(file, temp_chunk)

            if temp_chunk.ID == data_structure_3ds.MAT_MAP_FILEPATH:
                texture_name, read_str_len = helper_functions.read_string(file)

                img = textureDictionary[contextMaterial.name] = load_image(
                    texture_name, dirname
                )
                # plus one for the null character that gets removed
                temp_chunk.bytes_read += read_str_len

            elif temp_chunk.ID == data_structure_3ds.MAT_MAP_USCALE:
                u_scale = helper_functions.read_float(temp_chunk)
            elif temp_chunk.ID == data_structure_3ds.MAT_MAP_VSCALE:
                v_scale = helper_functions.read_float(temp_chunk)

            elif temp_chunk.ID == data_structure_3ds.MAT_MAP_UOFFSET:
                u_offset = helper_functions.read_float(temp_chunk)
            elif temp_chunk.ID == data_structure_3ds.MAT_MAP_VOFFSET:
                v_offset = helper_functions.read_float(temp_chunk)

            elif temp_chunk.ID == data_structure_3ds.MAT_MAP_TILING:
                tiling = helper_functions.read_short(file, temp_chunk)
                if tiling & 0x2:
                    extension = "mirror"
                elif tiling & 0x10:
                    extension = "decal"

            elif temp_chunk.ID == data_structure_3ds.MAT_MAP_ANG:
                print("\nwarning: ignoring UV rotation")

            helper_functions.skip_to_end(file, temp_chunk)
            new_chunk.bytes_read += temp_chunk.bytes_read

        # add the map to the material in the right channel
        if img:
            helper_functions.add_texture_to_material(
                img,
                new_texture,
                (u_scale, v_scale),
                (u_offset, v_offset),
                extension,
                contextMaterial,
                mapto,
            )

    dirname = os.path.dirname(file.name)

    # loop through all the data for this chunk (previous chunk) and see what it is
    while previous_chunk.bytes_read < previous_chunk.length:
        # print '\t', previous_chunk.bytes_read, 'keep going'
        # read the next chunk
        # print 'reading a chunk'
        helper_functions.read_chunk(file, new_chunk)

        if new_chunk.ID == data_structure_3ds.VERSION:
            version = helper_functions.read_int(file, new_chunk)
            if version > 3:
                print(
                    "\tNon-Fatal Error: Version greater than 3, may not load correctly:",
                    version,
                )

        # is it an object info chunk?
        elif new_chunk.ID == data_structure_3ds.OBJECTINFO:
            # print 'elif new_chunk.ID == OBJECTINFO:'
            # print 'found an OBJECTINFO chunk'
            process_next_chunk(file, new_chunk, importedObjects, IMAGE_SEARCH)

            # keep track of how much we read in the main chunk
            new_chunk.bytes_read += temp_chunk.bytes_read

        # is it an object chunk?
        elif new_chunk.ID == data_structure_3ds.OBJECT:

            if CreateBlenderObject:
                putContextMesh(
                    contextMesh_vertls, contextMesh_facels, contextMeshMaterials
                )
                contextMesh_vertls = []
                contextMesh_facels = []

                # preparando para receber o proximo objeto
                contextMeshMaterials = []  # matname:[face_idxs]
                contextMeshUV = None
                # Reset matrix
                contextMatrix_rot = None
                # contextMatrix_tx = None

            CreateBlenderObject = True
            contextObName, read_str_len = helper_functions.read_string(file)
            new_chunk.bytes_read += read_str_len

        # is it a material chunk?
        elif new_chunk.ID == data_structure_3ds.MATERIAL:
            contextMaterial = bpy.data.materials.new("Material")

        elif new_chunk.ID == data_structure_3ds.MAT_NAME:
            material_name, read_str_len = helper_functions.read_string(file)
            material_name = material_name.rstrip()

            contextMaterial.name = material_name
            materialDictionary[material_name] = contextMaterial
            new_chunk.bytes_read += read_str_len

        elif new_chunk.ID == data_structure_3ds.MAT_AMBIENT:
            helper_functions.read_chunk(file, temp_chunk)

            if temp_chunk.ID in [
                data_structure_3ds.MAT_FLOAT_COLOR,
                data_structure_3ds.MAT_24BIT_COLOR,
            ]:
                color = (
                    helper_functions.read_float_color(file, temp_chunk)
                    if temp_chunk.ID == data_structure_3ds.MAT_FLOAT_COLOR
                    else helper_functions.read_byte_color(file, temp_chunk)
                )
                contextMaterial.diffuse_color = color + [1.0]  # Adding alpha value as list
            else:
                helper_functions.skip_to_end(file, temp_chunk)

            new_chunk.bytes_read += temp_chunk.bytes_read

            if not contextMaterial.use_nodes:
                contextMaterial.use_nodes = True

            bsdf_node = contextMaterial.node_tree.nodes.get("Principled BSDF")
            if bsdf_node:
                bsdf_node.inputs["Specular"].default_value = 1.0
                bsdf_node.inputs["Roughness"].default_value = 0.0

        elif new_chunk.ID == data_structure_3ds.MAT_DIFFUSE:
            helper_functions.read_chunk(file, temp_chunk)

            if temp_chunk.ID in [
                data_structure_3ds.MAT_FLOAT_COLOR,
                data_structure_3ds.MAT_24BIT_COLOR,
            ]:
                color = (
                    helper_functions.read_float_color(file, temp_chunk)
                    if temp_chunk.ID == data_structure_3ds.MAT_FLOAT_COLOR
                    else helper_functions.read_byte_color(file, temp_chunk)
                )
                contextMaterial.diffuse_color = color + [1.0]  # Add alpha
            else:
                helper_functions.skip_to_end(file, temp_chunk)

            new_chunk.bytes_read += temp_chunk.bytes_read

            if not contextMaterial.use_nodes:
                contextMaterial.use_nodes = True

            bsdf_node = contextMaterial.node_tree.nodes.get("Principled BSDF")
            if bsdf_node:
                bsdf_node.inputs[
                    "Base Color"
                ].default_value = contextMaterial.diffuse_color

        elif new_chunk.ID == data_structure_3ds.MAT_SPECULAR:
            helper_functions.read_chunk(file, temp_chunk)

            if temp_chunk.ID in [
                data_structure_3ds.MAT_FLOAT_COLOR,
                data_structure_3ds.MAT_24BIT_COLOR,
            ]:
                contextMaterial.specular_color = (
                    helper_functions.read_float_color(file, temp_chunk)
                    if temp_chunk.ID == data_structure_3ds.MAT_FLOAT_COLOR
                    else helper_functions.read_byte_color(file, temp_chunk)
                )
            else:
                helper_functions.skip_to_end(file, temp_chunk)

            new_chunk.bytes_read += temp_chunk.bytes_read

        elif new_chunk.ID in [
            data_structure_3ds.MAT_TEXTURE_MAP,
            data_structure_3ds.MAT_SPECULAR_MAP,
            data_structure_3ds.MAT_OPACITY_MAP,
            data_structure_3ds.MAT_BUMP_MAP,
        ]:

            texture_id_map = {
                data_structure_3ds.MAT_TEXTURE_MAP: ("Diffuse", "COLOR"),
                data_structure_3ds.MAT_SPECULAR_MAP: ("Specular", "SPECULARITY"),
                data_structure_3ds.MAT_OPACITY_MAP: ("Opacity", "ALPHA"),
                data_structure_3ds.MAT_BUMP_MAP: ("Bump", "NORMAL"),
            }

            read_texture(new_chunk, temp_chunk, *texture_id_map[new_chunk.ID])

        elif new_chunk.ID == data_structure_3ds.MAT_TRANSPARENCY:
            helper_functions.read_chunk(file, temp_chunk)

            alpha_value = 1.0
            struct_map = {
                data_structure_3ds.PERCENTAGE_SHORT: (
                    "<H",
                    localspace_variable_names.STRUCT_SIZE_UNSIGNED_SHORT,
                ),
                data_structure_3ds.PERCENTAGE_FLOAT: (
                    "f",
                    localspace_variable_names.STRUCT_SIZE_FLOAT,
                ),
            }

            if temp_chunk.ID in struct_map:
                struct_format, struct_size = struct_map[temp_chunk.ID]
                temp_data = file.read(struct_size)
                temp_chunk.bytes_read += struct_size
                alpha_value = 1 - (
                    float(struct.unpack(struct_format, temp_data)[0]) / 100
                )
            else:
                print("Cannot read material transparency")

            new_chunk.bytes_read += temp_chunk.bytes_read

            if not contextMaterial.use_nodes:
                contextMaterial.use_nodes = True

            bsdf_node = contextMaterial.node_tree.nodes.get("Principled BSDF")
            if bsdf_node:
                bsdf_node.inputs["Alpha"].default_value = alpha_value

        elif new_chunk.ID == data_structure_3ds.OBJECT_LAMP:  # Basic lamp support.
            contextLamp, new_chunk = helper_functions.create_lamp(
                file, contextLamp, new_chunk, SCN, importedObjects
            )
            # Reset matrix
            contextMatrix_rot = None

        elif new_chunk.ID == data_structure_3ds.OBJECT_MESH:
            pass
        elif new_chunk.ID == data_structure_3ds.OBJECT_VERTICES:
            # Worldspace vertex locations
            temp_data = file.read(localspace_variable_names.STRUCT_SIZE_UNSIGNED_SHORT)
            num_verts = struct.unpack("<H", temp_data)[0]
            new_chunk.bytes_read += 2

            read_size = localspace_variable_names.STRUCT_SIZE_3FLOAT * num_verts
            contextMesh_vertls = struct.unpack(
                "<%df" % (num_verts * 3), file.read(read_size)
            )
            new_chunk.bytes_read += read_size

        elif new_chunk.ID == data_structure_3ds.OBJECT_FACES:
            temp_data = file.read(localspace_variable_names.STRUCT_SIZE_UNSIGNED_SHORT)
            num_faces = struct.unpack("<H", temp_data)[0]
            new_chunk.bytes_read += 2

            read_size = (
                localspace_variable_names.STRUCT_SIZE_4UNSIGNED_SHORT * num_faces
            )
            temp_data = file.read(read_size)
            new_chunk.bytes_read += read_size

            contextMesh_facels = struct.unpack("<%dH" % (num_faces * 4), temp_data)
            contextMesh_facels = [
                contextMesh_facels[i - 3: i]
                for i in range(3, len(contextMesh_facels) + 1, 4)
            ]

        elif new_chunk.ID == data_structure_3ds.OBJECT_MATERIAL:
            material_name, read_str_len = helper_functions.read_string(file)
            new_chunk.bytes_read += read_str_len  # remove 1 null character.

            temp_data = file.read(localspace_variable_names.STRUCT_SIZE_UNSIGNED_SHORT)
            num_faces_using_mat = struct.unpack("<H", temp_data)[0]
            new_chunk.bytes_read += localspace_variable_names.STRUCT_SIZE_UNSIGNED_SHORT

            read_size = (
                localspace_variable_names.STRUCT_SIZE_UNSIGNED_SHORT
                * num_faces_using_mat
            )
            temp_data = file.read(read_size)
            new_chunk.bytes_read += read_size

            face_indices = struct.unpack("<%dH" % (num_faces_using_mat), temp_data)

            contextMeshMaterials.append((material_name, face_indices))

        elif new_chunk.ID == data_structure_3ds.OBJECT_UV:
            temp_data = file.read(localspace_variable_names.STRUCT_SIZE_UNSIGNED_SHORT)
            num_uv = struct.unpack("<H", temp_data)[0]
            new_chunk.bytes_read += 2

            read_size = localspace_variable_names.STRUCT_SIZE_2FLOAT * num_uv
            temp_data = file.read(read_size)
            new_chunk.bytes_read += read_size

            uv_values = struct.unpack("<%df" % (num_uv * 2), temp_data)
            contextMeshUV = uv_values

        elif new_chunk.ID == data_structure_3ds.OBJECT_TRANS_MATRIX:
            # How do we know the matrix size? 54 == 4x4 48 == 4x3
            matrix_size = localspace_variable_names.STRUCT_SIZE_4x3MAT
            temp_data = file.read(matrix_size)
            data = list(struct.unpack("<ffffffffffff", temp_data))
            new_chunk.bytes_read += matrix_size

            row1 = data[:3] + [0]
            row2 = data[3:6] + [0]
            row3 = data[6:9] + [0]
            row4 = data[9:] + [1]
            contextMatrix_rot = mathutils.Matrix((row1, row2, row3, row4)).transposed()

        elif new_chunk.ID == data_structure_3ds.MAT_MAP_FILEPATH:
            material_name = contextMaterial.name
            texture_name, read_str_len = helper_functions.read_string(file)
            if material_name not in textureDictionary:
                texture = load_image(
                    texture_name, dirname, place_holder=False, recursive=IMAGE_SEARCH
                )
                textureDictionary[material_name] = texture
                print(f"Loaded texture {texture_name} for material {material_name}")

            # plus one for the null character that gets removed
            new_chunk.bytes_read += read_str_len

        elif new_chunk.ID == data_structure_3ds.EDITKEYFRAME:
            pass

        # Check if the chunk ID corresponds to any of the object node IDs.
        # If so, we reset 'child' to None since we're about to process another object.
        elif new_chunk.ID in {
            data_structure_3ds.ED_KEY_AMBIENT_NODE,
            data_structure_3ds.ED_KEY_OBJECT_NODE,
            data_structure_3ds.ED_KEY_CAMERA_NODE,
            data_structure_3ds.ED_KEY_TARGET_NODE,
            data_structure_3ds.ED_KEY_LIGHT_NODE,
            data_structure_3ds.ED_KEY_L_TARGET_NODE,
            data_structure_3ds.ED_KEY_SPOTLIGHT_NODE,
        }:
            child = None

        else:
            # Skip unidentified chunks by reading remaining bytes and discarding the data.
            buffer_size = new_chunk.length - new_chunk.bytes_read
            file.read(buffer_size)
            new_chunk.bytes_read += buffer_size

        # update the previous chunk bytes read
        previous_chunk.bytes_read += new_chunk.bytes_read
        # print 'Bytes left in this chunk: ', previous_chunk.length - previous_chunk.bytes_read

    # FINISHED LOOP
    # There will be a number of objects still not added
    if CreateBlenderObject:
        putContextMesh(contextMesh_vertls, contextMesh_facels, contextMeshMaterials)

    # Assign parents to objects
    # Check if we need to assign parents first because doing so recalculates the dependencies graph
    for index, current_object in enumerate(object_list):
        parent_index = object_parent[index]

        if parent_index == data_structure_3ds.ROOT_OBJECT:
            # Ensure that root objects have no parent
            if current_object.parent is not None:
                current_object.parent = None
        else:
            # Avoid self-parenting and index out of range errors
            if (
                parent_index < len(object_list)
                and current_object != object_list[parent_index]
            ):
                current_object.parent = object_list[parent_index]

    # Adjust pivot points for each mesh object
    for index, object in enumerate(object_list):
        if object.type == "MESH":
            pivot = pivot_list[index]

            # Get the object's matrix, defaulting to the identity matrix if not found
            object_matrix = OBJECT_MATRIX.get(object, mathutils.Matrix())

            # Create a translation matrix for the pivot adjustment
            pivot_adjustment_matrix = mathutils.Matrix.Translation(
                object_matrix.to_3x3() @ -pivot
            )

            # Transform the object data using the pivot adjustment matrix
            object.data.transform(pivot_adjustment_matrix)


def load_3ds(
    filepath,
    context,
    IMPORT_CONSTRAIN_BOUNDS=10.0,
    IMAGE_SEARCH=True,
    APPLY_MATRIX=True,
    global_matrix=None,
):

    print("importing 3DS: %r..." % (filepath), end="")
    time1 = time.perf_counter()

    current_chunk = Chunk3DS()
    file = open(filepath, "rb")

    # Deselect all other objects
    helper_functions.deselect_all_objects()

    # here we go!
    helper_functions.read_chunk(file, current_chunk)
    if current_chunk.ID != data_structure_3ds.PRIMARY:
        print("\tFatal Error:  Not a valid 3ds file: %r" % filepath)
        file.close()
        return

    if IMPORT_CONSTRAIN_BOUNDS:
        BOUNDS_3DS[:] = [1 << 30, 1 << 30, 1 << 30, -1 << 30, -1 << 30, -1 << 30]
    else:
        del BOUNDS_3DS[:]

    # IMAGE_SEARCH
    importedObjects = []  # Fill this list with objects
    process_next_chunk(file, current_chunk, importedObjects, IMAGE_SEARCH)

    if APPLY_MATRIX:
        for ob in importedObjects:
            if ob.type == "MESH":
                me = ob.data
                me.transform(ob.matrix_local.inverted())

    if global_matrix:
        for ob in importedObjects:
            if ob.parent is None:
                ob.matrix_world = ob.matrix_world * global_matrix

    for ob in importedObjects:
        context.view_layer.objects.active = ob
        ob.select_set(True)

    bpy.context.view_layer.update()

    axis_min = [1000000000] * 3
    axis_max = [-1000000000] * 3
    global_clamp_size = IMPORT_CONSTRAIN_BOUNDS
    if global_clamp_size != 0.0:
        # Get all object bounds
        for ob in importedObjects:
            for v in ob.bound_box:
                for axis, value in enumerate(v):
                    if axis_min[axis] > value:
                        axis_min[axis] = value
                    if axis_max[axis] < value:
                        axis_max[axis] = value

        # Scale objects
        max_axis = max(
            axis_max[0] - axis_min[0],
            axis_max[1] - axis_min[1],
            axis_max[2] - axis_min[2],
        )
        scale = 1.0

        while global_clamp_size < max_axis * scale:
            scale = scale / 10.0

        scale_material = mathutils.Matrix.Scale(scale, 4)

        for object in importedObjects:
            if object.parent is None:
                object.matrix_world = scale_material * object.matrix_world

    # Select all new objects.
    print(" done in %.4f sec." % (time.perf_counter() - time1))
    file.close()


def load(
    operator,
    context,
    filepath="",
    constrain_size=0.0,
    use_image_search=True,
    use_apply_transform=True,
    global_matrix=None,
):

    load_3ds(
        filepath,
        context,
        IMPORT_CONSTRAIN_BOUNDS=constrain_size,
        IMAGE_SEARCH=use_image_search,
        APPLY_MATRIX=use_apply_transform,
        global_matrix=global_matrix,
    )

    return {"FINISHED"}
