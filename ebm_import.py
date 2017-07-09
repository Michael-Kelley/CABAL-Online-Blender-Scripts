import bpy
#import binary
import os
import tempfile

from bpy_extras.io_utils import ImportHelper, orientation_helper_factory, axis_conversion
from bpy.props import StringProperty, BoolProperty, EnumProperty
from bpy.types import Operator
from mathutils import Matrix, Vector


#----------------#


C = bpy.context
S = bpy.context.scene
D = bpy.data
O = bpy.ops

IOEBMOrientationHelper = orientation_helper_factory("IOEBMOrientationHelper", axis_forward='Z', axis_up='Y')


#----------------#


header = {}


#----------------#


def read_ebm_header(context, file):
	return {
		'u0':		read_byte(file),
		'ver':		read_int(file),
		'u1':		read_byte(file),
		'flag':		read_int(file),
		'bnd_min':	read_floats(file, 3),
		'bnd_max':	read_floats(file, 3),
		'scale':	read_int(file)
	}

def read_ebm_materials(context, file):
	count = read_short(file)

	return [{
		'ambient':	read_floats(file, 4),
		'diffuse':	read_floats(file, 4),
		'specular':	read_floats(file, 4),
		'emissive':	read_floats(file, 4),
		'power':	read_float(file),
		'texture': {
			'name':		str(file.read(read_short(file)), 'utf-8'),
			'data': 	file.read(read_int(file)),
			'faceted':	(read_byte(file) == 1),
			'scroll':	read_floats(file, 2)
		},
		'layer': {
			'mat_id':	read_int(file),
			'faceted':	(read_byte(file) == 1),
			'scroll':	read_floats(file, 2),
			'flags':	read_int(file)
		}
	} for _ in range(count)]

def read_ebm_bones(context, file):
	count = read_short(file)

	return [{
		'name':		str(file.read(read_short(file)), 'utf-8'),
		'parent':	read_int(file),
		'matrix':	[read_floats(file, 4) for _ in range(4)],
		'p_matrix':	[read_floats(file, 4) for _ in range(4)]
	} for _ in range(count)]

def read_ebm_meshes(context, file, bone_count):
	count = read_short(file)
	meshes = []

	global header

	for i in range(count):
		mesh = {
			'name':		str(file.read(read_short(file)), 'utf-8'),
			'world':	read_floats(file, 16),
			'local':	read_floats(file, 16),
			'root':		read_int(file),
			'mat':		read_byte(file)
		}

		vcount = read_short(file)
		fcount = read_short(file)

		if (header['ver'] == 0x3F1):
			efx = str(file.read(read_short(file)), 'utf-8')

		mesh['verts'] = [{
			'pos':	read_floats(file, 3),
			'norm':	read_floats(file, 3),
			'uv':	read_floats(file, 2)
		} for _ in range(vcount)]

		mesh['faces'] = [read_shorts(file, 3) for _ in range(fcount)]

		mesh['influences'] = []

		if (vcount > 0):
			cid = read_uint(file)
			icount = read_short(file)

			for _ in range(icount):
				influence = []

				for __ in range(bone_count):
					bcount = read_int(file)

					influence.append({
						'indices':	read_ints(file, bcount),
						'weights':	read_floats(file, bcount)
					})

				mesh['influences'].append(influence)

		meshes.append(mesh)

	return meshes

def read_ebm(context, filepath, g_matrix):#, use_some_setting):
	f = open(filepath, 'rb')

	global header
	header = read_ebm_header(context, f)
	cid = read_uint(f)
	materials = read_ebm_materials(context, f)
	cid = read_uint(f)
	bones = read_ebm_bones(context, f)
	cid = read_uint(f)
	meshes = read_ebm_meshes(context, f, len(bones))

	f.close()

	mats = []
	
	for m in materials:
		material = D.materials.new(m['texture']['name'])
		material.mirror_color = m['ambient'][:-1]
		material.ambient = m['ambient'][3]
		material.diffuse_color = m['diffuse'][:-1]
		material.alpha = m['diffuse'][3]
		material.specular_color = m['specular'][:-1]
		material.emit = m['emissive'][3]
		material.specular_hardness = m['power']

		t = m['texture']

		filename = os.path.join(tempfile.gettempdir(), t['name'])
		file = open(filename, 'wb')
		file.write(t['data'])
		file.close()

		tex = D.textures.new(t['name'], type = 'IMAGE')
		tex.image = D.images.load(filename)
		tex.use_alpha = True

		mtex = material.texture_slots.add()
		mtex.texture = tex
		mtex.texture_coords = 'UV'

		mats.append(material)

	armature = D.armatures.new('Armature')
	armature.draw_type = 'STICK'
	obj = D.objects.new('Armature', armature)
	obj.show_x_ray = True

	context.scene.objects.link(obj)
	context.scene.objects.active = obj
	obj.select = True
	O.object.mode_set(mode='EDIT')

	for b in bones:
		bone = armature.edit_bones.new(b['name'])
		matrix = Matrix(b['matrix']).inverted().transposed()
		bone.tail = [1,0,0]
		bone.transform(matrix, scale=True, roll=True)

		if (b['parent'] != -1):
			bone.parent = armature.edit_bones[b['parent']]

	O.object.mode_set(mode='OBJECT')
	armature.transform(g_matrix * obj.matrix_world)

	for m in meshes:
		mesh = D.meshes.new(m['name'])
		verts = [v['pos'] for v in m['verts']]
		norms = [v['norm'] for v in m['verts']]
		uvs = [[v['uv'][0],-v['uv'][1]] for v in m['verts']]
		faces = m['faces']
		mesh.from_pydata(verts, [], faces)

		for i in range(len(norms)):
			mesh.vertices[i].normal = norms[i]

		uvtex = mesh.uv_textures.new()
		uvtex.name = "imported"
		uvlayer = mesh.uv_layers.active

		for i in range(len(faces)):
			uvlayer.data[i*3].uv = uvs[faces[i][0]]
			uvlayer.data[i*3+1].uv = uvs[faces[i][1]]
			uvlayer.data[i*3+2].uv = uvs[faces[i][2]]

		mesh.materials.append(mats[m['mat']])

		obj = D.objects.new(m['name'], mesh)
		mesh.transform(g_matrix * obj.matrix_world)

		for n in m['influences']:
			for i in range(len(bones)):
				inf = n[i]
				bone = armature.bones[i]
				group = obj.vertex_groups.new(bone.name)

				for j in range(len(inf['weights'])):
					group.add([inf['indices'][j]], inf['weights'][j], 'REPLACE')

		mod = obj.modifiers.new('Armature', 'ARMATURE')
		mod.object = D.objects['Armature']
		mod.use_bone_envelopes = False
		mod.use_vertex_groups = True

		S.objects.link(obj)

	return {'FINISHED'}


#----------------#


class ImportEBM(Operator, ImportHelper, IOEBMOrientationHelper):
	"""Load a Cabal Online EBM file"""
	bl_idname = "import_scene.cabal_ebm"
	bl_label = "Load EBM"

	filename_ext = ".ebm"

	filter_glob = StringProperty(
			default="*.ebm",
			options={'HIDDEN'},
			maxlen=255,
			)	

	# List of operator properties, the attributes will be assigned
	# to the class instance from the operator settings before calling.
	'''use_setting = BoolProperty(
			name="Example Boolean",
			description="Example Tooltip",
			default=True,
			)

	type = EnumProperty(
			name="Example Enum",
			description="Choose between two items",
			items=(('OPT_A', "First Option", "Description one"),
				   ('OPT_B', "Second Option", "Description two")),
			default='OPT_A',
			)'''

	def execute(self, context):
		g_matrix = Matrix.Scale(0.05, 4)
		g_matrix *= axis_conversion(
			to_forward=self.axis_forward,
			to_up=self.axis_up
		).to_4x4()

		return read_ebm(context, self.filepath, g_matrix)#, self.use_setting)


#----------------#


def menu_func_import(self, context):
	self.layout.operator(ImportEBM.bl_idname, text="Cabal Online Model (.ebm)")

def register():
	bpy.utils.register_class(ImportEBM)
	bpy.types.INFO_MT_file_import.append(menu_func_import)

def unregister():
	bpy.utils.unregister_class(ImportEBM)
	bpy.types.INFO_MT_file_import.remove(menu_func_import)

if __name__ == "__main__":
	register()

	# test call
	O.import_scene.cabal_ebm('INVOKE_DEFAULT')