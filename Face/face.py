import pygame
import sys
import time
import math
import random
from pygame.locals import * 

BLACK = (0, 0, 0)
EVE_BLUE = (0, 200, 255)
WHITE = (255, 255, 255)
TRANSPARENT = (0, 0, 0, 0)

BLINK_DURATION = 0.3
EMOTION_TRANSITION_TIME = 0.5

class FinleyFace:
    def __init__(self):
        """Initialize Pygame, screen, clock, and eye states."""
        pygame.init()

        info = pygame.display.Info()
        self.WIDTH = info.current_w
        self.HEIGHT = info.current_h
        self.HALF_WIDTH = self.WIDTH // 2
        self.HALF_HEIGHT = self.HEIGHT // 2

        self.screen = pygame.display.set_mode((self.WIDTH, self.HEIGHT), FULLSCREEN | NOFRAME)
        pygame.display.set_caption("Finley")
        self.clock = pygame.time.Clock()

        self.EYE_SPACING = self.WIDTH * 0.45
        self.EYE_WIDTH = self.WIDTH * 0.35
        self.EYE_HEIGHT = self.EYE_WIDTH * 0.7
        self.PUPIL_SIZE = self.EYE_WIDTH * 0.3 

        self.LEFT_EYE_X = self.HALF_WIDTH - (self.EYE_SPACING // 2)
        self.RIGHT_EYE_X = self.HALF_WIDTH + (self.EYE_SPACING // 2)
        self.EYE_Y = self.HALF_HEIGHT - 20 

        self.current_emotion = "neutral"
        self.target_emotion = "neutral"
        self.emotion_transition = 0.0
        self.transitioning = False

        self.is_blinking = False
        self.blink_progress = 0
        self.last_blink = time.time()
        self.blink_interval = random.uniform(2, 6)

        self.eye_target_x = 0.0
        self.eye_target_y = 0.0
        self.eye_current_x = 0.0
        self.eye_current_y = 0.0
        self.eye_move_speed = 6.0

        self.next_eye_move_time = time.time() + random.uniform(0.5, 3.0)
        self.eye_dwell_time = random.uniform(0.5, 3.0)
        self.focus_time = time.time() + random.uniform(5, 10)
        self.eye_state = "idle"

        self.auto_change = False
        self.last_emotion_change = time.time()
        self.emotion_change_interval = random.uniform(3, 7)

        self.font = pygame.font.Font(None, 36)
        self.show_info = True

        self.emotions = {
            "neutral": {
                "shape": "oval", "width_factor": 1.0, "height_factor": 1.0,
                "rotation": 0, "offset_y": 0, "tilt_angle": 15
            },
            "happy": {
                "shape": "oval", "width_factor": 1.2, "height_factor": 1.4,
                "rotation": 0, "offset_y": 0, "tilt_angle": 7,
                "cutout": {
                    "shape": "rectangle",
                    "y_pos_factor": 0.6,
                    "width_factor": 1.0
                }
            },
            "sad": {
                "shape": "arc", "width_factor": 1.2, "height_factor": 1.1,
                "start_angle": 180, "stop_angle": 360,
                "offset_y": -self.EYE_HEIGHT * 0.3, "tilt_angle": 10, "rotation": 0
            },
            "curious": {
                "shape": "oval", "width_factor": 1.2, "height_factor": 1.1,
                "rotation": 0, "offset_y": 0, "tilt_angle": 18
            },
            "angry": {
                "shape": "arc", "width_factor": 1.2, "height_factor": 0.7,
                "start_angle": 180, "stop_angle": 360,
                "offset_y": -self.EYE_HEIGHT * 0.2, "rotation": 0, "tilt_angle": 20
            },
            "surprised": {
                "shape": "oval", "width_factor": 1.2, "height_factor": 1.4,
                "rotation": 0, "offset_y": 0, "tilt_angle": 5
            },
            "sleepy": {
                "shape": "arc", "width_factor": 1.2, "height_factor": 0.5,
                "start_angle": 180, "stop_angle": 360,
                "offset_y": -self.EYE_HEIGHT * 0.4, "tilt_angle": 5, "rotation": 0
            },
            "scanning": {
                "shape": "oval", "width_factor": 1.2, "height_factor": 1.4,
                "rotation": 0, "offset_y": 0, "scanning": True, "tilt_angle": 0
            },
            "focused": {
                "shape": "special",
                "width_factor": 1.0,
                "height_factor": 1.0,
                "rotation": 0,
                "offset_y": 0,
                "tilt_angle": 15
            }
        }

    def draw_ellipse(self, x, y, width, height, color, fill=True, rotation=0, cutout=None):
        """Draw an ellipse with optional rotation and bottom cutout."""
        width = max(1, int(width)); height = max(1, int(height))
        target_surface = self.screen; blit_pos = (0, 0)
        origin_offset_x = x - width // 2; origin_offset_y = y - height // 2
        surface_for_rotation = None

        if rotation != 0:
            padding = max(width, height) // 2 + 5
            surf_size = (width + padding, height + padding)
            surface_for_rotation = pygame.Surface(surf_size, pygame.SRCALPHA)
            surface_for_rotation.fill(TRANSPARENT)
            target_surface = surface_for_rotation
            center_x_surf = surf_size[0] // 2; center_y_surf = surf_size[1] // 2
            origin_offset_x = center_x_surf - width // 2
            origin_offset_y = center_y_surf - height // 2
            blit_pos = (x, y)

        ellipse_rect = pygame.Rect(origin_offset_x, origin_offset_y, width, height)
        pygame.draw.ellipse(target_surface, color, ellipse_rect, 0 if fill else 2)

        if cutout and fill:
            cutout_shape = cutout.get("shape", "rectangle")
            cutout_color = TRANSPARENT if surface_for_rotation else BLACK
            center_x_main = origin_offset_x + width // 2
            center_y_main = origin_offset_y + height // 2

            if cutout_shape == "rectangle":
                cutout_y_pos_factor = cutout.get("y_pos_factor", 0.6)
                cutout_width_factor = cutout.get("width_factor", 1.0)
                rect_w = max(1, int(width * cutout_width_factor))
                rect_x = center_x_main - rect_w // 2
                rect_y = origin_offset_y + height * cutout_y_pos_factor
                rect_h = max(1, (origin_offset_y + height) - int(rect_y))
                rect_h = min(rect_h, target_surface.get_height() - int(rect_y))

                cutout_rect = pygame.Rect(rect_x, rect_y, rect_w, rect_h)
                if cutout_rect.height > 0 and cutout_rect.width > 0:
                     pygame.draw.rect(target_surface, cutout_color, cutout_rect, 0)


        if surface_for_rotation:
            rotated = pygame.transform.rotate(surface_for_rotation, rotation)
            blit_x = blit_pos[0] - rotated.get_width() // 2
            blit_y = blit_pos[1] - rotated.get_height() // 2
            self.screen.blit(rotated, (blit_x, blit_y))

    def draw_arc(self, x, y, width, height, start_angle, stop_angle, color, thickness=0, rotation=0):
        """Draw an arc. If thickness is 0, draw a filled segment."""
        width = max(1, int(width)); height = max(1, int(height))
        start_rad = math.radians(start_angle); stop_rad = math.radians(stop_angle)
        if abs(stop_rad - start_rad) < 1e-6 or width <= 0 or height <= 0: return

        if rotation != 0:
            padding = max(width, height) // 2 + abs(int(thickness)) + 5
            surf_size = (width + padding, height + padding)
            surface = pygame.Surface(surf_size, pygame.SRCALPHA); surface.fill(TRANSPARENT)
            draw_rect = pygame.Rect(padding // 2, padding // 2, width, height)
            center_x_surf = surf_size[0] // 2; center_y_surf = surf_size[1] // 2
            target_surf = surface

            if thickness > 0:
                 try: pygame.draw.arc(target_surf, color, draw_rect, start_rad, stop_rad, int(thickness))
                 except (ValueError, TypeError) as e: print(f"Error drawing arc line on surface: {e}, rect={draw_rect}, angles=({start_angle},{stop_angle}), thick={thickness}")
            elif thickness == 0:
                points = []
                num_points = max(2, int(abs(stop_angle - start_angle) / 5))
                for i in range(num_points + 1):
                    angle = start_rad + (stop_rad - start_rad) * i / num_points
                    point_x = center_x_surf + math.cos(angle) * width // 2
                    point_y = center_y_surf - math.sin(angle) * height // 2
                    points.append((point_x, point_y))
                points.append((center_x_surf, center_y_surf))
                if len(points) > 2:
                    try: pygame.draw.polygon(target_surf, color, points)
                    except (ValueError, TypeError) as e: print(f"Error drawing arc polygon on surface: {e}, points count={len(points)}")

            rotated = pygame.transform.rotate(surface, rotation)
            blit_x = x - rotated.get_width() // 2; blit_y = y - rotated.get_height() // 2
            self.screen.blit(rotated, (blit_x, blit_y))
        else:
            draw_rect = pygame.Rect(x - width // 2, y - height // 2, width, height)
            center_x_screen = x; center_y_screen = y
            target_surf = self.screen

            if thickness > 0:
                 try: pygame.draw.arc(target_surf, color, draw_rect, start_rad, stop_rad, int(thickness))
                 except (ValueError, TypeError) as e: print(f"Error drawing arc line on screen: {e}, rect={draw_rect}, angles=({start_angle},{stop_angle}), thick={thickness}")

            elif thickness == 0:
                points = []
                num_points = max(2, int(abs(stop_angle - start_angle) / 5))
                for i in range(num_points + 1):
                    angle = start_rad + (stop_rad - start_rad) * i / num_points
                    point_x = center_x_screen + math.cos(angle) * width // 2
                    point_y = center_y_screen - math.sin(angle) * height // 2
                    points.append((point_x, point_y))
                points.append((center_x_screen, center_y_screen))
                if len(points) > 2:
                     try: pygame.draw.polygon(target_surf, color, points)
                     except (ValueError, TypeError) as e: print(f"Error drawing arc polygon on screen: {e}, points count={len(points)}")


    def blend_emotions(self, emotion1, emotion2, factor):
        """Blend between two emotions based on transition factor (0.0 to 1.0)"""
        result = {}
        e1_props = self.emotions[emotion1]; e2_props = self.emotions[emotion2]

        common_props = ["width_factor", "height_factor", "offset_y", "rotation", "tilt_angle"]
        for prop in common_props:
            val1 = e1_props.get(prop, 0); val2 = e2_props.get(prop, 0)
            result[prop] = val1 * (1 - factor) + val2 * factor

        if emotion2 == "focused":
            if factor < 0.5:
                 result["shape"] = e1_props.get("shape", "oval")
            else:
                 result["shape"] = "special"
        else:
            dominant_props = e2_props if factor >= 0.5 else e1_props
            result["shape"] = dominant_props.get("shape", "oval")

            start_shape_is_arc = e1_props.get("shape") == "arc"
            target_shape_is_arc = e2_props.get("shape") == "arc"

            if start_shape_is_arc and target_shape_is_arc:
                start1 = e1_props.get("start_angle", 180); stop1 = e1_props.get("stop_angle", 360)
                start2 = e2_props.get("start_angle", 180); stop2 = e2_props.get("stop_angle", 360)
                result["start_angle"] = start1 * (1 - factor) + start2 * factor
                result["stop_angle"] = stop1 * (1 - factor) + stop2 * factor
            elif result["shape"] == "arc":
                 props_for_angles = e2_props if factor >= 0.5 else e1_props
                 result["start_angle"] = props_for_angles.get("start_angle", 180)
                 result["stop_angle"] = props_for_angles.get("stop_angle", 360)

        dominant_props = e2_props if factor >= 0.5 else e1_props
        result["cutout"] = dominant_props.get("cutout") if result["shape"] == dominant_props.get("shape") else None
        result["scanning"] = dominant_props.get("scanning", False)

        return result

    def get_current_eye_properties(self):
        """Get the current eye properties based on emotion state and transitions"""
        emotion_to_use = self.target_emotion if self.transitioning else self.current_emotion

        if emotion_to_use == "focused":
            if self.transitioning:
                 return self.blend_emotions(self.current_emotion, self.target_emotion, self.emotion_transition)
            else:
                props = self.emotions["focused"].copy()
                props.setdefault("shape", "special"); props.setdefault("width_factor", 1.0)
                props.setdefault("height_factor", 1.0); props.setdefault("rotation", 0)
                props.setdefault("offset_y", 0); props.setdefault("tilt_angle", 0)
                props.setdefault("scanning", False)
                return props

        elif self.transitioning:
            return self.blend_emotions(self.current_emotion, self.target_emotion, self.emotion_transition)
        else:
            props = self.emotions[self.current_emotion].copy()
            props.setdefault("shape", "oval"); props.setdefault("width_factor", 1.0)
            props.setdefault("height_factor", 1.0); props.setdefault("rotation", 0)
            props.setdefault("offset_y", 0); props.setdefault("tilt_angle", 0)
            props.setdefault("scanning", False)
            if props["shape"] == "arc":
                props.setdefault("start_angle", 180); props.setdefault("stop_angle", 360)
            return props


    def draw_eye(self, x, y, is_left=True):
        """Draw an eye based on the current emotion and animation state"""
        effective_emotion = self.target_emotion if self.transitioning else self.current_emotion
        is_transitioning_from_focused = self.current_emotion == "focused" and self.transitioning

        if effective_emotion == "focused" and not self.transitioning:
            if is_left:
                eye_props = self.emotions["angry"].copy()
                eye_props.setdefault("shape", "arc"); eye_props.setdefault("width_factor", 1.2); eye_props.setdefault("height_factor", 0.7)
                eye_props.setdefault("rotation", 0); eye_props.setdefault("offset_y", -self.EYE_HEIGHT * 0.2); eye_props.setdefault("tilt_angle", 20)
                eye_props.setdefault("start_angle", 180); eye_props.setdefault("stop_angle", 360)
                eye_props.setdefault("cutout", None); eye_props.setdefault("scanning", False)
            else:
                eye_props = self.emotions["curious"].copy()
                eye_props.setdefault("shape", "oval"); eye_props.setdefault("width_factor", 1.2); eye_props.setdefault("height_factor", 1.1)
                eye_props.setdefault("rotation", 0); eye_props.setdefault("offset_y", 0); eye_props.setdefault("tilt_angle", 18)
                eye_props.setdefault("cutout", None); eye_props.setdefault("scanning", False)

        else:
            eye_props = self.get_current_eye_properties()

        blink_factor = 1.0
        if self.is_blinking:
            progress = self.blink_progress * 2.0
            blink_factor = max(0.01, 1.0 - progress if progress < 1.0 else progress - 1.0)

        y_offset = eye_props.get("offset_y", 0); y_pos = y + y_offset
        width = self.EYE_WIDTH * eye_props.get("width_factor", 1.0)
        height = self.EYE_HEIGHT * eye_props.get("height_factor", 1.0) * blink_factor
        gaze_offset_x = self.eye_current_x * (self.EYE_WIDTH * 0.1)
        gaze_offset_y = self.eye_current_y * (self.EYE_HEIGHT * 0.1)
        base_rotation = eye_props.get("rotation", 0)
        current_tilt = eye_props.get("tilt_angle", 0)
        tilt_rotation = base_rotation - current_tilt if is_left else base_rotation + current_tilt
        draw_x = x + gaze_offset_x; draw_y = y_pos + gaze_offset_y

        shape = eye_props.get("shape", "oval")

        if is_transitioning_from_focused and self.emotion_transition < 0.5:
            shape = "angry" if is_left else "curious"
            if shape == "angry":
                angry_props = self.emotions["angry"]
                eye_props["start_angle"] = angry_props.get("start_angle", 180)
                eye_props["stop_angle"] = angry_props.get("stop_angle", 360)
            elif shape == "curious":
                 curious_props = self.emotions["curious"]
                 eye_props["cutout"] = eye_props.get("cutout")

        if width < 1 or height < 1:
            return

        cutout_params = eye_props.get("cutout")

        if shape == "oval" or shape == "curious":
             self.draw_ellipse(draw_x, draw_y, width, height, EVE_BLUE, True, tilt_rotation, cutout=cutout_params)

        elif shape == "arc" or shape == "angry":
            start = eye_props.get("start_angle", 180)
            stop = eye_props.get("stop_angle", 360)
            self.draw_arc(draw_x, draw_y, width, height, start, stop, EVE_BLUE, 0, tilt_rotation)

        elif shape == "special":
            self.draw_ellipse(draw_x, draw_y, width, height, EVE_BLUE, True, tilt_rotation, cutout=cutout_params)

    def update(self):
        """Update animation state (blink, transition, eye movement)."""
        current_time = time.time()
        delta_time = min(self.clock.get_time() / 1000.0, 0.1)

        if (
                not self.is_blinking
                and current_time - self.last_blink > self.blink_interval
        ):
            self.is_blinking = True
            self.blink_progress = 0.0
            self.last_blink = current_time
            self.blink_interval = random.uniform(2, 6)
        if self.is_blinking:
            self.blink_progress += delta_time / BLINK_DURATION
            if self.blink_progress >= 1.0:
                self.is_blinking = False
                self.blink_progress = 0.0

        if self.transitioning:
            self.emotion_transition += delta_time / EMOTION_TRANSITION_TIME
            self.emotion_transition = min(1.0, max(0.0, self.emotion_transition))
            if self.emotion_transition >= 1.0:
                self.transitioning = False
                self.current_emotion = self.target_emotion

        if delta_time > 1e-6:
            move_factor = 1.0 - math.exp(-self.eye_move_speed * delta_time)
            self.eye_current_x += (self.eye_target_x - self.eye_current_x) * move_factor
            self.eye_current_y += (self.eye_target_y - self.eye_current_y) * move_factor

        if current_time >= self.next_eye_move_time:
            if self.eye_state == "idle":
                if random.random() < 0.7:
                    self.eye_state = "looking"
                    self.eye_target_x = random.uniform(-0.8, 0.8)
                    self.eye_target_y = random.uniform(-0.4, 0.4)
                    self.eye_dwell_time = random.uniform(0.8, 2.0)
                else:
                    self.eye_target_x = random.uniform(-0.3, 0.3)
                    self.eye_target_y = random.uniform(-0.2, 0.2)
                    self.eye_dwell_time = random.uniform(0.3, 0.8)
                self.next_eye_move_time = current_time + self.eye_dwell_time

            elif self.eye_state == "looking" or self.eye_state == "focusing":
                self.eye_state = "idle"
                self.eye_target_x = random.uniform(-0.2, 0.2)
                self.eye_target_y = random.uniform(-0.1, 0.1)
                self.next_eye_move_time = current_time + random.uniform(0.5, 1.5)

        if current_time >= self.focus_time and self.eye_state != "focusing":
            self.eye_state = "focusing"
            self.eye_target_x = random.uniform(-1.0, 1.0)
            self.eye_target_y = random.uniform(-0.5, 0.5)
            focus_duration = random.uniform(1.5, 3.0)
            self.next_eye_move_time = current_time + focus_duration
            self.focus_time = current_time + random.uniform(5, 10) + focus_duration

        if (
                self.auto_change
                and not self.transitioning
                and current_time - self.last_emotion_change > self.emotion_change_interval
        ):
            possible_emotions = [
                e for e in self.emotions.keys() if e != self.current_emotion
            ]
            if possible_emotions:
                self.target_emotion = random.choice(possible_emotions)
                print(f"Auto changing to: {self.target_emotion}")
                self.transitioning = True
                self.emotion_transition = 0.0
                self.last_emotion_change = current_time
                self.emotion_change_interval = random.uniform(3, 7)

    def draw(self):
        """Clear screen, draw eyes, shared effects (scanning line), and info text."""
        self.screen.fill(BLACK)

        self.draw_eye(self.LEFT_EYE_X, self.EYE_Y, is_left=True)
        self.draw_eye(self.RIGHT_EYE_X, self.EYE_Y, is_left=False)

        current_props = self.get_current_eye_properties()
        effective_emotion = self.target_emotion if self.transitioning else self.current_emotion
        is_scanning_now = self.emotions[effective_emotion].get("scanning", False) and not self.is_blinking

        if is_scanning_now:
            scan_props = self.emotions["scanning"]
            scan_time = time.time() * 2.5
            scan_pos_factor = (math.sin(scan_time) + 1) / 2

            scan_width_factor = scan_props.get("width_factor", 1.2)
            scan_height_factor = scan_props.get("height_factor", 1.4)
            scan_eye_width = self.EYE_WIDTH * scan_width_factor
            scan_eye_height = self.EYE_HEIGHT * scan_height_factor

            leftmost_x = self.LEFT_EYE_X - scan_eye_width / 2
            rightmost_x = self.RIGHT_EYE_X + scan_eye_width / 2
            total_span_width = rightmost_x - leftmost_x

            scan_abs_x = leftmost_x + total_span_width * scan_pos_factor

            top_y = self.EYE_Y - scan_eye_height / 2
            bottom_y = self.EYE_Y + scan_eye_height / 2

            pygame.draw.line(self.screen, WHITE, (scan_abs_x, top_y), (scan_abs_x, bottom_y), 3)

        if self.show_info:
            fps = self.clock.get_fps()
            current_display = self.target_emotion.capitalize() if self.transitioning else self.current_emotion.capitalize()
            transition_perc = int(self.emotion_transition * 100) if self.transitioning else 100
            info_text = f"Emotion: {current_display} ({transition_perc}%) | FPS: {fps:.1f}"
            text_surf = self.font.render(info_text, True, WHITE)
            self.screen.blit(text_surf, (10, 10))

        emotion_text_display = self.target_emotion.capitalize() if self.transitioning else self.current_emotion.capitalize()
        status_text = f"{emotion_text_display}"
        status_surf = self.font.render(status_text, True, WHITE)
        status_rect = status_surf.get_rect(centerx=self.HALF_WIDTH, bottom=self.HEIGHT - 10)
        self.screen.blit(status_surf, status_rect)


    def handle_events(self):
        """Handle user input events (quit, keys)."""
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                sys.exit()
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    pygame.quit()
                    sys.exit()
                elif event.key == pygame.K_f:
                    self.show_info = not self.show_info
                elif event.key == pygame.K_a:
                    self.auto_change = not self.auto_change
                    print(f"Auto Emotion Change: {'ON' if self.auto_change else 'OFF'}")
                    if self.auto_change:
                         self.last_emotion_change = time.time()
                         self.emotion_change_interval = random.uniform(3, 7)
                elif event.key == pygame.K_b:
                    if not self.is_blinking:
                        self.is_blinking = True; self.blink_progress = 0.0

                elif event.key == pygame.K_1: self.set_emotion("neutral")
                elif event.key == pygame.K_2: self.set_emotion("happy")
                elif event.key == pygame.K_3: self.set_emotion("sad")
                elif event.key == pygame.K_4: self.set_emotion("angry")
                elif event.key == pygame.K_5: self.set_emotion("curious")
                elif event.key == pygame.K_6: self.set_emotion("surprised")
                elif event.key == pygame.K_7: self.set_emotion("sleepy")
                elif event.key == pygame.K_8: self.set_emotion("scanning")
                elif event.key == pygame.K_9: self.set_emotion("focused")

    def set_emotion(self, emotion):
        """Start transition to a new target emotion."""
        if emotion in self.emotions and emotion != self.target_emotion:
            if not self.transitioning:
                 self.current_emotion = self.target_emotion
            print(f"Setting emotion to: {emotion}")
            self.target_emotion = emotion
            self.transitioning = True
            self.emotion_transition = 0.0

    def run(self):
        """Main application loop."""
        while True:
            self.handle_events()
            self.update()
            self.draw()
            pygame.display.flip()
            self.clock.tick(60)

if __name__ == "__main__":
    app = FinleyFace()
    app.run()