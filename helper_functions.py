import bpy
import struct

from . import localspace_variable_names


def deselect_all_objects():
    """
    Deselects all currently selected objects in the Blender scene.

    Args: None

    Returns: None
    """
    if bpy.ops.object.select_all.poll():
        bpy.ops.object.select_all(action='DESELECT')
    else:
        scn = bpy.context.scene
        for obj in scn.objects:
            obj.select_set(False)


def create_new_mesh(name):
    """
    Creates a new 3D mesh object in Blender.

    Args:
    name (str): Name of the new mesh.

    Returns:
    bpy.types.Mesh: The created mesh.
    """
    return bpy.data.meshes.new(name)


def add_vertices_to_mesh(mesh, vertices):
    """
    Adds vertices to a mesh.

    Args:
    mesh (bpy.types.Mesh): Mesh to add vertices to.
    vertices (list of float): List of vertex coordinates.

    Returns: None
    """
    mesh.vertices.add(len(vertices) // 3)
    mesh.vertices.foreach_set("co", vertices)


def add_faces_to_mesh(mesh, faces):
    """
    Adds faces to a mesh.

    Args:
    mesh (bpy.types.Mesh): Mesh to add faces to.
    faces (list of int): List of face indices.

    Returns: None
    """
    mesh.polygons.add(len(faces))
    mesh.loops.add(len(faces) * 3)
    rearranged_faces = [(v3, v1, v2) if v3 == 0 else (v1, v2, v3)
                        for v1, v2, v3 in faces]
    mesh.polygons.foreach_set("loop_start", range(0, len(faces) * 3, 3))
    mesh.polygons.foreach_set("loop_total", (3,) * len(faces))
    mesh.loops.foreach_set(
        "vertex_index", [vertex for face in rearranged_faces for vertex in face])


def add_uv_layer(mesh):
    """
    Adds a new UV layer to a mesh.

    Args:
    mesh (bpy.types.Mesh): Mesh to add UV layer to.

    Returns:
    list: UV data of the newly added UV layer.
    """
    mesh.uv_layers.new()
    return mesh.uv_layers.active.data[:]


def assign_material(mesh, materials, MATDICT, TEXTURE_DICT):
    """
    Assigns materials to a mesh.

    Args:
    mesh (bpy.types.Mesh): Mesh to assign materials to.
    materials (list of str): List of material names.
    MATDICT (dict): Dictionary for mapping material names to materials.
    TEXTURE_DICT (dict): Dictionary for mapping material names to textures.

    Returns: None
    """
    for idx, (matName, faces) in enumerate(materials):
        bmat = MATDICT.get(matName)
        if not bmat:
            bmat = bpy.data.materials.new(matName)
            MATDICT[matName] = bmat
            print(f"Warning: material {matName} not defined!")
        mesh.materials.append(bmat)
        img = TEXTURE_DICT.get(bmat.name)
        for fidx in faces:
            mesh.polygons[fidx].material_index = idx
            if img:
                bmat.use_nodes = True
                tex_image = bmat.node_tree.nodes.new('ShaderNodeTexImage')
                tex_image.image = img
                bmat.node_tree.nodes['Principled BSDF'].inputs[0].default_value = bmat.node_tree.nodes['Image Texture'].outputs[0].default_value


def set_uv(mesh, faces, contextMeshUV):
    """
    Sets the UV coordinates for a mesh.

    Args:
    mesh (bpy.types.Mesh): Mesh to set UV coordinates for.
    faces (list of int): List of face indices.
    contextMeshUV (list of float): List of UV coordinates.

    Returns: None
    """
    uvl = mesh.uv_layers.active.data[:]
    for idx, polygon in enumerate(mesh.polygons):
        v1, v2, v3 = faces[idx]
        if v3 == 0:
            v1, v2, v3 = v3, v1, v2
        uv_coords = [contextMeshUV[v * 2: (v * 2) + 2] for v in (v1, v2, v3)]
        for i, uv_coord in enumerate(uv_coords):
            uvl[polygon.loop_start + i].uv = uv_coord


def add_object_to_scene(mesh, name):
    """
    Adds a mesh object to the Blender scene.

    Args:
    mesh (bpy.types.Mesh): Mesh to add to the scene.
    name (str): Name of the new object.

    Returns:
    bpy.types.Object: The created object.
    """
    obj = bpy.data.objects.new(name, mesh)
    bpy.context.collection.objects.link(obj)
    return obj


def set_matrix(obj, matrix):
    """
    Sets the transformation matrix for an object.

    Args:
    obj (bpy.types.Object): Object to set the transformation matrix for.
    matrix (mathutils.Matrix): Transformation matrix to apply to the object.

    Returns: None
    """
    if matrix:
        obj.matrix_local = matrix.copy()


def add_texture_to_material(image, texture, scale, offset, extension, material, mapto):
    """
    Adds an image texture to a material, configures its scale and mapping, 
    and connects it to the appropriate shader input.

    Args:
    image (bpy.types.Image): Image to use as a texture.
    texture (bpy.types.Texture): Texture to apply to the material.
    scale (tuple): Tuple (u_scale, v_scale) to scale the texture.
    offset (tuple): Tuple (u_offset, v_offset) to offset the texture.
    extension (str): Type of texture extension ("mirror", "decal").
    material (bpy.types.Material): Material to apply the texture to.
    mapto (str): Type of mapping to use ("COLOR", "SPECULARITY", "ALPHA", "NORMAL").

    Returns: None
    """
    mapto_mapping = {
        'COLOR': 'Base Color',
        'SPECULARITY': 'Specular',
        'ALPHA': 'Alpha',
        'NORMAL': 'Normal'
    }

    if mapto not in mapto_mapping.keys():
        print(
            "\tError: Cannot map to %r\n\tassuming diffuse color. modify material %r later." %
            (mapto, material.name)
        )
        mapto = "COLOR"

    if image:
        texture.image = image

    material.use_nodes = True
    bsdf = material.node_tree.nodes["Principled BSDF"]

    tex_image = material.node_tree.nodes.new('ShaderNodeTexImage')
    tex_image.image = texture.image
    tex_image.location = (-300, 300)

    # Add mapping node and texture coordinate node
    tex_coord = material.node_tree.nodes.new('ShaderNodeTexCoord')
    mapping = material.node_tree.nodes.new('ShaderNodeMapping')

    # Connect texture coordinate to mapping input
    material.node_tree.links.new(
        mapping.inputs['Vector'], tex_coord.outputs['UV'])

    # Connect mapping output to image texture input
    material.node_tree.links.new(
        tex_image.inputs['Vector'], mapping.outputs['Vector'])

    # Set the scale values
    mapping.inputs['Scale'].default_value[0] = scale[0]
    mapping.inputs['Scale'].default_value[1] = scale[1]

    material.node_tree.links.new(
        bsdf.inputs[mapto_mapping[mapto]], tex_image.outputs['Color'])

    if extension == 'mirror':
        # To implement mirror or decal extension, additional logic is required.
        pass
    elif extension == 'decal':
        pass


def read_chunk(file, chunk):
    """
    Reads a chunk of data from the given file.

    Args:
    file (file): File to read data from.
    chunk (Chunk): Chunk object that holds the ID, length, and bytes read of the data chunk.

    Returns: None
    """
    temp_data = file.read(struct.calcsize(chunk.binary_format))
    data = struct.unpack(chunk.binary_format, temp_data)
    chunk.ID = data[0]
    chunk.length = data[1]
    chunk.bytes_read = 6  # update the bytes read function


def read_string(file):
    """
    Reads a null-terminated string from a file.

    Args:
    file (file): File to read the string from.

    Returns:
    tuple: A tuple (string, length), where 'string' is the read string and 'length' is the length of the string plus one for the null character.
    """
    s = []
    while True:
        c = file.read(1)
        if c == b'\x00':
            break
        s.append(c)
    return str(b''.join(s), "utf-8", "replace"), len(s) + 1


def read_float_color(file, temp_chunk):
    temp_data = file.read(localspace_variable_names.STRUCT_SIZE_3FLOAT)
    temp_chunk.bytes_read += localspace_variable_names.STRUCT_SIZE_3FLOAT
    return [float(col) for col in struct.unpack('<3f', temp_data)]
