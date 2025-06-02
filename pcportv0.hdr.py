import ursina
from ursina import *
import math
import time

# --------------------------------------------------
# Super Mario 64 – Ursina Minimal Demo (No SmoothFollow)
# --------------------------------------------------
# Controls:
# ‣ WASD / Arrow keys = Move & turn
# ‣ Space             = Jump (multi-jump)
# ‣ Shift             = Crouch
# ‣ Q/E               = Rotate Camera
# --------------------------------------------------

# Colors for N64-style palette
color_mario_blue = color.rgb(70, 100, 235)
color_mario_red = color.rgb(230, 50, 40)
color_mario_skin = color.rgb(254, 205, 160)
color_mario_brown = color.rgb(100, 60, 20)
color_grass = color.rgb(34, 139, 34)
color_dirt = color.rgb(139, 69, 19)

class Mario64(Entity):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.model = None
        self.color = color.clear
        self.collider = 'box'
        self.scale = (0.6, 1.8, 0.6)
        self.origin_y = -0.5
        self.visual = Entity(parent=self, model='cube', color=color_mario_blue, scale=(0.7,1.1,0.45), position=(0,0.55,0))
        self.head = Entity(parent=self, model='cube', color=color_mario_skin, scale=(0.7,0.5,0.6), position=(0,1.25,0))
        self.eye_l = Entity(parent=self.head, model='quad', color=color.black, scale=(0.12, 0.18), position=(-0.18, 0.08, 0.31))
        self.eye_r = Entity(parent=self.head, model='quad', color=color.black, scale=(0.12, 0.18), position=(0.18, 0.08, 0.31))
        self.grounded = True
        self.velocity_y = 0
        self.speed = 7
        self.jump_count = 0
        self.air_move = Vec3(0,0,0)
    def update(self):
        move = Vec3(
            held_keys['d'] - held_keys['a'] + held_keys['right arrow'] - held_keys['left arrow'],
            0,
            held_keys['w'] - held_keys['s'] + held_keys['up arrow'] - held_keys['down arrow']
        )
        if move.length() > 0:
            move = move.normalized()
            yaw = math.degrees(math.atan2(move.x, move.z))
            self.rotation_y = lerp(self.rotation_y, yaw, time.dt*12)
            if self.grounded:
                self.position += self.forward * self.speed * time.dt
            else:
                self.air_move += move * self.speed * 0.1 * time.dt
                self.air_move = self.air_move.normalized() * min(self.air_move.length(), self.speed)
        if not self.grounded:
            self.position += self.air_move * time.dt
        self.velocity_y -= 25 * time.dt
        vertical_move = self.velocity_y * time.dt
        ground_check = raycast(self.world_position+Vec3(0,0.1,0), Vec3(0,-1,0), 0.2, ignore=[self])
        if ground_check.hit and self.velocity_y <= 0:
            self.y = ground_check.world_point.y
            self.velocity_y = 0
            self.grounded = True
            self.jump_count = 0
            self.air_move = Vec3(0,0,0)
        else:
            self.grounded = False
            self.y += vertical_move
        if self.y < -15:
            self.position = (0,5,0)
            self.velocity_y = 0
            self.air_move = Vec3(0,0,0)
            self.jump_count = 0
    def input(self, key):
        if key=='space':
            if self.grounded or self.jump_count<2:
                self.velocity_y = 8 if self.jump_count==0 else 6.5
                self.grounded = False
                self.jump_count += 1
        if key=='shift down':
            self.visual.scale_y = 0.7
            self.head.y = 1.0
        if key=='shift up':
            self.visual.scale_y = 1.1
            self.head.y = 1.25

app = Ursina(borderless=False)
window.title = 'Ursina SM64 Style Minimal Demo'
window.exit_button.visible = False
window.fps_counter.enabled = True

# Ground
Entity(model='cube', collider='box', scale=(60,1,60), position=(0,-0.51,0), color=color_grass, texture='white_cube')

# Platforms
Entity(model='cube', collider='box', color=color_dirt, position=(10,2.5,10), scale=(8,5,8))
Entity(model='cube', collider='box', color=color_dirt, position=(-12,3.5,5), scale=(6,7,6))

player = Mario64(position=(0,1,0))

# Camera Controller
class CameraController(Entity):
    def __init__(self, target, **kwargs):
        super().__init__(**kwargs)
        self.target = target
        self.dist = 15
        self.height = 5
        self.yaw = 0
        self.pitch = 15
    def update(self):
        if held_keys['q']:
            self.yaw -= 100*time.dt
        if held_keys['e']:
            self.yaw += 100*time.dt
        x = math.sin(math.radians(self.yaw))*self.dist
        z = math.cos(math.radians(self.yaw))*self.dist
        camera.position = lerp(camera.position, self.target.world_position+Vec3(x,self.height,z), time.dt*10)
        camera.look_at(self.target.world_position+Vec3(0,1,0))
CameraController(player)

# Lighting
DirectionalLight(y=50, z=-20, shadows=True)
AmbientLight(color=color.rgba(120,120,120, 0.4))
Sky(color=color.rgb(135, 206, 255))

Text("Ursina SM64 Minimal Demo", origin=(0,0), y=0.45, scale=1.5)
Text("WASD/Arrows: Move | Space: Jump | Shift: Crouch | Q/E: Camera", origin=(0,0), y=0.4, scale=1)

app.run()
