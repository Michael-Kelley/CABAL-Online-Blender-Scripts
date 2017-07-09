import bpy
import os

filename = os.path.join(os.path.dirname(bpy.data.filepath), "binary.py")
exec(compile(open(filename).read(), filename, 'exec'))

filename = os.path.join(os.path.dirname(bpy.data.filepath), "ebm_import.py")
exec(compile(open(filename).read(), filename, 'exec'))