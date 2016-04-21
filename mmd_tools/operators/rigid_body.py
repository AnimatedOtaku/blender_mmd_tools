# -*- coding: utf-8 -*-

import bpy
import math
import mathutils


from bpy.types import Operator

import mmd_tools.core.model as mmd_model
from mmd_tools.core import rigid_body
from mmd_tools import utils

class SelectRigidBody(Operator):
    bl_idname = 'mmd_tools.select_rigid_body'
    bl_label = 'Select Rigid Body'
    bl_description = ''
    bl_options = {'PRESET'}

    properties = bpy.props.EnumProperty(
        name='Properties',
        description='',
        options={'ENUM_FLAG'},
        items = [
            ('collision_group_number', 'Collision Group', '', 1),
            ('collision_group_mask', 'Collision Group Mask', '', 2),
            ('type', 'Rigid Type', '', 4),
            ('shape', 'Shape', '', 8),
            ('bone', 'Bone', '', 16),
            ],
        default=set(),
        )
    hide_others = bpy.props.BoolProperty(
        name='Hide Others',
        description='',
        default=False,
        )

    @classmethod
    def poll(cls, context):
        return mmd_model.isRigidBodyObject(context.active_object)

    def invoke(self, context, event):
        vm = context.window_manager
        return vm.invoke_props_dialog(self)

    def execute(self, context):
        obj = context.active_object
        root = mmd_model.Model.findRoot(obj)
        if root is None:
            self.report({ 'ERROR' }, "The model root can't be found")
            return { 'CANCELLED' }

        rig = mmd_model.Model(root)
        selection = {i for i in rig.rigidBodies()}

        for prop_name in self.properties:
            prop_value = getattr(obj.mmd_rigid, prop_name)
            if prop_name == 'collision_group_mask':
                prop_value = tuple(prop_value)
                for i in selection.copy():
                    if tuple(i.mmd_rigid.collision_group_mask) != prop_value:
                        selection.remove(i)
                        if self.hide_others:
                            i.select = False
                            i.hide = True
            else:
                for i in selection.copy():
                    if getattr(i.mmd_rigid, prop_name) != prop_value:
                        selection.remove(i)
                        if self.hide_others:
                            i.select = False
                            i.hide = True

        for i in selection:
            i.hide = False
            i.select = True

        return { 'FINISHED' }

class AddRigidBody(Operator):
    bl_idname = 'mmd_tools.add_rigid_body'
    bl_label = 'Add Rigid Body'
    bl_description = 'Adds a Rigid Body'
    bl_options = {'PRESET'}

    name_j = bpy.props.StringProperty(name='Name', default='$name_j')
    name_e = bpy.props.StringProperty(name='Name(Eng)', default='$name_e')

    collision_group_number = bpy.props.IntProperty(
        name='Collision Group',
        min=0,
        max=15,
        )
    collision_group_mask = bpy.props.BoolVectorProperty(
        name='Collision Group Mask',
        size=16,
        subtype='LAYER',
        )
    rigid_type = bpy.props.EnumProperty(
        name='Rigid Type',
        items = [
            (str(rigid_body.MODE_STATIC), 'Static', '', 1),
            (str(rigid_body.MODE_DYNAMIC), 'Dynamic', '', 2),
            (str(rigid_body.MODE_DYNAMIC_BONE), 'Dynamic&BoneTrack', '', 3),
            ],
        )
    rigid_shape = bpy.props.EnumProperty(
        name='Shape',
        items = [
            ('SPHERE', 'Sphere', '', 1),
            ('BOX', 'Box', '', 2),
            ('CAPSULE', 'Capsule', '', 3),
            ],
        )

    def __add_rigid_body(self, rig, arm_obj=None, pose_bone=None):
        name_j = self.name_j
        name_e = self.name_e
        loc = (0.0, 0.0, 0.0)
        rot = (0.0, 0.0, 0.0)
        size = mathutils.Vector([0.6, 0.6, 0.6])
        bone_name = None

        if pose_bone:
            bone_name = pose_bone.name
            name_j = name_j.replace('$name_j', pose_bone.mmd_bone.name_j or bone_name)
            name_e = name_e.replace('$name_e', pose_bone.mmd_bone.name_e or bone_name)

            target_bone = pose_bone.bone
            loc = (target_bone.head_local + target_bone.tail_local)/2
            rot = target_bone.matrix_local.to_euler('YXZ')
            rot.rotate_axis('X', math.pi/2)

            size *= target_bone.length
            if self.rigid_shape == 'SPHERE':
                size.x *= 0.8
            elif self.rigid_shape == 'BOX':
                size.x /= 3
                size.y /= 3
                size.z *= 0.8
            elif self.rigid_shape == 'CAPSULE':
                size.x /= 3

        return rig.createRigidBody(
                name = name_j,
                name_e = name_e,
                shape_type = rigid_body.shapeType(self.rigid_shape),
                dynamics_type = int(self.rigid_type),
                location = loc,
                rotation = rot,
                size = size,
                collision_group_number = self.collision_group_number,
                collision_group_mask = self.collision_group_mask,
                mass=1,
                friction = 0.0,
                angular_damping = 0.5,
                linear_damping = 0.5,
                bounce = 0.5,
                bone = bone_name,
                )

    def execute(self, context):
        obj = context.active_object
        root = mmd_model.Model.findRoot(obj)
        rig = mmd_model.Model(root)
        arm = rig.armature()
        if obj != arm:
            utils.selectAObject(root)
            root.select = False
        elif arm.mode != 'POSE':
            bpy.ops.object.mode_set(mode='POSE')

        selected_pose_bones = []
        if context.selected_pose_bones:
            selected_pose_bones = context.selected_pose_bones

        arm.select = False
        if len(selected_pose_bones) > 0:
            for pose_bone in selected_pose_bones:
                rigid = self.__add_rigid_body(rig, arm, pose_bone)
                rigid.select = True
        else:
            rigid = self.__add_rigid_body(rig)
            rigid.select = True
        return { 'FINISHED' }

    def invoke(self, context, event):
        no_bone = True
        if context.selected_bones and len(context.selected_bones) > 0:
            no_bone = False
        elif context.selected_pose_bones and len(context.selected_pose_bones) > 0:
            no_bone = False

        if no_bone:
            self.name_j = 'Rigid'
            self.name_e = 'Rigid_e'
        else:
            if self.name_j == 'Rigid':
                self.name_j = '$name_j'
            if self.name_e == 'Rigid_e':
                self.name_e = '$name_e'
        vm = context.window_manager
        return vm.invoke_props_dialog(self)

class RemoveRigidBody(Operator):
    bl_idname = 'mmd_tools.remove_rigid_body'
    bl_label = 'Remove Rigid Body'
    bl_description = 'Deletes the currently selected Rigid Body'
    bl_options = {'PRESET'}

    @classmethod
    def poll(cls, context):
        return mmd_model.isRigidBodyObject(context.active_object)

    def execute(self, context):
        obj = context.active_object
        root = mmd_model.Model.findRoot(obj)
        utils.selectAObject(obj) #ensure this is the only one object select
        bpy.ops.object.delete(use_global=True)
        if root:
            utils.selectAObject(root)
        return { 'FINISHED' } 

class AddJoint(Operator): 
    bl_idname = 'mmd_tools.add_joint'
    bl_label = 'Add Joint'
    bl_options = {'PRESET'} 

    use_bone_rotation = bpy.props.BoolProperty(
        name='Use Bone Rotation',
        description='',
        default=True,
        )

    def __enumerate_rigid_pair(self, bone_map):
        obj_seq = tuple(bone_map.keys())
        for rigid_a, bone_a in bone_map.items():
            for rigid_b, bone_b in bone_map.items():
                if bone_a and bone_b and bone_b.parent == bone_a:
                    obj_seq = ()
                    yield (rigid_a, rigid_b)
        if len(obj_seq) == 2:
            if obj_seq[1].mmd_rigid.type == str(rigid_body.MODE_STATIC):
                yield (obj_seq[1], obj_seq[0])
            else:
                yield obj_seq

    def __add_joint(self, rig, mmd_root, rigid_pair, bone_map):
        loc, rot = None, [0, 0, 0]
        rigid_a, rigid_b = rigid_pair
        bone_a = bone_map[rigid_a]
        bone_b = bone_map[rigid_b]
        if bone_a and bone_b:
            if bone_a.parent == bone_b:
                rigid_b, rigid_a = rigid_a, rigid_b
                bone_b, bone_a = bone_a, bone_b
            if bone_b.parent == bone_a:
                loc = bone_b.head_local
                if self.use_bone_rotation:
                    rot = bone_b.matrix_local.to_euler('YXZ')
                    rot.rotate_axis('X', math.pi/2)
        if loc is None:
            loc = (rigid_a.location + rigid_b.location)/2

        name_j = rigid_b.mmd_rigid.name_j or rigid_b.name
        name_e = rigid_b.mmd_rigid.name_e or rigid_b.name
        return rig.createJoint(
                name = name_j,
                name_e = name_e,
                location = loc,
                rotation = rot,
                size = 0.5 * mmd_root.scale,
                rigid_a = rigid_a,
                rigid_b = rigid_b,
                maximum_location = [0, 0, 0],
                minimum_location = [0, 0, 0],
                maximum_rotation = [math.pi/4]*3,
                minimum_rotation = [-math.pi/4]*3,
                spring_linear = [0, 0, 0],
                spring_angular = [0, 0, 0],
                )

    def execute(self, context):
        obj = context.active_object
        root = mmd_model.Model.findRoot(obj)
        rig = mmd_model.Model(root)
        mmd_root = rig.rootObject().mmd_root

        arm = rig.armature()
        bone_map = {}
        for i in context.selected_objects:
            if mmd_model.isRigidBodyObject(i):
                bone_map[i] = arm.data.bones.get(i.mmd_rigid.bone, None)

        if len(bone_map) < 2:
            self.report({ 'ERROR' }, "Please select two or more mmd rigid objects")
            return { 'CANCELLED' }

        utils.selectAObject(root)
        root.select = False
        if context.scene.rigidbody_world is None:
            bpy.ops.rigidbody.world_add()

        for pair in self.__enumerate_rigid_pair(bone_map):
            joint = self.__add_joint(rig, mmd_root, pair, bone_map)
            joint.select = True

        return { 'FINISHED' }

    def invoke(self, context, event):
        vm = context.window_manager
        return vm.invoke_props_dialog(self)

class RemoveJoint(Operator):
    bl_idname = 'mmd_tools.remove_joint'
    bl_label = 'Remove Joint'
    bl_description = 'Deletes the currently selected Joint'
    bl_options = {'PRESET'}  

    @classmethod
    def poll(cls, context):
        return mmd_model.isJointObject(context.active_object)

    def execute(self, context):
        obj = context.active_object
        root = mmd_model.Model.findRoot(obj)
        utils.selectAObject(obj) #ensure this is the only one object select
        bpy.ops.object.delete(use_global=True)
        if root:
            utils.selectAObject(root)
        return { 'FINISHED' }
