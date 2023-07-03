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


def process_next_object_chunk(file, previous_chunk):
    new_chunk = Chunk3DS()

    while (previous_chunk.bytes_read < previous_chunk.length):
        helper_functions.read_chunk(file, new_chunk)


def skip_to_end(file, skip_chunk):
    buffer_size = skip_chunk.length - skip_chunk.bytes_read
    binary_format = "%ic" % buffer_size
    file.read(struct.calcsize(binary_format))
    skip_chunk.bytes_read += buffer_size


def process_next_chunk(file, previous_chunk, importedObjects, IMAGE_SEARCH):
    from bpy_extras.image_utils import load_image

    # print previous_chunk.bytes_read, 'BYTES READ'
    contextObName = None
    contextLamp = [None, None]  # object, Data
    contextMaterial = None
    contextMatrix_rot = None  # Blender.mathutils.Matrix(); contextMatrix.identity()
    contextMesh_vertls = None  # flat array: (verts * 3)
    contextMesh_facels = None
    contextMeshMaterials = []  # (matname, [face_idxs])
    contextMeshUV = None  # flat array (verts * 2)

    textureDict = {}
    materialDic = {}

    # only init once
    object_list = []  # for hierarchy
    object_parent = []  # index of parent in hierarchy, 0xFFFF = no parent
    pivot_list = []  # pivots with hierarchy handling

    def putContextMesh(myContextMesh_vertls, myContextMesh_facels, myContextMeshMaterials):
        myContextMesh_facels = myContextMesh_facels or []

        if myContextMesh_vertls:
            bmesh = helper_functions.create_new_mesh(contextObName)
            helper_functions.add_vertices_to_mesh(bmesh, myContextMesh_vertls)
            helper_functions.add_faces_to_mesh(bmesh, myContextMesh_facels)

            uv_faces = helper_functions.add_uv_layer(
                bmesh) if bmesh.polygons and contextMeshUV else None

            helper_functions.assign_material(
                bmesh, myContextMeshMaterials, materialDic, textureDict)

            if uv_faces:
                helper_functions.set_uv(
                    bmesh, myContextMesh_facels, contextMeshUV)

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

    def read_float(temp_chunk):
        temp_data = file.read(localspace_variable_names.STRUCT_SIZE_FLOAT)
        temp_chunk.bytes_read += localspace_variable_names.STRUCT_SIZE_FLOAT
        return struct.unpack('<f', temp_data)[0]

    def read_short(temp_chunk):
        temp_data = file.read(
            localspace_variable_names.STRUCT_SIZE_UNSIGNED_SHORT)
        temp_chunk.bytes_read += localspace_variable_names.STRUCT_SIZE_UNSIGNED_SHORT
        return struct.unpack('<H', temp_data)[0]

    def read_byte_color(temp_chunk):
        temp_data = file.read(struct.calcsize('3B'))
        temp_chunk.bytes_read += 3
        # data [0,1,2] == rgb
        return [float(col) / 255 for col in struct.unpack('<3B', temp_data)]

    def read_texture(new_chunk, temp_chunk, name, mapto):
        new_texture = bpy.data.textures.new(name, type='IMAGE')

        u_scale, v_scale, u_offset, v_offset = 1.0, 1.0, 0.0, 0.0
        extension = 'wrap'
        while (new_chunk.bytes_read < new_chunk.length):
            # print 'MAT_TEXTURE_MAP..while', new_chunk.bytes_read, new_chunk.length
            helper_functions.read_chunk(file, temp_chunk)

            if temp_chunk.ID == data_structure_3ds.MAT_MAP_FILEPATH:
                texture_name, read_str_len = helper_functions.read_string(file)

                img = textureDict[contextMaterial.name] = load_image(
                    texture_name, dirname)
                # plus one for the null character that gets removed
                temp_chunk.bytes_read += read_str_len

            elif temp_chunk.ID == data_structure_3ds.MAT_MAP_USCALE:
                u_scale = read_float(temp_chunk)
            elif temp_chunk.ID == data_structure_3ds.MAT_MAP_VSCALE:
                v_scale = read_float(temp_chunk)

            elif temp_chunk.ID == data_structure_3ds.MAT_MAP_UOFFSET:
                u_offset = read_float(temp_chunk)
            elif temp_chunk.ID == data_structure_3ds.MAT_MAP_VOFFSET:
                v_offset = read_float(temp_chunk)

            elif temp_chunk.ID == data_structure_3ds.MAT_MAP_TILING:
                tiling = read_short(temp_chunk)
                if tiling & 0x2:
                    extension = 'mirror'
                elif tiling & 0x10:
                    extension = 'decal'

            elif temp_chunk.ID == data_structure_3ds.MAT_MAP_ANG:
                print("\nwarning: ignoring UV rotation")

            skip_to_end(file, temp_chunk)
            new_chunk.bytes_read += temp_chunk.bytes_read

        # add the map to the material in the right channel
        if img:
            helper_functions.add_texture_to_material(img, new_texture, (u_scale, v_scale),
                                                     (u_offset, v_offset), extension, contextMaterial, mapto)

    dirname = os.path.dirname(file.name)

    # loop through all the data for this chunk (previous chunk) and see what it is
    while (previous_chunk.bytes_read < previous_chunk.length):
        # print '\t', previous_chunk.bytes_read, 'keep going'
        # read the next chunk
        # print 'reading a chunk'
        helper_functions.read_chunk(file, new_chunk)

        print(str(hex(new_chunk.ID)) + " - " + str(int(new_chunk.length)))

        # is it a Version chunk?
        if new_chunk.ID == data_structure_3ds.VERSION:
            # print 'if new_chunk.ID == VERSION:'
            # print 'found a VERSION chunk'
            # read in the version of the file
            # it's an unsigned short (H)
            temp_data = file.read(struct.calcsize('I'))
            version = struct.unpack('<I', temp_data)[0]
            new_chunk.bytes_read += 4  # read the 4 bytes for the version number
            # this loader works with version 3 and below, but may not with 4 and above
            if version > 3:
                print(
                    '\tNon-Fatal Error:  Version greater than 3, may not load correctly: ', version)

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
                putContextMesh(contextMesh_vertls,
                               contextMesh_facels, contextMeshMaterials)
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

            # print("read material")

            # print 'elif new_chunk.ID == MATERIAL:'
            contextMaterial = bpy.data.materials.new('Material')

        elif new_chunk.ID == data_structure_3ds.MAT_NAME:
            # print 'elif new_chunk.ID == MAT_NAME:'
            material_name, read_str_len = helper_functions.read_string(file)

# 			print("material name", material_name)

            # plus one for the null character that ended the string
            new_chunk.bytes_read += read_str_len

            contextMaterial.name = material_name.rstrip()  # remove trailing  whitespace
            materialDic[material_name] = contextMaterial

        elif new_chunk.ID == data_structure_3ds.MAT_AMBIENT:
            helper_functions.read_chunk(file, temp_chunk)
            if temp_chunk.ID == data_structure_3ds.MAT_FLOAT_COLOR:
                color = helper_functions.read_float_color(file, temp_chunk)
                contextMaterial.diffuse_color = color + \
                    [1.0]  # Adding alpha value as list
            elif temp_chunk.ID == data_structure_3ds.MAT_24BIT_COLOR:
                color = read_byte_color(temp_chunk)
                contextMaterial.diffuse_color = color + \
                    [1.0]  # Adding alpha value as list
            else:
                skip_to_end(file, temp_chunk)
            new_chunk.bytes_read += temp_chunk.bytes_read

            if not contextMaterial.use_nodes:
                contextMaterial.use_nodes = True

            bsdf_node = contextMaterial.node_tree.nodes.get('Principled BSDF')
            if bsdf_node:
                bsdf_node.inputs['Specular'].default_value = 1.0
                bsdf_node.inputs['Roughness'].default_value = 0.0

        elif new_chunk.ID == data_structure_3ds.MAT_DIFFUSE:
            helper_functions.read_chunk(file, temp_chunk)
            if temp_chunk.ID == data_structure_3ds.MAT_FLOAT_COLOR:
                color = helper_functions.read_float_color(file, temp_chunk)
                contextMaterial.diffuse_color = color + [1.0]  # Add alpha
            elif temp_chunk.ID == data_structure_3ds.MAT_24BIT_COLOR:
                color = read_byte_color(temp_chunk)
                contextMaterial.diffuse_color = color + [1.0]  # Add alpha
            else:
                skip_to_end(file, temp_chunk)
            new_chunk.bytes_read += temp_chunk.bytes_read

            if not contextMaterial.use_nodes:
                contextMaterial.use_nodes = True

            bsdf_node = contextMaterial.node_tree.nodes.get('Principled BSDF')
            if bsdf_node:
                bsdf_node.inputs['Base Color'].default_value = contextMaterial.diffuse_color

        elif new_chunk.ID == data_structure_3ds.MAT_SPECULAR:
            # print 'elif new_chunk.ID == MAT_SPECULAR:'
            helper_functions.read_chunk(file, temp_chunk)
            if temp_chunk.ID == data_structure_3ds.MAT_FLOAT_COLOR:
                contextMaterial.specular_color = helper_functions.read_float_color(
                    file, temp_chunk)
            elif temp_chunk.ID == data_structure_3ds.MAT_24BIT_COLOR:
                contextMaterial.specular_color = read_byte_color(temp_chunk)
            else:
                skip_to_end(file, temp_chunk)
            new_chunk.bytes_read += temp_chunk.bytes_read

        elif new_chunk.ID == data_structure_3ds.MAT_TEXTURE_MAP:
            read_texture(new_chunk, temp_chunk, "Diffuse", "COLOR")

        elif new_chunk.ID == data_structure_3ds.MAT_SPECULAR_MAP:
            read_texture(new_chunk, temp_chunk, "Specular", "SPECULARITY")

        elif new_chunk.ID == data_structure_3ds.MAT_OPACITY_MAP:
            read_texture(new_chunk, temp_chunk, "Opacity", "ALPHA")

        elif new_chunk.ID == data_structure_3ds.MAT_BUMP_MAP:
            read_texture(new_chunk, temp_chunk, "Bump", "NORMAL")

        elif new_chunk.ID == data_structure_3ds.MAT_TRANSPARENCY:
            helper_functions.read_chunk(file, temp_chunk)

            alpha_value = 1.0
            if temp_chunk.ID == data_structure_3ds.PERCENTAGE_SHORT:
                temp_data = file.read(
                    localspace_variable_names.STRUCT_SIZE_UNSIGNED_SHORT)
                temp_chunk.bytes_read += localspace_variable_names.STRUCT_SIZE_UNSIGNED_SHORT
                alpha_value = 1 - \
                    (float(struct.unpack('<H', temp_data)[0]) / 100)
            elif temp_chunk.ID == data_structure_3ds.PERCENTAGE_FLOAT:
                temp_data = file.read(
                    localspace_variable_names.STRUCT_SIZE_FLOAT)
                temp_chunk.bytes_read += localspace_variable_names.STRUCT_SIZE_FLOAT
                alpha_value = 1 - float(struct.unpack('f', temp_data)[0])
            else:
                print("Cannot read material transparency")

            new_chunk.bytes_read += temp_chunk.bytes_read

            if not contextMaterial.use_nodes:
                contextMaterial.use_nodes = True

            bsdf_node = contextMaterial.node_tree.nodes.get('Principled BSDF')
            if bsdf_node:
                bsdf_node.inputs['Alpha'].default_value = alpha_value

        elif new_chunk.ID == data_structure_3ds.OBJECT_LAMP:  # Basic lamp support.

            temp_data = file.read(localspace_variable_names.STRUCT_SIZE_3FLOAT)

            x, y, z = struct.unpack('<3f', temp_data)
            new_chunk.bytes_read += localspace_variable_names.STRUCT_SIZE_3FLOAT

            # no lamp in dict that would be confusing
            contextLamp[1] = bpy.data.lamps.new("Lamp", 'POINT')
            contextLamp[0] = ob = bpy.data.objects.new("Lamp", contextLamp[1])

            SCN.collection.objects.link(ob)
            importedObjects.append(contextLamp[0])
            contextLamp[0].location = x, y, z

            # Reset matrix
            contextMatrix_rot = None

        elif new_chunk.ID == data_structure_3ds.OBJECT_MESH:
            # print 'Found an OBJECT_MESH chunk'
            pass
        elif new_chunk.ID == data_structure_3ds.OBJECT_VERTICES:
            """
            Worldspace vertex locations
            """
            # print 'elif new_chunk.ID == OBJECT_VERTICES:'
            temp_data = file.read(
                localspace_variable_names.STRUCT_SIZE_UNSIGNED_SHORT)
            num_verts = struct.unpack('<H', temp_data)[0]
            new_chunk.bytes_read += 2

            # print 'number of verts: ', num_verts
            contextMesh_vertls = struct.unpack(
                '<%df' % (num_verts * 3), file.read(localspace_variable_names.STRUCT_SIZE_3FLOAT * num_verts))
            new_chunk.bytes_read += localspace_variable_names.STRUCT_SIZE_3FLOAT * num_verts
            # dummyvert is not used atm!

            # print 'object verts: bytes read: ', new_chunk.bytes_read

        elif new_chunk.ID == data_structure_3ds.OBJECT_FACES:
            # print 'elif new_chunk.ID == OBJECT_FACES:'
            temp_data = file.read(
                localspace_variable_names.STRUCT_SIZE_UNSIGNED_SHORT)
            num_faces = struct.unpack('<H', temp_data)[0]
            new_chunk.bytes_read += 2
            # print 'number of faces: ', num_faces

            # print '\ngetting a face'
            temp_data = file.read(
                localspace_variable_names.STRUCT_SIZE_4UNSIGNED_SHORT * num_faces)
            new_chunk.bytes_read += localspace_variable_names.STRUCT_SIZE_4UNSIGNED_SHORT * \
                num_faces  # 4 short ints x 2 bytes each
            contextMesh_facels = struct.unpack(
                '<%dH' % (num_faces * 4), temp_data)
            contextMesh_facels = [contextMesh_facels[i - 3:i]
                                  for i in range(3, (num_faces * 4) + 3, 4)]

        elif new_chunk.ID == data_structure_3ds.OBJECT_MATERIAL:
            # print 'elif new_chunk.ID == OBJECT_MATERIAL:'
            material_name, read_str_len = helper_functions.read_string(file)
            new_chunk.bytes_read += read_str_len  # remove 1 null character.

            temp_data = file.read(
                localspace_variable_names.STRUCT_SIZE_UNSIGNED_SHORT)
            num_faces_using_mat = struct.unpack('<H', temp_data)[0]
            new_chunk.bytes_read += localspace_variable_names.STRUCT_SIZE_UNSIGNED_SHORT

            temp_data = file.read(
                localspace_variable_names.STRUCT_SIZE_UNSIGNED_SHORT * num_faces_using_mat)
            new_chunk.bytes_read += localspace_variable_names.STRUCT_SIZE_UNSIGNED_SHORT * \
                num_faces_using_mat

            temp_data = struct.unpack(
                "<%dH" % (num_faces_using_mat), temp_data)

            contextMeshMaterials.append((material_name, temp_data))

            # look up the material in all the materials

        elif new_chunk.ID == data_structure_3ds.OBJECT_UV:
            temp_data = file.read(
                localspace_variable_names.STRUCT_SIZE_UNSIGNED_SHORT)
            num_uv = struct.unpack('<H', temp_data)[0]
            new_chunk.bytes_read += 2

            temp_data = file.read(
                localspace_variable_names.STRUCT_SIZE_2FLOAT * num_uv)
            new_chunk.bytes_read += localspace_variable_names.STRUCT_SIZE_2FLOAT * num_uv
            contextMeshUV = struct.unpack('<%df' % (num_uv * 2), temp_data)

        elif new_chunk.ID == data_structure_3ds.OBJECT_TRANS_MATRIX:
            # How do we know the matrix size? 54 == 4x4 48 == 4x3
            temp_data = file.read(localspace_variable_names.STRUCT_SIZE_4x3MAT)
            data = list(struct.unpack('<ffffffffffff', temp_data))
            new_chunk.bytes_read += localspace_variable_names.STRUCT_SIZE_4x3MAT

            contextMatrix_rot = mathutils.Matrix((data[:3] + [0],
                                                  data[3:6] + [0],
                                                  data[6:9] + [0],
                                                  data[9:] + [1],
                                                  )).transposed()

        elif (new_chunk.ID == data_structure_3ds.MAT_MAP_FILEPATH):
            texture_name, read_str_len = helper_functions.read_string(file)
            if contextMaterial.name not in textureDict:
                textureDict[contextMaterial.name] = load_image(
                    texture_name, dirname, place_holder=False, recursive=IMAGE_SEARCH)

            # plus one for the null character that gets removed
            new_chunk.bytes_read += read_str_len
        elif new_chunk.ID == data_structure_3ds.EDITKEYFRAME:
            pass

        # including these here means their EK_OB_NODE_HEADER are scanned
        elif new_chunk.ID in {data_structure_3ds.ED_KEY_AMBIENT_NODE,
                              data_structure_3ds.ED_KEY_OBJECT_NODE,
                              data_structure_3ds.ED_KEY_CAMERA_NODE,
                              data_structure_3ds.ED_KEY_TARGET_NODE,
                              data_structure_3ds.ED_KEY_LIGHT_NODE,
                              data_structure_3ds.ED_KEY_L_TARGET_NODE,
                              data_structure_3ds.ED_KEY_SPOTLIGHT_NODE}:  # another object is being processed
            child = None

        else:
            # print 'skipping to end of this chunk'
            # print("unknown chunk: "+hex(new_chunk.ID))
            buffer_size = new_chunk.length - new_chunk.bytes_read
            binary_format = "%ic" % buffer_size
            temp_data = file.read(struct.calcsize(binary_format))
            new_chunk.bytes_read += buffer_size

        # update the previous chunk bytes read
        previous_chunk.bytes_read += new_chunk.bytes_read
        # print 'Bytes left in this chunk: ', previous_chunk.length - previous_chunk.bytes_read

    # FINISHED LOOP
    # There will be a number of objects still not added
    if CreateBlenderObject:
        putContextMesh(contextMesh_vertls, contextMesh_facels,
                       contextMeshMaterials)

    # Assign parents to objects
    # check _if_ we need to assign first because doing so recalcs the depsgraph
    for ind, ob in enumerate(object_list):
        parent = object_parent[ind]
        if parent == data_structure_3ds.ROOT_OBJECT:
            if ob.parent is not None:
                ob.parent = None
        else:
            # Avoid self-parenting and index out of range
            if parent < len(object_list) and ob != object_list[parent]:
                ob.parent = object_list[parent]

    # fix pivots
    for ind, ob in enumerate(object_list):
        if ob.type == 'MESH':
            pivot = pivot_list[ind]
            pivot_matrix = OBJECT_MATRIX.get(
                ob, mathutils.Matrix())  # unlikely to fail
            pivot_matrix = mathutils.Matrix.Translation(
                pivot_matrix.to_3x3() @ -pivot)
            ob.data.transform(pivot_matrix)


def load_3ds(filepath,
             context,
             IMPORT_CONSTRAIN_BOUNDS=10.0,
             IMAGE_SEARCH=True,
             APPLY_MATRIX=True,
             global_matrix=None):

    print("importing 3DS: %r..." % (filepath), end="")
    time1 = time.perf_counter()

    current_chunk = Chunk3DS()
    file = open(filepath, 'rb')

    # Deselect all other objects
    helper_functions.deselect_all_objects()

    # here we go!
    helper_functions.read_chunk(file, current_chunk)
    if current_chunk.ID != data_structure_3ds.PRIMARY:
        print('\tFatal Error:  Not a valid 3ds file: %r' % filepath)
        file.close()
        return

    if IMPORT_CONSTRAIN_BOUNDS:
        BOUNDS_3DS[:] = [1 << 30, 1 << 30, 1 <<
                         30, -1 << 30, -1 << 30, -1 << 30]
    else:
        del BOUNDS_3DS[:]

    # IMAGE_SEARCH
    importedObjects = []  # Fill this list with objects
    process_next_chunk(file, current_chunk, importedObjects, IMAGE_SEARCH)

    # fixme, make unglobal, clear in case
    OBJECT_DICTIONARY.clear()
    OBJECT_MATRIX.clear()

    if APPLY_MATRIX:
        for ob in importedObjects:
            if ob.type == 'MESH':
                me = ob.data
                me.transform(ob.matrix_local.inverted())

    if global_matrix:
        for ob in importedObjects:
            if ob.parent is None:
                ob.matrix_world = ob.matrix_world * global_matrix

    for ob in importedObjects:
        context.view_layer.objects.active = ob
        ob.select_set(True)

    layer = bpy.context.view_layer
    layer.update()

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
        max_axis = max(axis_max[0] - axis_min[0],
                       axis_max[1] - axis_min[1],
                       axis_max[2] - axis_min[2])
        scale = 1.0

        while global_clamp_size < max_axis * scale:
            scale = scale / 10.0

        scale_mat = mathutils.Matrix.Scale(scale, 4)

        for obj in importedObjects:
            if obj.parent is None:
                obj.matrix_world = scale_mat * obj.matrix_world

    # Select all new objects.
    print(" done in %.4f sec." % (time.perf_counter() - time1))
    file.close()


def load(operator,
         context,
         filepath="",
         constrain_size=0.0,
         use_image_search=True,
         use_apply_transform=True,
         global_matrix=None,
         ):

    load_3ds(filepath,
             context,
             IMPORT_CONSTRAIN_BOUNDS=constrain_size,
             IMAGE_SEARCH=use_image_search,
             APPLY_MATRIX=use_apply_transform,
             global_matrix=global_matrix,
             )

    return {'FINISHED'}
