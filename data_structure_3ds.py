######################################################
# Data Structures
######################################################

# Some of the chunks that we will see

ROOT_OBJECT = 0xFFFF

# ----- Primary Chunk, at the beginning of each file
PRIMARY = 0x4D4D

# ------ Main Chunks
# This gives the version of the mesh and is found right before the material and object information
OBJECTINFO = 0x3D3D
VERSION = 0x0002  # This gives the version of the .3ds file
EDITKEYFRAME = 0xB000  # This is the header for all of the key frame info

# ------ Data Chunks, used for various attributes
PERCENTAGE_SHORT = 0x30
PERCENTAGE_FLOAT = 0x31

# ------ sub defines of OBJECTINFO
MATERIAL = 0xAFFF  # This stored the texture info
OBJECT = 0x4000  # This stores the faces, vertices, etc...

# >------ sub defines of MATERIAL
# ------ sub defines of MATERIAL_BLOCK
MAT_NAME = 0xA000  # This holds the material name
MAT_AMBIENT = 0xA010  # Ambient color of the object/material
MAT_DIFFUSE = 0xA020  # This holds the color of the object/material
MAT_SPECULAR = 0xA030  # SPecular color of the object/material
MAT_SHINESS = 0xA040  # ??
MAT_TRANSPARENCY = 0xA050  # Transparency value of material
MAT_SELF_ILLUM = 0xA080  # Self Illumination value of material
MAT_WIRE = 0xA085  # Only render's wireframe

MAT_TEXTURE_MAP = 0xA200  # This is a header for a new texture map
MAT_SPECULAR_MAP = 0xA204  # This is a header for a new specular map
MAT_OPACITY_MAP = 0xA210  # This is a header for a new opacity map
MAT_REFLECTION_MAP = 0xA220  # This is a header for a new reflection map
MAT_BUMP_MAP = 0xA230  # This is a header for a new bump map
MAT_MAP_FILEPATH = 0xA300  # This holds the file name of the texture

MAT_MAP_TILING = 0xa351   # 2nd bit (from LSB) is mirror UV flag
MAT_MAP_USCALE = 0xA354   # U axis scaling
MAT_MAP_VSCALE = 0xA356   # V axis scaling
MAT_MAP_UOFFSET = 0xA358  # U axis offset
MAT_MAP_VOFFSET = 0xA35A  # V axis offset
MAT_MAP_ANG = 0xA35C      # UV rotation around the z-axis in rad

MAT_FLOAT_COLOR = 0x0010  # color defined as 3 floats
MAT_24BIT_COLOR = 0x0011  # color defined as 3 bytes

# >------ sub defines of OBJECT
OBJECT_MESH = 0x4100  # This lets us know that we are reading a new object
OBJECT_LAMP = 0x4600  # This lets un know we are reading a light object
OBJECT_LAMP_SPOT = 0x4610  # The light is a spotloght.
OBJECT_LAMP_OFF = 0x4620  # The light off.
OBJECT_LAMP_ATTENUATE = 0x4625
OBJECT_LAMP_RAYSHADE = 0x4627
OBJECT_LAMP_SHADOWED = 0x4630
OBJECT_LAMP_LOCAL_SHADOW = 0x4640
OBJECT_LAMP_LOCAL_SHADOW2 = 0x4641
OBJECT_LAMP_SEE_CONE = 0x4650
OBJECT_LAMP_SPOT_RECTANGULAR = 0x4651
OBJECT_LAMP_SPOT_OVERSHOOT = 0x4652
OBJECT_LAMP_SPOT_PROJECTOR = 0x4653
OBJECT_LAMP_EXCLUDE = 0x4654
OBJECT_LAMP_RANGE = 0x4655
OBJECT_LAMP_ROLL = 0x4656
OBJECT_LAMP_SPOT_ASPECT = 0x4657
OBJECT_LAMP_RAY_BIAS = 0x4658
OBJECT_LAMP_INNER_RANGE = 0x4659
OBJECT_LAMP_OUTER_RANGE = 0x465A
OBJECT_LAMP_MULTIPLIER = 0x465B
OBJECT_LAMP_AMBIENT_LIGHT = 0x4680

OBJECT_CAMERA = 0x4700  # This lets un know we are reading a camera object

# >------ sub defines of CAMERA
OBJECT_CAM_RANGES = 0x4720  # The camera range values

# >------ sub defines of OBJECT_MESH
OBJECT_VERTICES = 0x4110  # The objects vertices
OBJECT_FACES = 0x4120  # The objects faces
# This is found if the object has a material, either texture map or color
OBJECT_MATERIAL = 0x4130
OBJECT_UV = 0x4140  # The UV texture coordinates
OBJECT_TRANS_MATRIX = 0x4160  # The Object Matrix

# >------ sub defines of EDITKEYFRAME
ED_KEY_AMBIENT_NODE = 0xB001
ED_KEY_OBJECT_NODE = 0xB002
ED_KEY_CAMERA_NODE = 0xB003
ED_KEY_TARGET_NODE = 0xB004
ED_KEY_LIGHT_NODE = 0xB005
ED_KEY_L_TARGET_NODE = 0xB006
ED_KEY_SPOTLIGHT_NODE = 0xB007
# >------ sub defines of ED_KEY_OBJECT_NODE
# EK_OB_KEYFRAME_SEG = 0xB008
# EK_OB_KEYFRAME_CURTIME = 0xB009
# EK_OB_KEYFRAME_HEADER = 0xB00A
EK_OB_NODE_HEADER = 0xB010
EK_OB_INSTANCE_NAME = 0xB011
# EK_OB_PRESCALE = 0xB012
EK_OB_PIVOT = 0xB013
# EK_OB_BOUNDBOX =   0xB014
# EK_OB_MORPH_SMOOTH = 0xB015
EK_OB_POSITION_TRACK = 0xB020
EK_OB_ROTATION_TRACK = 0xB021
EK_OB_SCALE_TRACK = 0xB022
# EK_OB_CAMERA_FOV_TRACK = 0xB023
# EK_OB_CAMERA_ROLL_TRACK = 0xB024
# EK_OB_COLOR_TRACK = 0xB025
# EK_OB_MORPH_TRACK = 0xB026
# EK_OB_HOTSPOT_TRACK = 0xB027
# EK_OB_FALLOF_TRACK = 0xB028
# EK_OB_HIDE_TRACK = 0xB029
# EK_OB_NODE_ID = 0xB030
