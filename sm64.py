
from ursina import *
from math import sin, cos, atan2
import time

# --------------------------------------------------
# Super Mario 64 – Ursina NX2 Recreation
# --------------------------------------------------
# ‣ WASD / Arrow keys    = Move & turn
# ‣ Space                = Jump / Double / Triple Jump
# ‣ Shift                = Crouch / Long Jump
# --------------------------------------------------

# Custom colors for N64-like palette
color_mario_blue  = color.rgb(0, 0, 255)
color_mario_red   = color.rgb(255, 0, 0)
color_mario_peach = color.rgb(255, 182, 193)
color_grass_green = color.rgb(34, 139, 34)
color_dirt_brown  = color.rgb(139, 69, 19)

class Mario64(Entity):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        # --- Physical collider (invisible) ---
        self.model    = None
        self.color    = color.clear
        self.collider = 'box'
        self.scale    = (0.6, 1.8, 0.6)
        self.origin_y = -0.5  # Feet at Y=0

        # --- Visible mesh & sub-parts (low-poly Mario) ---
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

        # --- Movement parameters (tuned for Mario 64 feel) ---
        self.speed            = 8  # Mario's run speed
        self.turn_speed       = 120  # Degrees per second
        self.jump_height      = 4.5  # Single jump height
        self.double_jump_height = 5.5
        self.triple_jump_height = 7.0
        self.jump_duration    = 0.4
        self.gravity_strength = 20
        self.velocity_y       = 0
        self.grounded         = True
        self.jump_count       = 0
        self.last_jump_time   = 0
        self.crouching        = False
        self.wall_kick_cooldown = 0

    def update(self):
        # ---------- Camera-based movement (Mario 64 style) ----------
        move_dir = Vec3(0, 0, 0)
        if held_keys['w'] or held_keys['up arrow']:
            move_dir += camera.forward * Vec3(1, 0, 1)  # Move relative to camera
        if held_keys['s'] or held_keys['down arrow']:
            move_dir += camera.forward * Vec3(-1, 0, -1)
        if held_keys['a'] or held_keys['left arrow']:
            move_dir += camera.right * Vec3(-1, 0, -1)
        if held_keys['d'] or held_keys['right arrow']:
            move_dir += camera.right * Vec3(1, 0, 1)

        # Smooth turning to face movement direction
        if move_dir.length() > 0.01:  # Only rotate if movement is significant
            move_dir = move_dir.normalized()
            target_rotation = atan2(move_dir.x, move_dir.z) * 180 / 3.14159
            self.rotation_y = lerp(self.rotation_y, target_rotation, 10 * time.dt)

            # Collision check in movement direction
            ray = raycast(self.world_position + Vec3(0, 0.5, 0), move_dir, distance=self.speed * time.dt + 0.2,
                          ignore=[self] + self.children)
            if not ray.hit:
                self.position += move_dir * self.speed * time.dt

            # Head-bob and run animation
            self.visual.y = sin(time.time() * 15) * 0.1 if self.grounded else 0
            self.visual.rotation_z = sin(time.time() * 10) * 5 if self.grounded else 0

        # ---------- Gravity & vertical motion ----------
        self.velocity_y -= self.gravity_strength * time.dt
        self.y += self.velocity_y * time.dt

        # Ground check with increased distance
        ground_ray = raycast(self.world_position + Vec3(0, 0.1, 0), self.down,
                             distance=1.0, ignore=[self] + self.children)
        if ground_ray.hit and self.velocity_y <= 0:
            self.y = ground_ray.world_point.y + 0.05  # Snap slightly above ground
            self.velocity_y = 0
            self.grounded = True
            self.jump_count = 0
        else:
            self.grounded = False

        # ---------- Wall kick detection ----------
        if not self.grounded and self.wall_kick_cooldown <= 0:
            wall_ray = raycast(self.world_position + Vec3(0, 0.5, 0), move_dir, distance=0.7,
                               ignore=[self] + self.children)
            if wall_ray.hit:
                self.velocity_y = 4.0
                self.position -= move_dir * 0.5  # Push back slightly
                self.wall_kick_cooldown = 0.5

        self.wall_kick_cooldown -= time.dt

        # ---------- Fall-out respawn ----------
        if self.y < -50:
            self.respawn()

    def input(self, key):
        # Jump mechanics (single, double, triple)
        if key == 'space' and (self.grounded or (time.time() - self.last_jump_time < 0.5 and self.jump_count < 3)):
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

            # Squash & stretch animation
            self.visual.animate_scale_y(1.5, duration=0.1, curve=curve.out_quad)
            self.visual.animate_scale_y(1.0, duration=0.1, delay=0.2, curve=curve.in_quad)

        # Crouch and long jump
        if key == 'shift':
            self.crouching = True
            self.visual.scale_y = 0.8
        if key == 'shift up':
            self.crouching = False
            self.visual.scale_y = 1.6
        if key == 'space' and self.crouching and self.grounded:
            self.velocity_y = 3.5 / self.jump_duration
            self.position += (camera.forward * Vec3(1, 0, 1)).normalized() * 3
            self.grounded = False

    def respawn(self):
        self.position = (0, 10, 0)
        self.velocity_y = 0
        self.rotation_y = 0
        t = Text("Haha, you fell! Mama mia!", origin=(0, 0), scale=2)
        destroy(t, delay=2)

# --------------------------------------------------
# Scene setup (Bob-omb Battlefield inspired)
# --------------------------------------------------
app = Ursina()

window.title = 'Super Mario 64 – Ursina Recreation'
window.borderless = False
window.exit_button.visible = False
window.fps_counter.enabled = True

# Ground & terrain with thin box collider
Entity(model='cube', collider='box', scale=(100, 0.1, 100), position=(0, -0.05, 0), color=color_grass_green)

# Hills and platforms
Entity(model='cube', collider='box', color=color_dirt_brown, position=(10, 2, 10), scale=(8, 4, 8))
Entity(model='cube', collider='box', color=color_dirt_brown, position=(-15, 3, 5), scale=(6, 6, 6))
Entity(model='cube', collider='box', color=color.orange, position=(0, 5, -12), scale=(10, 2, 4))
Entity(model='cube', collider='box', color=color.gray, position=(20, 1, -10), scale=(12, 2, 6), rotation_x=-15)

# Player
player = Mario64(position=(0, 5, 0))

# Camera (Mario 64 Lakitu-style)
camera.pivot = player
camera.position = (0, 8, -20)
camera.rotation_x = 15
camera.add_script(SmoothFollow(target=player, offset=[0, 6, -15], speed=5))

# Camera rotation with mouse (C-button style)
class CameraController(Entity):
    def update(self):
        if held_keys['q']:
            camera.rotation_y -= 100 * time.dt
        if held_keys['e']:
            camera.rotation_y += 100 * time.dt

camera_controller = CameraController()

# Lighting & sky
sun = DirectionalLight(shadows=True, y=50, z=-20)
sun.look_at(Vec3(0, -1, -0.5))
AmbientLight(color=color.rgba(150, 150, 200, 0.2))
Sky(color=color.rgb(100, 150, 255))

# UI text
Text("Super Mario 64 – Ursina Recreation", y=0.45, origin=(0, 0))
Text("WASD/Arrows to Move | Space to Jump | Shift to Crouch | Q/E for Camera", y=0.4, origin=(0, 0), scale=0.8)

app.run()
