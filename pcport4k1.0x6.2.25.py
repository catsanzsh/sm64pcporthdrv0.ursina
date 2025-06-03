from ursina import *
from math import sin, cos, atan2
import time

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

        # Enhanced Mario model with arms
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

        # Movement parameters (SM64 PC port-inspired)
        self.speed            = 9
        self.turn_speed       = 150
        self.jump_height      = 4.8
        self.double_jump_height = 5.8
        self.triple_jump_height = 7.2
        self.jump_duration    = 0.38
        self.gravity_strength = 22
        self.velocity_y       = 0
        self.momentum         = Vec3(0, 0, 0)
        self.grounded         = True
        self.jump_count       = 0
        self.last_jump_time   = 0
        self.crouching        = False
        self.wall_kick_cooldown = 0
        self.coins            = 0
        self.show_collider    = False

    def update(self):
        # Camera-based movement with momentum
        move_dir = Vec3(0, 0, 0)
        if held_keys['w'] or held_keys['up arrow']:
            move_dir += camera.forward * Vec3(1, 0, 1)
        if held_keys['s'] or held_keys['down arrow']:
            move_dir += camera.forward * Vec3(-1, 0, -1)
        if held_keys['a'] or held_keys['left arrow']:
            move_dir += camera.right * Vec3(-1, 0, -1)
        if held_keys['d'] or held_keys['right arrow']:
            move_dir += camera.right * Vec3(1, 0, 1)

        if move_dir.length() > 0.01:
            move_dir = move_dir.normalized()
            target_rotation = atan2(move_dir.x, move_dir.z) * 180 / 3.14159
            self.rotation_y = lerp(self.rotation_y, target_rotation, 12 * time.dt)
            self.momentum = lerp(self.momentum, move_dir * self.speed, 8 * time.dt)
        else:
            self.momentum = lerp(self.momentum, Vec3(0, 0, 0), 10 * time.dt)

        # Collision check with momentum
        ray = raycast(self.world_position + Vec3(0, 0.5, 0), self.momentum.normalized(),
                      distance=self.momentum.length() * time.dt + 0.2, ignore=[self] + self.children)
        if not ray.hit:
            self.position += self.momentum * time.dt

        # Animations
        self.visual.y = sin(time.time() * 15) * 0.1 if self.grounded else 0
        self.arm_l.rotation_z = sin(time.time() * 10) * 20 if self.grounded else 0
        self.arm_r.rotation_z = -sin(time.time() * 10) * 20 if self.grounded else 0

        # Gravity and ground check
        self.velocity_y -= self.gravity_strength * time.dt
        self.y += self.velocity_y * time.dt
        ground_ray = raycast(self.world_position + Vec3(0, 0.1, 0), self.down, distance=1.0, ignore=[self] + self.children)
        if ground_ray.hit and self.velocity_y <= 0:
            self.y = ground_ray.world_point.y + 0.05
            self.velocity_y = 0
            self.grounded = True
            self.jump_count = 0
        else:
            self.grounded = False

        # Wall kick with angle check
        if not self.grounded and self.wall_kick_cooldown <= 0:
            wall_ray = raycast(self.world_position + Vec3(0, 0.5, 0), move_dir, distance=0.7,
                               ignore=[self] + self.children)
            if wall_ray.hit and move_dir.dot(wall_ray.normal) < -0.7:
                self.velocity_y = 4.5
                self.momentum = -move_dir * 3
                self.wall_kick_cooldown = 0.4

        self.wall_kick_cooldown -= time.dt

        # Coin collection
        for coin in scene.entities:
            if isinstance(coin, Coin) and distance(self, coin) < 1:
                self.coins += 1
                destroy(coin)
                Text(f"Coins: {self.coins}", position=(0.4, 0.45), origin=(0, 0), scale=1.5, duration=1)

        # Respawn
        if self.y < -50:
            self.respawn()

    def input(self, key):
        if key == 'space' and (self.grounded or (time.time() - self.last_jump_time < 0.4 and self.jump_count < 3)):
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
            self.velocity_y = 3.8 / self.jump_duration
            self.momentum += (camera.forward * Vec3(1, 0, 1)).normalized() * 4
            self.grounded = False

        # Debug toggle
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
        t = Text("Mama mia! You fell!", origin=(0, 0), scale=2)
        destroy(t, delay=2)

class Coin(Entity):
    def __init__(self, position=(0, 0, 0)):
        super().__init__(model='sphere', color=color_coin_gold, scale=0.5, position=position, collider='sphere')
    def update(self):
        self.rotation_y += 100 * time.dt
        self.scale = 0.5 + sin(time.time() * 5) * 0.05

class Goomba(Entity):
    def __init__(self, position=(0, 0, 0)):
        super().__init__(model='sphere', color=color_dirt_brown, scale=1, position=position, collider='sphere')
        self.direction = Vec3(1, 0, 0)
    def update(self):
        self.position += self.direction * 2 * time.dt
        if abs(self.x) > 20:
            self.direction = -self.direction
        self.scale = 1 + sin(time.time() * 5) * 0.1

# Scene setup
app = Ursina()
window.title = 'Super Mario 64 – Ursina SM64 PC Port'
window.borderless = False
window.exit_button.visible = False
window.fps_counter.enabled = True

# Terrain
Entity(model='cube', collider='box', scale=(100, 0.1, 100), position=(0, -0.05, 0), color=color_grass_green)
Entity(model='cube', collider='box', color=color_dirt_brown, position=(10, 2, 10), scale=(8, 4, 8))
Entity(model='cube', collider='box', color=color_dirt_brown, position=(-15, 3, 5), scale=(6, 6, 6))
Entity(model='cube', collider='box', color=color.orange, position=(0, 5, -12), scale=(10, 2, 4))
Entity(model='cube', collider='box', color=color.gray, position=(20, 1, -10), scale=(12, 2, 6), rotation_x=-15)
Entity(model='cube', collider='box', color=color.gray, position=(-10, 2, -5), scale=(8, 4, 8), rotation_x=20)  # Slope

# Collectibles and enemies
Coin(position=(5, 2, 5))
Coin(position=(-5, 3, 0))
Goomba(position=(15, 1, -5))

# Player
player = Mario64(position=(0, 5, 0))

# Camera
camera.pivot = player
camera.position = (0, 8, -20)
camera.rotation_x = 15
camera.add_script(SmoothFollow(target=player, offset=[0, 6, -15], speed=6))

# Camera controls
class CameraController(Entity):
    def __init__(self):
        super().__init__()
        self.zoom = -20
    def update(self):
        if held_keys['q']:
            camera.rotation_y -= 120 * time.dt
        if held_keys['e']:
            camera.rotation_y += 120 * time.dt
        if held_keys['z']:
            self.zoom = min(self.zoom + 10 * time.dt, -10)
            camera.z = self.zoom
        if held_keys['x']:
            self.zoom = max(self.zoom - 10 * time.dt, -30)
            camera.z = self.zoom

camera_controller = CameraController()

# Lighting and sky
sun = DirectionalLight(shadows=True, y=50, z=-20)
sun.look_at(Vec3(0, -1, -0.5))
AmbientLight(color=color.rgba(150, 150, 200, 0.2))
Sky(color=color.rgb(100, 150, 255))

# UI
Text("Super Mario 64 – Ursina SM64 PC Port", y=0.45, origin=(0, 0))
Text("WASD/Arrows: Move | Space: Jump | Shift: Crouch | Q/E: Camera | Z/X: Zoom | T: Debug", y=0.4, origin=(0, 0), scale=0.8)

app.run()
