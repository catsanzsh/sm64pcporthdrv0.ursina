 
from ursina import *
from math import sin, cos, atan2
import time
import numpy as np
import random

# Custom colors for N64-like palette
color_mario_blue  = color.rgb(0, 0, 255)
color_mario_red   = color.rgb(255, 0, 0)
color_mario_peach = color.rgb(255, 182, 193)
color_grass_green = color.rgb(34, 139, 34)
color_dirt_brown  = color.rgb(139, 69, 19)
color_coin_gold   = color.rgb(255, 215, 0)

class Mario64(Entity):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.model    = None
        self.color    = color.clear
        self.collider = 'box'
        self.scale    = (0.6, 1.8, 0.6)
        self.origin_y = -0.5

        # Enhanced Mario model
        self.visual   = Entity(parent=self, model='cube', color=color_mario_blue, scale=(0.8, 1.6, 0.4))
        self.hat      = Entity(parent=self.visual, model='cube', color=color_mario_red,
                               scale=(0.9, 0.3, 0.9), position=(0, 0.8, 0))
        self.face     = Entity(parent=self.visual, model='quad', color=color_mario_peach,
                               scale=(0.4, 0.4), position=(0, 0.4, 0.21))
        self.eye_l    = Entity(parent=self.face, model='quad', color=color.black,
                               scale=(0.2, 0.2), position=(-0.3, 0.2, 0.01))
        self.eye_r    = Entity(parent=self.face, model='quad', color=color.black,
                               scale=(0.2, 0.2), position=(0.3, 0.2, 0.01))
        self.mustache = Entity(parent=self.face, model='quad', color=color.black,
                               scale=(0.4, 0.1), position=(0, -0.2, 0.01))
        self.arm_l    = Entity(parent=self.visual, model='cube', color=color_mario_blue,
                               scale=(0.2, 0.5, 0.2), position=(-0.5, 0, 0))
        self.arm_r    = Entity(parent=self.visual, model='cube', color=color_mario_blue,
                               scale=(0.2, 0.5, 0.2), position=(0.5, 0, 0))
        self.leg_l    = Entity(parent=self.visual, model='cube', color=color_mario_blue,
                               scale=(0.2, 0.5, 0.2), position=(-0.2, -0.8, 0))
        self.leg_r    = Entity(parent=self.visual, model='cube', color=color_mario_blue,
                               scale=(0.2, 0.5, 0.2), position=(0.2, -0.8, 0))

        # Movement parameters
        self.speed            = 10
        self.turn_speed       = 160
        self.jump_height      = 5.0
        self.double_jump_height = 6.0
        self.triple_jump_height = 7.5
        self.jump_duration    = 0.35
        self.gravity_strength = 24
        self.velocity_y       = 0
        self.momentum         = Vec3(0, 0, 0)
        self.grounded         = True
        self.jump_count       = 0
        self.last_jump_time   = 0
        self.crouching        = False
        self.diving           = False
        self.sliding          = False
        self.wall_kick_cooldown = 0
        self.coins            = 0
        self.show_collider    = False
        self.ground_pound_landed = False

    def update(self):
        # Camera-based movement
        move_dir = Vec3(0, 0, 0)
        if held_keys['w'] or held_keys['up arrow']:
            move_dir += camera.forward * Vec3(1, 0, 1)
        if held_keys['s'] or held_keys['down arrow']:
            move_dir += camera.forward * Vec3(-1, 0, -1)
        if held_keys['a'] or held_keys['left arrow']:
            move_dir += camera.right * Vec3(-1, 0, -1)
        if held_keys['d'] or held_keys['right arrow']:
            move_dir += camera.right * Vec3(1, 0, 1)

        if move_dir.length() > 0.01 and not self.sliding:
            move_dir = move_dir.normalized()
            target_rotation = atan2(move_dir.x, move_dir.z) * 180 / 3.14159
            self.rotation_y = lerp(self.rotation_y, target_rotation, 15 * time.dt)
            self.momentum = lerp(self.momentum, move_dir * self.speed, 10 * time.dt)
        elif not self.sliding:
            self.momentum = lerp(self.momentum, Vec3(0, 0, 0), 12 * time.dt)

        # Collision check
        ray = raycast(self.world_position + Vec3(0, 0.5, 0), self.momentum.normalized(),
                      distance=self.momentum.length() * time.dt + 0.2, ignore=[self] + self.children)
        if not ray.hit:
            self.position += self.momentum * time.dt

        # Animations
        self.visual.y = sin(time.time() * 15) * 0.1 if self.grounded and not self.crouching else 0
        self.arm_l.rotation_z = sin(time.time() * 10) * 20 if self.grounded else 0
        self.arm_r.rotation_z = -sin(time.time() * 10) * 20 if self.grounded else 0
        self.leg_l.rotation_z = sin(time.time() * 10) * 20 if self.grounded else 0
        self.leg_r.rotation_z = -sin(time.time() * 10) * 20 if self.grounded else 0
        if self.diving:
            self.visual.rotation_x = lerp(self.visual.rotation_x, 45, 10 * time.dt)
        elif self.grounded:
            self.visual.rotation_x = lerp(self.visual.rotation_x, 0, 10 * time.dt)

        # Gravity and ground check
        self.velocity_y -= self.gravity_strength * time.dt
        self.y += self.velocity_y * time.dt
        ground_ray = raycast(self.world_position + Vec3(0, 0.1, 0), self.down, distance=1.5, ignore=[self] + self.children)
        if ground_ray.hit and self.velocity_y <= 0:
            self.y = ground_ray.world_point.y + 0.05
            self.velocity_y = 0
            self.grounded = True
            self.jump_count = 0
            self.diving = False
            if self.ground_pound_landed:
                self.ground_pound_landed = False
                for goomba in interactable_entities:
                    if isinstance(goomba, Goomba) and distance(self, goomba) < 3:
                        destroy(goomba)
                        Text("Stunned Goomba!", position=(0.4, 0.35), origin=(0, 0), scale=1.5, duration=1)

            # Slope handling
            normal = ground_ray.normal
            slope_angle = acos(normal.y) * 180 / 3.14159
            if slope_angle > 30 and not self.crouching:
                self.sliding = True
                slide_dir = Vec3(normal.x, 0, normal.z).normalized()
                self.momentum += slide_dir * 8 * time.dt
                self.visual.rotation_x = 20
            else:
                self.sliding = False
                self.visual.rotation_x = lerp(self.visual.rotation_x, 0, 10 * time.dt)
        else:
            self.grounded = False
            self.sliding = False

        # Wall kick
        if not self.grounded and self.wall_kick_cooldown <= 0:
            wall_ray = raycast(self.world_position + Vec3(0, 0.5, 0), move_dir, distance=0.7,
                               ignore=[self] + self.children)
            if wall_ray.hit and move_dir.dot(wall_ray.normal) < -0.7:
                self.velocity_y = 5.0
                self.momentum = -move_dir * 4
                self.wall_kick_cooldown = 0.3

        self.wall_kick_cooldown -= time.dt

        # Interactable entities
        for entity in interactable_entities[:]:
            if isinstance(entity, Coin) and distance(self, entity) < 1:
                self.coins += 1
                interactable_entities.remove(entity)
                destroy(entity)
                # Particle effect
                for i in range(5):
                    p = Entity(model='quad', color=color_coin_gold, scale=0.1, position=entity.position)
                    p.animate_position(p.position + Vec3(random.uniform(-0.5, 0.5), 1, random.uniform(-0.5, 0.5)),
                                      duration=0.5, curve=curve.out_quad)
                    destroy(p, delay=0.5)
                coin_ui.text = f"Coins: {self.coins}"
            if isinstance(entity, Goomba) and distance(self, entity) < 1:
                if self.velocity_y < -5 and not self.grounded:  # Stomp
                    interactable_entities.remove(entity)
                    destroy(entity)
                    self.velocity_y = 3.0
                    Text("Stomped Goomba!", position=(0.4, 0.35), origin=(0, 0), scale=1.5, duration=1)
                elif not self.grounded and entity.position.y + 0.5 > self.position.y:
                    self.respawn()
                    Text("Ouch! Hit by Goomba!", position=(0.4, 0.35), origin=(0, 0), scale=1.5, duration=1)

        # Respawn
        if self.y < -50:
            self.respawn()

    def input(self, key):
        if key == 'space' and (self.grounded or (time.time() - self.last_jump_time < 0.35 and self.jump_count < 3)):
            if self.grounded:
                self.jump_count = 1
            else:
                self.jump_count += 1

            if self.jump_count == 1:
                self.velocity_y = self.jump_height / self.jump_duration
            elif self.jump_count == 2:
                self.velocity_y = self.double_jump_height / self.jump_duration
            elif self.jump_count == 3:
                self.velocity_y = self.triple_jump_height / self.jump_duration

            self.grounded = False
            self.sliding = False
            self.last_jump_time = time.time()
            self.visual.animate_scale_y(1.5, duration=0.1, curve=curve.out_quad)
            self.visual.animate_scale_y(1.0, duration=0.1, delay=0.2, curve=curve.in_quad)

        if key == 'shift':
            self.crouching = True
            self.visual.scale_y = 0.8
        if key == 'shift up':
            self.crouching = False
            self.visual.scale_y = 1.6

        if key == 'space' and self.crouching and self.grounded:
            self.velocity_y = 4.0 / self.jump_duration
            self.momentum += (camera.forward * Vec3(1, 0, 1)).normalized() * 5
            self.grounded = False
            self.sliding = False

        if key == 'f' and not self.grounded and not self.diving:
            self.diving = True
            self.velocity_y = 2.0
            self.momentum += (camera.forward * Vec3(1, 0, 1)).normalized() * 6

        if key == 'g' and not self.grounded:
            self.velocity_y = -10.0
            self.diving = False
            self.ground_pound_landed = True
            self.visual.animate_scale_y(0.5, duration=0.1, curve=curve.out_quad)
            self.visual.animate_scale_y(1.0, duration=0.1, delay=0.2, curve=curve.in_quad)

        if key == 't':
            self.show_collider = not self.show_collider
            for e in scene.entities:
                if hasattr(e, 'collider'):
                    e.visible = self.show_collider if e.collider else False

    def respawn(self):
        self.position = (0, 10, 0)
        self.velocity_y = 0
        self.momentum = Vec3(0, 0, 0)
        self.rotation_y = 0
        self.diving = False
        self.crouching = False
        self.sliding = False
        self.visual.scale_y = 1.6
        self.visual.rotation_x = 0
        t = Text("Mama mia! You fell!", origin=(0, 0), scale=2)
        destroy(t, delay=2)

class Coin(Entity):
    def __init__(self, position=(0, 0, 0)):
        super().__init__(model='cylinder', color=color_coin_gold, scale=(0.5, 0.01, 0.5), position=position, collider='box')
        self.base_y = position[1]
        interactable_entities.append(self)
    def update(self):
        self.rotation_y += 120 * time.dt
        self.y = self.base_y + sin(time.time() * 5) * 0.1

class Goomba(Entity):
    def __init__(self, position=(0, 0, 0)):
        super().__init__(model='sphere', color=color_dirt_brown, scale=1, position=position, collider='sphere')
        self.direction = Vec3(random.uniform(-1, 1), 0, random.uniform(-1, 1)).normalized()
        interactable_entities.append(self)
    def update(self):
        if not hasattr(self, 'grounded'):
            self.grounded = True
        ground_ray = raycast(self.position + Vec3(0, 0.1, 0), self.down, distance=1.5)
        if ground_ray.hit:
            self.y = ground_ray.world_point.y + 0.5
            self.position += self.direction * 2 * time.dt
            if abs(self.x) > 25 or abs(self.z) > 25:
                self.direction = -self.direction
            self.grounded = True
        else:
            self.grounded = False
        self.scale = 1 + sin(time.time() * 5) * 0.1

# Scene setup
app = Ursina(vsync=False)
window.title = 'Super Mario 64 – Ursina SM64 PC Port'
window.borderless = False
window.exit_button.visible = False
window.fps_counter.enabled = True
window.size = (1280, 720)

# Interactable entities list
interactable_entities = []

# Terrain
ground = Entity(model='cube', collider='box', scale=(120, 0.1, 120), position=(0, -0.05, 0), color=color_grass_green)
Entity(model='cube', collider='box', color=color_dirt_brown, position=(12, 2.5, 12), scale=(10, 5, 10))
Entity(model='cube', collider='box', color=color_dirt_brown, position=(-18, 4, 8), scale=(8, 8, 8))
Entity(model='cube', collider='box', color=color.orange, position=(0, 6, -15), scale=(12, 2, 6))
Entity(model='cube', collider='box', color=color.gray, position=(25, 1.5, -12), scale=(15, 3, 8), rotation_x=-20)
Entity(model='cube', collider='box', color=color.gray, position=(-12, 3, -8), scale=(10, 6, 10), rotation_x=25)

# Environmental objects
for i in range(3):
    x, z = random.uniform(-40, 40), random.uniform(-40, 40)
    tree_trunk = Entity(model='cube', color=color_dirt_brown, scale=(0.5, 3, 0.5), position=(x, 1.5, z), collider='box')
    tree_leaves = Entity(model='sphere', color=color_grass_green, scale=2.5, position=(x, 3, z), collider='sphere')
for i in range(2):
    x, z = random.uniform(-40, 40), random.uniform(-40, 40)
    Entity(model='sphere', color=color.gray, scale=2, position=(x, 1, z), collider='sphere')

# Cannon prop
cannon = Entity(model='cylinder', color=color.gray, scale=(1, 2, 1), position=(20, 1, 20), rotation_x=30, collider='cylinder')

# Collectibles and enemies
for i in range(5):
    Coin(position=(random.uniform(-20, 20), random.uniform(2, 5), random.uniform(-20, 20)))
for i in range(3):
    Goomba(position=(random.uniform(-20, 20), 1, random.uniform(-20, 20)))

# Player
player = Mario64(position=(0, 10, 0))

# Camera
camera.pivot = player
camera.position = (0, 8, -20)
camera.rotation_x = 15
camera.fov = 60
camera.add_script(SmoothFollow(target=player, offset=[0, 6, -15], speed=6))

# Camera controls
class CameraController(Entity):
    def __init__(self):
        super().__init__()
        self.zoom = -20
    def update(self):
        if held_keys['q']:
            camera.rotation_y -= 140 * time.dt
        if held_keys['e']:
            camera.rotation_y += 140 * time.dt
        if held_keys['z']:
            self.zoom = min(self.zoom + 12 * time.dt, -10)
            camera.z = self.zoom
        if held_keys['x']:
            self.zoom = max(self.zoom - 12 * time.dt, -30)
            camera.z = self.zoom

camera_controller = CameraController()

# Lighting and sky
sun = DirectionalLight(shadows=True, y=50, z=-20, color=color.rgb(255, 240, 200))
sun.look_at(Vec3(0, -1, -0.5))
AmbientLight(color=color.rgba(180, 180, 220, 0.3))
Sky(color=color.rgb(100, 150, 255))
scene.fog_density = 0.008
scene.fog_color = color.rgb(100, 150, 255)

# UI
coin_ui = Text("Coins: 0", position=(0.4, 0.45), origin=(0, 0), scale=1.5)
Text("Super Mario 64 – Ursina SM64 PC Port", y=0.45, origin=(0, 0))
Text("WASD/Arrows: Move | Space: Jump | Shift: Crouch | F: Dive | G: Ground Pound | Q/E: Camera | Z/X: Zoom | T: Debug", y=0.4, origin=(0, 0), scale=0.8)

app.run()
